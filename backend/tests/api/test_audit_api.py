"""
End-to-end proof that write operations are audited through the real HTTP
contract, not just when a service is called directly (RF-BIT-001). Uses the
``documents`` endpoints (RF-PLA-001) as the vehicle: stable, already covers
create/update/deactivate in one place.
"""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.academics.models import CurriculumPlan
from apps.academics.services import close_academic_cycle
from apps.audit.models import AuditEvent
from apps.documents.services import compile_historical_cycle_report
from apps.enrolments.services import create_enrolment
from apps.evaluation.services import create_evaluation_unit, register_unit_grade
from apps.identity.services import disable_account
from tests.factories.academic import SectionFactory, SubjectFactory
from tests.factories.documents import DocumentTemplateFactory
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
    UserFactory,
)
from tests.factories.people import PersonFactory
from tests.factories.students import GuardianFactory, StudentFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def _grant_audit_permission(user):
    permission = PermissionFactory(codename="audit_read")
    RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))


def _grant_retention_policy_declare(user):
    permission = PermissionFactory(codename="retention_policy_declare")
    RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))


def _grant_sensitive_student_read(user, student):
    permission = PermissionFactory(codename="student_view_sensitive")
    assignment = RoleAssignmentFactory(
        user=user,
        role=RoleFactory(permissions=[permission]),
    )
    ScopeGrantFactory(assignment=assignment, student=student)


def test_creating_a_resource_via_the_api_is_audited(admin_client, institution):
    response = admin_client.post(
        reverse("document-template-list-create"),
        {"name": "Constancia", "code": "CONST"},
        content_type="application/json",
    )

    assert response.status_code == 201
    event = AuditEvent.objects.latest("created_at")
    assert event.action == "documents.template.created"
    assert event.actor_id == admin_client.user.id


def test_updating_a_resource_via_the_api_is_audited(admin_client, institution):
    template = DocumentTemplateFactory(institution=institution, name="Old")

    response = admin_client.patch(
        reverse("document-template-detail", args=[template.public_id]),
        {"name": "New"},
        content_type="application/json",
    )

    assert response.status_code == 200
    event = AuditEvent.objects.latest("created_at")
    assert event.action == "documents.template.updated"
    assert event.resource_identifier == str(template.pk)
    assert event.context["changes"]["name"] == {"before": "Old", "after": "New"}


def test_deactivating_a_resource_via_the_api_is_audited(admin_client, institution):
    template = DocumentTemplateFactory(institution=institution)

    response = admin_client.delete(reverse("document-template-detail", args=[template.public_id]))

    assert response.status_code == 204
    event = AuditEvent.objects.latest("created_at")
    assert event.action == "documents.template.deactivated"


def test_listing_audit_events_via_the_api_is_filterable(auth_client, admin_client, institution):
    """RF-BIT-006: restricted consulta, filterable by tipo de accion (among others)."""
    _grant_audit_permission(auth_client.user)
    created = admin_client.post(
        reverse("document-template-list-create"),
        {"name": "Constancia", "code": "CONST"},
        content_type="application/json",
    )

    assert created.status_code == 201

    response = auth_client.get(
        reverse("audit-event-list"), {"action": "documents.template.created"}
    )

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 1
    assert results[0]["action"] == "documents.template.created"
    assert results[0]["actor_username"] == admin_client.user.username


def test_exporting_audit_events_via_the_api_generates_a_file_and_is_itself_audited(
    auth_client, admin_client, institution
):
    """RF-BIT-006, Escenario 1: exportacion auditada."""
    _grant_audit_permission(auth_client.user)
    created = admin_client.post(
        reverse("document-template-list-create"),
        {"name": "Constancia", "code": "CONST"},
        content_type="application/json",
    )

    assert created.status_code == 201

    response = auth_client.get(reverse("audit-event-export"))

    assert response.status_code == 200
    assert response["Content-Type"] == "text/csv"
    assert b"documents.template.created" in response.content

    export_event = AuditEvent.objects.latest("created_at")
    assert export_event.action == "audit.export.created"
    assert export_event.actor_id == auth_client.user.id
    assert export_event.context["count"] >= 1


def test_emitted_document_history_is_queryable_by_student(auth_client, institution):
    """
    RF-EMI-007: the system stores a log of emitted documents showing user,
    date, document type and student -- and it must be queryable by student.
    """
    _grant_audit_permission(auth_client.user)
    section = SectionFactory(academic_cycle__institution=institution)
    enrolment = create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )
    close_academic_cycle(cycle=section.academic_cycle)
    compile_historical_cycle_report(enrolment=enrolment, actor=auth_client.user)

    response = auth_client.get(
        reverse("audit-event-list"),
        {"resource": "Document", "resource_identifier": str(enrolment.student.pk)},
    )

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 1
    event = results[0]
    assert event["action"] == "documents.document.issued"
    assert event["actor_username"] == auth_client.user.username
    assert event["context"]["document_type"] == "Boleta"
    assert event["context"]["student_id"] == enrolment.student.pk
    assert "created_at" in event


def test_declaring_data_retention_via_the_api_records_an_audit_event(auth_client):
    """RNF-LEG-001: declaring a retention period is itself an audited operation."""
    _grant_retention_policy_declare(auth_client.user)

    response = auth_client.post(
        reverse("audit-retention-declaration-create"),
        {
            "category": "student.health_notes",
            "period_days": 1825,
            "legal_basis": "Reglamento interno de proteccion de datos, art. 12",
            "applies_to_minors": True,
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    event = AuditEvent.objects.get(action="compliance.retention.declared")
    assert event.actor_id == auth_client.user.id
    assert event.context["period_days"] == 1825
    assert event.context["applies_to_minors"] is True


def test_declaring_data_retention_without_permission_is_denied(auth_client):
    response = auth_client.post(
        reverse("audit-retention-declaration-create"),
        {
            "category": "student.health_notes",
            "period_days": 1825,
            "legal_basis": "Reglamento interno",
        },
        content_type="application/json",
    )

    assert response.status_code == 403
    assert not AuditEvent.objects.filter(action="compliance.retention.declared").exists()


def test_reading_a_students_family_contacts_via_the_api_is_audited(auth_client):
    """RF-BIT-003: consulting one identified student's family contact data is a sensitive read."""
    student = StudentFactory()
    _grant_sensitive_student_read(auth_client.user, student)

    response = auth_client.get(
        reverse("student-emergency-contact-list-create", args=[student.public_id])
    )

    assert response.status_code == 200
    event = AuditEvent.objects.latest("created_at")
    assert event.action == "students.emergency_contacts.read"
    assert event.context["student_id"] == student.pk
    assert event.actor_id == auth_client.user.id


def test_a_guardian_without_a_student_association_is_denied_and_audited(client):
    """
    RF-BIT-004, Escenario 1, through the real HTTP contract: a guardian who
    holds the read permission but has no relation to any student hits the
    student detail endpoint and gets denied, and the attempt is audited.
    """
    permission = PermissionFactory(codename="student_view_basic")
    guardian = GuardianFactory()
    user = UserFactory(person=guardian.person, password="demo-pass-123")
    RoleAssignmentFactory(
        user=user, role=RoleFactory(permissions=[permission]), identity_scope=False
    )
    unrelated_student = StudentFactory()
    client.force_login(user)

    response = client.get(reverse("student-detail", args=[unrelated_student.pk]))

    assert response.status_code == 403
    event = AuditEvent.objects.latest("created_at")
    assert event.action == "identity.authorization.denied"
    assert event.actor_id == user.id
    assert event.context["reason"] == "missing_scope"


def test_disabling_the_actor_does_not_alter_their_past_audit_events(admin_client, institution):
    """
    RF-BIT-007: attribution for a request made through the real API survives
    the actor's account being disabled afterwards.
    """
    response = admin_client.post(
        reverse("document-template-list-create"),
        {"name": "Constancia", "code": "CONST2"},
        content_type="application/json",
    )
    assert response.status_code == 201
    actor_id = admin_client.user.id
    actor_username = admin_client.user.username

    admin = UserFactory(is_superuser=True)
    disable_account(actor=admin, user=admin_client.user, force=True)

    event = AuditEvent.objects.get(action="documents.template.created", actor_id=actor_id)
    assert event.actor_id == actor_id
    assert event.actor_label == actor_username


def test_result_trace_endpoint_requires_audit_read_permission(auth_client):
    section = SectionFactory()
    enrolment = create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )
    subject = SubjectFactory(institution=section.academic_cycle.institution)

    response = auth_client.get(
        reverse(
            "result-trace",
            kwargs={"enrolment_id": enrolment.public_id, "subject_id": subject.public_id},
        )
    )

    assert response.status_code == 403


def test_result_trace_endpoint_returns_unit_grades_and_is_audited_as_a_sensitive_read(auth_client):
    """RF-RES-009: consultarla exige permiso de auditoria y queda registrada
    en la bitacora como lectura sensible del estudiante identificado."""
    today = timezone.localdate()
    section = SectionFactory()
    cycle = section.academic_cycle
    enrolment = create_enrolment(
        student=StudentFactory(), academic_cycle=cycle, grade=section.grade, section=section
    )
    subject = SubjectFactory(institution=cycle.institution)
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
        value=85,
    )
    _grant_audit_permission(auth_client.user)

    response = auth_client.get(
        reverse(
            "result-trace",
            kwargs={"enrolment_id": enrolment.public_id, "subject_id": subject.public_id},
        )
    )

    assert response.status_code == 200
    body = response.json()
    assert body["unit_grades"] == [{"unit_number": 1, "unit_name": "Unidad 1", "value": 85}]
    assert body["corrections"] == []
    assert body["recovery_grade"] is None

    event = AuditEvent.objects.get(action="audit.result_trace.viewed")
    assert event.actor_id == auth_client.user.id
    assert event.context["student_id"] == enrolment.student.pk
