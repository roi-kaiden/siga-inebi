import hashlib
from datetime import date, timedelta

import pytest
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from apps.academics.models import CurriculumPlan
from apps.academics.services import close_academic_cycle
from apps.audit.models import AuditEvent
from apps.documents.field_catalog import FIELD_TAG_CODES
from apps.documents.models import DocumentDownloadToken, DocumentRecord, DocumentTemplate
from apps.documents.services import (
    compile_generated_document,
    issue_document_download_token,
)
from apps.enrolments.services import create_enrolment, set_document_requirement
from apps.evaluation.services import (
    close_evaluation_unit,
    create_evaluation_unit,
    register_unit_grade,
)
from tests.factories.academic import InstitutionFactory, SectionFactory, SubjectFactory
from tests.factories.documents import DocumentTemplateFactory, DocumentTemplateVersionFactory
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
    UserFactory,
)
from tests.factories.people import PersonFactory
from tests.factories.students import GuardianFactory, StudentFactory, StudentGuardianRelationFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]

MISSING_UUID = "00000000-0000-0000-0000-000000000000"


def _detail(response):
    return response.json()["error"]["detail"]


def _items(response):
    return response.json()["results"]


# --------------------------------------------------------------------------- #
# authentication
# --------------------------------------------------------------------------- #


@pytest.mark.security
@pytest.mark.parametrize(
    ("method", "url_name", "kwargs"),
    [
        ("get", "document-template-list-create", {}),
        ("get", "document-field-tag-list", {}),
        ("get", "document-type-list-create", {}),
        ("get", "document-storage-consumption", {}),
        ("get", "document-official-issuance-eligibility", {}),
        ("get", "document-historical-cycle-report", {}),
        ("get", "document-template-detail", {"public_id": MISSING_UUID}),
        ("get", "document-template-version-list", {"public_id": MISSING_UUID}),
        ("post", "document-template-preview", {"public_id": MISSING_UUID}),
        ("post", "document-record-upload", {}),
        ("post", "document-record-scan", {}),
        ("post", "document-record-version-create", {"public_id": MISSING_UUID}),
        ("get", "document-record-download", {"public_id": MISSING_UUID}),
        ("post", "document-record-integrity-verify", {"public_id": MISSING_UUID}),
        ("get", "enrolment-document-record-list", {"enrolment_id": MISSING_UUID}),
        ("get", "document-type-detail", {"public_id": MISSING_UUID}),
        ("post", "document-delivery-receipt-create", {}),
        ("post", "document-batch-compile", {}),
    ],
)
def test_document_endpoints_require_authentication(client, method, url_name, kwargs):
    response = getattr(client, method)(reverse(url_name, kwargs=kwargs))

    assert response.status_code in (401, 403)


# --------------------------------------------------------------------------- #
# create / list
# --------------------------------------------------------------------------- #


def test_create_document_template_returns_201_with_public_id(admin_client, institution):
    response = admin_client.post(
        reverse("document-template-list-create"),
        {"name": "Constancia de estudios", "code": "const", "kind": "certificate"},
        content_type="application/json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["code"] == "CONST"
    assert body["kind"] == "certificate"
    assert "public_id" in body
    assert DocumentTemplate.objects.filter(institution=institution, code="CONST").exists()


def test_document_template_response_includes_institutional_header(auth_client, institution):
    template = DocumentTemplateFactory(institution=institution)

    response = auth_client.get(reverse("document-template-detail", args=[template.public_id]))

    assert response.status_code == 200
    header = response.json()["header"]
    assert header["institution_name"] == institution.name
    assert header["institution_short_name"] == institution.short_name
    assert header["logo_url"] is None


@override_settings(
    DOCUMENT_STORAGE_GROWTH_PER_CYCLE_BYTES=200,
    DOCUMENT_STORAGE_WARNING_THRESHOLD_BYTES=50,
)
def test_storage_consumption_endpoint_reports_operational_capacity_warning(auth_client):
    student = StudentFactory()
    DocumentRecord.objects.create(
        student=student,
        filename="heavy.pdf",
        storage_key="local/heavy.pdf",
        content_type="application/pdf",
        size_bytes=60,
        checksum="heavy",
    )

    response = auth_client.get(reverse("document-storage-consumption"))

    assert response.status_code == 200
    body = response.json()
    assert body["total_bytes"] == 60
    assert body["projected_growth_bytes_per_cycle"] == 200
    assert body["projected_total_bytes"] == 260
    assert body["warning_threshold_bytes"] == 50
    assert body["warning_active"] is True
    assert body["warning_level"] == "warning"
    assert body["threshold_utilization_ratio"] == 1.2
    assert body["threshold_utilization_percent"] == 120.0
    assert body["by_content_type"]


def test_document_delivery_receipt_can_be_created(auth_client):
    student = StudentFactory()
    guardian = GuardianFactory()
    StudentGuardianRelationFactory(student=student, guardian=guardian, is_primary=True)

    response = auth_client.post(
        reverse("document-delivery-receipt-create"),
        {
            "student_id": str(student.public_id),
            "guardian_id": str(guardian.public_id),
            "document_type": "Certificado",
            "recipient_name": "Ana López",
            "folio": "DOC-2026-0001",
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["document_type"] == "Certificado"
    assert body["student_id"] == str(student.public_id)
    assert body["guardian_id"] == str(guardian.public_id)


def test_secure_document_download_uses_signed_token_and_serves_the_file(client):
    user = UserFactory()
    permission = PermissionFactory(codename="document_read")
    assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    student = StudentFactory()
    ScopeGrantFactory(assignment=assignment, student=student)
    payload = b"secure content"
    document = DocumentRecord.objects.create(
        student=student,
        filename="secure-document.pdf",
        storage_key="local/secure-document.pdf",
        content_type="application/pdf",
        size_bytes=len(payload),
        checksum=__import__("hashlib").sha256(payload).hexdigest(),
    )
    default_storage.save(document.storage_key, ContentFile(payload))

    client.force_login(user)
    token = issue_document_download_token(actor=user, document=document)

    response = client.get(
        reverse("document-record-download", args=[document.public_id]),
        {"token": token.token},
    )

    assert response.status_code == 200
    assert response.content == payload
    assert 'attachment; filename="secure-document.pdf"' in response.headers["Content-Disposition"]


@pytest.mark.security
def test_document_download_rejects_missing_token(client):
    user = UserFactory()
    permission = PermissionFactory(codename="document_read")
    assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    student = StudentFactory()
    ScopeGrantFactory(assignment=assignment, student=student)
    payload = b"content"
    document = DocumentRecord.objects.create(
        student=student,
        filename="doc.pdf",
        storage_key="local/doc.pdf",
        content_type="application/pdf",
        size_bytes=len(payload),
        checksum=hashlib.sha256(payload).hexdigest(),
    )
    default_storage.save(document.storage_key, ContentFile(payload))

    client.force_login(user)
    response = client.get(reverse("document-record-download", args=[document.public_id]))

    assert response.status_code == 400
    assert "token" in _detail(response).lower()


@pytest.mark.security
def test_document_download_rejects_invalid_token(client):
    user = UserFactory()
    permission = PermissionFactory(codename="document_read")
    assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    student = StudentFactory()
    ScopeGrantFactory(assignment=assignment, student=student)
    payload = b"content"
    document = DocumentRecord.objects.create(
        student=student,
        filename="doc.pdf",
        storage_key="local/doc.pdf",
        content_type="application/pdf",
        size_bytes=len(payload),
        checksum=hashlib.sha256(payload).hexdigest(),
    )
    default_storage.save(document.storage_key, ContentFile(payload))

    client.force_login(user)
    response = client.get(
        reverse("document-record-download", args=[document.public_id]),
        {"token": "tampered-token-value"},
    )

    assert response.status_code == 400
    assert "no es valido" in _detail(response).lower()


@pytest.mark.security
def test_document_download_rejects_expired_token(client):
    user = UserFactory()
    permission = PermissionFactory(codename="document_read")
    assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    student = StudentFactory()
    ScopeGrantFactory(assignment=assignment, student=student)
    payload = b"content"
    document = DocumentRecord.objects.create(
        student=student,
        filename="doc.pdf",
        storage_key="local/doc.pdf",
        content_type="application/pdf",
        size_bytes=len(payload),
        checksum=hashlib.sha256(payload).hexdigest(),
    )
    default_storage.save(document.storage_key, ContentFile(payload))

    client.force_login(user)
    token = issue_document_download_token(actor=user, document=document)
    DocumentDownloadToken.objects.filter(pk=token.pk).update(
        expires_at=timezone.now() - timedelta(minutes=10)
    )

    response = client.get(
        reverse("document-record-download", args=[document.public_id]),
        {"token": token.token},
    )

    assert response.status_code == 400
    assert "vencio" in _detail(response).lower()


@pytest.mark.security
def test_document_download_rejects_token_of_another_user(client):
    user_a = UserFactory()
    user_b = UserFactory()
    student = StudentFactory()
    permission = PermissionFactory(codename="document_read")
    for u in (user_a, user_b):
        a = RoleAssignmentFactory(user=u, role=RoleFactory(permissions=[permission]))
        ScopeGrantFactory(assignment=a, student=student)
    payload = b"content"
    document = DocumentRecord.objects.create(
        student=student,
        filename="doc.pdf",
        storage_key="local/doc.pdf",
        content_type="application/pdf",
        size_bytes=len(payload),
        checksum=hashlib.sha256(payload).hexdigest(),
    )
    default_storage.save(document.storage_key, ContentFile(payload))

    token = issue_document_download_token(actor=user_a, document=document)

    client.force_login(user_b)
    response = client.get(
        reverse("document-record-download", args=[document.public_id]),
        {"token": token.token},
    )

    assert response.status_code == 400
    assert "no corresponde" in _detail(response).lower()


@pytest.mark.security
def test_document_download_token_is_single_use(client):
    user = UserFactory()
    permission = PermissionFactory(codename="document_read")
    assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    student = StudentFactory()
    ScopeGrantFactory(assignment=assignment, student=student)
    payload = b"content"
    document = DocumentRecord.objects.create(
        student=student,
        filename="doc.pdf",
        storage_key="local/doc.pdf",
        content_type="application/pdf",
        size_bytes=len(payload),
        checksum=hashlib.sha256(payload).hexdigest(),
    )
    default_storage.save(document.storage_key, ContentFile(payload))

    client.force_login(user)
    token = issue_document_download_token(actor=user, document=document)

    first = client.get(
        reverse("document-record-download", args=[document.public_id]),
        {"token": token.token},
    )
    assert first.status_code == 200

    second = client.get(
        reverse("document-record-download", args=[document.public_id]),
        {"token": token.token},
    )
    assert second.status_code == 400
    assert "no es valido o vencio" in _detail(second).lower()


def test_document_record_integrity_verify_success(client):
    user = UserFactory()
    permission = PermissionFactory(codename="document_read")
    assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    student = StudentFactory()
    ScopeGrantFactory(assignment=assignment, student=student)
    payload = b"payload to verify"
    checksum = hashlib.sha256(payload).hexdigest()
    document = DocumentRecord.objects.create(
        student=student,
        filename="archivo.pdf",
        storage_key=f"documents/{student.public_id}/archivo.pdf",
        content_type="application/pdf",
        size_bytes=len(payload),
        checksum=checksum,
    )
    default_storage.save(document.storage_key, ContentFile(payload))

    client.force_login(user)
    response = client.post(reverse("document-record-integrity-verify", args=[document.public_id]))

    assert response.status_code == 204
    assert AuditEvent.objects.filter(
        action="documents.document.integrity_verified",
        actor=user,
        resource_identifier=str(document.pk),
    ).exists()


def test_document_record_integrity_verify_detects_corrupted_payload(client):
    user = UserFactory()
    permission = PermissionFactory(codename="document_read")
    assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    student = StudentFactory()
    ScopeGrantFactory(assignment=assignment, student=student)
    payload = b"genuine payload"
    checksum = hashlib.sha256(payload).hexdigest()
    document = DocumentRecord.objects.create(
        student=student,
        filename="archivo.pdf",
        storage_key=f"documents/{student.public_id}/corrupted.pdf",
        content_type="application/pdf",
        size_bytes=len(payload),
        checksum=checksum,
    )
    default_storage.save(document.storage_key, ContentFile(b"tampered payload"))

    client.force_login(user)
    response = client.post(reverse("document-record-integrity-verify", args=[document.public_id]))

    assert response.status_code == 400
    assert "checksum" in _detail(response).lower()


def test_document_record_integrity_verify_requires_scoped_permission(client):
    user = UserFactory()
    student = StudentFactory()
    payload = b"some payload"
    document = DocumentRecord.objects.create(
        student=student,
        filename="archivo.pdf",
        storage_key=f"documents/{student.public_id}/unauthorized.pdf",
        content_type="application/pdf",
        size_bytes=len(payload),
        checksum=hashlib.sha256(payload).hexdigest(),
    )
    default_storage.save(document.storage_key, ContentFile(payload))

    client.force_login(user)
    response = client.post(reverse("document-record-integrity-verify", args=[document.public_id]))

    assert response.status_code == 403


def test_document_record_integrity_verify_returns_404_for_unknown_record(client):
    user = UserFactory(is_superuser=True)
    client.force_login(user)
    response = client.post(reverse("document-record-integrity-verify", args=[MISSING_UUID]))

    assert response.status_code == 404


def test_document_record_upload_success_and_audited(client):
    user = UserFactory()
    permission = PermissionFactory(codename="document_upload")
    assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    student = StudentFactory()
    ScopeGrantFactory(assignment=assignment, student=student)

    file_content = b"%PDF-1.4 official document content"
    uploaded = SimpleUploadedFile("partida.pdf", file_content, content_type="application/pdf")

    client.force_login(user)
    response = client.post(
        reverse("document-record-upload"),
        {"student_id": str(student.public_id), "file": uploaded},
        format="multipart",
    )

    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "partida.pdf"
    assert data["version_number"] == 1
    assert data["status"] == "active"
    assert data["checksum"] == hashlib.sha256(file_content).hexdigest()

    record = DocumentRecord.objects.get(public_id=data["public_id"])
    assert AuditEvent.objects.filter(
        action="documents.document.uploaded",
        actor=user,
        resource_identifier=str(record.pk),
    ).exists()


def test_document_record_upload_rejects_disallowed_content_type(client):
    user = UserFactory()
    permission = PermissionFactory(codename="document_upload")
    assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    student = StudentFactory()
    ScopeGrantFactory(assignment=assignment, student=student)

    uploaded = SimpleUploadedFile(
        "script.exe", b"binary content", content_type="application/x-msdownload"
    )

    client.force_login(user)
    response = client.post(
        reverse("document-record-upload"),
        {"student_id": str(student.public_id), "file": uploaded},
        format="multipart",
    )

    assert response.status_code == 400
    assert "no es admitido" in _detail(response).lower()


@override_settings(DOCUMENT_MAX_UPLOAD_SIZE_BYTES=100)
def test_document_record_upload_rejects_oversized_file(client):
    user = UserFactory()
    permission = PermissionFactory(codename="document_upload")
    assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    student = StudentFactory()
    ScopeGrantFactory(assignment=assignment, student=student)

    uploaded = SimpleUploadedFile("large.pdf", b"x" * 200, content_type="application/pdf")

    client.force_login(user)
    response = client.post(
        reverse("document-record-upload"),
        {"student_id": str(student.public_id), "file": uploaded},
        format="multipart",
    )

    assert response.status_code == 400
    assert "excede el tamano maximo" in _detail(response).lower()


def test_document_record_upload_requires_scoped_permission(client):
    user = UserFactory()
    student = StudentFactory()

    uploaded = SimpleUploadedFile("partida.pdf", b"%PDF-1.4 test", content_type="application/pdf")

    client.force_login(user)
    response = client.post(
        reverse("document-record-upload"),
        {"student_id": str(student.public_id), "file": uploaded},
        format="multipart",
    )

    assert response.status_code == 403


def test_scanned_document_upload_success_and_audited(client):
    user = UserFactory()
    permission = PermissionFactory(codename="document_upload")
    assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    student = StudentFactory()
    ScopeGrantFactory(assignment=assignment, student=student)

    file_content = b"%PDF-1.4 scanned document"
    uploaded = SimpleUploadedFile("scan_doc.pdf", file_content, content_type="application/pdf")

    client.force_login(user)
    response = client.post(
        reverse("document-record-scan"),
        {"student_id": str(student.public_id), "file": uploaded},
        format="multipart",
    )

    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "scan_doc.pdf"
    assert data["status"] == "active"
    record = DocumentRecord.objects.get(public_id=data["public_id"])
    assert AuditEvent.objects.filter(
        action="documents.scanned_document.registered",
        actor=user,
        resource_identifier=str(record.pk),
    ).exists()


def test_scanned_document_upload_requires_scoped_permission(client):
    user = UserFactory()
    student = StudentFactory()

    uploaded = SimpleUploadedFile("scan.pdf", b"%PDF-1.4 scan", content_type="application/pdf")

    client.force_login(user)
    response = client.post(
        reverse("document-record-scan"),
        {"student_id": str(student.public_id), "file": uploaded},
        format="multipart",
    )

    assert response.status_code == 403


def test_document_record_version_create_replaces_active_version_and_preserves_history(client):
    user = UserFactory()
    permission = PermissionFactory(codename="document_upload")
    assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    student = StudentFactory()
    ScopeGrantFactory(assignment=assignment, student=student)

    v1_payload = b"%PDF-1.4 version 1 content"
    record_v1 = DocumentRecord.objects.create(
        student=student,
        filename="expediente.pdf",
        storage_key=f"documents/{student.public_id}/v1.pdf",
        content_type="application/pdf",
        size_bytes=len(v1_payload),
        checksum=hashlib.sha256(v1_payload).hexdigest(),
        status=DocumentRecord.StorageStatus.ACTIVE,
        version_number=1,
    )
    default_storage.save(record_v1.storage_key, ContentFile(v1_payload))

    v2_payload = b"%PDF-1.4 version 2 content"
    replacement_file = SimpleUploadedFile(
        "expediente_v2.pdf", v2_payload, content_type="application/pdf"
    )

    client.force_login(user)
    response = client.post(
        reverse("document-record-version-create", args=[record_v1.public_id]),
        {"file": replacement_file},
        format="multipart",
    )

    assert response.status_code == 201
    data = response.json()
    assert data["version_number"] == 2
    assert data["status"] == "active"

    record_v1.refresh_from_db()
    assert record_v1.status == DocumentRecord.StorageStatus.ARCHIVED
    assert record_v1.is_active is False

    assert DocumentRecord.objects.filter(pk=record_v1.pk).exists()
    assert DocumentRecord.objects.filter(public_id=data["public_id"]).exists()
    assert AuditEvent.objects.filter(
        action="documents.document.version_created",
        actor=user,
    ).exists()


def test_document_record_version_create_requires_scoped_permission(client):
    user = UserFactory()
    student = StudentFactory()
    payload = b"%PDF-1.4 content"
    record = DocumentRecord.objects.create(
        student=student,
        filename="expediente.pdf",
        storage_key=f"documents/{student.public_id}/v1.pdf",
        content_type="application/pdf",
        size_bytes=len(payload),
        checksum=hashlib.sha256(payload).hexdigest(),
        status=DocumentRecord.StorageStatus.ACTIVE,
    )
    default_storage.save(record.storage_key, ContentFile(payload))

    replacement = SimpleUploadedFile("exp_new.pdf", b"%PDF-1.4 v2", content_type="application/pdf")
    client.force_login(user)
    response = client.post(
        reverse("document-record-version-create", args=[record.public_id]),
        {"file": replacement},
        format="multipart",
    )

    assert response.status_code == 403


def test_enrolment_document_record_list_returns_records(client):
    user = UserFactory()
    permission = PermissionFactory(codename="document_read")
    assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    student = StudentFactory()
    ScopeGrantFactory(assignment=assignment, student=student)
    enrolment = _enrolment()
    enrolment.student = student
    enrolment.save()

    payload = b"%PDF-1.4 doc"
    doc = DocumentRecord.objects.create(
        student=student,
        enrolment=enrolment,
        filename="boleta.pdf",
        storage_key=f"documents/{student.public_id}/b.pdf",
        content_type="application/pdf",
        size_bytes=len(payload),
        checksum=hashlib.sha256(payload).hexdigest(),
    )
    default_storage.save(doc.storage_key, ContentFile(payload))

    client.force_login(user)
    response = client.get(reverse("enrolment-document-record-list", args=[enrolment.public_id]))

    assert response.status_code == 200
    items = _items(response)
    assert len(items) == 1
    assert items[0]["filename"] == "boleta.pdf"


def test_enrolment_document_record_list_requires_scoped_permission(client):
    user = UserFactory()
    enrolment = _enrolment()

    client.force_login(user)
    response = client.get(reverse("enrolment-document-record-list", args=[enrolment.public_id]))

    assert response.status_code == 403


def test_document_template_header_ignores_submitted_value_on_create(admin_client, institution):
    response = admin_client.post(
        reverse("document-template-list-create"),
        {
            "name": "Constancia",
            "code": "CONST",
            "header": {"institution_name": "Suplantado", "logo_url": "http://evil.example/x.png"},
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["header"]["institution_name"] == institution.name


def test_document_template_header_ignores_submitted_value_on_update(admin_client, institution):
    template = DocumentTemplateFactory(institution=institution)

    response = admin_client.patch(
        reverse("document-template-detail", args=[template.public_id]),
        {"header": {"institution_name": "Suplantado"}},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["header"]["institution_name"] == institution.name


def test_create_document_template_rejects_duplicate_code_with_400(admin_client, institution):
    DocumentTemplateFactory(institution=institution, code="CONST")

    response = admin_client.post(
        reverse("document-template-list-create"),
        {"name": "Otra", "code": "CONST"},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "already" in str(_detail(response))


def test_create_document_template_rejects_missing_code_with_field_error(admin_client, institution):
    response = admin_client.post(
        reverse("document-template-list-create"),
        {"name": "Sin codigo"},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "code" in _detail(response)


def test_list_document_templates_only_returns_current_institution(auth_client, institution):
    DocumentTemplateFactory(institution=institution, code="CONST")
    DocumentTemplateFactory(code="OTHER")  # another institution

    response = auth_client.get(reverse("document-template-list-create"))

    assert response.status_code == 200
    codes = [item["code"] for item in _items(response)]
    assert codes == ["CONST"]


def test_list_document_templates_hides_inactive_by_default_and_shows_them_on_request(
    auth_client, institution
):
    DocumentTemplateFactory(institution=institution, code="ACTIVE")
    DocumentTemplateFactory(institution=institution, code="INACTIVE", is_active=False)

    default = auth_client.get(reverse("document-template-list-create"))
    included = auth_client.get(
        reverse("document-template-list-create"), {"include_inactive": "true"}
    )

    assert [item["code"] for item in _items(default)] == ["ACTIVE"]
    assert sorted(item["code"] for item in _items(included)) == ["ACTIVE", "INACTIVE"]


# --------------------------------------------------------------------------- #
# detail / update / deactivate
# --------------------------------------------------------------------------- #


def test_document_template_detail_returns_404_for_unknown_public_id(auth_client, institution):
    response = auth_client.get(reverse("document-template-detail", args=[MISSING_UUID]))

    assert response.status_code == 404


def test_document_template_detail_returns_404_for_another_institution(auth_client, institution):
    foreign = DocumentTemplateFactory()  # different institution

    response = auth_client.get(reverse("document-template-detail", args=[foreign.public_id]))

    assert response.status_code == 404


def test_patch_document_template_updates_name(admin_client, institution):
    template = DocumentTemplateFactory(institution=institution, name="Old")

    response = admin_client.patch(
        reverse("document-template-detail", args=[template.public_id]),
        {"name": "New"},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["name"] == "New"


def test_patch_document_template_does_not_accept_code(admin_client, institution):
    template = DocumentTemplateFactory(institution=institution, code="ORIGINAL")

    response = admin_client.patch(
        reverse("document-template-detail", args=[template.public_id]),
        {"code": "CHANGED"},
        content_type="application/json",
    )

    assert response.status_code == 200
    template.refresh_from_db()
    assert template.code == "ORIGINAL"


def test_delete_document_template_deactivates_instead_of_deleting(admin_client, institution):
    template = DocumentTemplateFactory(institution=institution)

    response = admin_client.delete(reverse("document-template-detail", args=[template.public_id]))

    assert response.status_code == 204
    template.refresh_from_db()
    assert template.is_active is False
    assert DocumentTemplate.objects.filter(pk=template.pk).exists()


# --------------------------------------------------------------------------- #
# versions (RF-PLA-005)
# --------------------------------------------------------------------------- #


@pytest.mark.security
def test_document_template_versions_endpoint_requires_authentication(client, institution):
    template = DocumentTemplateFactory(institution=institution)

    response = client.get(reverse("document-template-version-list", args=[template.public_id]))

    assert response.status_code in (401, 403)


def test_create_document_template_creates_its_first_version(admin_client, institution):
    create_response = admin_client.post(
        reverse("document-template-list-create"),
        {"name": "Constancia", "code": "CONST"},
        content_type="application/json",
    )
    public_id = create_response.json()["public_id"]

    response = admin_client.get(reverse("document-template-version-list", args=[public_id]))

    assert response.status_code == 200
    items = _items(response)
    assert len(items) == 1
    assert items[0]["sequence"] == 1
    assert items[0]["name"] == "Constancia"


def test_update_document_template_adds_a_new_version_most_recent_first(admin_client, institution):
    template = DocumentTemplateFactory(institution=institution, name="Old")
    DocumentTemplateVersionFactory(template=template, sequence=1, name="Old")

    admin_client.patch(
        reverse("document-template-detail", args=[template.public_id]),
        {"name": "New"},
        content_type="application/json",
    )

    response = admin_client.get(
        reverse("document-template-version-list", args=[template.public_id])
    )

    sequences = [item["sequence"] for item in _items(response)]
    assert sequences == [2, 1]


def test_document_template_versions_returns_404_for_another_institution(auth_client, institution):
    foreign = DocumentTemplateFactory()  # different institution

    response = auth_client.get(reverse("document-template-version-list", args=[foreign.public_id]))

    assert response.status_code == 404


def test_document_template_preview_is_ephemeral_and_uses_sample_payload(auth_client, institution):
    template = DocumentTemplateFactory(
        institution=institution,
        content="Constancia para {{student.full_name}} de {{institution.name}}",
    )

    response = auth_client.post(
        reverse("document-template-preview", args=[template.public_id]),
        {"payload": {"student.full_name": "Ana", "institution.name": "INEBI"}},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["content"] == "Constancia para Ana de INEBI"
    template.refresh_from_db()
    assert template.content == "Constancia para {{student.full_name}} de {{institution.name}}"


def test_document_upload_requires_permission_and_scope(auth_client):
    student = StudentFactory()
    upload = SimpleUploadedFile("respaldo.pdf", b"pdf content", content_type="application/pdf")

    denied = auth_client.post(
        reverse("document-record-upload"),
        {"student_id": str(student.public_id), "file": upload},
    )
    assert denied.status_code == 403

    permission = PermissionFactory(codename="document_upload")
    assignment = RoleAssignmentFactory(
        user=auth_client.user, role=RoleFactory(permissions=[permission])
    )
    ScopeGrantFactory(assignment=assignment, student=student)
    accepted = auth_client.post(
        reverse("document-record-upload"),
        {
            "student_id": str(student.public_id),
            "file": SimpleUploadedFile(
                "respaldo.pdf", b"pdf content", content_type="application/pdf"
            ),
        },
    )

    assert accepted.status_code == 201
    assert accepted.json()["version_number"] == 1


# --------------------------------------------------------------------------- #
# field tags
# --------------------------------------------------------------------------- #


def test_list_field_tags_returns_the_fixed_catalogue(auth_client):
    response = auth_client.get(reverse("document-field-tag-list"))

    assert response.status_code == 200
    codes = {item["code"] for item in _items(response)}
    assert codes == set(FIELD_TAG_CODES)
    assert all(item["sensitive"] is False for item in _items(response))


def test_list_document_types_returns_the_institution_catalogue(auth_client):
    InstitutionFactory()

    response = auth_client.get(reverse("document-type-list-create"))

    assert response.status_code == 200
    assert [(item["code"], item["label"]) for item in _items(response)] == [
        ("certificate", "Certificado"),
        ("other", "Otro"),
        ("report", "Reporte"),
    ]


def test_document_type_is_created_updated_and_deactivated_over_the_api(admin_client):
    """RNF-MAN-001: the whole lifecycle of a document type is an API call."""
    InstitutionFactory()

    created = admin_client.post(
        reverse("document-type-list-create"),
        {"code": "Constancia", "label": "Constancia"},
        content_type="application/json",
    )

    assert created.status_code == 201
    assert created.json()["code"] == "constancia"
    public_id = created.json()["public_id"]

    updated = admin_client.patch(
        reverse("document-type-detail", args=[public_id]),
        {"label": "Constancia de estudios"},
        content_type="application/json",
    )

    assert updated.status_code == 200
    assert updated.json()["label"] == "Constancia de estudios"

    template = admin_client.post(
        reverse("document-template-list-create"),
        {"name": "Constancia", "code": "CONST", "kind": "constancia"},
        content_type="application/json",
    )

    assert template.status_code == 201
    assert template.json()["kind"] == "constancia"

    blocked = admin_client.delete(reverse("document-type-detail", args=[public_id]))

    assert blocked.status_code == 400

    admin_client.delete(reverse("document-template-detail", args=[template.json()["public_id"]]))
    removed = admin_client.delete(reverse("document-type-detail", args=[public_id]))

    assert removed.status_code == 204
    assert "constancia" not in {
        item["code"] for item in _items(admin_client.get(reverse("document-type-list-create")))
    }


def test_creating_a_template_with_an_unknown_type_is_rejected(admin_client):
    InstitutionFactory()

    response = admin_client.post(
        reverse("document-template-list-create"),
        {"name": "Constancia", "code": "CONST", "kind": "inexistente"},
        content_type="application/json",
    )

    assert response.status_code == 400


def _grant_document_issue(user):
    permission = PermissionFactory(codename="document_issue")
    return RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))


def _enrolment():
    section = SectionFactory()
    return create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )


def _eligibility(client, enrolment_id):
    return client.get(
        reverse("document-official-issuance-eligibility"), {"enrolment_id": str(enrolment_id)}
    )


def test_official_document_eligibility_allows_complete_enrolment(auth_client):
    enrolment = _enrolment()
    _grant_document_issue(auth_client.user)

    response = _eligibility(auth_client, enrolment.public_id)

    assert response.status_code == 200
    assert response.json() == {"eligible": True, "blocking_document_codes": []}


def test_official_document_eligibility_reports_pending_documents(auth_client):
    enrolment = _enrolment()
    set_document_requirement(enrolment=enrolment, code="BIRTH-CERT", name="Birth certificate")
    _grant_document_issue(auth_client.user)

    response = _eligibility(auth_client, enrolment.public_id)

    assert response.status_code == 200
    assert response.json() == {"eligible": False, "blocking_document_codes": ["BIRTH-CERT"]}
    assert AuditEvent.objects.filter(action="documents.official_issuance.blocked").exists()


def test_official_document_eligibility_returns_404_for_unknown_enrolment(auth_client):
    _grant_document_issue(auth_client.user)

    response = _eligibility(auth_client, MISSING_UUID)

    assert response.status_code == 404


@pytest.mark.security
def test_official_document_eligibility_requires_issue_permission(auth_client):
    enrolment = _enrolment()

    response = _eligibility(auth_client, enrolment.public_id)

    assert response.status_code == 403
    assert AuditEvent.objects.filter(action="documents.official_issuance.denied").exists()


def _historical_cycle_report(client, enrolment_id):
    return client.get(
        reverse("document-historical-cycle-report"), {"enrolment_id": str(enrolment_id)}
    )


def test_historical_cycle_report_is_generated_for_a_closed_cycle(auth_client):
    section = SectionFactory()
    enrolment = create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )
    close_academic_cycle(cycle=section.academic_cycle)
    _grant_document_issue(auth_client.user)

    response = _historical_cycle_report(auth_client, enrolment.public_id)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert b"Boleta" in response.content


def test_historical_cycle_report_includes_unit_grades_condition_and_promotion(auth_client):
    """RF-RES-008: boleta de un ciclo cerrado incluye notas por unidad, nota
    final, condicion por subarea y condicion de promocion."""
    today = date.today()
    section = SectionFactory()
    cycle = section.academic_cycle
    enrolment = create_enrolment(
        student=StudentFactory(),
        academic_cycle=cycle,
        grade=section.grade,
        section=section,
    )
    subject = SubjectFactory(institution=cycle.institution, name="Matematica")
    CurriculumPlan.objects.create(academic_cycle=cycle, grade=section.grade, subject=subject)
    unit = create_evaluation_unit(
        academic_cycle=cycle,
        number=1,
        name="Unidad 1",
        starts_on=cycle.starts_on,
        ends_on=cycle.starts_on + timedelta(days=30),
        capture_starts_on=today - timedelta(days=5),
        capture_ends_on=today + timedelta(days=5),
    )
    register_unit_grade(
        enrolment=enrolment,
        subject=subject,
        evaluation_unit=unit,
        teacher=PersonFactory(),
        value=65,
    )
    close_evaluation_unit(unit)
    close_academic_cycle(cycle=cycle)
    _grant_document_issue(auth_client.user)

    response = _historical_cycle_report(auth_client, enrolment.public_id)

    assert response.status_code == 200
    assert b"Unidad 1: 65" in response.content
    assert b"Nota final: 65" in response.content
    assert b"Aprobado" in response.content
    assert b"Promovido" in response.content


def test_historical_cycle_report_rejects_an_open_cycle(auth_client):
    enrolment = _enrolment()
    _grant_document_issue(auth_client.user)

    response = _historical_cycle_report(auth_client, enrolment.public_id)

    assert response.status_code == 400
    assert "cerrado" in _detail(response)


def test_historical_cycle_report_returns_404_for_unknown_enrolment(auth_client):
    _grant_document_issue(auth_client.user)

    response = _historical_cycle_report(auth_client, MISSING_UUID)

    assert response.status_code == 404


@pytest.mark.security
def test_historical_cycle_report_requires_issue_permission(auth_client):
    enrolment = _enrolment()

    response = _historical_cycle_report(auth_client, enrolment.public_id)

    assert response.status_code == 403


def _compile_batch(client, **payload):
    return client.post(reverse("document-batch-compile"), payload, content_type="application/json")


def test_document_batch_compile_generates_report_for_whole_section(auth_client):
    section = SectionFactory()
    create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )
    close_academic_cycle(cycle=section.academic_cycle)
    _grant_document_issue(auth_client.user)

    response = _compile_batch(auth_client, section_id=str(section.public_id))

    assert response.status_code == 200
    assert response.json() == {"count": 1, "replayed": False}


def test_document_batch_compile_requires_section_or_grade(auth_client):
    _grant_document_issue(auth_client.user)

    response = _compile_batch(auth_client)

    assert response.status_code == 400


def test_document_batch_compile_requires_issue_permission(auth_client):
    section = SectionFactory()

    response = _compile_batch(auth_client, section_id=str(section.public_id))

    assert response.status_code == 403


def test_document_batch_compile_is_idempotent_via_client_batch_id(auth_client):
    section = SectionFactory()
    create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )
    close_academic_cycle(cycle=section.academic_cycle)
    _grant_document_issue(auth_client.user)

    first = _compile_batch(
        auth_client, section_id=str(section.public_id), client_batch_id="retry-abc"
    )
    second = _compile_batch(
        auth_client, section_id=str(section.public_id), client_batch_id="retry-abc"
    )

    assert first.json() == {"count": 1, "replayed": False}
    assert second.json() == {"count": 1, "replayed": True}


def test_document_verification_is_public_and_confirms_a_genuine_code(client):
    """RF-EMI-009: no authentication required, per the issue's own acceptance criteria."""
    template = DocumentTemplateFactory()
    generated = compile_generated_document(
        template=template,
        payload={"document_type": "Certificado", "folio": "DOC-2026-0001"},
    )

    response = client.get(reverse("document-verify", args=[generated.verification_code]))

    assert response.status_code == 200
    assert response.json() == {
        "valid": True,
        "document_type": "Certificado",
        "folio": "DOC-2026-0001",
        "issued_at": generated.issued_at,
        "vigencia": "vigente",
    }


def test_document_verification_rejects_an_unknown_code(client):
    response = client.get(reverse("document-verify", args=["does-not-exist"]))

    assert response.status_code == 200
    assert response.json() == {"valid": False}


@pytest.mark.security
def test_document_verification_is_rate_limited_per_ip(client):
    """RNF-SEG-006: a burst against the public endpoint receives a 429 response."""
    cache.clear()

    responses = [client.get(reverse("document-verify", args=["does-not-exist"])) for _ in range(20)]
    blocked = client.get(reverse("document-verify", args=["does-not-exist"]))

    assert all(response.status_code == 200 for response in responses)
    assert blocked.status_code == 429

    cache.clear()


def test_official_document_eligibility_allows_superuser_without_role(client):
    enrolment = _enrolment()
    client.force_login(UserFactory(is_superuser=True))

    response = _eligibility(client, enrolment.public_id)

    assert response.status_code == 200
    assert response.json() == {"eligible": True, "blocking_document_codes": []}


def test_include_sensitive_field_tags_without_permission_returns_403(auth_client):
    response = auth_client.get(reverse("document-field-tag-list"), {"include_sensitive": "true"})

    assert response.status_code == 403


def test_include_sensitive_field_tags_with_permission_returns_200(auth_client):
    permission = PermissionFactory(codename="student_view_sensitive")
    RoleAssignmentFactory(user=auth_client.user, role=RoleFactory(permissions=[permission]))

    response = auth_client.get(reverse("document-field-tag-list"), {"include_sensitive": "true"})

    assert response.status_code == 200
    codes = {item["code"] for item in _items(response)}
    assert codes == set(FIELD_TAG_CODES)
