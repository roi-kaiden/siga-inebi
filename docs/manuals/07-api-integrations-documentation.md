# Manual de Documentación de API e Integraciones — SIGA-INEBI

**Documento:** Manual 07 — Documentación de API e Integraciones  
**Sistema:** Sistema de Información y Gestión Académica — Instituto Nacional de Educación Básica para Adultos (SIGA-INEBI)  
**Versión del documento:** 1.0.0 (Fase 7 — Candidato de Entrega)  
**Responsable:** Roí (Documentos, contratos API y auditoría transversal)  
**Revisor independiente asignado:** Estuardo  
**Especificación viva:** OpenAPI 3.0 en `/api/v1/schema/` y Swagger UI interactivo en `/api/v1/docs/`  

---

## 1. Objetivo y alcance

Este documento define de forma exhaustiva, contractual y verificable la interfaz de programación de aplicaciones (API REST) y las directrices de integración de **SIGA-INEBI**.

Cumple estrictamente con las directrices de `docs/manuals/07-api-integrations-documentation-instructions.md`, las convenciones arquitectónicas de `docs/architecture/api-conventions.md` y las reglas de diseño institucional establecidas en `AGENTS.md`:

1. **Contratos verificables:** Todos los endpoints documentados corresponden a rutas, vistas y serializadores implementados en la aplicación. No se documentan endpoints hipotéticos ni diferidos.
2. **Denegación por defecto:** Cada recurso sensible exige autenticación previa, permisos atómicos obligatorios y alcances institucionales validados en el backend.
3. **Privacidad y confidencialidad:** Todos los ejemplos son sintéticos y sanitizados. No se incluyen nombres reales de alumnos, credenciales institucionales, tokens en texto claro ni secretos criptográficos.
4. **Autosuficiencia arquitectónica:** Se documenta la independencia total del sistema respecto a servicios de terceros para su operativa diaria base.

---

## 2. Información general y convenciones

### 2.1 URL base y versionado

Todas las rutas públicas y protegidas de la API se exponen bajo el prefijo unificado de versión:

```text
/api/v1/
```

Cualquier cambio futuro que introduzca rupturas contractuales en serializadores, nombres de campos o comportamiento de estado requerirá un nuevo prefijo (`/api/v2/`) conforme a la política de evolución de software institucional.

### 2.2 Formato de datos, fechas y zona horaria

- **Formato de intercambio:** `application/json; charset=utf-8` tanto para el cuerpo de solicitudes como de respuestas, salvo endpoints de descarga binaria (`application/pdf`, `image/jpeg`, `image/png`, `text/csv`).
- **Nomenclatura de atributos:** Nombres técnicos en inglés utilizando `snake_case` (ej. `public_id`, `created_at`, `is_active`). Nombres de catálogos funcionales y mensajes de error en español formal.
- **Representación temporal (ISO 8601):**
  - Marcas temporales de auditoría y sistema: Formato extendido UTC `YYYY-MM-DDTHH:MM:SSZ` (ej. `2026-10-12T15:30:00Z`).
  - Fechas de calendario académico y vigencias: Formato estándar `YYYY-MM-DD` (ej. `2026-01-15`).
- **Zona horaria de referencia:** Toda fecha efectiva, evento de asistencia o cierre de jornada se evalúa en la zona horaria institucional de Guatemala: `America/Guatemala` (UTC-06:00).

### 2.3 Identificadores de recursos

Para evitar ataques de enumeración y fugas de volumen de datos:
- Las claves primarias internas (`id` enteros secuenciales) están aisladas en la base de datos PostgreSQL.
- Las URLs de la API exponen identificadores opacos universales UUID v4 (`public_id`), por ejemplo `b1a2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d`.
- Los códigos de catálogo administrativo se normalizan en mayúsculas o minúsculas según el dominio (ej. plantillas `CONST`, roles `profesor_titular`).

### 2.4 Paginación estándar

Los endpoints de listado de colecciones aplican paginación basada en número de página:

```json
{
  "count": 142,
  "next": "/api/v1/students/?page=2",
  "previous": null,
  "results": [ ... ]
}
```

- Parámetro `page`: Número de página solicitada (base 1).
- Parámetro `page_size`: Límite de elementos por página (predeterminado: 20; máximo configurable: 100).

### 2.5 Respuestas HTTP y sobre de errores normalizado

La API utiliza los códigos de estado HTTP estándar:

| Código | Significado | Condición de aplicación |
|---|---|---|
| **200 OK** | Éxito | Consultas y actualizaciones exitosas. |
| **201 Created** | Creado | Recursos creados satisfactoriamente con encabezado `Location` o `public_id`. |
| **204 No Content** | Sin contenido | Operaciones exitosas que no retornan cuerpo (desactivaciones lógicas o verificaciones). |
| **400 Bad Request** | Error de dominio o formato | Cuerpos inválidos, tipos no permitidos o violación de invariantes de negocio (`DomainError`). |
| **401 Unauthorized** | No autenticado | Solicitud anónima a un endpoint protegido por sesión. |
| **403 Forbidden** | Denegado / Prohibido | Usuario autenticado carece del permiso atómico o del alcance (`ScopeGrant`) necesario. |
| **404 Not Found** | No encontrado | El recurso con el `public_id` indicado no existe en la institución del usuario. |
| **409 Conflict** | Conflicto de concurrencia | Conflicto de estado, duplicación de código único o colisión en asignaciones. |
| **429 Too Many Requests** | Límite de tasa excedido | Exceso de solicitudes en endpoints públicos con control de ráfaga (throttle). |
| **500 Internal Error** | Error no controlado | Fallo inesperado en el servidor; nunca revela detalles de depuración al cliente. |

#### Estructura del sobre de error (`api_exception_handler`):

```json
{
  "error": {
    "status_code": 400,
    "detail": "El archivo adjunto excede el tamano maximo de 10485760 bytes."
  }
}
```

En validaciones de formularios con múltiples campos:

```json
{
  "error": {
    "status_code": 400,
    "detail": {
      "code": ["Ya existe un tipo de documento con el codigo 'CONST' en esta institucion."],
      "name": ["Este campo es requerido."]
    }
  }
}
```

---

## 3. Autenticación, autorización y seguridad

### 3.1 Mecanismo de autenticación por sesión segura

SIGA-INEBI utiliza **sesiones HTTP respaldadas por cookies criptográficas** gestionadas por Django REST Framework y la capa de sesiones de base de datos:

1. **Credenciales en login:** El cliente envía credenciales vía `POST /api/v1/auth/login/`.
2. **Emisión de cookies:** Al autenticar exitosamente, el servidor emite una cookie de sesión (`sessionid`) con los siguientes atributos obligatorios:
   - `HttpOnly`: Impide acceso a la cookie mediante scripts JavaScript en el navegador (mitigación contra XSS).
   - `SameSite=Lax`: Restringe el envío de la cookie en solicitudes cruzadas (mitigación contra CSRF).
   - `Secure`: Requerido en producción bajo HTTPS.
3. **Prohibición de persistencia en frontend:** **Bajo ninguna circunstancia** se persisten tokens de autenticación o credenciales en `localStorage`, `sessionStorage` o variables globales de JavaScript. La sesión reside exclusivamente en la cookie controlada por el navegador.

### 3.2 Protección contra Cross-Site Request Forgery (CSRF)

- Todas las peticiones de modificación (`POST`, `PUT`, `PATCH`, `DELETE`) en el navegador requieren la inclusión del encabezado `X-CSRFToken`.
- El token CSRF se lee de la cookie `csrftoken` emitida por el backend al cargar la aplicación y se adjunta automáticamente por el cliente HTTP (`axios` / `fetch`).

### 3.3 Modelo de autorización: Denegación por defecto y alcances obligatorios

El sistema aplica una matriz de seguridad de tres capas:

```text
[ Usuario Autenticado ]
       ↓
[ 1. Rol Activo ] ──> ¿Tiene asignado al menos un rol institucional vigente?
       ↓
[ 2. Permiso Atómico ] ──> ¿El rol contiene el permiso atómico específico (ej. document_read)?
       ↓
[ 3. Alcance Obligatorio (ScopeGrant) ] ──> ¿El usuario posee alcance sobre el recurso destino
                                             (ej. institución, grado, sección o estudiante)?
       ↓
[ Operación Permitida / Asiento de Auditoría ]
```

- **Denegación por defecto:** Cualquier intento de acceso sin permiso o fuera del alcance asignado se rechaza con HTTP 403 y genera un registro de auditoría (`action="*.denied"`).
- **Inexistencia de puertas traseras:** Los administradores y docentes se rigen por la misma comprobación de alcance. La cuenta `superuser` solo se utiliza para emergencias de infraestructura y mantenimiento.

---

## 4. Catálogo de endpoints por dominio

### 4.1 Autenticación y control de sesión (`/api/v1/auth/`)

| Método | Ruta | Finalidad | Permiso requerido |
|---|---|---|---|
| `POST` | `/api/v1/auth/login/` | Iniciar sesión institucional y emitir cookie | Ninguno (público) |
| `POST` | `/api/v1/auth/logout/` | Cerrar la sesión actual e invalidar cookie | Autenticado |
| `POST` | `/api/v1/auth/logout/all/` | Revocar todas las sesiones activas del usuario | Autenticado |
| `GET` | `/api/v1/auth/me/` | Consultar perfil, persona, roles y permisos del actor | Autenticado |
| `POST` | `/api/v1/auth/password/change/` | Cambio de contraseña por el propio titular (RF-AUT-006) | Autenticado |

#### Ejemplo sanitizado — Consulta de sesión actual (`GET /api/v1/auth/me/`):

```http
GET /api/v1/auth/me/ HTTP/1.1
Host: siga.inebi.edu.gt
Accept: application/json
```

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "user": {
    "username": "secretaria.general",
    "email": "secretaria@inebi.edu.gt",
    "person": {
      "first_name": "Claudia",
      "last_name": "Morales",
      "cui": "2847192830101"
    },
    "roles": [
      {
        "name": "Secretaría Académica",
        "slug": "secretaria_academica",
        "permissions": ["document_upload", "document_read", "document_issue", "enrolment_read"]
      }
    ],
    "scopes": [
      {
        "scope_type": "institution",
        "target_id": "c1f2e3d4-b5a6-7890-abcd-ef1234567890"
      }
    ]
  }
}
```

---

### 4.2 Documentos, expedientes y archivo (`/api/v1/documents/`)

Este dominio gestiona plantillas documentales (RF-PLA), expedientes (RF-DOC), archivo digital (RF-ARC), emisión (RF-EMI) y descargas controladas (RNF-SEG-004).

| Método | Ruta | Finalidad | Permiso / Alcance |
|---|---|---|---|
| `GET` | `/api/v1/documents/templates/` | Listar plantillas documentales activas | `document_read` (Institución) |
| `POST` | `/api/v1/documents/templates/` | Crear nueva plantilla de documento | `document_template_manage` |
| `GET` | `/api/v1/documents/templates/{public_id}/` | Detalle de plantilla con encabezado institucional | `document_read` (Institución) |
| `PATCH` | `/api/v1/documents/templates/{public_id}/` | Actualizar nombre/configuración de plantilla | `document_template_manage` |
| `DELETE` | `/api/v1/documents/templates/{public_id}/` | Desactivar plantilla (baja lógica, no eliminación) | `document_template_manage` |
| `GET` | `/api/v1/documents/templates/{public_id}/versions/` | Listar versiones históricas inmutables | `document_read` (Institución) |
| `POST` | `/api/v1/documents/templates/{public_id}/preview/` | Previsualización efímera en memoria (RF-PLA-006) | `document_template_manage` |
| `POST` | `/api/v1/documents/records/` | Subir archivo al expediente del estudiante | `document_upload` (Estudiante) |
| `POST` | `/api/v1/documents/records/scan/` | Registro de documento digitalizado/escáner (RF-DOC-007) | `document_upload` (Estudiante) |
| `POST` | `/api/v1/documents/records/{public_id}/versions/` | Reemplazar documento creando versión inmutable | `document_upload` (Estudiante) |
| `GET` | `/api/v1/documents/records/{public_id}/download/` | Descarga segura mediante token temporal firmado | `document_read` + Token válido |
| `POST` | `/api/v1/documents/records/{public_id}/verify/` | Verificar integridad física por checksum SHA-256 | `document_read` (Estudiante) |
| `GET` | `/api/v1/documents/enrolments/{enrolment_id}/records/` | Listar documentos adjuntos a una matrícula | `document_read` (Estudiante) |
| `GET` | `/api/v1/documents/field-tags/` | Catálogo cerrado de marcadores permitidos | `document_read` |
| `GET` | `/api/v1/documents/types/` | Catálogo de tipos de documento institucionales | Autenticado |
| `POST` | `/api/v1/documents/types/` | Registrar nuevo tipo en el catálogo (RNF-MAN-001) | `scope.assign` |
| `GET` | `/api/v1/documents/storage-consumption/` | Resumen de consumo de almacenamiento y advertencia | Autenticado |
| `GET` | `/api/v1/documents/official-issuance/eligibility/` | Evaluar si matrícula puede emitir documentos | `document_issue` |
| `GET` | `/api/v1/documents/historical-cycle-report/` | Generar boleta en memoria de ciclo cerrado | `document_issue` (Estudiante) |
| `POST` | `/api/v1/documents/official-issuance/batches/` | Emisión por lote con idempotencia de reintento | `document_issue` (Grado/Sección) |
| `POST` | `/api/v1/documents/delivery-receipts/` | Registrar constancia de entrega a encargado | `document_issue` |
| `GET` | `/api/v1/documents/verify/{code}/` | Verificación pública de autenticidad por código | Público (con Rate Limit) |

#### Ejemplo sanitizado — Subida de documento (`POST /api/v1/documents/records/`):

```http
POST /api/v1/documents/records/ HTTP/1.1
Host: siga.inebi.edu.gt
Content-Type: multipart/form-data; boundary=----WebKitFormBoundaryXYZ

------WebKitFormBoundaryXYZ
Content-Disposition: form-data; name="student_id"

f47ac10b-58cc-4372-a567-0e02b2c3d479
------WebKitFormBoundaryXYZ
Content-Disposition: form-data; name="file"; filename="certificado_nacimiento.pdf"
Content-Type: application/pdf

%PDF-1.4 ... [contenido binario] ...
------WebKitFormBoundaryXYZ--
```

```http
HTTP/1.1 201 Created
Content-Type: application/json

{
  "public_id": "a89b3f42-c109-4821-b328-9f123456789a",
  "student_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "filename": "certificado_nacimiento.pdf",
  "content_type": "application/pdf",
  "size_bytes": 245890,
  "checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "status": "active",
  "version_number": 1,
  "created_at": "2026-10-12T16:00:00Z"
}
```

*Efecto de auditoría:* Se genera un evento `documents.document.uploaded` registrando actor, identificador de recurso y versión.

#### Ejemplo sanitizado — Verificación pública (`GET /api/v1/documents/verify/{code}/`):

```http
GET /api/v1/documents/verify/vK92mX10_892jklQ761234za/ HTTP/1.1
Host: siga.inebi.edu.gt
Accept: application/json
```

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "valid": true,
  "document_type": "Certificado de Estudios",
  "folio": "DOC-2026-0045",
  "issued_at": "2026-10-10T11:20:00Z",
  "vigencia": "vigente"
}
```

*Nota de privacidad (RF-EMI-009):* No revela nombres de personas, documentos de identificación ni datos académicos confidenciales; únicamente valida la autenticidad del documento físico portado.

---

### 4.3 Auditoría transversal y cumplimiento (`/api/v1/audit/`)

La bitácora de auditoría registra toda escritura sensible, lecturas de datos confidenciales e intentos de acceso no autorizados (RF-BIT).

| Método | Ruta | Finalidad | Permiso requerido |
|---|---|---|---|
| `GET` | `/api/v1/audit/events/` | Consultar asientos con filtros de acción/actor/fecha | `audit_read` |
| `GET` | `/api/v1/audit/events/export/` | Exportar bitácora en CSV (operación auditada) | `audit_read` |
| `POST` | `/api/v1/audit/retention-declarations/` | Declarar periodo de retención legal (RNF-LEG-001) | `retention_policy_declare` |
| `GET` | `/api/v1/audit/enrolments/{id}/subjects/{id}/result-trace/` | Trazabilidad completa de calificaciones (RF-RES-009) | `audit_read` |

*Inmutabilidad estricta (RF-BIT-005):* No existen rutas `POST`, `PUT`, `PATCH` ni `DELETE` para eventos de auditoría. Cualquier intento HTTP en esas rutas retorna `405 Method Not Allowed`.

---

### 4.4 Identidad y cuentas (`/api/v1/identity/`)

Gestiona el ciclo de vida de usuarios, credenciales, roles y asignación de alcances (RF-CTA, RF-PER, RF-ALC).

| Método | Ruta | Finalidad | Permiso requerido |
|---|---|---|---|
| `GET` | `/api/v1/identity/accounts/` | Listado administrativo de cuentas | `account_manage` |
| `POST` | `/api/v1/identity/accounts/` | Provisión de nueva cuenta institucional | `account_manage` |
| `POST` | `/api/v1/identity/accounts/{id}/disable/` | Desactivar cuenta registrando motivo obligatorio | `account_manage` |
| `GET` | `/api/v1/identity/roles/` | Catálogo de roles y permisos asociados | `role_view` |
| `POST` | `/api/v1/identity/roles/` | Creación de rol administrativo | `role_manage` |
| `POST` | `/api/v1/identity/roles/assign/` | Asignar rol con alcance institucional obligatorio | `role_assign` |

---

### 4.5 Estudiantes, salud y observaciones (`/api/v1/students/`)

Gestiona el expediente del alumno, contactos de emergencia y ficha médica (RF-EST, RF-EXP, RNF-PRI).

| Método | Ruta | Finalidad | Permiso requerido |
|---|---|---|---|
| `GET` | `/api/v1/students/` | Listar estudiantes dentro del alcance del usuario | `student_view_basic` |
| `POST` | `/api/v1/students/` | Registrar ficha de estudiante | `student_create` |
| `GET` | `/api/v1/students/{id}/` | Consultar datos generales del estudiante | `student_view_basic` (con alcance) |
| `GET` | `/api/v1/students/{id}/contacts/` | Contactos de emergencia (lectura sensible auditada) | `student_view_sensitive` |
| `GET` | `/api/v1/students/{id}/health/` | Información médica confidencial (RF-EXP-006) | `student_view_health` |

---

### 4.6 Ciclo académico y estructura (`/api/v1/academics/`)

Administra ciclos escolares, jornadas, sedes, grados, secciones y asignaturas (RF-CIC, RF-AUL, RF-HOR).

| Método | Ruta | Finalidad | Permiso requerido |
|---|---|---|---|
| `GET` | `/api/v1/academics/cycles/` | Listar ciclos lectivos y estados (borrador/activo/cerrado) | Autenticado |
| `POST` | `/api/v1/academics/cycles/{id}/close/` | Cierre irreversible de ciclo escolar (RF-CIC-005) | `academic_admin` |
| `GET` | `/api/v1/academics/classrooms/` | Catálogo de aulas con estado de servicio y capacidad | Autenticado |
| `PATCH` | `/api/v1/academics/classrooms/{id}/` | Modificar disponibilidad de aula (disponible/mantenimiento) | `academic_admin` |
| `GET` | `/api/v1/academics/sections/` | Secciones configuradas por grado y jornada | Autenticado |

---

### 4.7 Matrícula y movimientos (`/api/v1/enrolments/`)

Controla el ingreso, cambio de sección y requisitos documentales del estudiante (RF-MAT, RF-MOV).

| Método | Ruta | Finalidad | Permiso requerido |
|---|---|---|---|
| `GET` | `/api/v1/enrolments/` | Consultar matrículas por ciclo escolar | `enrolment_read` |
| `POST` | `/api/v1/enrolments/` | Registrar matrícula inicial en sección abierta | `enrolment_write` |
| `POST` | `/api/v1/enrolments/{id}/change-section/` | Traslado de sección conservando historial | `enrolment_write` |
| `GET` | `/api/v1/enrolments/{id}/requirements/` | Estado de requisitos documentales obligatorios | `enrolment_read` |

---

### 4.8 Asistencia y credenciales (`/api/v1/attendance/`)

Operaciones de escaneo en punto de acceso, registro de justificaciones y estado diario (RF-ASI, RF-CRE, RF-JOR, RF-JUS).

| Método | Ruta | Finalidad | Permiso requerido |
|---|---|---|---|
| `POST` | `/api/v1/attendance/scan/` | Ingesta de escaneo QR opaco en entrada/salida | `attendance_scan` |
| `POST` | `/api/v1/attendance/scan/batch/` | Envío por lote con tolerancia a desconexión temporal | `attendance_scan` |
| `GET` | `/api/v1/attendance/day-status/` | Estado diario de presencia de un alumno identificado | `attendance_read` |
| `POST` | `/api/v1/attendance/justifications/` | Registrar justificación de inasistencia con adjunto | `attendance_justify` |

---

### 4.9 Reportes consolidados (`/api/v1/reporting/`)

| Método | Ruta | Finalidad | Permiso requerido |
|---|---|---|---|
| `GET` | `/api/v1/reporting/attendance/summary/` | Porcentaje de asistencia agregado por sección | `reporting_view` |
| `GET` | `/api/v1/reporting/grades/consolidated/` | Cuadro de rendimiento académico | `reporting_view` |

---

### 4.10 Monitoreo y salud del sistema (`/api/v1/health/`)

Endpoints de sondeo operativo para balanceadores de carga y plataformas de ejecución en la nube:

| Método | Ruta | Finalidad | Acceso |
|---|---|---|---|
| `GET` | `/api/v1/health/` | Sondeo liveness del proceso web HTTP | Público |
| `GET` | `/api/v1/health/database/` | Sondeo readiness con verificación real de PostgreSQL | Público / Monitoreo |

Respuesta estándar de salud:
```json
{
  "status": "ok",
  "database": "connected"
}
```

---

## 5. Integraciones externas y límites del sistema

Conforme a las directrices institucionales de `07-api-integrations-documentation-instructions.md` (§ Integraciones):

### 5.1 Declaración expresa de autosuficiencia operativa

> **Declaración institucional:**  
> La solución tecnológica SIGA-INEBI **no depende de APIs externas, servicios SaaS comerciales ni proveedores de nube de terceros** para su operación académica base.  
> Todos los algoritmos de verificación, cálculo de notas, generación de códigos de verificación criptográficos, almacenamiento documental, compilación de boletas y trazabilidad de asistencia operan de forma 100% autónoma en el servidor de la institución.

### 5.2 Integración con periféricos de hardware en cliente

El sistema admite la interacción directa con periféricos estándar en la estación de trabajo del usuario:

1. **Lectores de código de barras / QR:**
   - Compatibles como dispositivos de entrada tipo teclado (HID keyboard emulation) o mediante acceso directo a la cámara web a través de la API estándar de HTML5 `navigator.mediaDevices.getUserMedia()`.
   - No requieren software intermediario ni controladores de terceros.
2. **Escáneres y digitalizadores documentales:**
   - La subida directa de documentos digitalizados (`POST /api/v1/documents/records/scan/`) recibe archivos estándar generados por cualquier escáner compatible con el sistema operativo cliente (controladores TWAIN / SANE / WIA).
   - El archivo se envía mediante transporte HTTP estándar `multipart/form-data`.

---

## 6. Procedimiento de verificación contractual y pruebas

Cualquier desarrollador o auditor independiente puede verificar la conformidad de la API contra la implementación activa siguiendo este procedimiento:

1. **Descarga del esquema OpenAPI:**
   ```bash
   curl -s http://localhost:8000/api/v1/schema/ -o openapi.yaml
   ```
2. **Ejecución de la suite automatizada de pruebas de contratos API:**
   ```bash
   make test-backend
   ```
   O ejecutando directamente los módulos de contrato:
   ```bash
   pytest backend/tests/api/test_documents_api.py -v
   pytest backend/tests/api/test_audit_api.py -v
   ```
3. **Comprobación de inmutabilidad y denegación:**
   Verificar que toda petición sin cookie de sesión o con métodos no permitidos retorne estrictamente los códigos de rechazo HTTP declarados en este manual.
