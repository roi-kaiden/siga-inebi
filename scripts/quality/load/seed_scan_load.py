"""Siembra datos SINTETICOS para la prueba de carga de escaneo (RNF-REN-001/002).

Se ejecuta DENTRO del backend, con las mismas fabricas que usan las pruebas:

    docker compose exec -T backend python manage.py shell \
        < scripts/quality/load/seed_scan_load.py > /tmp/scan-load-seed.json

Variables: LOAD_OPERATORS (def. 3) y LOAD_STUDENTS (def. 300).

Escribe en stdout una unica linea JSON (ids, usuarios y codigos). NUNCA usar
contra una base con datos reales: crea cuentas con contrasena conocida.
"""

import json
import os

from django.db import connection

from apps.attendance.models import AttendanceEvent  # noqa: F401  (valida el import)
from apps.enrolments.services import create_enrolment
from tests.factories.academic import SectionFactory
from tests.factories.attendance import ControlPointFactory, JornadaParametersFactory
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    UserFactory,
)
from tests.factories.students import StudentFactory

OPERATORS = int(os.environ.get("LOAD_OPERATORS", "3"))
STUDENTS = int(os.environ.get("LOAD_STUDENTS", "300"))
PASSWORD = "load-test-pass-123"  # sintetica; solo para el entorno de prueba

parameters = JornadaParametersFactory()
control_point = ControlPointFactory(campus=parameters.shift.campus)
role = RoleFactory(
    permissions=[PermissionFactory(codename=c) for c in ("attendance_scan", "attendance_record_entry")]
)

usernames = []
for _ in range(OPERATORS):
    user = UserFactory(password=PASSWORD)
    RoleAssignmentFactory(user=user, role=role)
    usernames.append(user.username)

SECTION_SIZE = 20  # cupo por seccion; sembrar mas en una sola la rechaza
section = None
student_codes = []
for n in range(STUDENTS):
    if n % SECTION_SIZE == 0:
        section = SectionFactory(academic_cycle=parameters.academic_cycle)
    student = StudentFactory()
    create_enrolment(
        student=student,
        academic_cycle=parameters.academic_cycle,
        grade=section.offering.grade,
        section=section,
    )
    student_codes.append(student.student_code)

print(
    json.dumps(
        {
            "password": PASSWORD,
            "operators": usernames,
            "shift_id": str(parameters.shift.public_id),
            "control_point_id": str(control_point.public_id),
            "student_codes": student_codes,
            "database": connection.settings_dict["NAME"],
        }
    )
)
