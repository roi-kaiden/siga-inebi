"""
Endpoints de sugerencia: lo que el formulario muestra antes de guardar.

Todos son de lectura y derivan del mismo codigo que usa el alta. Eso es lo que se
prueba aca: que el valor OFRECIDO sea el valor GUARDADO. Un formulario que
sugiere "SED-01" y almacena "SED-02" es peor que uno que no sugiere nada, porque
la persona ya anoto el primero en un papel.
"""

from datetime import date

import pytest
from django.urls import reverse

from apps.academics.models import AcademicCycle, Level
from tests.factories.academic import (
    AcademicCycleFactory,
    CampusFactory,
    LevelFactory,
)
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
)
from tests.factories.students import StudentFactory
from tests.factories.teachers import TeacherFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def _grant_student_editing(user):
    """El alta de expedientes exige permiso con alcance; la sugerencia no."""
    permission = PermissionFactory(codename="student_edit_basic")
    assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    return ScopeGrantFactory(assignment=assignment, module_key="students")


def _institutional_person(first_name, last_name, cui, birth_date):
    return {
        "first_name": first_name,
        "last_name": last_name,
        "cui": cui,
        "birth_date": birth_date,
        "phone_number": "55501234",
        "sex": "female",
        "nationality": "Guatemalteca",
        "address": "1a Calle 2-34 Zona 1",
        "department": "Guatemala",
        "municipality": "Guatemala",
    }


# --------------------------------------------------------------------------- #
# codigos
# --------------------------------------------------------------------------- #


def test_student_next_code_matches_what_creating_would_assign(auth_client, institution):
    _grant_student_editing(auth_client.user)
    suggested = auth_client.get(reverse("student-next-code")).json()["student_code"]

    created = auth_client.post(
        reverse("student-list"),
        {"person": _institutional_person("Ana", "Lopez", "1234567890123", "2010-03-15")},
        content_type="application/json",
    )

    assert created.status_code == 201
    assert created.json()["student_code"] == suggested


def test_student_creation_still_accepts_an_explicit_code(auth_client, institution):
    _grant_student_editing(auth_client.user)

    response = auth_client.post(
        reverse("student-list"),
        {
            "person": _institutional_person("Ana", "Lopez", "1234567890123", "2010-03-15"),
            "student_code": "MIN-42",
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["student_code"] == "MIN-42"


def test_student_next_code_skips_a_code_already_taken(auth_client, institution):
    taken = auth_client.get(reverse("student-next-code")).json()["student_code"]
    StudentFactory(student_code=taken)

    assert auth_client.get(reverse("student-next-code")).json()["student_code"] != taken


def test_teacher_next_code_matches_what_creating_would_assign(auth_client, institution):
    suggested = auth_client.get(reverse("teacher-next-code")).json()["employee_code"]

    created = auth_client.post(
        reverse("teacher-list"),
        {
            "person": _institutional_person("Luis", "Perez", "2345678901234", "1985-07-22"),
            "specialty": "Matematica",
            "position": "Docente Titulado",
        },
        content_type="application/json",
    )

    assert created.status_code == 201
    assert created.json()["employee_code"] == suggested


def test_teacher_next_code_continues_the_existing_series(auth_client, institution):
    TeacherFactory(employee_code="DOC-012")

    assert auth_client.get(reverse("teacher-next-code")).json()["employee_code"] == "DOC-013"


def test_level_next_code_matches_what_creating_would_assign(auth_client, admin_client, institution):
    CampusFactory(institution=institution)
    suggested = auth_client.get(reverse("level-next-code")).json()["code"]

    created = admin_client.post(
        reverse("level-list-create"),
        {"name": "Preprimaria"},
        content_type="application/json",
    )

    assert created.status_code == 201
    assert created.json()["code"] == suggested


def test_grade_next_code_is_derived_from_its_level(auth_client, admin_client, institution):
    level = LevelFactory(institution=institution, code="BAS")

    suggested = auth_client.get(reverse("level-grade-next-code", args=[level.public_id])).json()[
        "code"
    ]

    created = admin_client.post(
        reverse("level-grade-list-create", args=[level.public_id]),
        {"name": "Primero Basico"},
        content_type="application/json",
    )

    assert suggested == "BAS1"
    assert created.status_code == 201
    assert created.json()["code"] == "BAS1"


def test_suggestion_endpoints_require_authentication(client, institution):
    assert client.get(reverse("student-next-code")).status_code == 403
    assert client.get(reverse("teacher-next-code")).status_code == 403
    assert client.get(reverse("campus-next-code")).status_code == 403
    assert client.get(reverse("level-next-code")).status_code == 403


# --------------------------------------------------------------------------- #
# ciclo escolar
# --------------------------------------------------------------------------- #


def test_cycle_defaults_derive_name_and_validity_from_the_year(auth_client, institution):
    payload = auth_client.get(reverse("academic-cycle-defaults"), {"year": 2027}).json()

    assert payload == {
        "year": 2027,
        "name": "Ciclo 2027",
        # 15/01/2027 es viernes; 31/10/2027 es domingo, asi que cierra el viernes 29.
        "starts_on": "2027-01-15",
        "ends_on": "2027-10-29",
    }


def test_cycle_defaults_without_a_year_propose_the_next_one(auth_client, institution):
    """
    Lo que el establecimiento va a registrar es el ciclo siguiente al ultimo.

    Proponer el anio corriente obligaria a corregirlo cada vez, que es la clase
    de valor por omision que estorba mas que ayudar.
    """
    AcademicCycleFactory(institution=institution, year=2026, starts_on=date(2026, 1, 15))

    assert auth_client.get(reverse("academic-cycle-defaults")).json()["year"] == 2027


def test_cycle_defaults_rejects_a_year_that_is_not_a_number(auth_client, institution):
    response = auth_client.get(reverse("academic-cycle-defaults"), {"year": "dos mil"})

    assert response.status_code == 400


def test_creating_a_cycle_with_only_the_year_derives_the_rest(admin_client, institution):
    response = admin_client.post(
        reverse("academic-cycle-list-create"),
        {"year": 2029},
        content_type="application/json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Ciclo 2029"
    # 15/01/2029 es lunes; 31/10/2029 es miercoles.
    assert (body["starts_on"], body["ends_on"]) == ("2029-01-15", "2029-10-31")
    assert body["status"] == AcademicCycle.CycleStatus.DRAFT


def test_creating_a_cycle_still_accepts_explicit_dates_and_name(admin_client, institution):
    """Un acuerdo ministerial puede mover el calendario; la API lo permite."""
    response = admin_client.post(
        reverse("academic-cycle-list-create"),
        {
            "year": 2030,
            "name": "Ciclo escolar 2030 (extendido)",
            "starts_on": "2030-01-07",
            "ends_on": "2030-11-15",
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Ciclo escolar 2030 (extendido)"
    assert (body["starts_on"], body["ends_on"]) == ("2030-01-07", "2030-11-15")


# --------------------------------------------------------------------------- #
# orden por posicion, a traves de la API
# --------------------------------------------------------------------------- #


def test_level_can_be_inserted_after_a_sibling(admin_client, institution):
    primaria = LevelFactory(institution=institution, code="PRI", sequence=1)
    LevelFactory(institution=institution, code="DIV", sequence=2)

    response = admin_client.post(
        reverse("level-list-create"),
        {"name": "Basico", "insert_after": str(primaria.public_id)},
        content_type="application/json",
    )

    assert response.status_code == 201
    assert [
        (level.code, level.sequence)
        for level in Level.objects.filter(institution=institution).order_by("sequence")
    ] == [("PRI", 1), ("NIV-01", 2), ("DIV", 3)]


def test_level_can_be_moved_to_the_first_position(admin_client, institution):
    """``insert_after: null`` es la primera posicion, no "sin posicion"."""
    LevelFactory(institution=institution, code="PRI", sequence=1)
    basico = LevelFactory(institution=institution, code="BAS", sequence=2)

    response = admin_client.patch(
        reverse("level-detail", args=[basico.public_id]),
        {"insert_after": None},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert [
        (level.code, level.sequence)
        for level in Level.objects.filter(institution=institution).order_by("sequence")
    ] == [("BAS", 1), ("PRI", 2)]


def test_renaming_a_level_leaves_its_position_alone(admin_client, institution):
    LevelFactory(institution=institution, code="PRI", sequence=1)
    basico = LevelFactory(institution=institution, code="BAS", sequence=2)

    response = admin_client.patch(
        reverse("level-detail", args=[basico.public_id]),
        {"name": "Ciclo Basico"},
        content_type="application/json",
    )

    assert response.status_code == 200
    basico.refresh_from_db()
    assert (basico.name, basico.sequence) == ("Ciclo Basico", 2)


def test_inserting_after_a_level_of_another_institution_is_rejected(admin_client, institution):
    stranger = LevelFactory(code="OTR")

    response = admin_client.post(
        reverse("level-list-create"),
        {"name": "Basico", "insert_after": str(stranger.public_id)},
        content_type="application/json",
    )

    assert response.status_code == 404
    assert not Level.objects.filter(institution=institution).exists()
