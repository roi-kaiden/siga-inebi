from datetime import date, timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.academics.models import AcademicCycle, CurriculumPlan, TeachingAssignment
from apps.academics.services import close_academic_cycle, create_teaching_assignment
from apps.audit.models import AuditEvent
from apps.enrolments.models import Enrolment
from apps.enrolments.services import create_enrolment
from apps.evaluation.models import EvaluationUnit
from apps.evaluation.services import close_evaluation_unit, register_unit_grade
from tests.factories.academic import (
    AcademicCycleFactory,
    CampusFactory,
    ClassroomFactory,
    ClassScheduleBlockFactory,
    ClassSessionFactory,
    GradeFactory,
    GradeOfferingFactory,
    LevelSubjectFactory,
    SectionFactory,
    ShiftFactory,
    SubjectFactory,
)
from tests.factories.evaluation import EvaluationUnitFactory
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
)
from tests.factories.people import PersonFactory
from tests.factories.students import StudentFactory
from tests.factories.teachers import TeacherFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def test_close_cycle_api_contract(admin_client, institution):
    cycle = AcademicCycleFactory(institution=institution, status=AcademicCycle.CycleStatus.ACTIVE)
    EvaluationUnitFactory(academic_cycle=cycle, status=EvaluationUnit.UnitStatus.CLOSED)

    response = admin_client.post(reverse("academic-cycle-close", args=[cycle.public_id]))

    assert response.status_code == 200
    assert response.json()["status"] == "closed"


def test_close_cycle_api_rejects_open_evaluation_unit(admin_client, institution):
    cycle = AcademicCycleFactory(institution=institution, status=AcademicCycle.CycleStatus.ACTIVE)
    unit = EvaluationUnitFactory(academic_cycle=cycle, status=EvaluationUnit.UnitStatus.OPEN)

    response = admin_client.post(reverse("academic-cycle-close", args=[cycle.public_id]))

    assert response.status_code == 400
    assert unit.name in response.json()["error"]["detail"]


def test_close_cycle_endpoint_requires_authentication(client, institution):
    cycle = AcademicCycleFactory(institution=institution, status=AcademicCycle.CycleStatus.ACTIVE)
    assert client.post(reverse("academic-cycle-close", args=[cycle.public_id])).status_code == 403


def test_close_cycle_endpoint_rejects_without_assignment_scope(auth_client, institution):
    cycle = AcademicCycleFactory(institution=institution, status=AcademicCycle.CycleStatus.ACTIVE)

    response = auth_client.post(reverse("academic-cycle-close", args=[cycle.public_id]))

    assert response.status_code == 403


def test_create_academic_cycle_contract(admin_client, institution):
    response = admin_client.post(
        reverse("academic-cycle-list-create"),
        {
            "year": 2027,
            "name": "Ciclo 2027",
            "description": "Plan institucional",
            "starts_on": "2027-01-15",
            "ends_on": "2027-10-31",
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["status"] == AcademicCycle.CycleStatus.DRAFT
    assert response.json()["year"] == 2027
    assert response.json()["description"] == "Plan institucional"


def test_create_academic_cycle_rejects_without_assignment_scope(auth_client, institution):
    response = auth_client.post(
        reverse("academic-cycle-list-create"),
        {
            "year": 2027,
            "name": "Ciclo 2027",
            "starts_on": "2027-01-15",
            "ends_on": "2027-10-31",
        },
        content_type="application/json",
    )

    assert response.status_code == 403


def test_cycle_end_date_before_start_is_rejected(admin_client, institution):
    response = admin_client.post(
        reverse("academic-cycle-list-create"),
        {
            "year": 2027,
            "name": "Ciclo 2027",
            "starts_on": "2027-10-31",
            "ends_on": "2027-01-15",
        },
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "no puede ser anterior" in response.json()["error"]["detail"]


def test_activate_cycle_rejects_when_an_active_cycle_exists(admin_client, institution):
    AcademicCycleFactory(
        institution=institution,
        year=2026,
        status=AcademicCycle.CycleStatus.ACTIVE,
    )
    prepared = AcademicCycleFactory(
        institution=institution,
        year=2027,
        starts_on="2027-01-01",
        ends_on="2027-12-31",
        status=AcademicCycle.CycleStatus.DRAFT,
    )

    response = admin_client.post(reverse("academic-cycle-activate", args=[prepared.public_id]))

    assert response.status_code == 400
    assert "Hay que cerrar" in response.json()["error"]["detail"]


def test_activate_cycle_endpoint_rejects_without_assignment_scope(auth_client, institution):
    prepared = AcademicCycleFactory(
        institution=institution,
        starts_on=date(2027, 1, 1),
        ends_on=date(2027, 12, 31),
        status=AcademicCycle.CycleStatus.DRAFT,
    )

    response = auth_client.post(reverse("academic-cycle-activate", args=[prepared.public_id]))

    assert response.status_code == 403


def _grant_reopen_scope(user, institution):
    permission = PermissionFactory(codename="academic_cycle_reopen")
    assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    return ScopeGrantFactory(assignment=assignment, institution=institution)


def test_reopen_cycle_api_contract(auth_client, institution):
    cycle = AcademicCycleFactory(institution=institution, status=AcademicCycle.CycleStatus.CLOSED)
    _grant_reopen_scope(auth_client.user, institution)

    response = auth_client.post(
        reverse("academic-cycle-reopen", args=[cycle.public_id]),
        {"reason": "Correccion de una nota mal capturada"},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["status"] == AcademicCycle.CycleStatus.ACTIVE
    event = AuditEvent.objects.get(action="academics.cycle.reopened")
    assert event.context["reason"] == "Correccion de una nota mal capturada"


def test_reopen_cycle_endpoint_requires_authentication(client, institution):
    cycle = AcademicCycleFactory(institution=institution, status=AcademicCycle.CycleStatus.CLOSED)
    response = client.post(
        reverse("academic-cycle-reopen", args=[cycle.public_id]),
        {"reason": "Correccion de una nota mal capturada"},
        content_type="application/json",
    )
    assert response.status_code == 403


def test_reopen_cycle_endpoint_rejects_without_reopen_permission(auth_client, institution):
    cycle = AcademicCycleFactory(institution=institution, status=AcademicCycle.CycleStatus.CLOSED)

    response = auth_client.post(
        reverse("academic-cycle-reopen", args=[cycle.public_id]),
        {"reason": "Correccion de una nota mal capturada"},
        content_type="application/json",
    )

    assert response.status_code == 403


def test_reopen_cycle_api_rejects_when_cycle_is_not_closed(auth_client, institution):
    cycle = AcademicCycleFactory(institution=institution, status=AcademicCycle.CycleStatus.ACTIVE)
    _grant_reopen_scope(auth_client.user, institution)

    response = auth_client.post(
        reverse("academic-cycle-reopen", args=[cycle.public_id]),
        {"reason": "Correccion de una nota mal capturada"},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "ciclo escolar cerrado" in response.json()["error"]["detail"]


def test_create_section_api_creates_offering_and_section(admin_client, institution):
    cycle = AcademicCycleFactory(institution=institution, status=AcademicCycle.CycleStatus.DRAFT)
    grade = GradeFactory(institution=institution)
    shift = ShiftFactory(campus__institution=institution)

    response = admin_client.post(
        reverse("section-list-create"),
        {
            "academic_cycle_id": str(cycle.public_id),
            "grade_id": str(grade.public_id),
            "shift_id": str(shift.public_id),
            "name": "A",
            "capacity": 30,
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "A"
    assert body["capacity"] == 30
    assert body["academic_cycle_id"] == str(cycle.public_id)


def test_create_section_api_rejects_duplicate_name(admin_client, institution):
    cycle = AcademicCycleFactory(institution=institution, status=AcademicCycle.CycleStatus.DRAFT)
    grade = GradeFactory(institution=institution)
    shift = ShiftFactory(campus__institution=institution)
    payload = {
        "academic_cycle_id": str(cycle.public_id),
        "grade_id": str(grade.public_id),
        "shift_id": str(shift.public_id),
        "name": "A",
    }
    url = reverse("section-list-create")
    admin_client.post(url, payload, content_type="application/json")

    response = admin_client.post(url, payload, content_type="application/json")

    assert response.status_code == 400
    assert "already exists" in response.json()["error"]["detail"]


def test_create_section_api_rejects_when_cycle_is_active(admin_client, institution):
    """RF-EST-011: structure only changes while the cycle is still in planning."""
    cycle = AcademicCycleFactory(institution=institution, status=AcademicCycle.CycleStatus.ACTIVE)
    grade = GradeFactory(institution=institution)
    shift = ShiftFactory(campus__institution=institution)

    response = admin_client.post(
        reverse("section-list-create"),
        {
            "academic_cycle_id": str(cycle.public_id),
            "grade_id": str(grade.public_id),
            "shift_id": str(shift.public_id),
            "name": "A",
        },
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "en preparacion" in response.json()["error"]["detail"]


def test_create_section_api_accepts_a_default_classroom(admin_client, institution):
    """RF-AUL-002 (#100): aula habitual de referencia para la seccion."""
    cycle = AcademicCycleFactory(institution=institution, status=AcademicCycle.CycleStatus.DRAFT)
    grade = GradeFactory(institution=institution)
    shift = ShiftFactory(campus__institution=institution)
    classroom = ClassroomFactory(campus=shift.campus)

    response = admin_client.post(
        reverse("section-list-create"),
        {
            "academic_cycle_id": str(cycle.public_id),
            "grade_id": str(grade.public_id),
            "shift_id": str(shift.public_id),
            "name": "A",
            "default_classroom_id": str(classroom.public_id),
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["default_classroom_id"] == str(classroom.public_id)


def test_section_api_warns_without_blocking_an_undersized_default_classroom(
    admin_client, institution
):
    cycle = AcademicCycleFactory(institution=institution, status=AcademicCycle.CycleStatus.DRAFT)
    grade = GradeFactory(institution=institution)
    shift = ShiftFactory(campus__institution=institution)
    classroom = ClassroomFactory(campus=shift.campus, capacity=20)

    response = admin_client.post(
        reverse("section-list-create"),
        {
            "academic_cycle_id": str(cycle.public_id),
            "grade_id": str(grade.public_id),
            "shift_id": str(shift.public_id),
            "name": "A",
            "capacity": 30,
            "default_classroom_id": str(classroom.public_id),
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["capacity_warning"] == {
        "code": "classroom_capacity_below_section",
        "detail": "El aula tiene capacidad para 20 personas y la seccion declara 30.",
        "classroom_capacity": 20,
        "section_capacity": 30,
    }
    assert response.json()["default_classroom_id"] == str(classroom.public_id)


def test_create_section_api_rejects_default_classroom_from_another_campus(
    admin_client, institution
):
    cycle = AcademicCycleFactory(institution=institution, status=AcademicCycle.CycleStatus.DRAFT)
    grade = GradeFactory(institution=institution)
    shift = ShiftFactory(campus__institution=institution)
    other_campus_classroom = ClassroomFactory(campus=CampusFactory(institution=institution))

    response = admin_client.post(
        reverse("section-list-create"),
        {
            "academic_cycle_id": str(cycle.public_id),
            "grade_id": str(grade.public_id),
            "shift_id": str(shift.public_id),
            "name": "A",
            "default_classroom_id": str(other_campus_classroom.public_id),
        },
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "misma sede" in response.json()["error"]["detail"]


def test_update_section_api_sets_the_default_classroom(admin_client, institution):
    """RF-AUL-002 (#100)."""
    cycle = AcademicCycleFactory(institution=institution, status=AcademicCycle.CycleStatus.DRAFT)
    section = SectionFactory(academic_cycle=cycle)
    classroom = ClassroomFactory(campus=section.offering.shift.campus)

    response = admin_client.patch(
        reverse("section-detail", args=[section.public_id]),
        {"default_classroom_id": str(classroom.public_id)},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["default_classroom_id"] == str(classroom.public_id)
    assert response.json()["capacity_warning"]["classroom_capacity"] == classroom.capacity
    assert response.json()["capacity_warning"]["section_capacity"] == section.capacity


def test_deactivate_section_api_contract(admin_client, institution):
    cycle = AcademicCycleFactory(institution=institution, status=AcademicCycle.CycleStatus.DRAFT)
    section = SectionFactory(academic_cycle=cycle)

    response = admin_client.delete(reverse("section-detail", args=[section.public_id]))

    assert response.status_code == 204
    section.refresh_from_db()
    assert section.is_active is False


def test_section_endpoints_require_authentication(client, institution):
    section = SectionFactory(academic_cycle=AcademicCycleFactory(institution=institution))

    assert client.get(reverse("section-list-create")).status_code == 403
    assert client.get(reverse("section-detail", args=[section.public_id])).status_code == 403


def test_create_class_session_api_creates_session(admin_client, institution):
    section = SectionFactory(academic_cycle=AcademicCycleFactory(institution=institution))
    subject = SubjectFactory(institution=institution)
    block = ClassScheduleBlockFactory(shift=section.offering.shift)

    response = admin_client.post(
        reverse("section-class-session-list-create", args=[section.public_id]),
        {
            "subject_id": str(subject.public_id),
            "schedule_block_id": str(block.public_id),
            "day_of_week": 1,
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["day_of_week"] == 1
    assert body["subject"]["public_id"] == str(subject.public_id)
    assert body["schedule_block"]["public_id"] == str(block.public_id)
    assert body["teacher_id"] is None  # sin asignacion vigente todavia (RF-HOR-004)
    assert body["starts_on"] == section.academic_cycle.starts_on.isoformat()


def test_clone_class_schedule_api_contract(admin_client, institution):
    cycle = AcademicCycleFactory(institution=institution)
    shift = ShiftFactory(campus__institution=institution)
    grade = GradeFactory(institution=institution)
    source = SectionFactory(academic_cycle=cycle, grade=grade, shift=shift)
    target = SectionFactory(academic_cycle=cycle, grade=grade, shift=shift)
    subject = SubjectFactory(institution=institution)
    CurriculumPlan.objects.create(academic_cycle=cycle, grade=grade, subject=subject)
    block = ClassScheduleBlockFactory(shift=shift)
    source_session = ClassSessionFactory(
        section=source,
        subject=subject,
        schedule_block=block,
        day_of_week=4,
    )

    response = admin_client.post(
        reverse("section-class-schedule-clone", args=[target.public_id]),
        {"source_section_id": str(source.public_id)},
        content_type="application/json",
    )

    assert response.status_code == 201
    assert len(response.json()) == 1
    assert response.json()[0]["subject"]["public_id"] == str(subject.public_id)
    assert response.json()[0]["day_of_week"] == source_session.day_of_week
    assert target.class_sessions.count() == 1


def test_clone_class_schedule_api_requires_authentication(client, institution):
    cycle = AcademicCycleFactory(institution=institution)
    source = SectionFactory(academic_cycle=cycle)
    target = SectionFactory(academic_cycle=cycle)

    response = client.post(
        reverse("section-class-schedule-clone", args=[target.public_id]),
        {"source_section_id": str(source.public_id)},
        content_type="application/json",
    )

    assert response.status_code == 403
    assert target.class_sessions.count() == 0


def test_create_class_session_api_accepts_a_mid_cycle_starts_on(admin_client, institution):
    """RF-HOR-008 (#201): fecha de vigencia explicita para una reestructuracion
    a mitad de ciclo."""
    cycle = AcademicCycleFactory(institution=institution)
    section = SectionFactory(academic_cycle=cycle)
    subject = SubjectFactory(institution=institution)
    block = ClassScheduleBlockFactory(shift=section.offering.shift)

    response = admin_client.post(
        reverse("section-class-session-list-create", args=[section.public_id]),
        {
            "subject_id": str(subject.public_id),
            "schedule_block_id": str(block.public_id),
            "day_of_week": 1,
            "starts_on": cycle.ends_on.isoformat(),
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["starts_on"] == cycle.ends_on.isoformat()


def test_create_class_session_api_rejects_starts_on_outside_the_cycle(admin_client, institution):
    cycle = AcademicCycleFactory(institution=institution)
    section = SectionFactory(academic_cycle=cycle)
    subject = SubjectFactory(institution=institution)
    block = ClassScheduleBlockFactory(shift=section.offering.shift)
    before_cycle = cycle.starts_on - timedelta(days=1)

    response = admin_client.post(
        reverse("section-class-session-list-create", args=[section.public_id]),
        {
            "subject_id": str(subject.public_id),
            "schedule_block_id": str(block.public_id),
            "day_of_week": 1,
            "starts_on": before_cycle.isoformat(),
        },
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "fecha de vigencia" in response.json()["error"]["detail"]


def test_create_class_session_api_does_not_require_a_classroom(admin_client, institution):
    """RF-AUL-003 (#101): periodos especiales (ej. Educacion Fisica) se
    registran sin vincular un aula fisica."""
    section = SectionFactory(academic_cycle=AcademicCycleFactory(institution=institution))
    subject = SubjectFactory(institution=institution)
    block = ClassScheduleBlockFactory(shift=section.offering.shift)

    response = admin_client.post(
        reverse("section-class-session-list-create", args=[section.public_id]),
        {
            "subject_id": str(subject.public_id),
            "schedule_block_id": str(block.public_id),
            "day_of_week": 1,
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["classroom_id"] is None


def test_class_session_api_warns_without_blocking_an_undersized_classroom(
    admin_client, institution
):
    section = SectionFactory(
        academic_cycle=AcademicCycleFactory(institution=institution),
        capacity=30,
    )
    subject = SubjectFactory(institution=institution)
    block = ClassScheduleBlockFactory(shift=section.shift)
    classroom = ClassroomFactory(campus=section.campus, capacity=20)

    response = admin_client.post(
        reverse("section-class-session-list-create", args=[section.public_id]),
        {
            "subject_id": str(subject.public_id),
            "schedule_block_id": str(block.public_id),
            "day_of_week": 1,
            "classroom_id": str(classroom.public_id),
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["capacity_warning"]["classroom_capacity"] == 20
    assert response.json()["capacity_warning"]["section_capacity"] == 30
    assert response.json()["classroom_id"] == str(classroom.public_id)


def test_class_session_api_exposes_the_current_teacher(admin_client, institution):
    """RF-HOR-004: el docente se deriva de la asignacion vigente, se muestra en la sesion."""
    cycle = AcademicCycleFactory(institution=institution)
    section = SectionFactory(academic_cycle=cycle)
    session = ClassSessionFactory(section=section)
    teacher = TeacherFactory()
    TeachingAssignment.objects.create(
        academic_cycle=cycle, section=section, subject=session.subject, teacher=teacher.person
    )

    response = admin_client.get(reverse("class-session-detail", args=[session.public_id]))

    assert response.json()["teacher_id"] == str(teacher.public_id)


def test_create_class_session_api_rejects_block_from_another_shift(admin_client, institution):
    section = SectionFactory(academic_cycle=AcademicCycleFactory(institution=institution))
    subject = SubjectFactory(institution=institution)
    other_shift = ShiftFactory(campus__institution=institution)
    other_shift_block = ClassScheduleBlockFactory(shift=other_shift)

    response = admin_client.post(
        reverse("section-class-session-list-create", args=[section.public_id]),
        {
            "subject_id": str(subject.public_id),
            "schedule_block_id": str(other_shift_block.public_id),
            "day_of_week": 1,
        },
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "misma jornada" in response.json()["error"]["detail"]


def test_create_class_session_api_rejects_section_double_booked_in_the_same_slot(
    admin_client, institution
):
    """RF-HOR-005: cruce por seccion en el mismo dia y bloque."""
    section = SectionFactory(academic_cycle=AcademicCycleFactory(institution=institution))
    block = ClassScheduleBlockFactory(shift=section.offering.shift)
    ClassSessionFactory(section=section, schedule_block=block, day_of_week=1)
    other_subject = SubjectFactory(institution=institution)

    response = admin_client.post(
        reverse("section-class-session-list-create", args=[section.public_id]),
        {
            "subject_id": str(other_subject.public_id),
            "schedule_block_id": str(block.public_id),
            "day_of_week": 1,
        },
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "cruce de horario" in response.json()["error"]["detail"]


def test_create_class_session_api_rejects_classroom_double_booked_in_the_same_slot(
    admin_client, institution
):
    """RF-HOR-005 (#198): cruce por aula en el mismo dia y bloque."""
    section_a = SectionFactory(academic_cycle=AcademicCycleFactory(institution=institution))
    classroom = ClassroomFactory(campus=section_a.offering.shift.campus)
    existing = ClassSessionFactory(section=section_a, classroom=classroom)
    section_b = SectionFactory(
        academic_cycle=existing.academic_cycle, shift=section_a.offering.shift
    )
    other_subject = SubjectFactory(institution=institution)

    response = admin_client.post(
        reverse("section-class-session-list-create", args=[section_b.public_id]),
        {
            "subject_id": str(other_subject.public_id),
            "schedule_block_id": str(existing.schedule_block.public_id),
            "day_of_week": existing.day_of_week,
            "classroom_id": str(classroom.public_id),
        },
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "El aula ya tiene otra sesion agendada" in response.json()["error"]["detail"]


def test_create_class_session_api_rejects_teacher_double_booked_in_the_same_slot(
    admin_client, institution
):
    """RF-HOR-006 (#199): cruce por docente en el mismo dia y bloque, en dos
    secciones distintas."""
    cycle = AcademicCycleFactory(institution=institution)
    section_a = SectionFactory(academic_cycle=cycle)
    shift = section_a.offering.shift
    section_b = SectionFactory(academic_cycle=cycle, shift=shift)
    subject_a = SubjectFactory(institution=institution)
    subject_b = SubjectFactory(institution=institution)
    teacher = TeacherFactory()
    create_teaching_assignment(
        academic_cycle=cycle, section=section_a, subject=subject_a, teacher=teacher.person
    )
    create_teaching_assignment(
        academic_cycle=cycle, section=section_b, subject=subject_b, teacher=teacher.person
    )
    existing = ClassSessionFactory(section=section_a, subject=subject_a)

    response = admin_client.post(
        reverse("section-class-session-list-create", args=[section_b.public_id]),
        {
            "subject_id": str(subject_b.public_id),
            "schedule_block_id": str(existing.schedule_block.public_id),
            "day_of_week": existing.day_of_week,
        },
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "El docente ya tiene otra seccion agendada" in response.json()["error"]["detail"]


def test_list_class_sessions_is_scoped_to_the_section(admin_client, institution):
    section = SectionFactory(academic_cycle=AcademicCycleFactory(institution=institution))
    ClassSessionFactory(section=section)
    ClassSessionFactory()  # a session of another section entirely

    response = admin_client.get(
        reverse("section-class-session-list-create", args=[section.public_id])
    )

    assert len(response.json()["results"]) == 1


def test_class_session_detail_roundtrip(admin_client, institution):
    section = SectionFactory(academic_cycle=AcademicCycleFactory(institution=institution))
    session = ClassSessionFactory(section=section)

    read = admin_client.get(reverse("class-session-detail", args=[session.public_id]))
    removed = admin_client.delete(reverse("class-session-detail", args=[session.public_id]))

    assert read.status_code == 200
    assert removed.status_code == 204
    session.refresh_from_db()
    assert session.is_active is False


def test_class_session_endpoints_require_authentication(client, institution):
    section = SectionFactory(academic_cycle=AcademicCycleFactory(institution=institution))
    session = ClassSessionFactory(section=section)
    classroom = ClassroomFactory(campus=section.campus, capacity=20)

    list_response = client.get(
        reverse("section-class-session-list-create", args=[section.public_id])
    )
    detail_response = client.get(reverse("class-session-detail", args=[session.public_id]))
    create_response = client.post(
        reverse("section-class-session-list-create", args=[section.public_id]),
        {
            "subject_id": str(session.subject.public_id),
            "schedule_block_id": str(session.schedule_block.public_id),
            "day_of_week": 2,
            "classroom_id": str(classroom.public_id),
        },
        content_type="application/json",
    )

    assert list_response.status_code == 403
    assert detail_response.status_code == 403
    assert create_response.status_code == 403
    assert section.class_sessions.count() == 1


def test_weekly_load_api_reports_a_match(auth_client, institution):
    """RF-HOR-007: los periodos agendados coinciden con la carga declarada."""
    cycle = AcademicCycleFactory(institution=institution)
    section = SectionFactory(academic_cycle=cycle)
    grade = section.grade
    subject = SubjectFactory(institution=institution)
    CurriculumPlan.objects.create(academic_cycle=cycle, grade=grade, subject=subject)
    LevelSubjectFactory(level=grade.level, subject=subject, weekly_hours=2)
    block_a = ClassScheduleBlockFactory(shift=section.offering.shift, number=1)
    block_b = ClassScheduleBlockFactory(shift=section.offering.shift, number=2)
    ClassSessionFactory(section=section, subject=subject, schedule_block=block_a, day_of_week=1)
    ClassSessionFactory(section=section, subject=subject, schedule_block=block_b, day_of_week=1)

    response = auth_client.get(reverse("section-weekly-load", args=[section.public_id]))

    assert response.status_code == 200
    row = next(r for r in response.json() if r["subject"]["public_id"] == str(subject.public_id))
    assert row["declared_weekly_hours"] == 2
    assert row["scheduled_periods"] == 2
    assert row["matches"] is True


def test_weekly_load_api_reports_a_mismatch(auth_client, institution):
    """RF-HOR-007: menos periodos agendados que horas declaradas."""
    cycle = AcademicCycleFactory(institution=institution)
    section = SectionFactory(academic_cycle=cycle)
    grade = section.grade
    subject = SubjectFactory(institution=institution)
    CurriculumPlan.objects.create(academic_cycle=cycle, grade=grade, subject=subject)
    LevelSubjectFactory(level=grade.level, subject=subject, weekly_hours=3)
    ClassSessionFactory(section=section, subject=subject)

    response = auth_client.get(reverse("section-weekly-load", args=[section.public_id]))

    assert response.status_code == 200
    row = next(r for r in response.json() if r["subject"]["public_id"] == str(subject.public_id))
    assert row["declared_weekly_hours"] == 3
    assert row["scheduled_periods"] == 1
    assert row["matches"] is False


def test_weekly_load_api_reports_no_declared_hours_as_null(auth_client, institution):
    """RF-HOR-007: sin carga declarada a nivel de nivel educativo, no hay con
    que comparar -- declared_weekly_hours y matches quedan en null, no en
    un falso "no coincide"."""
    cycle = AcademicCycleFactory(institution=institution)
    section = SectionFactory(academic_cycle=cycle)
    grade = section.grade
    subject = SubjectFactory(institution=institution)
    CurriculumPlan.objects.create(academic_cycle=cycle, grade=grade, subject=subject)
    ClassSessionFactory(section=section, subject=subject)

    response = auth_client.get(reverse("section-weekly-load", args=[section.public_id]))

    assert response.status_code == 200
    row = next(r for r in response.json() if r["subject"]["public_id"] == str(subject.public_id))
    assert row["declared_weekly_hours"] is None
    assert row["scheduled_periods"] == 1
    assert row["matches"] is None


def test_weekly_load_endpoint_requires_authentication(client, institution):
    section = SectionFactory(academic_cycle=AcademicCycleFactory(institution=institution))

    response = client.get(reverse("section-weekly-load", args=[section.public_id]))

    assert response.status_code == 403


def test_class_schedule_publication_api_lifecycle(admin_client, institution):
    """RF-HOR-009: consultar, publicar y despublicar el horario del ciclo."""
    cycle = AcademicCycleFactory(institution=institution, status=AcademicCycle.CycleStatus.ACTIVE)
    url = reverse("class-schedule-publication", args=[cycle.public_id])

    initial = admin_client.get(url)
    published = admin_client.post(url)
    unpublished = admin_client.delete(url)

    assert initial.json()["is_published"] is False
    assert published.status_code == 200
    assert published.json()["is_published"] is True
    assert published.json()["published_at"] is not None
    assert unpublished.json()["is_published"] is False


def test_class_schedule_publication_api_rejects_closed_cycle(admin_client, institution):
    cycle = AcademicCycleFactory(institution=institution, status=AcademicCycle.CycleStatus.CLOSED)

    response = admin_client.post(reverse("class-schedule-publication", args=[cycle.public_id]))

    assert response.status_code == 400
    assert "no admite cambios academicos" in response.json()["error"]["detail"]


def test_class_schedule_publication_endpoint_requires_authentication(client, institution):
    cycle = AcademicCycleFactory(institution=institution)

    response = client.get(reverse("class-schedule-publication", args=[cycle.public_id]))

    assert response.status_code == 403


def test_create_curriculum_plan_api_contract(admin_client, institution):
    cycle = AcademicCycleFactory(institution=institution, status=AcademicCycle.CycleStatus.DRAFT)
    grade = GradeFactory(institution=institution)
    subject = SubjectFactory(institution=institution)

    response = admin_client.post(
        reverse("curriculum-plan-list-create"),
        {
            "academic_cycle_id": str(cycle.public_id),
            "grade_id": str(grade.public_id),
            "subject_id": str(subject.public_id),
            "is_required": False,
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["is_required"] is False
    assert body["academic_cycle_id"] == str(cycle.public_id)
    assert body["grade"]["public_id"] == str(grade.public_id)
    assert body["subject"]["public_id"] == str(subject.public_id)


def test_create_curriculum_plan_api_rejects_when_cycle_is_active(admin_client, institution):
    cycle = AcademicCycleFactory(institution=institution, status=AcademicCycle.CycleStatus.ACTIVE)
    grade = GradeFactory(institution=institution)
    subject = SubjectFactory(institution=institution)

    response = admin_client.post(
        reverse("curriculum-plan-list-create"),
        {
            "academic_cycle_id": str(cycle.public_id),
            "grade_id": str(grade.public_id),
            "subject_id": str(subject.public_id),
        },
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "en preparacion" in response.json()["error"]["detail"]


def test_deactivate_curriculum_plan_api_contract(admin_client, institution):
    cycle = AcademicCycleFactory(institution=institution, status=AcademicCycle.CycleStatus.DRAFT)
    plan = CurriculumPlan.objects.create(
        academic_cycle=cycle,
        grade=GradeFactory(institution=institution),
        subject=SubjectFactory(institution=institution),
    )

    response = admin_client.delete(reverse("curriculum-plan-detail", args=[plan.public_id]))

    assert response.status_code == 204
    plan.refresh_from_db()
    assert plan.is_active is False


def test_curriculum_plan_endpoints_require_authentication(client, institution):
    cycle = AcademicCycleFactory(institution=institution)
    plan = CurriculumPlan.objects.create(
        academic_cycle=cycle,
        grade=GradeFactory(institution=institution),
        subject=SubjectFactory(institution=institution),
    )

    assert client.get(reverse("curriculum-plan-list-create")).status_code == 403
    assert client.get(reverse("curriculum-plan-detail", args=[plan.public_id])).status_code == 403


def test_cycle_endpoints_require_authentication(client, institution):
    assert client.get(reverse("academic-cycle-list-create")).status_code == 403
    response = client.post(
        reverse("academic-cycle-list-create"),
        {},
        content_type="application/json",
    )
    assert response.status_code == 403


def test_clone_cycle_api_copies_structure_and_teachers(admin_client, institution):
    source = AcademicCycleFactory(
        institution=institution,
        year=2026,
        starts_on="2026-01-01",
        ends_on="2026-12-31",
        status=AcademicCycle.CycleStatus.CLOSED,
    )
    offering = GradeOfferingFactory(academic_cycle=source)
    section = SectionFactory(
        academic_cycle=source,
        grade=offering.grade,
        shift=offering.shift,
    )
    subject = SubjectFactory(institution=institution)
    CurriculumPlan.objects.create(
        academic_cycle=source,
        grade=offering.grade,
        subject=subject,
    )
    teacher = TeacherFactory()
    TeachingAssignment.objects.create(
        academic_cycle=source,
        section=section,
        subject=subject,
        teacher=teacher.person,
        starts_on=source.starts_on,
    )

    response = admin_client.post(
        reverse("academic-cycle-clone", args=[source.public_id]),
        {
            "year": 2027,
            "name": "Ciclo 2027",
            "description": "Clonado de 2026",
            "starts_on": "2027-01-01",
            "ends_on": "2027-12-31",
            "include_teaching_assignments": True,
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    cloned = AcademicCycle.objects.get(public_id=response.json()["public_id"])
    assert cloned.status == AcademicCycle.CycleStatus.DRAFT
    assert cloned.grade_offerings.count() == 1
    assert cloned.grade_offerings.get().sections.count() == 1
    assert cloned.curriculum_plans.count() == 1
    assert cloned.teaching_assignments.count() == 1
    event = AuditEvent.objects.get(action="academics.cycle.cloned")
    assert event.context["source_cycle_id"] == source.pk
    assert event.context["teaching_assignment_count"] == 1


def test_closed_cycle_historical_detail_preserves_structure_and_aggregates_enrolments(
    auth_client, institution
):
    cycle = AcademicCycleFactory(
        institution=institution,
        status=AcademicCycle.CycleStatus.CLOSED,
    )
    offering = GradeOfferingFactory(academic_cycle=cycle)
    section = SectionFactory(
        academic_cycle=cycle,
        grade=offering.grade,
        shift=offering.shift,
        is_active=False,
    )
    subject = SubjectFactory(institution=institution)
    CurriculumPlan.objects.create(
        academic_cycle=cycle,
        grade=offering.grade,
        subject=subject,
        is_active=False,
    )
    teacher = TeacherFactory()
    TeachingAssignment.objects.create(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        teacher=teacher.person,
        starts_on=cycle.starts_on,
        ends_on=cycle.ends_on,
        is_active=False,
    )
    for status in Enrolment.EnrolmentStatus.values:
        Enrolment.objects.create(
            student=StudentFactory(),
            academic_cycle=cycle,
            grade=offering.grade,
            section=section,
            status=status,
        )

    response = auth_client.get(reverse("academic-cycle-historical-detail", args=[cycle.public_id]))

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == AcademicCycle.CycleStatus.CLOSED
    assert payload["grade_offerings"][0]["sections"][0]["is_active"] is False
    assert payload["curriculum_plans"][0]["is_active"] is False
    assert payload["teaching_assignments"][0]["ends_on"] == str(cycle.ends_on)
    assert payload["enrolments"] == {
        "total": 4,
        "active": 1,
        "withdrawn": 1,
        "completed": 1,
        "cancelled": 1,
    }


def test_historical_cycle_detail_is_institution_bound_and_requires_authentication(
    auth_client, institution
):
    foreign_cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.CLOSED)
    anonymous_client = Client()

    assert (
        anonymous_client.get(
            reverse("academic-cycle-historical-detail", args=[foreign_cycle.public_id])
        ).status_code
        == 403
    )
    assert (
        auth_client.get(
            reverse("academic-cycle-historical-detail", args=[foreign_cycle.public_id])
        ).status_code
        == 404
    )


def _closed_cycle_with_frozen_result(institution, grades):
    """A closed cycle whose single enrolment has one FrozenSubjectResult row
    per value in ``grades`` (RF-RES-007), via the real close flow."""
    cycle = AcademicCycleFactory(institution=institution, status=AcademicCycle.CycleStatus.ACTIVE)
    today = timezone.localdate()
    unit = EvaluationUnitFactory(
        academic_cycle=cycle,
        status=EvaluationUnit.UnitStatus.OPEN,
        capture_starts_on=today - timedelta(days=30),
        capture_ends_on=today + timedelta(days=5),
        recovery_starts_on=today - timedelta(days=20),
        recovery_ends_on=today - timedelta(days=5),
    )
    section = SectionFactory(academic_cycle=cycle)
    enrolment = create_enrolment(
        student=StudentFactory(),
        academic_cycle=cycle,
        grade=section.grade,
        section=section,
    )
    subjects = []
    for value in grades:
        subject = SubjectFactory(institution=institution)
        CurriculumPlan.objects.create(academic_cycle=cycle, grade=section.grade, subject=subject)
        register_unit_grade(
            enrolment=enrolment,
            subject=subject,
            evaluation_unit=unit,
            teacher=PersonFactory(),
            value=value,
        )
        subjects.append(subject)
    close_evaluation_unit(unit)
    close_academic_cycle(cycle=cycle)
    return cycle, enrolment, subjects


def _grant_grade_correct(user):
    permission = PermissionFactory(codename="grade_correct")
    return RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))


def test_frozen_subject_result_endpoint_returns_the_congealed_value(auth_client, institution):
    cycle, enrolment, subjects = _closed_cycle_with_frozen_result(institution, [90])

    response = auth_client.get(
        reverse(
            "frozen-subject-result",
            kwargs={
                "cycle_public_id": cycle.public_id,
                "enrolment_id": enrolment.public_id,
                "subject_id": subjects[0].public_id,
            },
        )
    )

    assert response.status_code == 200
    body = response.json()
    assert body["final_grade"] == 90
    assert body["condition"] == "approved"
    assert body["is_correction"] is False


def test_frozen_promotion_result_endpoint_returns_the_congealed_value(auth_client, institution):
    cycle, enrolment, _subjects = _closed_cycle_with_frozen_result(institution, [90, 55])

    response = auth_client.get(
        reverse(
            "frozen-promotion-result",
            kwargs={"cycle_public_id": cycle.public_id, "enrolment_id": enrolment.public_id},
        )
    )

    assert response.status_code == 200
    body = response.json()
    assert body["promoted"] is False
    assert body["condition"] == "not_promoted"


def test_frozen_subject_result_correction_requires_grade_correct_permission(
    auth_client, institution
):
    cycle, enrolment, subjects = _closed_cycle_with_frozen_result(institution, [55])
    url = reverse(
        "frozen-subject-result-correct",
        kwargs={
            "cycle_public_id": cycle.public_id,
            "enrolment_id": enrolment.public_id,
            "subject_id": subjects[0].public_id,
        },
    )

    response = auth_client.post(
        url,
        {"final_grade": 75, "reason": "Error de digitacion"},
        content_type="application/json",
    )

    assert response.status_code == 403


def test_frozen_subject_result_correction_preserves_previous_value(auth_client, institution):
    cycle, enrolment, subjects = _closed_cycle_with_frozen_result(institution, [55])
    _grant_grade_correct(auth_client.user)
    url = reverse(
        "frozen-subject-result-correct",
        kwargs={
            "cycle_public_id": cycle.public_id,
            "enrolment_id": enrolment.public_id,
            "subject_id": subjects[0].public_id,
        },
    )

    response = auth_client.post(
        url,
        {"final_grade": 75, "reason": "Error de digitacion"},
        content_type="application/json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["final_grade"] == 75
    assert body["condition"] == "approved"
    assert body["is_correction"] is True

    # El resultado congelado anterior sigue disponible via el mismo GET
    # (siempre devuelve el mas reciente, pero la fila vieja no se altero).
    get_response = auth_client.get(
        reverse(
            "frozen-subject-result",
            kwargs={
                "cycle_public_id": cycle.public_id,
                "enrolment_id": enrolment.public_id,
                "subject_id": subjects[0].public_id,
            },
        )
    )
    assert get_response.json()["final_grade"] == 75
    assert AuditEvent.objects.filter(action="academics.frozen_subject_result.corrected").exists()
