"""
Domain services for the document templates catalogue (RF-PLA-001).

Every invariant lives here, never in views or serializers (AGENTS.md #8).

Uniqueness is delegated to the database constraint and translated back into a
``DomainError`` by ``unique_violation_as``. Reading first and writing afterwards
would leave a window for two concurrent requests to both pass the check.
"""

import hashlib
import os
import re
import secrets
import uuid
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import models, transaction
from django.db.models import Max
from django.utils import timezone

from apps.audit.services import diff_fields, record_event
from apps.common.db import unique_violation_as
from apps.common.exceptions import AuthorizationError, DomainError
from apps.documents.field_catalog import FIELD_TAG_CODES, FIELD_TAGS
from apps.documents.kind_catalog import DEFAULT_DOCUMENT_KIND_CODE, DEFAULT_DOCUMENT_KINDS
from apps.documents.models import (
    DocumentBatchRun,
    DocumentDeliveryReceipt,
    DocumentDownloadToken,
    DocumentKind,
    DocumentRecord,
    DocumentTemplate,
    DocumentTemplateVersion,
    DocumentVerificationCode,
    OfficialFolio,
)
from apps.enrolments.models import Enrolment, EnrolmentDocumentRequirement
from apps.enrolments.services import pending_required_document_codes
from apps.evaluation.models import Grade
from apps.students.models import StudentGuardianRelation

SENSITIVE_FIELD_TAGS_PERMISSION = "student_view_sensitive"
OFFICIAL_ISSUANCE_PERMISSION = "document_issue"
DOCUMENT_READ_PERMISSION = "document_read"
DOCUMENT_UPLOAD_PERMISSION = "document_upload"
ALLOWED_DOCUMENT_CONTENT_TYPES = {
    "application/pdf": {".pdf"},
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
}


def normalize_document_filename(filename):
    """Return a safe, deterministic, lowercase basename for persisted storage names."""
    original = (filename or "document").strip()
    name = os.path.basename(original)
    stem = Path(name).stem
    suffix = Path(name).suffix.lower()

    normalized_stem = re.sub(r"[^a-z0-9]+", "-", (stem or "document").lower()).strip("-_.")
    if not normalized_stem:
        normalized_stem = "document"

    if suffix in {".pdf", ".jpg", ".jpeg", ".png"}:
        return f"{normalized_stem}{suffix}"

    # The caller must validate the extension before using the output; this keeps the
    # normalization deterministic without inventing a new storage policy.
    return f"{normalized_stem}.pdf"


def validate_document_upload(upload):
    """Validate uploaded documents against the documented file storage rules."""
    if upload is None:
        raise DomainError("Se requiere adjuntar un documento.")

    original_name = getattr(upload, "name", "") or "document"
    content_type = (getattr(upload, "content_type", "") or "").lower()
    payload = upload.read()
    size_bytes = len(payload)
    upload.seek(0)

    if not payload:
        raise DomainError("El documento adjunto esta vacio.")

    suffix = Path(original_name).suffix.lower()
    allowed_suffixes = set().union(*(types for types in ALLOWED_DOCUMENT_CONTENT_TYPES.values()))
    if suffix not in allowed_suffixes:
        raise DomainError("El tipo del documento adjunto no es admitido.")

    resolved_content_type = None
    for mime_type, suffixes in ALLOWED_DOCUMENT_CONTENT_TYPES.items():
        if suffix in suffixes:
            resolved_content_type = mime_type
            break

    if resolved_content_type is None:
        raise DomainError("El tipo del documento adjunto no es admitido.")

    if content_type and content_type not in ALLOWED_DOCUMENT_CONTENT_TYPES:
        raise DomainError("El tipo del documento adjunto no es admitido.")

    max_size = getattr(settings, "DOCUMENT_MAX_UPLOAD_SIZE_BYTES", 10 * 1024 * 1024)
    if size_bytes > max_size:
        raise DomainError(f"El documento adjunto excede el tamano maximo de {max_size} bytes.")

    return {
        "filename": original_name,
        "normalized_filename": normalize_document_filename(original_name),
        "content_type": resolved_content_type,
        "size_bytes": size_bytes,
        "extension": suffix,
    }


@transaction.atomic
def register_scanned_document(
    *,
    student,
    enrolment=None,
    upload=None,
    actor=None,
    source="scanner",
):
    """Register a document captured directly from a scanner or local document peripheral.

    RF-DOC-007 defines a direct digitalization flow into the dossier. The practical
    implementation here focuses on the minimal validated path already supported by
    the document domain: file-type validation, checksum capture, and metadata
    persistence in the student's dossier without inventing a separate storage stack.
    """
    if student is None:
        raise DomainError("Se requiere un estudiante para registrar el documento escaneado.")
    if upload is None:
        raise DomainError("Se requiere adjuntar un documento escaneado.")
    if actor is not None:
        _ensure_document_upload_access(actor=actor, student=student)

    validated = validate_document_upload(upload)
    payload = upload.read()
    checksum = hashlib.sha256(payload).hexdigest()
    upload.seek(0)

    record = _create_document_record(
        student=student,
        enrolment=enrolment,
        payload=payload,
        validated=validated,
        checksum=checksum,
        storage_prefix="scanner",
    )

    _audit(
        actor,
        "documents.scanned_document.registered",
        record,
        source=source,
        content_type=validated["content_type"],
        size_bytes=validated["size_bytes"],
        storage_key=record.storage_key,
    )
    return record


def _ensure_document_upload_access(*, actor, student):
    if not actor or not getattr(actor, "is_authenticated", False):
        raise AuthorizationError("Debe estar autenticado para adjuntar documentos.")
    if actor.is_superuser:
        return True
    allowed = actor.has_scoped_permission(DOCUMENT_UPLOAD_PERMISSION, scope={"student": student})
    if allowed:
        return True
    record_event(
        actor=actor,
        action="documents.document.upload_denied",
        resource="StudentDocument",
        resource_identifier=str(student.pk),
        context={"result": "denied", "reason": "missing_permission_or_scope"},
    )
    raise AuthorizationError("El actor no tiene permiso y alcance para adjuntar documentos.")


def _storage_key(*, student, normalized_filename, prefix="documents"):
    suffix = Path(normalized_filename).suffix
    return f"{prefix}/{student.public_id}/{secrets.token_urlsafe(18)}{suffix}"


def _create_document_record(
    *, student, enrolment, payload, validated, checksum, supersedes=None, storage_prefix="documents"
):
    storage_key = _storage_key(
        student=student,
        normalized_filename=validated["normalized_filename"],
        prefix=storage_prefix,
    )
    saved_key = default_storage.save(storage_key, ContentFile(payload))
    try:
        return DocumentRecord.objects.create(
            student=student,
            enrolment=enrolment,
            filename=validated["filename"],
            storage_key=saved_key,
            content_type=validated["content_type"],
            size_bytes=validated["size_bytes"],
            checksum=checksum,
            status=DocumentRecord.StorageStatus.ACTIVE,
            version_group_id=supersedes.version_group_id if supersedes else uuid.uuid4(),
            version_number=(supersedes.version_number + 1) if supersedes else 1,
            supersedes=supersedes,
        )
    except Exception:
        default_storage.delete(saved_key)
        raise


@transaction.atomic
def upload_document_record(*, actor, student, enrolment=None, upload):
    """Store an attachment outside the database after permission and checksum validation."""
    _ensure_document_upload_access(actor=actor, student=student)
    if enrolment is not None and enrolment.student_id != student.pk:
        raise DomainError("La matricula indicada no pertenece al estudiante del documento.")
    validated = validate_document_upload(upload)
    payload = upload.read()
    upload.seek(0)
    record = _create_document_record(
        student=student,
        enrolment=enrolment,
        payload=payload,
        validated=validated,
        checksum=hashlib.sha256(payload).hexdigest(),
    )
    _audit(actor, "documents.document.uploaded", record, version=record.version_number)
    return record


@transaction.atomic
def replace_document_record(*, actor, record, upload):
    """Create a new immutable attachment version and retain the prior version."""
    record = DocumentRecord.objects.select_for_update().get(pk=record.pk)
    _ensure_document_upload_access(actor=actor, student=record.student)
    if not record.is_active:
        raise DomainError("Solo se puede reemplazar la version vigente del documento.")
    validated = validate_document_upload(upload)
    payload = upload.read()
    upload.seek(0)
    replacement = _create_document_record(
        student=record.student,
        enrolment=record.enrolment,
        payload=payload,
        validated=validated,
        checksum=hashlib.sha256(payload).hexdigest(),
        supersedes=record,
    )
    record.status = DocumentRecord.StorageStatus.ARCHIVED
    record.is_active = False
    record.save(update_fields=["status", "is_active", "updated_at"])
    _audit(
        actor,
        "documents.document.version_created",
        replacement,
        supersedes_id=str(record.public_id),
        version=replacement.version_number,
    )
    return replacement


def normalize_document_kind_code(value, *, field="code"):
    """
    Codes are lower case and hyphen/underscore friendly, never blank.

    Lower case because the codes the API already published ("certificate",
    "report", "other") are lower case, and a catalogue an administrator can now
    type into must not be able to introduce a second "Certificate" that reads
    as the same type but matches nothing.
    """
    code = (value or "").strip().lower()
    if not code:
        raise DomainError(f"Se requiere {field} con contenido.")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", code):
        raise DomainError(
            "El codigo del tipo de documento solo admite minusculas, digitos, guion y guion bajo."
        )
    return code


def ensure_default_document_kinds(*, institution):
    """
    Give an institution the starting catalogue if it has none (RNF-MAN-001).

    Idempotent and additive: an institution that already has rows -- including
    one where every row was deactivated on purpose -- is left alone, so this
    never resurrects a type an administrator retired.
    """
    if DocumentKind.objects.filter(institution=institution).exists():
        return DocumentKind.objects.filter(institution=institution)

    DocumentKind.objects.bulk_create(
        [
            DocumentKind(institution=institution, code=code, label=label)
            for code, label in DEFAULT_DOCUMENT_KINDS
        ]
    )
    return DocumentKind.objects.filter(institution=institution)


def list_document_types(*, institution, include_inactive=False):
    """
    The institution's document-type catalogue as ``(code, label)`` pairs.

    Read from the database, never from a constant: RNF-MAN-001 requires that
    adding or relabelling a document type be an administrative action, not a
    deploy.
    """
    kinds = DocumentKind.objects.filter(institution=institution)
    if not include_inactive:
        kinds = kinds.filter(is_active=True)
    return tuple(kinds.order_by("label").values_list("code", "label"))


def resolve_document_kind(*, institution, code, allow_inactive=False):
    """Resolve a catalogue row by code, or explain which codes exist."""
    normalized = str(code or "").strip().lower()
    kinds = DocumentKind.objects.filter(institution=institution, code=normalized)
    if not allow_inactive:
        kinds = kinds.filter(is_active=True)
    kind = kinds.first()
    if kind is None:
        available = ", ".join(
            sorted(code for code, _label in list_document_types(institution=institution))
        )
        configured = available or "ninguno"
        raise DomainError(
            f"Tipo de documento no admitido: '{code}'. Tipos configurados: {configured}."
        )
    return kind


def _document_kind_conflicts(code):
    return {
        "unique_document_kind_code_per_institution": (
            f"Ya existe un tipo de documento con el codigo '{code}' en esta institucion."
        ),
    }


@transaction.atomic
def create_document_kind(*, institution, code, label, description="", actor=None, is_active=True):
    """Register a document type in the institutional catalogue (RNF-MAN-001)."""
    code = normalize_document_kind_code(code)
    label = _clean_name(label, field="label")

    with unique_violation_as(_document_kind_conflicts(code)):
        kind = DocumentKind.objects.create(
            institution=institution,
            code=code,
            label=label,
            description=(description or "").strip(),
            is_active=is_active,
        )

    _audit(actor, "documents.kind.created", kind, code=code, label=label)
    return kind


@transaction.atomic
def update_document_kind(*, kind, label=None, description=None, actor=None):
    """
    Relabel a document type. The code is immutable, like every other catalogue
    code in the repo: templates and the immutable version snapshots already
    reference it.
    """
    if label is not None:
        label = _clean_name(label, field="label")
    if description is not None:
        description = description.strip()

    return _changed(
        kind,
        actor,
        "documents.kind.updated",
        label=label,
        description=description,
    )


@transaction.atomic
def deactivate_document_kind(*, kind, actor=None):
    """
    Retire a document type without deleting it (ADR-0006). Idempotent.

    A type still referenced by an active template stays: deactivating it would
    leave that template pointing at a type no longer offered, and the issuance
    path resolves templates by type.
    """
    if not kind.is_active:
        return kind

    if kind.templates.filter(is_active=True).exists():
        raise DomainError(
            "No se puede desactivar un tipo de documento con plantillas activas; "
            "desactive primero las plantillas."
        )

    kind.is_active = False
    kind.save(update_fields=["is_active", "updated_at"])
    _audit(actor, "documents.kind.deactivated", kind)
    return kind


def get_active_document_template(*, institution, kind):
    """Resolve the single active template for a given institutional document kind."""
    document_kind = resolve_document_kind(institution=institution, code=kind)
    normalized_kind = document_kind.code

    templates = DocumentTemplate.objects.filter(
        institution=institution,
        document_kind=document_kind,
        is_active=True,
    ).order_by("created_at")
    if templates.count() != 1:
        raise DomainError(
            f"Se requiere exactamente una plantilla activa para el tipo de documento "
            f"'{normalized_kind}'; se encontraron {templates.count()}."
        )
    return templates.get()


def ensure_document_access(*, actor, student=None, document=None, access_type="read"):
    """Guard and audit every document read or download from one boundary."""
    target_student = student or getattr(document, "student", None)
    resource_identifier = str(getattr(document, "pk", "") or getattr(target_student, "pk", ""))
    context = {
        "result": "success",
        "access_type": access_type,
        "student_id": str(getattr(target_student, "pk", "")),
    }
    if document is not None:
        context["document_id"] = str(document.pk)

    if target_student is None:
        record_event(
            actor=actor,
            action="documents.document.read_denied",
            resource="DocumentRecord",
            resource_identifier=resource_identifier,
            context={"result": "denied", "access_type": access_type, "reason": "missing_student"},
        )
        raise AuthorizationError("El acceso a documentos requiere un estudiante como destino.")

    if not actor or not getattr(actor, "is_authenticated", False):
        record_event(
            actor=actor,
            action="documents.document.read_denied",
            resource="DocumentRecord",
            resource_identifier=resource_identifier,
            context={**context, "result": "denied", "reason": "unauthenticated"},
        )
        raise AuthorizationError("Debe estar autenticado para leer documentos.")

    if actor.is_superuser:
        record_event(
            actor=actor,
            action="documents.document.read",
            resource="DocumentRecord",
            resource_identifier=resource_identifier,
            context=context,
        )
        return True

    if not actor.has_atomic_permission(DOCUMENT_READ_PERMISSION):
        record_event(
            actor=actor,
            action="documents.document.read_denied",
            resource="DocumentRecord",
            resource_identifier=resource_identifier,
            context={**context, "result": "denied", "reason": "missing_permission"},
        )
        raise AuthorizationError("El actor no tiene permiso para leer documentos.")

    if not actor.has_scoped_permission(DOCUMENT_READ_PERMISSION, scope={"student": target_student}):
        record_event(
            actor=actor,
            action="documents.document.read_denied",
            resource="DocumentRecord",
            resource_identifier=resource_identifier,
            context={**context, "result": "denied", "reason": "missing_scope"},
        )
        raise AuthorizationError("El actor no tiene el alcance requerido para leer documentos.")

    record_event(
        actor=actor,
        action="documents.document.read",
        resource="DocumentRecord",
        resource_identifier=resource_identifier,
        context=context,
    )
    return True


def issue_document_download_token(*, actor, document):
    """Issue a brief signed document download token."""
    ensure_document_access(actor=actor, document=document, access_type="download")
    raw_token = secrets.token_urlsafe(24)
    expires_at = timezone.now() + timedelta(minutes=5)
    token = DocumentDownloadToken.objects.create(
        document=document,
        created_by=actor,
        token_hash=hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
        expires_at=expires_at,
    )
    token.token = raw_token
    return token


def register_document_delivery_receipt(
    *,
    actor=None,
    student=None,
    guardian=None,
    document_type="",
    folio="",
    recipient_name="",
    delivered_at=None,
    notes="",
):
    """Persist the acknowledgement that a printed document was received by a guardian."""
    if student is None:
        raise DomainError("Se requiere un estudiante para registrar la entrega del documento.")
    if guardian is None:
        raise DomainError("Se requiere un encargado para registrar la entrega del documento.")

    document_label = str(document_type or "").strip()
    if not document_label:
        raise DomainError("Se requiere el tipo de documento entregado.")

    if not StudentGuardianRelation.objects.filter(
        student=student, guardian=guardian, ends_at__isnull=True
    ).exists():
        raise DomainError("El encargado no tiene una relacion activa con el estudiante.")

    receipt = DocumentDeliveryReceipt.objects.create(
        student=student,
        guardian=guardian,
        document_type=document_label,
        folio=str(folio or "").strip(),
        recipient_name=str(recipient_name or "").strip(),
        delivered_at=delivered_at or timezone.now(),
        notes=str(notes or "").strip(),
    )

    record_event(
        actor=actor,
        action="documents.delivery.receipt.created",
        resource="DocumentDeliveryReceipt",
        resource_identifier=str(receipt.pk),
        context={
            "student_id": student.pk,
            "guardian_id": guardian.pk,
            "document_type": document_label,
            "folio": receipt.folio,
            "recipient_name": receipt.recipient_name,
            "delivered_at": receipt.delivered_at.isoformat(),
            "result": "success",
        },
    )
    return receipt


def validate_document_download_token(*, document, token, actor=None):
    """Validate and reject expired, invalid, or actor-mismatched download tokens."""
    if not token:
        raise DomainError("Se requiere un token de descarga valido.")
    if actor is not None and not getattr(actor, "is_authenticated", False):
        raise AuthorizationError("Debe estar autenticado para descargar un documento.")

    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    try:
        download_token = DocumentDownloadToken.objects.get(document=document, token_hash=digest)
    except DocumentDownloadToken.DoesNotExist as exc:
        raise DomainError("El token de descarga proporcionado no es valido.") from exc

    if not download_token.is_valid:
        raise DomainError("El token de descarga proporcionado no es valido o vencio.")

    if actor is not None and download_token.created_by_id != actor.pk:
        raise DomainError("El token de descarga no corresponde al actor autenticado.")

    download_token.used_at = timezone.now()
    download_token.save(update_fields=["used_at", "updated_at"])
    return True


def list_field_tags(*, actor=None, include_sensitive=False):
    """
    Fixed, predefined catalogue of dynamic tags templates may reference
    (RF-PLA-002). Sensitive/confidential tags are excluded by default
    (RF-PLA-003); including them requires ``student.view_sensitive``.
    """
    if not include_sensitive:
        return tuple(tag for tag in FIELD_TAGS if not tag[2])

    is_authorized = bool(
        actor
        and (actor.is_superuser or actor.has_atomic_permission(SENSITIVE_FIELD_TAGS_PERMISSION))
    )
    if not is_authorized:
        record_event(
            actor=actor,
            action="documents.field_tag_catalog.sensitive_read_denied",
            resource="FieldTag",
            context={"result": "denied", "reason": "missing_permission"},
        )
        raise AuthorizationError("El actor no tiene permiso para ver etiquetas de campo sensibles.")

    record_event(
        actor=actor,
        action="documents.field_tag_catalog.sensitive_read",
        resource="FieldTag",
        context={"result": "success"},
    )
    return FIELD_TAGS


def record_document_read_audit(
    *,
    actor,
    subject=None,
    resource=None,
    action="documents.document.read",
    context=None,
):
    """Audits a document read when the caller is allowed to access confidential dossier data."""
    subject_label = resource or type(subject).__name__ if subject is not None else "Document"
    resource_identifier = (
        str(subject.pk) if subject is not None and getattr(subject, "pk", None) is not None else ""
    )
    is_authorized = bool(
        actor and (actor.is_superuser or actor.has_atomic_permission(DOCUMENT_READ_PERMISSION))
    )
    if not is_authorized:
        record_event(
            actor=actor,
            action="documents.document.read_denied",
            resource=subject_label,
            resource_identifier=resource_identifier,
            context={"result": "denied", "reason": "missing_permission", **(context or {})},
        )
        raise AuthorizationError("El actor no tiene permiso para leer documentos.")

    record_event(
        actor=actor,
        action=action,
        resource=subject_label,
        resource_identifier=resource_identifier,
        context={"result": "success", **(context or {})},
    )
    return True


def student_document_dossier(*, student):
    """Return a consolidated view of the student's history, requirements and document records."""
    enrolments = list(
        Enrolment.objects.filter(student=student)
        .select_related("student", "academic_cycle", "grade", "section")
        .order_by("-effective_on", "-created_at", "-pk")
    )
    requirements = list(
        EnrolmentDocumentRequirement.objects.filter(enrolment__student=student)
        .select_related("enrolment")
        .order_by("-enrolment__effective_on", "code")
    )
    documents = list(
        DocumentRecord.objects.filter(student=student)
        .select_related("student", "enrolment")
        .order_by("-created_at", "-pk")
    )
    return {
        "student_id": str(student.public_id),
        "enrolments": [
            {
                "enrolment_id": str(enrolment.public_id),
                "status": enrolment.status,
                "is_active": enrolment.is_active,
                "academic_cycle_id": str(enrolment.academic_cycle.public_id),
                "grade_id": str(enrolment.grade.public_id),
                "section_id": str(enrolment.section.public_id),
                "effective_on": enrolment.effective_on.isoformat(),
                "ends_on": enrolment.ends_on.isoformat() if enrolment.ends_on else None,
            }
            for enrolment in enrolments
        ],
        "requirements": [
            {
                "enrolment_id": str(requirement.enrolment.public_id),
                "code": requirement.code,
                "name": requirement.name,
                "status": requirement.status,
                "is_required": requirement.is_required,
                "is_active": requirement.is_active,
            }
            for requirement in requirements
        ],
        "documents": [
            {
                "document_id": str(document.public_id),
                "enrolment_id": str(document.enrolment.public_id) if document.enrolment else None,
                "filename": document.filename,
                "storage_key": document.storage_key,
                "content_type": document.content_type,
                "size_bytes": document.size_bytes,
                "checksum": document.checksum,
                "status": document.status,
                "is_active": document.is_active,
                "created_at": document.created_at.isoformat(),
            }
            for document in documents
        ],
    }


def _clean_code(value, *, field="code"):
    code = (value or "").strip().upper()
    if not code:
        raise DomainError(f"Se requiere {field} con contenido.")
    return code


def _clean_name(value, *, field="name"):
    name = (value or "").strip()
    if not name:
        raise DomainError(f"Se requiere {field} con contenido.")
    return name


def _audit(actor, action, instance, *, changes=None, **context):
    record_event(
        actor=actor,
        action=action,
        resource=type(instance).__name__,
        resource_identifier=str(instance.pk),
        context=context,
        changes=changes,
    )


def _record_document_issue(*, actor, student=None, document_type="", issued_at=None, folio=""):
    """
    Persist issuing metadata in the audit trail for official or historical
    documents, and mint the public verification code for RF-EMI-009. The
    code is random and unique (``DocumentVerificationCode.code``), never
    derived from the folio's sequential counter, so a public lookup cannot
    enumerate issued documents.
    """
    verification_code = secrets.token_urlsafe(24)
    DocumentVerificationCode.objects.create(
        code=verification_code,
        document_type=str(document_type or ""),
        folio=str(folio or ""),
        issued_at=str(issued_at) if issued_at is not None else "",
    )

    payload = {
        "document_type": str(document_type or ""),
        "issued_at": str(issued_at) if issued_at is not None else "",
        "folio": str(folio or ""),
        "verification_code": verification_code,
        "result": "success",
    }
    if student is not None:
        payload["student_id"] = getattr(student, "pk", student)
    record_event(
        actor=actor,
        action="documents.document.issued",
        resource="Document",
        resource_identifier=str(getattr(student, "pk", "") or ""),
        context=payload,
    )
    return verification_code


def _changed(instance, actor, action, **candidates):
    """
    Apply the fields whose value was actually supplied, persist only those, and
    audit what changed -- including before/after values (RF-BIT-002). ``None``
    means "not supplied", never "set to null".
    """
    fields = [name for name, value in candidates.items() if value is not None]
    changes = diff_fields(instance, **candidates)  # read before mutating
    for name in fields:
        setattr(instance, name, candidates[name])

    instance.save(update_fields=[*fields, "updated_at"])
    _audit(actor, action, instance, changes=changes, fields=fields)
    return instance


def _document_template_conflicts(code):
    return {
        "unique_document_template_code_per_institution": (
            f"Document template code '{code}' already exists for this institution."
        ),
        "unique_active_document_template_per_kind_per_institution": (
            "An active document template already exists for this institution and document type."
        ),
    }


def _version_conflicts():
    return {
        "unique_document_template_version_sequence": ("Concurrent update detected; retry."),
    }


def _record_version(template):
    """Append an immutable content snapshot (RF-PLA-005)."""
    next_sequence = (template.versions.aggregate(Max("sequence"))["sequence__max"] or 0) + 1
    with unique_violation_as(_version_conflicts()):
        DocumentTemplateVersion.objects.create(
            template=template,
            sequence=next_sequence,
            name=template.name,
            kind=template.document_kind.code,
            description=template.description,
            content=template.content,
        )


@transaction.atomic
def create_document_template(
    *,
    institution,
    name,
    code,
    kind=DEFAULT_DOCUMENT_KIND_CODE,
    description="",
    content="",
    actor=None,
    is_active=True,
):
    """
    Register a document template.

    The code is normalised to upper case and unique per institution, including
    inactive templates, so history stays readable (same rule as campus codes,
    ADR-0006).
    """
    name = _clean_name(name)
    code = _clean_code(code)
    content = (content or "").strip()
    document_kind = resolve_document_kind(institution=institution, code=kind)

    with unique_violation_as(_document_template_conflicts(code)):
        template = DocumentTemplate.objects.create(
            institution=institution,
            name=name,
            code=code,
            document_kind=document_kind,
            description=(description or "").strip(),
            content=content,
            is_active=is_active,
        )

    _audit(actor, "documents.template.created", template, code=code, kind=document_kind.code)
    _record_version(template)
    return template


@transaction.atomic
def update_document_template(
    *, template, name=None, description=None, kind=None, content=None, actor=None
):
    """
    Update the descriptive attributes of a document template. The code is
    immutable. Any explicitly supplied field records a new version
    (RF-PLA-005); a call with nothing to change does not.
    """
    if name is not None:
        name = _clean_name(name)
    if description is not None:
        description = description.strip()
    if content is not None:
        content = content.strip()
    document_kind = (
        resolve_document_kind(institution=template.institution, code=kind)
        if kind is not None
        else None
    )

    with unique_violation_as(_document_template_conflicts(template.code)):
        updated = _changed(
            template,
            actor,
            "documents.template.updated",
            name=name,
            description=description,
            document_kind=document_kind,
            content=content,
        )

    if any(value is not None for value in (name, description, kind, content)):
        _record_version(updated)

    return updated


@transaction.atomic
def deactivate_document_template(*, template, actor=None):
    """Deactivate a document template instead of deleting it. Idempotent."""
    if not template.is_active:
        return template

    template.is_active = False
    template.save(update_fields=["is_active", "updated_at"])
    _audit(actor, "documents.template.deactivated", template)
    return template


def deactivate_document_record(*, record, actor=None):
    """Retain the document record for history without hard deletion."""
    if not record.is_active:
        return record

    record.is_active = False
    record.status = DocumentRecord.StorageStatus.RETAINED
    record.save(update_fields=["is_active", "status", "updated_at"])
    _audit(actor, "documents.record.deactivated", record, storage_status=record.status)
    return record


def storage_consumption_summary(*, actor):
    """RF-ARC-005: auditable total of persisted attachment storage.

    The summary exposes both raw totals and the operational capacity signal
    required by RNF-CAP-002 without inventing a new storage subsystem.
    """
    if not actor or not getattr(actor, "is_authenticated", False):
        raise AuthorizationError("Debe estar autenticado para consultar el almacenamiento.")

    queryset = DocumentRecord.objects.all()
    summary = queryset.aggregate(
        total_bytes=models.Sum("size_bytes"),
        file_count=models.Count("pk"),
        retained_count=models.Count(
            "pk", filter=models.Q(status=DocumentRecord.StorageStatus.RETAINED)
        ),
    )
    total_bytes = int(summary["total_bytes"] or 0)
    projected_growth_bytes = getattr(
        settings, "DOCUMENT_STORAGE_GROWTH_PER_CYCLE_BYTES", 2 * 1024**3
    )
    warning_threshold_bytes = getattr(
        settings,
        "DOCUMENT_STORAGE_WARNING_THRESHOLD_BYTES",
        projected_growth_bytes,
    )
    warning_active = total_bytes >= warning_threshold_bytes
    threshold_utilization_ratio = (
        (total_bytes / warning_threshold_bytes) if warning_threshold_bytes else 0
    )
    result = {
        "total_bytes": total_bytes,
        "file_count": summary["file_count"] or 0,
        "retained_count": summary["retained_count"] or 0,
        "projected_growth_bytes_per_cycle": int(projected_growth_bytes),
        "projected_total_bytes": int(total_bytes + projected_growth_bytes),
        "warning_threshold_bytes": int(warning_threshold_bytes),
        "warning_active": warning_active,
        "warning_level": "warning" if warning_active else "ok",
        "threshold_utilization_ratio": float(threshold_utilization_ratio),
        "threshold_utilization_percent": float(threshold_utilization_ratio * 100),
        "by_content_type": list(
            queryset.values("content_type").annotate(
                count=models.Count("id"), size=models.Sum("size_bytes")
            )
        ),
    }
    record_event(
        actor=actor,
        action="documents.storage_consumption.read",
        resource="DocumentRecord",
        context={"result": "success", **result},
    )
    return result


def issue_official_document_folio(*, institution, document_type="", issued_at=None):
    """Allocate the next institutional sequential folio for an official document."""
    if institution is None:
        raise DomainError("Se requiere una institucion para emitir el folio de un documento.")

    issued_at = issued_at or timezone.now()
    year = issued_at.year
    latest = (
        OfficialFolio.objects.filter(institution=institution, year=year)
        .order_by("-sequence")
        .values_list("sequence", flat=True)
        .first()
    )
    sequence = (latest or 0) + 1
    folio = OfficialFolio.objects.create(
        institution=institution,
        year=year,
        sequence=sequence,
        document_type=(document_type or "").strip(),
        issued_at=issued_at,
    )
    return folio.folio_code


def _pdf_text(value, *, limit):
    """
    Escape a string for a PDF literal.

    ``(``, ``)`` and ``\\`` end or shift the literal, so a name with a
    parenthesis in it would produce a file no reader can open. Truncation
    happens after escaping so it cannot cut an escape sequence in half.
    """
    escaped = str(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return escaped.encode("utf-8")[:limit]


def preview_document_template(*, template, payload=None, actor=None):
    """Render a template preview using only the closed field-tag catalogue.

    This keeps the preview deterministic and safe: only whitelisted markers are
    allowed and the dataset is bounded to a closed, static catalog instead of
    arbitrary template evaluation.
    """
    if template is None:
        raise DomainError("Se requiere una plantilla para generar la vista previa.")

    template_content = str(getattr(template, "content", "") or "")
    mapping = dict(payload or {})
    markers = re.findall(r"{{\s*([A-Za-z0-9_.-]+)\s*}}", template_content)
    for marker in markers:
        if marker not in FIELD_TAG_CODES:
            raise DomainError(
                f"El marcador '{marker}' no esta permitido dentro del catalogo cerrado de "
                "etiquetas de plantilla."
            )

    rendered = template_content
    for marker in markers:
        rendered = rendered.replace(f"{{{{{marker}}}}}", str(mapping.get(marker, "")))

    _audit(
        actor,
        "documents.template.previewed",
        template,
        marker_count=len(markers),
        markers=markers,
    )

    return {
        "content": rendered,
        "markers": markers,
        "marker_count": len(markers),
    }


def validate_document_checksum(*, document, payload):
    """Verify a document payload against the stored checksum metadata."""
    if document is None:
        raise DomainError("Se requiere un registro de documento para validar la integridad.")
    if payload is None:
        raise DomainError("Se requiere el contenido del documento para validar la integridad.")

    expected = document.checksum.strip()
    actual = hashlib.sha256(payload).hexdigest()
    if expected != actual:
        raise DomainError("El checksum del documento no coincide con el contenido almacenado.")
    return True


def verify_stored_document_checksum(*, actor, document):
    """Read stored bytes and prove their checksum still matches immutable metadata."""
    ensure_document_access(actor=actor, document=document)
    try:
        with default_storage.open(document.storage_key, "rb") as stored_file:
            payload = stored_file.read()
    except OSError as exc:
        raise DomainError("El contenido almacenado del documento no esta disponible.") from exc
    validate_document_checksum(document=document, payload=payload)
    _audit(actor, "documents.document.integrity_verified", document, result="success")
    return True


def verify_document_storage_integrity(*, actor=None, institution=None):
    """Audit the persisted document store for missing or corrupted files.

    This is the smallest operational implementation of RNF-RES-003: a single
    admin-facing integrity scan over the stored document metadata, without
    introducing a background worker or broader storage subsystem.
    """
    if actor is not None:
        if not getattr(actor, "is_authenticated", False):
            raise AuthorizationError(
                "Debe estar autenticado para verificar la integridad del archivo."
            )
        if not actor.is_superuser and not actor.has_atomic_permission(DOCUMENT_READ_PERMISSION):
            raise AuthorizationError(
                "El actor no tiene permiso para verificar la integridad del archivo."
            )

    queryset = DocumentRecord.objects.all()
    if institution is not None:
        queryset = queryset.filter(student__enrolments__academic_cycle__institution=institution)

    issues = []
    ok = 0
    corrupted = 0
    unreadable = 0
    missing = 0

    for record in queryset.select_related("student").order_by("-created_at"):
        storage_key = record.storage_key
        if not default_storage.exists(storage_key):
            missing += 1
            issues.append(
                {
                    "document_id": str(record.public_id),
                    "student_id": str(record.student.public_id),
                    "storage_key": storage_key,
                    "status": "missing",
                    "message": "El archivo persistido no existe en almacenamiento.",
                }
            )
            continue

        try:
            with default_storage.open(storage_key, "rb") as stored_file:
                payload = stored_file.read()
        except OSError:
            unreadable += 1
            issues.append(
                {
                    "document_id": str(record.public_id),
                    "student_id": str(record.student.public_id),
                    "storage_key": storage_key,
                    "status": "unreadable",
                    "message": "El archivo persistido no puede leerse.",
                }
            )
            continue

        actual_checksum = hashlib.sha256(payload).hexdigest()
        if actual_checksum != record.checksum:
            corrupted += 1
            issues.append(
                {
                    "document_id": str(record.public_id),
                    "student_id": str(record.student.public_id),
                    "storage_key": storage_key,
                    "status": "corrupted",
                    "expected_checksum": record.checksum,
                    "observed_checksum": actual_checksum,
                    "message": "El archivo persistido no coincide con su checksum registrado.",
                }
            )
            continue

        ok += 1

    result = {
        "total_checked": ok + corrupted + unreadable + missing,
        "ok": ok,
        "corrupted": corrupted,
        "unreadable": unreadable,
        "missing": missing,
        "by_status": {
            "ok": ok,
            "corrupted": corrupted,
            "unreadable": unreadable,
            "missing": missing,
        },
        "issues": issues,
    }
    record_event(
        actor=actor,
        action="documents.storage.integrity_checked",
        resource="DocumentRecord",
        context={
            "result": "success",
            "total_checked": result["total_checked"],
            "ok": ok,
            "corrupted": corrupted,
            "unreadable": unreadable,
            "missing": missing,
        },
    )
    return result


def document_storage_usage_summary(*, institution=None):
    """Summarize stored document usage from metadata only, without direct file access.

    RNF-CAP-002 requires a cycle-growth estimate and a warning threshold so the
    storage policy can be tuned without inventing a separate persistence model.
    """
    queryset = DocumentRecord.objects.all()
    if institution is not None:
        scoped_queryset = queryset.filter(
            student__enrolments__academic_cycle__institution=institution
        )
        if scoped_queryset.exists():
            queryset = scoped_queryset.distinct()

    total_files = queryset.count()
    total_size_bytes = queryset.aggregate(total_size=models.Sum("size_bytes"))["total_size"] or 0
    projected_growth_bytes = getattr(
        settings, "DOCUMENT_STORAGE_GROWTH_PER_CYCLE_BYTES", 2 * 1024**3
    )
    warning_threshold_bytes = getattr(
        settings,
        "DOCUMENT_STORAGE_WARNING_THRESHOLD_BYTES",
        projected_growth_bytes,
    )
    warning_active = total_size_bytes >= warning_threshold_bytes
    warning_level = "warning" if warning_active else "ok"
    threshold_utilization_ratio = (
        (total_size_bytes / warning_threshold_bytes) if warning_threshold_bytes else 0
    )
    threshold_utilization_percent = threshold_utilization_ratio * 100

    return {
        "total_files": total_files,
        "total_size_bytes": int(total_size_bytes),
        "projected_growth_bytes_per_cycle": int(projected_growth_bytes),
        "projected_total_bytes": int(total_size_bytes + projected_growth_bytes),
        "warning_threshold_bytes": int(warning_threshold_bytes),
        "warning_active": warning_active,
        "warning_level": warning_level,
        "threshold_utilization_ratio": float(threshold_utilization_ratio),
        "threshold_utilization_percent": float(threshold_utilization_percent),
        "by_content_type": list(
            queryset.values("content_type").annotate(
                count=models.Count("id"), size=models.Sum("size_bytes")
            )
        ),
    }


def compile_generated_document(*, template, payload=None, persist=False, actor=None):
    """Compile a document in memory and never store generated PDFs on disk.

    RF-DOC-008 requires that generated reports and certificates remain ephemeral:
    they are assembled on demand and not persisted as a stored file record.
    """
    if persist:
        raise DomainError(
            "Los documentos generados se componen en memoria y no deben persistirse en "
            "almacenamiento."
        )

    data = payload or {}
    student_name = str(data.get("student_name") or "Documento")
    document_type = str(data.get("document_type") or getattr(template, "name", "Documento"))
    title = f"{document_type}: {student_name}"
    issued_at = data.get("issued_at") or timezone.now().isoformat()
    folio = data.get("folio") or ""
    student = data.get("student")

    _audit(
        actor,
        "documents.generated_document.compiled",
        template,
        document_type=getattr(template, "kind", "other"),
        persisted=False,
        issued_at=str(issued_at),
        folio=folio,
    )
    verification_code = _record_document_issue(
        actor=actor,
        student=student,
        document_type=document_type,
        issued_at=issued_at,
        folio=folio,
    )

    metadata_line = f"Emitido: {issued_at}"
    if folio:
        metadata_line = f"{metadata_line} | Folio: {folio}"
    verification_line = f"Codigo de verificacion: {verification_code}"
    # El pie de emision se DIBUJA: se construia y se descartaba, asi que el folio
    # no aparecia en el documento que alguien firma o archiva — el numero que
    # hace rastreable una certificacion vivia solo en la bitacora.
    stream = (
        b"BT /F1 12 Tf 30 120 Td ("
        + _pdf_text(title, limit=80)
        + b") Tj ET\n"
        + b"BT /F1 9 Tf 30 90 Td ("
        + _pdf_text(metadata_line, limit=120)
        + b") Tj ET\n"
        + b"BT /F1 8 Tf 30 75 Td ("
        + _pdf_text(verification_line, limit=140)
        + b") Tj ET\n"
    )
    rendered = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        b"4 0 obj\n<< /Length "
        + str(len(stream)).encode("ascii")
        + b" >>\nstream\n"
        + stream
        + b"endstream\nendobj\n"
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        b"xref\n0 6\n0000000000 65535 f\n0000000010 00000 n\n0000000060 00000 n\n"
        b"0000000125 00000 n\n0000000267 00000 n\n0000000780 00000 n\ntrailer\n"
        b"<< /Root 1 0 R /Size 6 >>\nstartxref\n870\n%%EOF"
    )

    generated = type(
        "GeneratedDocument",
        (),
        {
            "content": rendered,
            "content_type": "application/pdf",
            "storage_key": None,
            "persisted": False,
            "issued_at": str(issued_at),
            "folio": folio,
            "verification_code": verification_code,
        },
    )()
    return generated


def compile_document_batch(
    *,
    section=None,
    grade=None,
    academic_cycle=None,
    document_type="Boleta",
    issued_at=None,
    actor=None,
    client_batch_id=None,
):
    """Compile a block of in-memory report cards for a whole section or grade.

    The generator is intentionally ephemeral: it returns PDF bytes in memory and
    never creates a persisted DocumentRecord or mutates any historical academic
    state. This is the minimal batch path required by RF-EMI-006 while keeping
    the data model and audit trail consistent with the rest of the document domain.

    ``client_batch_id`` makes a retry idempotent: a caller who resends the same
    id after a network failure gets the recorded outcome back (count only, no
    regenerated PDFs) instead of the batch running -- and being audited -- a
    second time. Ampliacion a pedido del usuario; RF-EMI-006 no la exige.
    """
    if section is None and grade is None:
        raise DomainError("Se requiere una seccion o un grado para generar el lote de documentos.")

    if client_batch_id:
        existing = DocumentBatchRun.objects.filter(client_batch_id=client_batch_id).first()
        if existing is not None:
            return {"count": existing.enrolment_count, "documents": [], "replayed": True}

    queryset = Enrolment.objects.select_related("student", "academic_cycle", "grade", "section")
    if section is not None:
        queryset = queryset.filter(section=section)
    if grade is not None:
        queryset = queryset.filter(grade=grade)
    if academic_cycle is not None:
        queryset = queryset.filter(academic_cycle=academic_cycle)

    documents = []
    for enrolment in queryset.order_by("section__name", "pk"):
        generated = compile_historical_cycle_report(
            enrolment=enrolment,
            issued_at=issued_at,
            actor=actor,
        )
        documents.append(
            {
                "enrolment_id": str(enrolment.public_id),
                "student_name": str(enrolment.student),
                "document_type": document_type,
                "content": generated.content,
                "content_type": generated.content_type,
                "storage_key": generated.storage_key,
                "persisted": generated.persisted,
                "issued_at": generated.issued_at,
                "folio": generated.folio,
            }
        )

    if client_batch_id:
        try:
            with unique_violation_as({"unique_document_batch_run_client_batch_id": "replayed"}):
                DocumentBatchRun.objects.create(
                    client_batch_id=client_batch_id,
                    document_type=document_type,
                    enrolment_count=len(documents),
                )
        except DomainError:
            # Lost the race to a concurrent identical request: that request's
            # audit event already covers this batch, so this one must not add
            # a second. Return its recorded outcome instead.
            existing = DocumentBatchRun.objects.get(client_batch_id=client_batch_id)
            return {"count": existing.enrolment_count, "documents": [], "replayed": True}

    _audit(
        actor,
        "documents.document_batch.compiled",
        section or grade or enrolment,
        count=len(documents),
        document_type=document_type,
        scope="section" if section is not None else "grade",
    )

    return {"count": len(documents), "documents": documents}


_SUBJECT_CONDITION_LABELS = {
    "approved": "Aprobado",
    "approved_by_recovery": "Aprobado por recuperacion",
    "failed": "Reprobado",
}


def _subject_condition_label(condition):
    return _SUBJECT_CONDITION_LABELS.get(condition or None, "Sin calificar")


def compile_historical_cycle_report(*, enrolment, issued_at=None, actor=None):
    """
    Compile a transient report card for a closed academic cycle (RF-RES-008),
    without altering history.

    Reads the FROZEN result of each subarea and the frozen promotion outcome
    (RF-RES-007, ``apps.academics.{FrozenSubjectResult,FrozenPromotionResult}``)
    whenever any exist for this enrolment, so the values printed here are
    guaranteed to be the exact ones the system used to decide each condition
    -- they can never drift from what ``get_final_subject_grade``/
    ``determine_promotion`` computed at close time, even if evaluation
    config or academic structure changes afterward (this is the whole point
    of freezing, RF-RES-007 Escenario 1). Crucially, the set of subareas
    printed also comes from the frozen rows, not from a fresh
    ``curriculum_subjects`` read: deactivating a ``CurriculumPlan`` entry
    after close must not make its subarea silently vanish from an already
    -issued boleta. Falls back to a live recomputation over the current
    curriculum plan only when NO frozen row exists at all for this enrolment
    -- a cycle closed before this freeze existed: still correct, just
    without the "never recalculates" guarantee a properly frozen cycle gets.

    Cross-domain read (documented exception, same style as RF-RES-006/007):
    domain-map.md does not list school-cycle/institutional-structure as a
    document-generation dependency, but the frozen tables live in
    ``apps.academics`` per issue #261's own placement; this calls its public
    ``queries`` module, not its internal tables.

    Public contract note (AGENTS.md #3): this changes what was previously
    rendered. The prior version iterated ``Grade`` rows directly and
    repeated a subarea's line once per registered unit (a bug: a 3-unit
    subarea printed its final grade three times), with no per-unit
    breakdown, no condition, and no promotion. Callers
    (``compile_document_batch``, the API view) keep the same return shape;
    only the rendered content grows.
    """
    if enrolment is None:
        raise DomainError("Se requiere una matricula para generar la boleta de calificaciones.")

    enrolment.refresh_from_db(fields=["academic_cycle"])
    cycle = enrolment.academic_cycle
    if not getattr(cycle, "is_closed", False):
        raise DomainError("La boleta solo puede generarse para un ciclo cerrado.")

    from apps.academics import queries as academics_queries
    from apps.enrolments.services import determine_promotion
    from apps.evaluation import queries as evaluation_queries
    from apps.evaluation.services import get_final_subject_grade

    issued_at = issued_at or timezone.now().isoformat()

    # Version mas reciente de cada subarea congelada, si el ciclo llego a
    # congelarse (RF-RES-007). Meta.ordering de FrozenSubjectResult ya trae
    # -created_at, -pk primero, asi que la primera fila vista por subject_id
    # es siempre la vigente.
    frozen_by_subject = {}
    for row in academics_queries.frozen_subject_results_for_enrolment(enrolment=enrolment):
        frozen_by_subject.setdefault(row.subject_id, row)
    frozen_rows = sorted(frozen_by_subject.values(), key=lambda row: row.subject.name)

    if frozen_rows:
        subjects = [row.subject for row in frozen_rows]
    else:
        subjects = list(evaluation_queries.curriculum_subjects(cycle, enrolment.grade))

    _audit(
        actor,
        "documents.historical_cycle_report.compiled",
        enrolment,
        cycle_id=str(cycle.public_id),
        persisted=False,
        issued_at=str(issued_at),
        subject_count=len(subjects),
    )
    verification_code = _record_document_issue(
        actor=actor,
        student=enrolment.student,
        document_type="Boleta",
        issued_at=issued_at,
        folio="",
    )

    lines = [
        "Boleta de calificaciones",
        f"Estudiante: {enrolment.student}",
        f"Ciclo: {cycle.name} ({cycle.starts_on} - {cycle.ends_on})",
    ]
    if subjects:
        for subject in subjects:
            lines.append(f"Subarea: {subject.name}")
            unit_grades = (
                Grade.objects.filter(enrolment=enrolment, subject=subject)
                .select_related("evaluation_unit")
                .order_by("evaluation_unit__number")
            )
            for grade in unit_grades:
                lines.append(f"  Unidad {grade.evaluation_unit.number}: {grade.value}")

            frozen = frozen_by_subject.get(subject.pk)
            if frozen is not None:
                final_grade, condition = frozen.final_grade, frozen.condition or None
            else:
                summary = get_final_subject_grade(enrolment, subject)
                final_grade, condition = summary["final_grade"], summary["condition"]
            grade_label = final_grade if final_grade is not None else "NC"
            lines.append(f"  Nota final: {grade_label} ({_subject_condition_label(condition)})")
    else:
        lines.append("- Sin calificaciones registradas.")

    frozen_promotion = academics_queries.latest_frozen_promotion_result(enrolment=enrolment)
    promoted = (
        frozen_promotion.promoted
        if frozen_promotion is not None
        else determine_promotion(enrolment)["promoted"]
    )
    lines.append(f"Condicion de promocion: {'Promovido' if promoted else 'No promovido'}")
    lines.append(f"Codigo de verificacion: {verification_code}")

    stream = b""
    for index, line in enumerate(lines):
        y_position = 180 - (index * 15)
        stream += b"BT /F1 10 Tf 30 " + str(y_position).encode("ascii") + b" Td ("
        stream += _pdf_text(line, limit=140)
        stream += b") Tj ET\n"

    rendered = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 420 220] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        b"4 0 obj\n<< /Length "
        + str(len(stream)).encode("ascii")
        + b" >>\nstream\n"
        + stream
        + b"endstream\nendobj\n"
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        b"xref\n0 6\n0000000000 65535 f\n0000000010 00000 n\n0000000060 00000 n\n"
        b"0000000125 00000 n\n0000000267 00000 n\n0000000780 00000 n\ntrailer\n"
        b"<< /Root 1 0 R /Size 6 >>\nstartxref\n870\n%%EOF"
    )

    generated = type(
        "GeneratedDocument",
        (),
        {
            "content": rendered,
            "content_type": "application/pdf",
            "storage_key": None,
            "persisted": False,
            "issued_at": str(issued_at),
            "folio": "",
            "verification_code": verification_code,
        },
    )()
    return generated


def verify_document(*, code):
    """
    Public, unauthenticated lookup for RF-EMI-009: confirms whether a code
    printed on an emitted document is genuine. Deliberately returns only
    ``document_type``/``issued_at`` on a match and ``{"valid": False}``
    otherwise -- never a distinct "malformed" vs "not found" answer, and
    never who the document was for, so the response cannot be used to
    enumerate or identify students.
    """
    if not code:
        return {"valid": False}

    record = DocumentVerificationCode.objects.filter(code=code).first()
    if record is None:
        return {"valid": False}

    return {
        "valid": True,
        "document_type": record.document_type,
        "folio": record.folio,
        "issued_at": record.issued_at,
        "vigencia": "vigente" if record.is_active else "revocada",
    }


def ensure_official_document_issuance_permission(*, actor):
    """
    Authorization gate for the official document issuance decision (RF-MAT-006).
    Denied attempts are audited, like the sensitive field tag catalogue.
    """
    is_authorized = bool(
        actor and (actor.is_superuser or actor.has_atomic_permission(OFFICIAL_ISSUANCE_PERMISSION))
    )
    if not is_authorized:
        record_event(
            actor=actor,
            action="documents.official_issuance.denied",
            resource="OfficialDocumentIssuance",
            context={"result": "denied", "reason": "missing_permission"},
        )
        raise AuthorizationError("El actor no tiene permiso para emitir documentos oficiales.")

    return True


def evaluate_official_document_issuance(*, enrolment, actor=None):
    """
    Official issuance is allowed only when the enrolment is administratively
    solvent and all required documents are delivered. The list preserves the
    existing document-code convention while also surfacing the state check from
    RF-EMI-004.
    """
    blocking_codes = []

    if enrolment is None:
        blocking_codes.append("ENROLMENT_REQUIRED")
    else:
        if getattr(enrolment, "status", None) != Enrolment.EnrolmentStatus.ACTIVE:
            blocking_codes.append("ENROLMENT_NOT_ACTIVE")

        student = getattr(enrolment, "student", None)
        if student is not None and getattr(student, "status", None) != student.StudentStatus.ACTIVE:
            blocking_codes.append("STUDENT_NOT_ACTIVE")

        blocking_codes.extend(pending_required_document_codes(enrolment=enrolment))

    blocking_codes = list(dict.fromkeys(blocking_codes))
    if blocking_codes:
        _audit(
            actor,
            "documents.official_issuance.blocked",
            enrolment,
            pending_document_codes=blocking_codes,
        )
    else:
        _audit(actor, "documents.official_issuance.allowed", enrolment)

    return blocking_codes


def ensure_official_document_issuance_allowed(*, enrolment, actor=None):
    """Guard for issuance callers: raise when the enrolment is not eligible."""
    blocking_codes = evaluate_official_document_issuance(enrolment=enrolment, actor=actor)
    if blocking_codes:
        raise DomainError(
            "La emision del documento oficial esta bloqueada por documentos obligatorios "
            f"pendientes: {', '.join(blocking_codes)}."
        )

    return True
