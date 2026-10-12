"""
Contract tests for the published OpenAPI schema.

The schema is not documentation-only: it is the source of truth for anything
generated from it (typed clients, SDKs) and the contract other teams read in
`/api/v1/docs/`. A wrong schema is worse than no schema, because it looks
authoritative.

These endpoints are handwritten on ``GenericAPIView``/``APIView``, so
drf-spectacular cannot infer their contract and silently documents something
false unless every operation declares it with ``extend_schema``. These tests
exist so removing an annotation fails here instead of shipping a lie.
"""

import pytest
from drf_spectacular.drainage import GENERATOR_STATS, reset_generator_stats
from drf_spectacular.generators import SchemaGenerator

READ_ONLY_FIELDS = {"public_id", "created_at", "updated_at"}

# Listados que paginan dentro del handler: drf-spectacular no lo puede inferir.
PAGINATED_LISTINGS = [
    "/api/v1/audit/events/",
    "/api/v1/attendance/events/",
    "/api/v1/attendance/alerts/",
    "/api/v1/attendance/jornada-parameters/",
    "/api/v1/reporting/alerts/",
    "/api/v1/reporting/absence-threshold-parameters/",
    "/api/v1/students/{public_id}/emergency-contacts/",
]

# Operaciones cuyo cuerpo real difiere del serializer de lectura de la vista.
WRITE_BODIES = [
    ("/api/v1/attendance/events/", "post", {"student_id", "shift_id", "event_date"}),
    ("/api/v1/attendance/jornada-parameters/", "post", {"shift_id", "academic_cycle_id"}),
    ("/api/v1/attendance/jornada-closures/", "post", {"shift_id", "event_date"}),
    ("/api/v1/reporting/absence-threshold-parameters/", "post", {"shift_id", "max_absences"}),
    ("/api/v1/reporting/alert-evaluations/", "post", {"shift_id", "event_date"}),
]

# Vistas de configuracion que quedaban FUERA del schema por no poder inferirse.
CONFIG_OPERATIONS = [
    ("/api/v1/academics/evaluation-config/", "get"),
    ("/api/v1/academics/evaluation-config/", "patch"),
    ("/api/v1/academics/cycles/{cycle_public_id}/evaluation-config/", "get"),
    ("/api/v1/academics/cycles/{cycle_public_id}/evaluation-config/", "patch"),
    (
        "/api/v1/academics/cycles/{cycle_public_id}/evaluation-units/"
        "{unit_public_id}/recovery-window/",
        "patch",
    ),
]


@pytest.fixture(scope="module")
def schema():
    return SchemaGenerator().get_schema(request=None, public=True)


def _resolve(schema, node):
    """Sigue los `$ref` hasta el componente concreto."""
    while node and "$ref" in node:
        node = schema["components"]["schemas"][node["$ref"].split("/")[-1]]
    return node or {}


def _request_schema(schema, operation):
    content = (operation.get("requestBody") or {}).get("content", {})
    for mime in ("application/json", "multipart/form-data"):
        if mime in content:
            return _resolve(schema, content[mime]["schema"])
    return None


def _response_schema(schema, operation, code="200"):
    content = operation.get("responses", {}).get(code, {}).get("content", {})
    if "application/json" not in content:
        return None
    return _resolve(schema, content["application/json"]["schema"])


@pytest.mark.parametrize("path", PAGINATED_LISTINGS)
def test_paginated_listing_documents_the_envelope(schema, path):
    body = _response_schema(schema, schema["paths"][path]["get"])

    assert body is not None, f"{path} GET no documenta respuesta"
    # Sin esto el schema dice "objeto suelto" y un cliente generado no encuentra
    # `results`, aunque el endpoint si lo devuelva.
    assert "results" in body.get("properties", {}), (
        f"{path} GET deberia documentar el sobre paginado; "
        f"documenta {sorted(body.get('properties', {}))}"
    )
    assert "count" in body["properties"]


@pytest.mark.parametrize("path,verb,expected_subset", WRITE_BODIES)
def test_write_body_uses_the_real_input_contract(schema, path, verb, expected_subset):
    body = _request_schema(schema, schema["paths"][path][verb])

    assert body is not None, f"{path} {verb.upper()} no documenta cuerpo"
    required = set(body.get("required", []))
    assert expected_subset <= required, (
        f"{path} {verb.upper()} deberia exigir {sorted(expected_subset)}; exige {sorted(required)}"
    )


def test_no_write_body_requires_read_only_fields(schema):
    """Un campo que el backend ignora no puede ser obligatorio al enviarlo."""
    offenders = []
    for path, operations in schema["paths"].items():
        for verb in ("post", "patch", "put"):
            if verb not in operations:
                continue
            body = _request_schema(schema, operations[verb])
            if not body:
                continue
            leaked = set(body.get("required", [])) & READ_ONLY_FIELDS
            if leaked:
                offenders.append(f"{verb.upper()} {path} -> {sorted(leaked)}")

    assert offenders == [], "Campos de solo lectura exigidos en el cuerpo:\n" + "\n".join(offenders)


def test_acknowledge_takes_no_body(schema):
    """La alerta se identifica por la ruta y el actor por la sesion."""
    operation = schema["paths"]["/api/v1/reporting/alerts/{public_id}/acknowledge/"]["post"]

    assert _request_schema(schema, operation) is None


@pytest.mark.parametrize("path,verb", CONFIG_OPERATIONS)
def test_configuration_endpoints_are_published(schema, path, verb):
    """Estas vistas se descartaban del schema por no poder inferirse."""
    operation = schema["paths"].get(path, {}).get(verb)

    assert operation is not None, f"{verb.upper()} {path} no aparece en el schema"
    assert _response_schema(schema, operation) is not None, (
        f"{verb.upper()} {path} no documenta su respuesta"
    )


def test_query_filters_are_documented(schema):
    """Los filtros del tablero de alertas viajan en la URL: deben estar en el schema."""
    operation = schema["paths"]["/api/v1/reporting/alerts/"]["get"]
    documented = {p["name"] for p in operation.get("parameters", []) if p["in"] == "query"}

    assert {"shift_id", "event_date", "alert_type", "is_active", "acknowledged"} <= documented


def test_schema_generation_has_no_errors():
    """
    Una vista que drf-spectacular no puede inferir se descarta con un error y
    desaparece del schema sin que nadie lo note: era el caso de las tres vistas
    de configuracion de evaluacion. Este test convierte ese silencio en un fallo.
    """
    reset_generator_stats()
    SchemaGenerator().get_schema(request=None, public=True)

    errors = list(GENERATOR_STATS._error_cache)

    assert errors == [], "La generacion del schema reporta errores:\n" + "\n".join(
        str(error) for error in errors
    )


@pytest.mark.parametrize("url", ["/api/v1/schema/", "/api/v1/docs/"])
def test_openapi_endpoints_reject_anonymous_requests(client, url):
    response = client.get(url)

    assert response.status_code in {401, 403}


@pytest.mark.parametrize("url", ["/api/v1/schema/", "/api/v1/docs/"])
def test_openapi_endpoints_serve_authenticated_sessions(auth_client, url):
    response = auth_client.get(url)

    assert response.status_code == 200
