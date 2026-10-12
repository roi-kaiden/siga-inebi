"""
API contract tests for evaluation units.

RF-EVC-001: Estructura de unidades del ciclo
RF-EVC-002: Ventana de captura de notas
RF-EVC-003: Ventana de recuperacion
RF-EVC-004: Brecha excepcional autorizada
RF-EVC-005: Configuracion global heredable

Scenario 1: Configuración de cuatro unidades
Scenario 2: Unidades solapadas
Scenario 3: Captura dentro de la ventana
Scenario 4: Captura con la ventana cerrada
Scenario 5: Recuperación fuera de fecha
Scenario 6: Docente que no alcanzó a subir notas
Scenario 7: Expiración automática
Scenario 8: Ciclo que se aparta del valor global
Scenario 13: Preparación del ciclo siguiente
"""

from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from apps.academics.models import CurriculumPlan, TeachingAssignment
from apps.academics.services import close_academic_cycle
from apps.enrolments.services import create_enrolment
from apps.evaluation.models import CaptureExceptionGrant, EvaluationUnit, Grade, RecoveryGrade
from apps.evaluation.services import close_evaluation_unit, register_unit_grade, set_recovery_window
from apps.students.services import create_student_guardian_relation
from tests.factories.academic import AcademicCycleFactory, SectionFactory, SubjectFactory
from tests.factories.evaluation import EvaluationUnitFactory
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


def _grant_grade_write(user, *, section, subject, academic_cycle):
    """
    Give ``user`` the grade_write permission and a teaching assignment over
    ``section``/``subject``, matching RF-CAL-006's docente scope.
    """
    permission = PermissionFactory(codename="grade_write")
    RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    TeachingAssignment.objects.create(
        academic_cycle=academic_cycle,
        section=section,
        subject=subject,
        teacher=user.person,
        starts_on=academic_cycle.starts_on,
    )


def _grant_evaluation_configuration(user, *, institution):
    """Grant the evaluation configuration permission with institution scope."""
    permission = PermissionFactory(codename="evaluation_configure_units")
    assignment = RoleAssignmentFactory(
        user=user,
        role=RoleFactory(permissions=[permission]),
        identity_scope=False,
    )
    ScopeGrantFactory(assignment=assignment, institution=institution)


class TestEvaluationUnitAPI:
    """Tests for evaluation unit REST endpoints."""

    def test_create_evaluation_unit_success(self, auth_client, institution):
        """
        POST /api/v1/academics/cycles/{cycle_id}/evaluation-units/
        GIVEN un ciclo escolar sin unidades configuradas
        WHEN un usuario autorizado define una unidad con sus fechas
        THEN el sistema responde 201 con los datos registrados
        """
        cycle = AcademicCycleFactory(
            institution=institution,
            starts_on=date(2026, 1, 15),
            ends_on=date(2026, 10, 31),
        )

        response = auth_client.post(
            reverse(
                "evaluation-unit-list",
                kwargs={"cycle_public_id": str(cycle.public_id)},
            ),
            {
                "number": 1,
                "name": "Unit 1",
                "starts_on": "2026-01-15",
                "ends_on": "2026-03-15",
                "capture_starts_on": "2026-01-01",
                "capture_ends_on": "2026-04-30",
                "status": "open",
            },
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.json()
        assert data["number"] == 1
        assert data["name"] == "Unit 1"
        assert data["status"] == EvaluationUnit.UnitStatus.OPEN
        assert data["starts_on"] == "2026-01-15"
        assert data["ends_on"] == "2026-03-15"
        assert data["capture_starts_on"] == "2026-01-01"
        assert data["capture_ends_on"] == "2026-04-30"

    def test_create_multiple_units_in_same_cycle(self, auth_client, institution):
        """
        Scenario 1: Create four units successfully
        """
        cycle = AcademicCycleFactory(
            institution=institution,
            starts_on=date(2026, 1, 15),
            ends_on=date(2026, 10, 31),
        )

        base_url = reverse(
            "evaluation-unit-list",
            kwargs={"cycle_public_id": str(cycle.public_id)},
        )

        for i in range(1, 5):
            response = auth_client.post(
                base_url,
                {
                    "number": i,
                    "name": f"Unit {i}",
                    "starts_on": f"2026-{1 + (i - 1) * 2:02d}-01",
                    "ends_on": f"2026-{2 + (i - 1) * 2:02d}-28",
                    "capture_starts_on": f"2026-{1 + (i - 1) * 2:02d}-01",
                    "capture_ends_on": f"2026-{2 + (i - 1) * 2:02d}-28",
                    "status": "open",
                },
                content_type="application/json",
            )
            assert response.status_code == 201, f"Failed to create unit {i}: {response.json()}"

        # Verify all units exist
        units = EvaluationUnit.objects.filter(academic_cycle=cycle)
        assert units.count() == 4
        assert list(units.values_list("number", flat=True)) == [1, 2, 3, 4]

    def test_reject_overlapping_dates_api(self, auth_client, institution):
        """
        Scenario 2: Unidades solapadas
        GIVEN un ciclo con una unidad ya configurada
        WHEN se intenta crear otra cuyo rango de fechas se solapa
        THEN el sistema responde 400 con detalle del conflicto
        """
        cycle = AcademicCycleFactory(
            institution=institution,
            starts_on=date(2026, 1, 15),
            ends_on=date(2026, 10, 31),
        )

        base_url = reverse(
            "evaluation-unit-list",
            kwargs={"cycle_public_id": str(cycle.public_id)},
        )

        # Create first unit
        response = auth_client.post(
            base_url,
            {
                "number": 1,
                "name": "Unit 1",
                "starts_on": "2026-01-01",
                "ends_on": "2026-02-28",
                "capture_starts_on": "2026-01-01",
                "capture_ends_on": "2026-02-28",
                "status": "open",
            },
            content_type="application/json",
        )
        assert response.status_code == 201

        # Try to create overlapping unit
        response = auth_client.post(
            base_url,
            {
                "number": 2,
                "name": "Unit 2",
                "starts_on": "2026-02-01",  # overlaps with unit 1
                "ends_on": "2026-03-31",
                "capture_starts_on": "2026-02-01",
                "capture_ends_on": "2026-03-31",
                "status": "open",
            },
            content_type="application/json",
        )
        assert response.status_code == 400
        assert "overlap" in response.json()["error"]["detail"].lower()

    def test_reject_invalid_date_range_api(self, auth_client, institution):
        """
        Test end_date before start_date rejected.
        """
        cycle = AcademicCycleFactory(institution=institution)
        base_url = reverse(
            "evaluation-unit-list",
            kwargs={"cycle_public_id": str(cycle.public_id)},
        )

        response = auth_client.post(
            base_url,
            {
                "number": 1,
                "name": "Unit 1",
                "starts_on": "2026-03-01",
                "ends_on": "2026-01-01",  # invalid
                "capture_starts_on": "2026-01-01",
                "capture_ends_on": "2026-04-01",
                "status": "open",
            },
            content_type="application/json",
        )

        assert response.status_code == 400
        detail = response.json()["error"]["detail"]
        assert "no puede ser anterior" in detail["ends_on"][0].lower()

    def test_list_units_by_cycle(self, auth_client, institution):
        """
        GET /api/v1/academics/cycles/{cycle_id}/evaluation-units/
        """
        cycle = AcademicCycleFactory(institution=institution)

        # Create some units
        from tests.factories.evaluation import EvaluationUnitFactory

        for i in range(1, 4):
            EvaluationUnitFactory(academic_cycle=cycle, number=i)

        response = auth_client.get(
            reverse(
                "evaluation-unit-list",
                kwargs={"cycle_public_id": str(cycle.public_id)},
            )
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 3
        assert [u["number"] for u in data["results"]] == [1, 2, 3]

    def test_cycle_not_found_returns_404(self, auth_client):
        """
        Test endpoint with invalid cycle ID.
        """
        import uuid

        response = auth_client.post(
            reverse(
                "evaluation-unit-list",
                kwargs={"cycle_public_id": str(uuid.uuid4())},
            ),
            {
                "number": 1,
                "name": "Unit 1",
                "starts_on": "2026-01-01",
                "ends_on": "2026-02-28",
                "capture_starts_on": "2026-01-01",
                "capture_ends_on": "2026-02-28",
            },
            content_type="application/json",
        )

        assert response.status_code == 404
        assert "not found" in response.json()["error"]["detail"]["detail"].lower()


class TestRecoveryWindowAPI:
    """Tests for PATCH recovery-window endpoint (RF-EVC-003)."""

    def test_set_recovery_window_success(self, auth_client, institution):
        """
        PATCH /api/v1/academics/cycles/{cycle_id}/evaluation-units/{unit_id}/recovery-window/
        """
        cycle = AcademicCycleFactory(institution=institution)
        unit = EvaluationUnitFactory(academic_cycle=cycle, number=1)

        response = auth_client.patch(
            reverse(
                "evaluation-unit-recovery-window",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(unit.public_id),
                },
            ),
            {
                "recovery_starts_on": "2026-03-10",
                "recovery_ends_on": "2026-03-20",
            },
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["recovery_starts_on"] == "2026-03-10"
        assert data["recovery_ends_on"] == "2026-03-20"

    def test_reject_invalid_recovery_date_range_api(self, auth_client, institution):
        """
        Test that recovery end date before start date is rejected.
        """
        cycle = AcademicCycleFactory(institution=institution)
        unit = EvaluationUnitFactory(academic_cycle=cycle, number=1)

        response = auth_client.patch(
            reverse(
                "evaluation-unit-recovery-window",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(unit.public_id),
                },
            ),
            {
                "recovery_starts_on": "2026-03-20",
                "recovery_ends_on": "2026-03-10",
            },
            content_type="application/json",
        )

        assert response.status_code == 400

    def test_unit_not_found_returns_404(self, auth_client, institution):
        """
        Test endpoint with invalid unit ID.
        """
        import uuid

        cycle = AcademicCycleFactory(institution=institution)

        response = auth_client.patch(
            reverse(
                "evaluation-unit-recovery-window",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(uuid.uuid4()),
                },
            ),
            {
                "recovery_starts_on": "2026-03-10",
                "recovery_ends_on": "2026-03-20",
            },
            content_type="application/json",
        )

        assert response.status_code == 404


class TestEvaluationUnitCloseAPI:
    """Tests for PATCH close endpoint (RF-EVC-007)."""

    def _enrolment(self, cycle):
        section = SectionFactory(academic_cycle=cycle)
        student = StudentFactory()
        return create_enrolment(
            student=student,
            academic_cycle=cycle,
            grade=section.grade,
            section=section,
        )

    def test_close_unit_success(self, auth_client, institution):
        """
        Scenario: Cierre de una unidad
        PATCH /api/v1/academics/cycles/{cycle_id}/evaluation-units/{unit_id}/close/
        """
        cycle = AcademicCycleFactory(institution=institution)
        yesterday = timezone.localdate() - timedelta(days=1)
        unit = EvaluationUnitFactory(
            academic_cycle=cycle,
            capture_starts_on=yesterday - timedelta(days=30),
            capture_ends_on=yesterday,
        )
        _grant_evaluation_configuration(auth_client.user, institution=institution)

        response = auth_client.patch(
            reverse(
                "evaluation-unit-close",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(unit.public_id),
                },
            ),
            content_type="application/json",
        )

        assert response.status_code == 200
        assert response.json()["status"] == "closed"

        from apps.audit.models import AuditEvent

        assert AuditEvent.objects.filter(
            action="evaluation.unit_closed", actor=auth_client.user
        ).exists()

    def test_close_unit_requires_configuration_permission(self, auth_client, institution):
        cycle = AcademicCycleFactory(institution=institution)
        unit = EvaluationUnitFactory(academic_cycle=cycle)

        response = auth_client.patch(
            reverse(
                "evaluation-unit-close",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(unit.public_id),
                },
            ),
            content_type="application/json",
        )

        assert response.status_code == 403
        unit.refresh_from_db()
        assert unit.status == EvaluationUnit.UnitStatus.OPEN

    def test_close_unit_requires_institution_scope(self, auth_client, institution):
        cycle = AcademicCycleFactory(institution=institution)
        unit = EvaluationUnitFactory(academic_cycle=cycle)
        permission = PermissionFactory(codename="evaluation_configure_units")
        RoleAssignmentFactory(
            user=auth_client.user,
            role=RoleFactory(permissions=[permission]),
            identity_scope=False,
        )

        response = auth_client.patch(
            reverse(
                "evaluation-unit-close",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(unit.public_id),
                },
            ),
            content_type="application/json",
        )

        assert response.status_code == 403
        unit.refresh_from_db()
        assert unit.status == EvaluationUnit.UnitStatus.OPEN

    def test_closed_unit_rejects_grade_correction_without_grant_api(self, auth_client, institution):
        """
        AND las notas de esa unidad dejan de admitir modificación salvo brecha excepcional
        """
        cycle = AcademicCycleFactory(institution=institution)
        yesterday = timezone.localdate() - timedelta(days=1)
        unit = EvaluationUnitFactory(
            academic_cycle=cycle,
            capture_starts_on=yesterday - timedelta(days=30),
            capture_ends_on=yesterday,
        )
        _grant_evaluation_configuration(auth_client.user, institution=institution)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=institution)
        teacher = PersonFactory()
        Grade.objects.create(enrolment=enrolment, subject=subject, evaluation_unit=unit, value=70)
        _grant_grade_write(
            auth_client.user, section=enrolment.section, subject=subject, academic_cycle=cycle
        )

        close_response = auth_client.patch(
            reverse(
                "evaluation-unit-close",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(unit.public_id),
                },
            ),
            content_type="application/json",
        )
        assert close_response.status_code == 200

        response = auth_client.post(
            reverse(
                "evaluation-unit-grades",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(unit.public_id),
                },
            ),
            {
                "enrolment": enrolment.public_id,
                "subject": subject.public_id,
                "teacher": teacher.public_id,
                "value": 90,
            },
            content_type="application/json",
        )

        assert response.status_code == 400
        assert "esta cerrada" in response.json()["error"]["detail"].lower()

    def test_reject_closing_an_already_closed_unit_api(self, auth_client, institution):
        cycle = AcademicCycleFactory(institution=institution)
        unit = EvaluationUnitFactory(academic_cycle=cycle)
        _grant_evaluation_configuration(auth_client.user, institution=institution)

        url = reverse(
            "evaluation-unit-close",
            kwargs={
                "cycle_public_id": str(cycle.public_id),
                "unit_public_id": str(unit.public_id),
            },
        )
        first = auth_client.patch(url, content_type="application/json")
        assert first.status_code == 200

        second = auth_client.patch(url, content_type="application/json")
        assert second.status_code == 400

    def test_unit_not_found_returns_404_for_close(self, auth_client, institution):
        import uuid

        cycle = AcademicCycleFactory(institution=institution)

        response = auth_client.patch(
            reverse(
                "evaluation-unit-close",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(uuid.uuid4()),
                },
            ),
            content_type="application/json",
        )

        assert response.status_code == 404


class TestCaptureExceptionGrantAPI:
    """Tests for POST capture-exceptions endpoint (RF-EVC-004)."""

    def test_grant_capture_exception_success(self, auth_client, institution):
        """
        Scenario 6: Docente que no alcanzó a subir notas
        POST /api/v1/academics/cycles/{cycle_id}/evaluation-units/{unit_id}/capture-exceptions/
        """
        cycle = AcademicCycleFactory(institution=institution)
        unit = EvaluationUnitFactory(academic_cycle=cycle, number=1)
        subject = SubjectFactory(institution=institution)
        teacher = PersonFactory()
        expires_at = timezone.now() + timedelta(days=1)

        response = auth_client.post(
            reverse(
                "evaluation-unit-capture-exceptions",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(unit.public_id),
                },
            ),
            {
                "subject": subject.public_id,
                "teacher": teacher.public_id,
                "reason": "No alcanzó a subir notas por falla eléctrica.",
                "expires_at": expires_at.isoformat(),
            },
            content_type="application/json",
        )

        assert response.status_code == 201, response.json()
        data = response.json()
        assert data["reason"] == "No alcanzó a subir notas por falla eléctrica."
        assert CaptureExceptionGrant.objects.filter(
            evaluation_unit=unit, subject=subject, teacher=teacher
        ).exists()

    def test_reject_empty_reason_api(self, auth_client, institution):
        """
        Test that granting an exception without a reason is rejected.
        """
        cycle = AcademicCycleFactory(institution=institution)
        unit = EvaluationUnitFactory(academic_cycle=cycle, number=1)
        subject = SubjectFactory(institution=institution)
        teacher = PersonFactory()

        response = auth_client.post(
            reverse(
                "evaluation-unit-capture-exceptions",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(unit.public_id),
                },
            ),
            {
                "subject": subject.public_id,
                "teacher": teacher.public_id,
                "reason": "   ",
                "expires_at": (timezone.now() + timedelta(days=1)).isoformat(),
            },
            content_type="application/json",
        )

        assert response.status_code == 400

    def test_unit_not_found_returns_404_for_grant(self, auth_client, institution):
        """
        Test endpoint with invalid unit ID.
        """
        import uuid

        cycle = AcademicCycleFactory(institution=institution)
        subject = SubjectFactory(institution=institution)
        teacher = PersonFactory()

        response = auth_client.post(
            reverse(
                "evaluation-unit-capture-exceptions",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(uuid.uuid4()),
                },
            ),
            {
                "subject": subject.public_id,
                "teacher": teacher.public_id,
                "reason": "Motivo válido.",
                "expires_at": (timezone.now() + timedelta(days=1)).isoformat(),
            },
            content_type="application/json",
        )

        assert response.status_code == 404


class TestEvaluationConfigAPI:
    """Tests for global/cycle evaluation configuration endpoints (RF-EVC-005)."""

    def test_cycle_departs_from_global_value_api(self, auth_client, institution):
        """
        Scenario 8: Ciclo que se aparta del valor global
        """
        # Set the global default.
        response = auth_client.patch(
            reverse("evaluation-global-config"),
            {"default_unit_count": 4},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["default_unit_count"] == 4

        cycle_a = AcademicCycleFactory(
            institution=institution,
            year=2030,
            starts_on=date(2030, 1, 1),
            ends_on=date(2030, 12, 31),
            status="draft",
        )
        cycle_b = AcademicCycleFactory(
            institution=institution,
            year=2031,
            starts_on=date(2031, 1, 1),
            ends_on=date(2031, 12, 31),
            status="draft",
        )

        # Before any override, both cycles inherit the global default.
        for cycle in (cycle_a, cycle_b):
            response = auth_client.get(
                reverse("cycle-evaluation-config", kwargs={"cycle_public_id": str(cycle.public_id)})
            )
            assert response.status_code == 200
            assert response.json()["unit_count"] is None
            assert response.json()["effective_unit_count"] == 4

        # Cycle A departs from the global value.
        response = auth_client.patch(
            reverse("cycle-evaluation-config", kwargs={"cycle_public_id": str(cycle_a.public_id)}),
            {"unit_count": 3},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["unit_count"] == 3
        assert response.json()["effective_unit_count"] == 3

        # Cycle B and the global config remain unchanged.
        response = auth_client.get(
            reverse("cycle-evaluation-config", kwargs={"cycle_public_id": str(cycle_b.public_id)})
        )
        assert response.json()["unit_count"] is None
        assert response.json()["effective_unit_count"] == 4

        response = auth_client.get(reverse("evaluation-global-config"))
        assert response.json()["default_unit_count"] == 4

    def test_reject_non_positive_global_unit_count_api(self, auth_client):
        """
        Test that a non-positive default_unit_count is rejected.
        """
        response = auth_client.patch(
            reverse("evaluation-global-config"),
            {"default_unit_count": 0},
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_cycle_config_not_found_returns_404(self, auth_client):
        """
        Test endpoint with invalid cycle ID.
        """
        import uuid

        response = auth_client.get(
            reverse("cycle-evaluation-config", kwargs={"cycle_public_id": str(uuid.uuid4())})
        )
        assert response.status_code == 404


class TestCloneCycleEvaluationConfigAPI:
    """Tests for the evaluation-config clone endpoint (RF-EVC-006)."""

    def _source_and_target(self, institution, *, target_status="draft"):
        source = AcademicCycleFactory(
            institution=institution,
            year=2025,
            starts_on=date(2025, 1, 1),
            ends_on=date(2025, 10, 31),
            status="closed",
        )
        target = AcademicCycleFactory(
            institution=institution,
            year=2026,
            starts_on=date(2026, 1, 5),
            ends_on=date(2026, 11, 4),
            status=target_status,
        )
        return source, target

    def test_clone_success(self, auth_client, institution):
        """
        Scenario 13: Preparación del ciclo siguiente
        POST /api/v1/academics/cycles/{source_id}/evaluation-config/clone/
        """
        source, target = self._source_and_target(institution)
        unit = EvaluationUnitFactory(
            academic_cycle=source,
            number=1,
            starts_on=date(2025, 1, 15),
            ends_on=date(2025, 3, 15),
            capture_starts_on=date(2025, 3, 10),
            capture_ends_on=date(2025, 3, 20),
        )
        _grant_evaluation_configuration(auth_client.user, institution=institution)

        response = auth_client.post(
            reverse(
                "cycle-evaluation-config-clone", kwargs={"cycle_public_id": str(source.public_id)}
            ),
            {"target_cycle": str(target.public_id)},
            content_type="application/json",
        )

        assert response.status_code == 201
        body = response.json()
        assert len(body) == 1
        shift = target.starts_on - source.starts_on
        assert body[0]["starts_on"] == str(unit.starts_on + shift)
        assert body[0]["ends_on"] == str(unit.ends_on + shift)
        assert body[0]["capture_starts_on"] == str(unit.capture_starts_on + shift)
        assert body[0]["capture_ends_on"] == str(unit.capture_ends_on + shift)
        assert EvaluationUnit.objects.filter(academic_cycle=target).count() == 1

        from apps.audit.models import AuditEvent

        assert AuditEvent.objects.filter(action="evaluation.config_cloned").exists()

    def test_clone_requires_configuration_permission(self, auth_client, institution):
        source, target = self._source_and_target(institution)
        EvaluationUnitFactory(academic_cycle=source, number=1)

        response = auth_client.post(
            reverse(
                "cycle-evaluation-config-clone", kwargs={"cycle_public_id": str(source.public_id)}
            ),
            {"target_cycle": str(target.public_id)},
            content_type="application/json",
        )

        assert response.status_code == 403
        assert not EvaluationUnit.objects.filter(academic_cycle=target).exists()

    def test_clone_requires_institution_scope(self, auth_client, institution):
        source, target = self._source_and_target(institution)
        EvaluationUnitFactory(academic_cycle=source, number=1)
        permission = PermissionFactory(codename="evaluation_configure_units")
        RoleAssignmentFactory(
            user=auth_client.user,
            role=RoleFactory(permissions=[permission]),
            identity_scope=False,
        )

        response = auth_client.post(
            reverse(
                "cycle-evaluation-config-clone", kwargs={"cycle_public_id": str(source.public_id)}
            ),
            {"target_cycle": str(target.public_id)},
            content_type="application/json",
        )

        assert response.status_code == 403

    def test_clone_target_not_in_draft_returns_400(self, auth_client, institution):
        source, target = self._source_and_target(institution, target_status="closed")
        EvaluationUnitFactory(academic_cycle=source, number=1)
        _grant_evaluation_configuration(auth_client.user, institution=institution)

        response = auth_client.post(
            reverse(
                "cycle-evaluation-config-clone", kwargs={"cycle_public_id": str(source.public_id)}
            ),
            {"target_cycle": str(target.public_id)},
            content_type="application/json",
        )

        assert response.status_code == 400

    def test_clone_source_not_found_returns_404(self, auth_client, institution):
        import uuid

        target = AcademicCycleFactory(institution=institution, status="draft")
        _grant_evaluation_configuration(auth_client.user, institution=institution)

        response = auth_client.post(
            reverse("cycle-evaluation-config-clone", kwargs={"cycle_public_id": str(uuid.uuid4())}),
            {"target_cycle": str(target.public_id)},
            content_type="application/json",
        )

        assert response.status_code == 404


class TestGradeAPI:
    """Tests for RF-CAL-001: Registro de la nota de unidad."""

    def _enrolment(self, cycle):
        section = SectionFactory(academic_cycle=cycle)
        student = StudentFactory()
        return create_enrolment(
            student=student,
            academic_cycle=cycle,
            grade=section.grade,
            section=section,
        )

    def _open_unit(self, cycle):
        """
        A unit whose capture window brackets today explicitly. The factory's
        default dates are offset by ``number``, a sequence shared across the
        whole test session, so they drift away from today as more units are
        created; the window bounds must be set explicitly here.
        """
        today = timezone.localdate()
        return EvaluationUnitFactory(
            academic_cycle=cycle,
            capture_starts_on=today - timedelta(days=5),
            capture_ends_on=today + timedelta(days=5),
        )

    def test_register_grade_success(self, auth_client, institution):
        """
        Scenario 9: Registro de una nota por el docente
        POST /api/v1/academics/cycles/{cycle_id}/evaluation-units/{unit_id}/grades/
        """
        cycle = AcademicCycleFactory(institution=institution)
        unit = self._open_unit(cycle)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=institution)
        teacher = PersonFactory()
        _grant_grade_write(
            auth_client.user, section=enrolment.section, subject=subject, academic_cycle=cycle
        )

        response = auth_client.post(
            reverse(
                "evaluation-unit-grades",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(unit.public_id),
                },
            ),
            {
                "enrolment": enrolment.public_id,
                "subject": subject.public_id,
                "teacher": teacher.public_id,
                "value": 85,
            },
            content_type="application/json",
        )

        assert response.status_code == 201, response.json()
        data = response.json()
        assert data["value"] == 85
        assert data["subject"] == str(subject.public_id)
        assert Grade.objects.filter(
            enrolment=enrolment, subject=subject, evaluation_unit=unit
        ).exists()

    def test_register_grade_again_updates_existing_row(self, auth_client, institution):
        """
        Test that posting the same (enrolment, subject, unit) again updates
        the existing grade instead of creating a duplicate.
        """
        cycle = AcademicCycleFactory(institution=institution)
        unit = self._open_unit(cycle)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=institution)
        teacher = PersonFactory()
        _grant_grade_write(
            auth_client.user, section=enrolment.section, subject=subject, academic_cycle=cycle
        )

        url = reverse(
            "evaluation-unit-grades",
            kwargs={
                "cycle_public_id": str(cycle.public_id),
                "unit_public_id": str(unit.public_id),
            },
        )
        payload = {
            "enrolment": enrolment.public_id,
            "subject": subject.public_id,
            "teacher": teacher.public_id,
            "value": 70,
        }
        first = auth_client.post(url, payload, content_type="application/json")
        assert first.status_code == 201

        payload["value"] = 90
        second = auth_client.post(url, payload, content_type="application/json")
        assert second.status_code == 201
        assert second.json()["value"] == 90
        assert (
            Grade.objects.filter(enrolment=enrolment, subject=subject, evaluation_unit=unit).count()
            == 1
        )

    def test_reject_grade_when_capture_window_closed_api(self, auth_client, institution):
        """
        Test that a grade is rejected via the API when the capture window is closed.
        """
        cycle = AcademicCycleFactory(institution=institution)
        yesterday = timezone.localdate() - timedelta(days=1)
        unit = EvaluationUnitFactory(
            academic_cycle=cycle,
            starts_on=yesterday - timedelta(days=30),
            ends_on=yesterday,
            capture_starts_on=yesterday - timedelta(days=30),
            capture_ends_on=yesterday,
        )
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=institution)
        teacher = PersonFactory()
        _grant_grade_write(
            auth_client.user, section=enrolment.section, subject=subject, academic_cycle=cycle
        )

        response = auth_client.post(
            reverse(
                "evaluation-unit-grades",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(unit.public_id),
                },
            ),
            {
                "enrolment": enrolment.public_id,
                "subject": subject.public_id,
                "teacher": teacher.public_id,
                "value": 85,
            },
            content_type="application/json",
        )

        assert response.status_code == 400
        assert "esta cerrada" in response.json()["error"]["detail"].lower()

    def test_list_grades_by_unit(self, auth_client, institution):
        """
        GET /api/v1/academics/cycles/{cycle_id}/evaluation-units/{unit_id}/grades/
        """
        cycle = AcademicCycleFactory(institution=institution)
        unit = EvaluationUnitFactory(academic_cycle=cycle)
        subject = SubjectFactory(institution=institution)
        for _ in range(3):
            enrolment = self._enrolment(cycle)
            Grade.objects.create(
                enrolment=enrolment, subject=subject, evaluation_unit=unit, value=80
            )

        response = auth_client.get(
            reverse(
                "evaluation-unit-grades",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(unit.public_id),
                },
            )
        )

        assert response.status_code == 200
        assert len(response.json()["results"]) == 3

    def test_unit_not_found_returns_404_for_grade(self, auth_client, institution):
        """
        Test endpoint with invalid unit ID.
        """
        import uuid

        cycle = AcademicCycleFactory(institution=institution)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=institution)
        teacher = PersonFactory()

        response = auth_client.post(
            reverse(
                "evaluation-unit-grades",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(uuid.uuid4()),
                },
            ),
            {
                "enrolment": enrolment.public_id,
                "subject": subject.public_id,
                "teacher": teacher.public_id,
                "value": 85,
            },
            content_type="application/json",
        )

        assert response.status_code == 404


class TestGradeCorrectionAPI:
    """Tests for RF-CAL-005: Corrección de notas registradas."""

    def _enrolment(self, cycle):
        section = SectionFactory(academic_cycle=cycle)
        student = StudentFactory()
        return create_enrolment(
            student=student,
            academic_cycle=cycle,
            grade=section.grade,
            section=section,
        )

    def _open_unit(self, cycle):
        today = timezone.localdate()
        return EvaluationUnitFactory(
            academic_cycle=cycle,
            capture_starts_on=today - timedelta(days=5),
            capture_ends_on=today + timedelta(days=5),
        )

    def test_correction_with_open_window_is_accepted_and_audited_api(
        self, auth_client, institution
    ):
        """
        Scenario: Corrección con la ventana abierta
        GIVEN una nota registrada y una ventana de captura abierta
        WHEN el docente la corrige
        THEN el sistema acepta el cambio y registra en bitácora el valor anterior y el nuevo
        """
        from apps.audit.models import AuditEvent

        cycle = AcademicCycleFactory(institution=institution)
        unit = self._open_unit(cycle)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=institution)
        teacher = PersonFactory()
        _grant_grade_write(
            auth_client.user, section=enrolment.section, subject=subject, academic_cycle=cycle
        )

        url = reverse(
            "evaluation-unit-grades",
            kwargs={
                "cycle_public_id": str(cycle.public_id),
                "unit_public_id": str(unit.public_id),
            },
        )
        payload = {
            "enrolment": enrolment.public_id,
            "subject": subject.public_id,
            "teacher": teacher.public_id,
            "value": 70,
        }
        first = auth_client.post(url, payload, content_type="application/json")
        assert first.status_code == 201

        payload["value"] = 90
        second = auth_client.post(url, payload, content_type="application/json")

        assert second.status_code == 201
        assert second.json()["value"] == 90

        event = AuditEvent.objects.filter(action="evaluation.grade_updated").latest("created_at")
        assert event.context["changes"] == {"value": {"before": 70, "after": 90}}

    def test_correction_with_closed_window_and_no_grant_is_rejected_api(
        self, auth_client, institution
    ):
        """
        Scenario: Corrección con la ventana cerrada y sin brecha
        GIVEN una nota de una unidad cerrada, sin brecha excepcional vigente
        WHEN el docente intenta corregirla
        THEN el sistema rechaza la operación
        """
        cycle = AcademicCycleFactory(institution=institution)
        yesterday = timezone.localdate() - timedelta(days=1)
        unit = EvaluationUnitFactory(
            academic_cycle=cycle,
            starts_on=yesterday - timedelta(days=30),
            ends_on=yesterday,
            capture_starts_on=yesterday - timedelta(days=30),
            capture_ends_on=yesterday,
        )
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=institution)
        teacher = PersonFactory()
        _grant_grade_write(
            auth_client.user, section=enrolment.section, subject=subject, academic_cycle=cycle
        )
        Grade.objects.create(enrolment=enrolment, subject=subject, evaluation_unit=unit, value=70)

        response = auth_client.post(
            reverse(
                "evaluation-unit-grades",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(unit.public_id),
                },
            ),
            {
                "enrolment": enrolment.public_id,
                "subject": subject.public_id,
                "teacher": teacher.public_id,
                "value": 90,
            },
            content_type="application/json",
        )

        assert response.status_code == 400
        assert "esta cerrada" in response.json()["error"]["detail"].lower()
        assert (
            Grade.objects.get(enrolment=enrolment, subject=subject, evaluation_unit=unit).value
            == 70
        )

    def test_closed_cycle_denies_grade_write_and_preserves_frozen_result(
        self, auth_client, institution
    ):
        """CP-INT-EVA-001: a closed cycle keeps the grade and frozen result unchanged."""
        from apps.academics.models import FrozenSubjectResult

        cycle = AcademicCycleFactory(institution=institution)
        unit = self._open_unit(cycle)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=institution)
        teacher = auth_client.user.person
        _grant_grade_write(
            auth_client.user, section=enrolment.section, subject=subject, academic_cycle=cycle
        )
        CurriculumPlan.objects.create(
            academic_cycle=cycle, grade=enrolment.grade, subject=subject
        )
        url = reverse(
            "evaluation-unit-grades",
            kwargs={"cycle_public_id": cycle.public_id, "unit_public_id": unit.public_id},
        )
        payload = {
            "enrolment": enrolment.public_id,
            "subject": subject.public_id,
            "teacher": teacher.public_id,
            "value": 70,
        }
        assert auth_client.post(url, payload, content_type="application/json").status_code == 201
        close_evaluation_unit(unit)
        close_academic_cycle(cycle=cycle)
        frozen = FrozenSubjectResult.objects.get(enrolment=enrolment, subject=subject)

        payload["value"] = 90
        response = auth_client.post(url, payload, content_type="application/json")

        assert response.status_code == 403
        grade = Grade.objects.get(enrolment=enrolment, subject=subject, evaluation_unit=unit)
        assert grade.value == 70
        frozen.refresh_from_db()
        assert frozen.final_grade == 70


class TestGradeAuthorizationAPI:
    """Tests for RF-CAL-006: Alcance del docente sobre las notas."""

    def _enrolment(self, cycle):
        section = SectionFactory(academic_cycle=cycle)
        student = StudentFactory()
        return create_enrolment(
            student=student,
            academic_cycle=cycle,
            grade=section.grade,
            section=section,
        )

    def _open_unit(self, cycle):
        today = timezone.localdate()
        return EvaluationUnitFactory(
            academic_cycle=cycle,
            capture_starts_on=today - timedelta(days=5),
            capture_ends_on=today + timedelta(days=5),
        )

    def test_reject_grade_write_for_subarea_ajena(self, auth_client, institution):
        """
        Scenario 12: Subárea ajena
        GIVEN un docente sin asignación sobre una subárea
        WHEN intenta registrar una nota de esa subárea
        THEN el sistema deniega la operación
        """
        cycle = AcademicCycleFactory(institution=institution)
        unit = self._open_unit(cycle)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=institution)
        teacher = PersonFactory()
        # auth_client.user has the atomic permission but no TeachingAssignment
        # over this section/subject: an ajena subárea.
        permission = PermissionFactory(codename="grade_write")
        RoleAssignmentFactory(user=auth_client.user, role=RoleFactory(permissions=[permission]))

        response = auth_client.post(
            reverse(
                "evaluation-unit-grades",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(unit.public_id),
                },
            ),
            {
                "enrolment": enrolment.public_id,
                "subject": subject.public_id,
                "teacher": teacher.public_id,
                "value": 85,
            },
            content_type="application/json",
        )

        assert response.status_code == 403
        assert not Grade.objects.filter(
            enrolment=enrolment, subject=subject, evaluation_unit=unit
        ).exists()

    def test_reject_grade_write_without_atomic_permission(self, auth_client, institution):
        """
        Test that a teacher with a matching assignment but no grade_write
        permission at all is still denied: scope alone is not enough.
        """
        cycle = AcademicCycleFactory(institution=institution)
        unit = self._open_unit(cycle)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=institution)
        teacher = PersonFactory()
        TeachingAssignment.objects.create(
            academic_cycle=cycle,
            section=enrolment.section,
            subject=subject,
            teacher=auth_client.user.person,
            starts_on=cycle.starts_on,
        )

        response = auth_client.post(
            reverse(
                "evaluation-unit-grades",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(unit.public_id),
                },
            ),
            {
                "enrolment": enrolment.public_id,
                "subject": subject.public_id,
                "teacher": teacher.public_id,
                "value": 85,
            },
            content_type="application/json",
        )

        assert response.status_code == 403

    def test_grade_write_denial_is_audited(self, auth_client, institution):
        """
        Test that a denied grade write is recorded in the audit trail
        (RF-CAL-006 touches the sensitive identity-access domain).
        """
        cycle = AcademicCycleFactory(institution=institution)
        unit = self._open_unit(cycle)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=institution)
        teacher = PersonFactory()
        permission = PermissionFactory(codename="grade_write")
        RoleAssignmentFactory(user=auth_client.user, role=RoleFactory(permissions=[permission]))

        auth_client.post(
            reverse(
                "evaluation-unit-grades",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(unit.public_id),
                },
            ),
            {
                "enrolment": enrolment.public_id,
                "subject": subject.public_id,
                "teacher": teacher.public_id,
                "value": 85,
            },
            content_type="application/json",
        )

        from apps.audit.models import AuditEvent

        event = AuditEvent.objects.get(action="evaluation.grade_write_denied")
        assert event.context["enrolment_id"] == str(enrolment.public_id)
        assert event.context["subject_id"] == str(subject.public_id)

    def test_accept_grade_write_with_matching_assignment(self, auth_client, institution):
        """
        Test that a teacher with a matching TeachingAssignment and the
        grade_write permission can register the grade.
        """
        cycle = AcademicCycleFactory(institution=institution)
        unit = self._open_unit(cycle)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=institution)
        teacher = PersonFactory()
        _grant_grade_write(
            auth_client.user, section=enrolment.section, subject=subject, academic_cycle=cycle
        )

        response = auth_client.post(
            reverse(
                "evaluation-unit-grades",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(unit.public_id),
                },
            ),
            {
                "enrolment": enrolment.public_id,
                "subject": subject.public_id,
                "teacher": teacher.public_id,
                "value": 85,
            },
            content_type="application/json",
        )

        assert response.status_code == 201, response.json()

    def test_teacher_grade_list_scoped_to_own_assignment(self, auth_client, institution):
        """
        Test that a teacher listing grades for a unit only sees the ones for
        sections/subjects they are assigned to.
        """
        cycle = AcademicCycleFactory(institution=institution)
        unit = self._open_unit(cycle)
        own_subject = SubjectFactory(institution=institution)
        other_subject = SubjectFactory(institution=institution)
        own_enrolment = self._enrolment(cycle)
        other_enrolment = self._enrolment(cycle)
        Grade.objects.create(
            enrolment=own_enrolment, subject=own_subject, evaluation_unit=unit, value=80
        )
        Grade.objects.create(
            enrolment=other_enrolment, subject=other_subject, evaluation_unit=unit, value=90
        )
        TeachingAssignment.objects.create(
            academic_cycle=cycle,
            section=own_enrolment.section,
            subject=own_subject,
            teacher=auth_client.user.person,
            starts_on=cycle.starts_on,
        )

        response = auth_client.get(
            reverse(
                "evaluation-unit-grades",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(unit.public_id),
                },
            )
        )

        assert response.status_code == 200
        results = response.json()["results"]
        assert len(results) == 1
        assert results[0]["subject"] == str(own_subject.public_id)


class TestGradeScaleAPI:
    """Tests for RF-CAL-002: Escala y validación de la nota."""

    def _enrolment(self, cycle):
        section = SectionFactory(academic_cycle=cycle)
        student = StudentFactory()
        return create_enrolment(
            student=student,
            academic_cycle=cycle,
            grade=section.grade,
            section=section,
        )

    def _open_unit(self, cycle):
        today = timezone.localdate()
        return EvaluationUnitFactory(
            academic_cycle=cycle,
            capture_starts_on=today - timedelta(days=5),
            capture_ends_on=today + timedelta(days=5),
        )

    def test_reject_value_above_scale_api(self, auth_client, institution):
        """
        Scenario 10: Nota fuera de rango
        GIVEN un docente registrando notas
        WHEN introduce un valor superior a cien
        THEN el sistema rechaza el valor indicando el rango admitido
        """
        cycle = AcademicCycleFactory(institution=institution)
        unit = self._open_unit(cycle)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=institution)
        teacher = PersonFactory()

        response = auth_client.post(
            reverse(
                "evaluation-unit-grades",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(unit.public_id),
                },
            ),
            {
                "enrolment": enrolment.public_id,
                "subject": subject.public_id,
                "teacher": teacher.public_id,
                "value": 101,
            },
            content_type="application/json",
        )

        assert response.status_code == 400
        assert "entre 0 y 100" in response.json()["error"]["detail"]["value"][0]

    def test_reject_negative_value_api(self, auth_client, institution):
        """
        Test that a negative value is rejected via the API.
        """
        cycle = AcademicCycleFactory(institution=institution)
        unit = self._open_unit(cycle)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=institution)
        teacher = PersonFactory()

        response = auth_client.post(
            reverse(
                "evaluation-unit-grades",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(unit.public_id),
                },
            ),
            {
                "enrolment": enrolment.public_id,
                "subject": subject.public_id,
                "teacher": teacher.public_id,
                "value": -1,
            },
            content_type="application/json",
        )

        assert response.status_code == 400

    def test_reject_non_numeric_value_api(self, auth_client, institution):
        """
        Test that a non-numeric value is rejected via the API.
        """
        cycle = AcademicCycleFactory(institution=institution)
        unit = self._open_unit(cycle)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=institution)
        teacher = PersonFactory()

        response = auth_client.post(
            reverse(
                "evaluation-unit-grades",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(unit.public_id),
                },
            ),
            {
                "enrolment": enrolment.public_id,
                "subject": subject.public_id,
                "teacher": teacher.public_id,
                "value": "not-a-number",
            },
            content_type="application/json",
        )

        assert response.status_code == 400

    def test_accept_boundary_values_api(self, auth_client, institution):
        """
        Test that the scale boundaries (0 and 100) are accepted via the API.
        """
        cycle = AcademicCycleFactory(institution=institution)
        unit = self._open_unit(cycle)
        subject = SubjectFactory(institution=institution)
        teacher = PersonFactory()
        url = reverse(
            "evaluation-unit-grades",
            kwargs={
                "cycle_public_id": str(cycle.public_id),
                "unit_public_id": str(unit.public_id),
            },
        )

        for value in (0, 100):
            enrolment = self._enrolment(cycle)
            _grant_grade_write(
                auth_client.user,
                section=enrolment.section,
                subject=subject,
                academic_cycle=cycle,
            )
            response = auth_client.post(
                url,
                {
                    "enrolment": enrolment.public_id,
                    "subject": subject.public_id,
                    "teacher": teacher.public_id,
                    "value": value,
                },
                content_type="application/json",
            )
            assert response.status_code == 201, response.json()
            assert response.json()["value"] == value


class TestCurrentAverageAPI:
    """Tests for RF-CAL-003: Distinción entre sin calificar y cero."""

    def _enrolment(self, cycle):
        section = SectionFactory(academic_cycle=cycle)
        student = StudentFactory()
        return create_enrolment(
            student=student,
            academic_cycle=cycle,
            grade=section.grade,
            section=section,
        )

    def _units(self, cycle, count):
        today = timezone.localdate()
        units = []
        for i in range(count):
            starts = today + timedelta(days=i * 70)
            units.append(
                EvaluationUnitFactory(
                    academic_cycle=cycle,
                    number=i + 1,
                    starts_on=starts,
                    ends_on=starts + timedelta(days=60),
                    capture_starts_on=today - timedelta(days=5),
                    capture_ends_on=today + timedelta(days=5),
                )
            )
        return units

    def test_current_average_excludes_pending_units_api(self, auth_client, institution):
        """
        Scenario 11: Promedio en curso con notas pendientes
        GET {cycle}/enrolments/{enrolment_id}/subjects/{subject_id}/current-average/
        """
        cycle = AcademicCycleFactory(institution=institution)
        units = self._units(cycle, 4)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=institution)
        teacher = PersonFactory()
        _grant_grade_write(
            auth_client.user, section=enrolment.section, subject=subject, academic_cycle=cycle
        )

        grades_url = reverse(
            "evaluation-unit-grades",
            kwargs={
                "cycle_public_id": str(cycle.public_id),
                "unit_public_id": str(units[0].public_id),
            },
        )
        auth_client.post(
            grades_url,
            {
                "enrolment": enrolment.public_id,
                "subject": subject.public_id,
                "teacher": teacher.public_id,
                "value": 80,
            },
            content_type="application/json",
        )
        grades_url = reverse(
            "evaluation-unit-grades",
            kwargs={
                "cycle_public_id": str(cycle.public_id),
                "unit_public_id": str(units[1].public_id),
            },
        )
        auth_client.post(
            grades_url,
            {
                "enrolment": enrolment.public_id,
                "subject": subject.public_id,
                "teacher": teacher.public_id,
                "value": 90,
            },
            content_type="application/json",
        )

        response = auth_client.get(
            reverse(
                "grade-current-average",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "enrolment_id": enrolment.public_id,
                    "subject_id": subject.public_id,
                },
            )
        )

        assert response.status_code == 200
        data = response.json()
        assert data["average"] == 85
        assert data["graded_units"] == 2
        assert data["pending_units"] == 2
        assert data["total_units"] == 4

    def test_current_average_is_none_when_nothing_graded_api(self, auth_client, institution):
        """
        Test that the average is null, not zero, when nothing is graded yet.
        """
        cycle = AcademicCycleFactory(institution=institution)
        self._units(cycle, 2)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=institution)

        response = auth_client.get(
            reverse(
                "grade-current-average",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "enrolment_id": enrolment.public_id,
                    "subject_id": subject.public_id,
                },
            )
        )

        assert response.status_code == 200
        data = response.json()
        assert data["average"] is None
        assert data["pending_units"] == 2

    def test_current_average_enrolment_not_found_returns_404(self, auth_client, institution):
        """
        Test endpoint with an enrolment from a different cycle.
        """
        cycle = AcademicCycleFactory(institution=institution)
        other_cycle = AcademicCycleFactory(
            institution=institution,
            year=cycle.year + 1,
            starts_on=date(cycle.year + 1, 1, 1),
            ends_on=date(cycle.year + 1, 12, 31),
            status="draft",
        )
        enrolment = self._enrolment(other_cycle)
        subject = SubjectFactory(institution=institution)

        response = auth_client.get(
            reverse(
                "grade-current-average",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "enrolment_id": enrolment.public_id,
                    "subject_id": subject.public_id,
                },
            )
        )

        assert response.status_code == 404


class TestFinalSubjectGradeAPI:
    """Tests for RF-RES-001: Nota final de la subárea."""

    def _enrolment(self, cycle):
        section = SectionFactory(academic_cycle=cycle)
        student = StudentFactory()
        return create_enrolment(
            student=student,
            academic_cycle=cycle,
            grade=section.grade,
            section=section,
        )

    def _units(self, cycle, count):
        today = timezone.localdate()
        units = []
        for i in range(count):
            starts = today + timedelta(days=i * 70)
            units.append(
                EvaluationUnitFactory(
                    academic_cycle=cycle,
                    number=i + 1,
                    starts_on=starts,
                    ends_on=starts + timedelta(days=60),
                    capture_starts_on=today - timedelta(days=5),
                    capture_ends_on=today + timedelta(days=5),
                )
            )
        return units

    def test_final_grade_is_the_average_of_all_graded_units_api(self, auth_client, institution):
        """
        Scenario 12: Promedio de las unidades
        GET {cycle}/enrolments/{enrolment_id}/subjects/{subject_id}/final-grade/
        """
        cycle = AcademicCycleFactory(institution=institution)
        units = self._units(cycle, 2)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=institution)
        teacher = PersonFactory()
        _grant_grade_write(
            auth_client.user, section=enrolment.section, subject=subject, academic_cycle=cycle
        )

        grades_url = reverse(
            "evaluation-unit-grades",
            kwargs={
                "cycle_public_id": str(cycle.public_id),
                "unit_public_id": str(units[0].public_id),
            },
        )
        auth_client.post(
            grades_url,
            {
                "enrolment": enrolment.public_id,
                "subject": subject.public_id,
                "teacher": teacher.public_id,
                "value": 60,
            },
            content_type="application/json",
        )
        grades_url = reverse(
            "evaluation-unit-grades",
            kwargs={
                "cycle_public_id": str(cycle.public_id),
                "unit_public_id": str(units[1].public_id),
            },
        )
        auth_client.post(
            grades_url,
            {
                "enrolment": enrolment.public_id,
                "subject": subject.public_id,
                "teacher": teacher.public_id,
                "value": 100,
            },
            content_type="application/json",
        )

        response = auth_client.get(
            reverse(
                "grade-final-subject-grade",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "enrolment_id": enrolment.public_id,
                    "subject_id": subject.public_id,
                },
            )
        )

        assert response.status_code == 200
        data = response.json()
        assert data["average"] == 80
        assert data["graded_units"] == 2
        assert data["pending_units"] == 0

    def test_final_grade_enrolment_not_found_returns_404(self, auth_client, institution):
        """
        Test endpoint with an invalid enrolment ID.
        """
        cycle = AcademicCycleFactory(institution=institution)
        subject = SubjectFactory(institution=institution)

        response = auth_client.get(
            reverse(
                "grade-final-subject-grade",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "enrolment_id": "00000000-0000-0000-0000-000000000000",
                    "subject_id": subject.public_id,
                },
            )
        )

        assert response.status_code == 404


class TestFinalGradeRoundingAPI:
    """Tests for RF-RES-002: Punto único de redondeo."""

    def _enrolment(self, cycle):
        section = SectionFactory(academic_cycle=cycle)
        student = StudentFactory()
        return create_enrolment(
            student=student,
            academic_cycle=cycle,
            grade=section.grade,
            section=section,
        )

    def _units(self, cycle, count):
        today = timezone.localdate()
        units = []
        for i in range(count):
            starts = today + timedelta(days=i * 70)
            units.append(
                EvaluationUnitFactory(
                    academic_cycle=cycle,
                    number=i + 1,
                    starts_on=starts,
                    ends_on=starts + timedelta(days=60),
                    capture_starts_on=today - timedelta(days=5),
                    capture_ends_on=today + timedelta(days=5),
                )
            )
        return units

    def test_half_fraction_rounds_up_api(self, auth_client, institution):
        """
        Scenario: Fracción exacta de un medio
        GIVEN un estudiante cuyo promedio de unidades es 59.5
        WHEN se calcula su nota final
        THEN el resultado es 60
        """
        cycle = AcademicCycleFactory(institution=institution)
        units = self._units(cycle, 2)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=institution)
        teacher = PersonFactory()
        _grant_grade_write(
            auth_client.user, section=enrolment.section, subject=subject, academic_cycle=cycle
        )

        for unit, value in zip(units, (59, 60), strict=True):
            auth_client.post(
                reverse(
                    "evaluation-unit-grades",
                    kwargs={
                        "cycle_public_id": str(cycle.public_id),
                        "unit_public_id": str(unit.public_id),
                    },
                ),
                {
                    "enrolment": enrolment.public_id,
                    "subject": subject.public_id,
                    "teacher": teacher.public_id,
                    "value": value,
                },
                content_type="application/json",
            )

        response = auth_client.get(
            reverse(
                "grade-final-subject-grade",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "enrolment_id": enrolment.public_id,
                    "subject_id": subject.public_id,
                },
            )
        )

        assert response.status_code == 200
        data = response.json()
        assert data["average"] == 59.5
        assert data["final_grade"] == 60


class TestSubjectApprovalAPI:
    """Tests for RF-RES-003: Aprobación de la subárea."""

    def _enrolment(self, cycle):
        section = SectionFactory(academic_cycle=cycle)
        student = StudentFactory()
        return create_enrolment(
            student=student,
            academic_cycle=cycle,
            grade=section.grade,
            section=section,
        )

    def _register_final_grade(self, auth_client, cycle, institution, *, value):
        unit = EvaluationUnitFactory(academic_cycle=cycle, number=1)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=institution)
        teacher = PersonFactory()
        _grant_grade_write(
            auth_client.user, section=enrolment.section, subject=subject, academic_cycle=cycle
        )
        auth_client.post(
            reverse(
                "evaluation-unit-grades",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(unit.public_id),
                },
            ),
            {
                "enrolment": enrolment.public_id,
                "subject": subject.public_id,
                "teacher": teacher.public_id,
                "value": value,
            },
            content_type="application/json",
        )
        return enrolment, subject

    def test_final_grade_at_threshold_is_approved_api(self, auth_client, institution):
        """
        Scenario: Nota final en el umbral
        GIVEN un estudiante con nota final de exactamente sesenta en una subárea
        WHEN se determina su condición
        THEN la subárea queda aprobada
        """
        cycle = AcademicCycleFactory(institution=institution)
        enrolment, subject = self._register_final_grade(auth_client, cycle, institution, value=60)

        response = auth_client.get(
            reverse(
                "grade-final-subject-grade",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "enrolment_id": enrolment.public_id,
                    "subject_id": subject.public_id,
                },
            )
        )

        assert response.status_code == 200
        data = response.json()
        assert data["final_grade"] == 60
        assert data["approved"] is True

    def test_final_grade_below_threshold_is_not_approved_api(self, auth_client, institution):
        cycle = AcademicCycleFactory(institution=institution)
        enrolment, subject = self._register_final_grade(auth_client, cycle, institution, value=59)

        response = auth_client.get(
            reverse(
                "grade-final-subject-grade",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "enrolment_id": enrolment.public_id,
                    "subject_id": subject.public_id,
                },
            )
        )

        assert response.status_code == 200
        assert response.json()["approved"] is False


class TestEnrolmentGradesAPI:
    """Tests for RF-CAL-007: Visibilidad de las notas."""

    def _enrolment(self, cycle):
        section = SectionFactory(academic_cycle=cycle)
        student = StudentFactory()
        return create_enrolment(
            student=student,
            academic_cycle=cycle,
            grade=section.grade,
            section=section,
        )

    def _guardian_user(self, *, student):
        guardian = GuardianFactory()
        user = UserFactory(person=guardian.person)
        permission = PermissionFactory(codename="student_view_basic")
        RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
        create_student_guardian_relation(
            student=student, guardian=guardian, relationship_label="Madre"
        )
        return user

    def test_guardian_sees_only_associated_student_grades(self, client, institution):
        """
        Scenario: Encargado consulta el portal
        GIVEN un encargado con un estudiante asociado
        WHEN consulta las notas en su portal
        THEN el sistema presenta únicamente las de ese estudiante
        """
        cycle = AcademicCycleFactory(institution=institution)
        unit = EvaluationUnitFactory(academic_cycle=cycle)
        subject = SubjectFactory(institution=institution)

        enrolment = self._enrolment(cycle)
        Grade.objects.create(enrolment=enrolment, subject=subject, evaluation_unit=unit, value=88)

        other_enrolment = self._enrolment(cycle)
        Grade.objects.create(
            enrolment=other_enrolment, subject=subject, evaluation_unit=unit, value=42
        )

        user = self._guardian_user(student=enrolment.student)
        client.force_login(user)

        response = client.get(
            reverse(
                "enrolment-grades",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "enrolment_id": str(enrolment.public_id),
                },
            )
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["value"] == 88

    def test_guardian_without_association_is_denied(self, client, institution):
        """
        A guardian without a current association to the enrolment's student
        must not be able to read that student's grades.
        """
        cycle = AcademicCycleFactory(institution=institution)
        unit = EvaluationUnitFactory(academic_cycle=cycle)
        subject = SubjectFactory(institution=institution)

        enrolment = self._enrolment(cycle)
        Grade.objects.create(enrolment=enrolment, subject=subject, evaluation_unit=unit, value=88)

        unrelated_student = StudentFactory()
        user = self._guardian_user(student=unrelated_student)
        client.force_login(user)

        response = client.get(
            reverse(
                "enrolment-grades",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "enrolment_id": str(enrolment.public_id),
                },
            )
        )

        assert response.status_code == 403

    def test_enrolment_not_found_returns_404_for_grades(self, auth_client, institution):
        cycle = AcademicCycleFactory(institution=institution)

        response = auth_client.get(
            reverse(
                "enrolment-grades",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "enrolment_id": "00000000-0000-0000-0000-000000000000",
                },
            )
        )

        assert response.status_code == 404


ATTENDANCE_SERVICE_PATH = "apps.attendance.services.compute_attendance_percentage"


class TestRecoveryEligibilityAPI:
    """Tests for RF-RES-004: Elegibilidad de recuperación (endpoint contract)."""

    def _setup(self, institution, *, plan_size, failed_count):
        cycle = AcademicCycleFactory(institution=institution)
        section = SectionFactory(academic_cycle=cycle)
        enrolment = create_enrolment(
            student=StudentFactory(),
            academic_cycle=cycle,
            grade=section.grade,
            section=section,
        )
        today = timezone.localdate()
        unit = EvaluationUnitFactory(
            academic_cycle=cycle,
            number=1,
            starts_on=today,
            ends_on=today + timedelta(days=60),
            capture_starts_on=today - timedelta(days=5),
            capture_ends_on=today + timedelta(days=5),
        )
        teacher = PersonFactory()
        for index in range(plan_size):
            subject = SubjectFactory(institution=institution)
            CurriculumPlan.objects.create(
                academic_cycle=cycle, grade=section.grade, subject=subject
            )
            register_unit_grade(
                enrolment=enrolment,
                subject=subject,
                evaluation_unit=unit,
                teacher=teacher,
                value=50 if index < failed_count else 80,
            )
        return cycle, enrolment

    def _url(self, cycle, enrolment):
        return reverse(
            "recovery-eligibility",
            kwargs={
                "cycle_public_id": str(cycle.public_id),
                "enrolment_id": str(enrolment.public_id),
            },
        )

    def test_eligible_student_contract(self, auth_client, institution):
        """
        Escenario 1: Estudiante elegible
        GET {cycle}/enrolments/{enrolment_id}/recovery-eligibility/
        """
        cycle, enrolment = self._setup(institution, plan_size=8, failed_count=2)

        with patch(ATTENDANCE_SERVICE_PATH, return_value=SimpleNamespace(percentage=85.0)):
            response = auth_client.get(self._url(cycle, enrolment))

        assert response.status_code == 200
        data = response.json()
        assert data["eligible"] is True
        assert data["reasons"] == []
        assert data["failed_subjects"] == 2
        assert data["total_subjects"] == 8
        assert data["failed_limit"] == 3

    def test_not_eligible_by_attendance_contract(self, auth_client, institution):
        """
        Escenario 2: Asistencia insuficiente
        THEN el endpoint responde eligible=false e indica la asistencia como causa.
        """
        cycle, enrolment = self._setup(institution, plan_size=8, failed_count=2)

        with patch(ATTENDANCE_SERVICE_PATH, return_value=SimpleNamespace(percentage=75.0)):
            response = auth_client.get(self._url(cycle, enrolment))

        assert response.status_code == 200
        data = response.json()
        assert data["eligible"] is False
        assert any("asistencia" in reason.lower() for reason in data["reasons"])

    def test_not_eligible_by_failed_count_contract(self, auth_client, institution):
        """
        Escenario 3: Exceso de subáreas reprobadas
        THEN el endpoint responde eligible=false e indica la cantidad como causa.
        """
        cycle, enrolment = self._setup(institution, plan_size=12, failed_count=5)

        with patch(ATTENDANCE_SERVICE_PATH, return_value=SimpleNamespace(percentage=85.0)):
            response = auth_client.get(self._url(cycle, enrolment))

        assert response.status_code == 200
        data = response.json()
        assert data["eligible"] is False
        assert data["failed_subjects"] == 5
        assert data["failed_limit"] == 4
        assert any("subareas" in reason.lower() for reason in data["reasons"])

    def test_enrolment_not_found_returns_404(self, auth_client, institution):
        cycle = AcademicCycleFactory(institution=institution)

        response = auth_client.get(
            reverse(
                "recovery-eligibility",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "enrolment_id": "00000000-0000-0000-0000-000000000000",
                },
            )
        )

        assert response.status_code == 404


class TestRecoveryGradeAPI:
    """Tests for RF-RES-005: Registro de la nota de recuperación (endpoint contract)."""

    def _setup(self, institution, *, plan_size=8, failed_count=1, open_recovery_window=True):
        cycle = AcademicCycleFactory(institution=institution)
        section = SectionFactory(academic_cycle=cycle)
        enrolment = create_enrolment(
            student=StudentFactory(),
            academic_cycle=cycle,
            grade=section.grade,
            section=section,
        )
        today = timezone.localdate()
        unit = EvaluationUnitFactory(
            academic_cycle=cycle,
            number=1,
            starts_on=today,
            ends_on=today + timedelta(days=60),
            capture_starts_on=today - timedelta(days=5),
            capture_ends_on=today + timedelta(days=5),
        )
        teacher = PersonFactory()
        subjects = []
        for index in range(plan_size):
            subject = SubjectFactory(institution=institution)
            CurriculumPlan.objects.create(
                academic_cycle=cycle, grade=section.grade, subject=subject
            )
            register_unit_grade(
                enrolment=enrolment,
                subject=subject,
                evaluation_unit=unit,
                teacher=teacher,
                value=50 if index < failed_count else 80,
            )
            subjects.append(subject)
        if open_recovery_window:
            set_recovery_window(unit, today - timedelta(days=1), today + timedelta(days=1))
        return cycle, enrolment, subjects

    def _url(self, cycle, enrolment):
        return reverse(
            "recovery-grade-create",
            kwargs={
                "cycle_public_id": str(cycle.public_id),
                "enrolment_id": str(enrolment.public_id),
            },
        )

    def test_register_recovery_grade_success(self, auth_client, institution):
        """
        Escenario 1: Recuperación aprobada
        POST {cycle}/enrolments/{enrolment_id}/recovery-grades/
        THEN 201, condicion aprobada por recuperacion, nota final original conservada.
        """
        cycle, enrolment, subjects = self._setup(institution)

        with patch(ATTENDANCE_SERVICE_PATH, return_value=SimpleNamespace(percentage=90.0)):
            response = auth_client.post(
                self._url(cycle, enrolment),
                {"subject": str(subjects[0].public_id), "value": 65},
                content_type="application/json",
            )

        assert response.status_code == 201
        data = response.json()
        assert data["value"] == 65
        assert data["original_final_grade"] == 50
        assert data["condition"] == "approved_by_recovery"

        # The original final grade stays consultable on its own endpoint.
        final = auth_client.get(
            reverse(
                "grade-final-subject-grade",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "enrolment_id": str(enrolment.public_id),
                    "subject_id": str(subjects[0].public_id),
                },
            )
        ).json()
        assert final["final_grade"] == 50
        assert final["condition"] == "approved_by_recovery"

    def test_register_recovery_grade_rejected_for_non_eligible(self, auth_client, institution):
        """
        Escenario 2: Intento sobre un estudiante no elegible
        THEN 400 con la causa de la no elegibilidad y ninguna nota registrada.
        """
        cycle, enrolment, subjects = self._setup(institution)

        with patch(ATTENDANCE_SERVICE_PATH, return_value=SimpleNamespace(percentage=70.0)):
            response = auth_client.post(
                self._url(cycle, enrolment),
                {"subject": str(subjects[0].public_id), "value": 65},
                content_type="application/json",
            )

        assert response.status_code == 400
        assert "asistencia" in response.content.decode().lower()
        assert RecoveryGrade.objects.count() == 0

    def test_recovery_grade_enrolment_not_found_returns_404(self, auth_client, institution):
        cycle = AcademicCycleFactory(institution=institution)
        subject = SubjectFactory(institution=institution)

        response = auth_client.post(
            reverse(
                "recovery-grade-create",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "enrolment_id": "00000000-0000-0000-0000-000000000000",
                },
            ),
            {"subject": str(subject.public_id), "value": 65},
            content_type="application/json",
        )

        assert response.status_code == 404


class TestCaptureProgressAPI:
    """Tests for RF-CAL-008: Seguimiento de notas pendientes (endpoint contract)."""

    def _setup(self, institution):
        cycle = AcademicCycleFactory(institution=institution)
        section = SectionFactory(academic_cycle=cycle)
        for _ in range(2):
            create_enrolment(
                student=StudentFactory(),
                academic_cycle=cycle,
                grade=section.grade,
                section=section,
            )
        today = timezone.localdate()
        unit = EvaluationUnitFactory(
            academic_cycle=cycle,
            number=1,
            starts_on=today - timedelta(days=5),
            ends_on=today + timedelta(days=5),
            capture_starts_on=today - timedelta(days=5),
            capture_ends_on=today + timedelta(days=5),
        )
        subject_a = SubjectFactory(institution=institution)
        subject_b = SubjectFactory(institution=institution)
        for subject in (subject_a, subject_b):
            CurriculumPlan.objects.create(
                academic_cycle=cycle, grade=section.grade, subject=subject
            )
        teacher_b = PersonFactory()
        TeachingAssignment.objects.create(
            academic_cycle=cycle,
            section=section,
            subject=subject_b,
            teacher=teacher_b,
            starts_on=cycle.starts_on,
        )
        for enrolment in section.enrolments.all():
            register_unit_grade(
                enrolment=enrolment,
                subject=subject_a,
                evaluation_unit=unit,
                teacher=PersonFactory(),
                value=70,
            )
        return cycle, unit, subject_b, teacher_b

    def test_capture_progress_before_window_close(self, auth_client, institution):
        """
        Escenario: Consulta antes del cierre de la ventana
        GET {cycle}/evaluation-units/{unit_public_id}/capture-progress/
        """
        cycle, unit, subject_b, teacher_b = self._setup(institution)

        response = auth_client.get(
            reverse(
                "evaluation-unit-capture-progress",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(unit.public_id),
                },
            )
        )

        assert response.status_code == 200
        data = response.json()
        assert data["window_open"] is True
        pending = next(
            row for row in data["rows"] if row["subject"]["public_id"] == str(subject_b.public_id)
        )
        assert pending["students_pending"] == 2
        assert pending["students_graded"] == 0
        assert pending["teacher"]["public_id"] == str(teacher_b.public_id)
        assert pending["teacher"]["name"] == str(teacher_b)

    def test_capture_progress_unit_not_found_returns_404(self, auth_client, institution):
        cycle = AcademicCycleFactory(institution=institution)

        response = auth_client.get(
            reverse(
                "evaluation-unit-capture-progress",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": "00000000-0000-0000-0000-000000000000",
                },
            )
        )

        assert response.status_code == 404


class TestBulkGradeUploadAPI:
    """Tests for RF-CAL-004: Carga masiva desde archivo (endpoint contract)."""

    def _setup(self, auth_client, institution):
        cycle = AcademicCycleFactory(institution=institution)
        section = SectionFactory(academic_cycle=cycle)
        enrolments = [
            create_enrolment(
                student=StudentFactory(),
                academic_cycle=cycle,
                grade=section.grade,
                section=section,
            )
            for _ in range(2)
        ]
        today = timezone.localdate()
        unit = EvaluationUnitFactory(
            academic_cycle=cycle,
            number=1,
            starts_on=today - timedelta(days=5),
            ends_on=today + timedelta(days=5),
            capture_starts_on=today - timedelta(days=5),
            capture_ends_on=today + timedelta(days=5),
        )
        subject = SubjectFactory(institution=institution)
        _grant_grade_write(auth_client.user, section=section, subject=subject, academic_cycle=cycle)
        return cycle, unit, section, subject, enrolments

    def _url(self, cycle, unit):
        return reverse(
            "evaluation-unit-grades-bulk",
            kwargs={
                "cycle_public_id": str(cycle.public_id),
                "unit_public_id": str(unit.public_id),
            },
        )

    def _csv(self, lines):
        body = "student_code,value\n" + "\n".join(lines) + "\n"
        return SimpleUploadedFile("grades.csv", body.encode("utf-8"), content_type="text/csv")

    def test_valid_file_registers_all_rows(self, auth_client, institution):
        cycle, unit, section, subject, enrolments = self._setup(auth_client, institution)

        response = auth_client.post(
            self._url(cycle, unit),
            {
                "file": self._csv(
                    [
                        f"{enrolments[0].student.student_code},70",
                        f"{enrolments[1].student.student_code},85",
                    ]
                ),
                "subject": str(subject.public_id),
                "section": str(section.public_id),
                "teacher": str(auth_client.user.person.public_id),
            },
        )

        assert response.status_code == 200
        assert response.json() == {"created": 2}
        assert Grade.objects.filter(evaluation_unit=unit, subject=subject).count() == 2

    def test_file_with_invalid_row_saves_nothing(self, auth_client, institution):
        cycle, unit, section, subject, enrolments = self._setup(auth_client, institution)

        response = auth_client.post(
            self._url(cycle, unit),
            {
                "file": self._csv(
                    [
                        f"{enrolments[0].student.student_code},70",
                        "STU-NOT-IN-SECTION,80",
                    ]
                ),
                "subject": str(subject.public_id),
                "section": str(section.public_id),
                "teacher": str(auth_client.user.person.public_id),
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert data["created"] == 0
        assert [e["row"] for e in data["errors"]] == [2]
        assert Grade.objects.filter(evaluation_unit=unit).count() == 0

    def test_unit_not_found_returns_404(self, auth_client, institution):
        cycle = AcademicCycleFactory(institution=institution)
        section = SectionFactory(academic_cycle=cycle)
        subject = SubjectFactory(institution=institution)

        response = auth_client.post(
            reverse(
                "evaluation-unit-grades-bulk",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": "00000000-0000-0000-0000-000000000000",
                },
            ),
            {
                "file": self._csv(["STU-0001,70"]),
                "subject": str(subject.public_id),
                "section": str(section.public_id),
                "teacher": str(auth_client.user.person.public_id),
            },
        )

        assert response.status_code == 404
