# Correcciones y regresión — Fase 7

## Estado

Correcciones verificadas técnicamente en RUN-PAB-20261012-04, consolidado por
Pablo. Revisión independiente pendiente. Ninguna fila representa cierre
institucional. La línea base inicial se conserva como historial.

## Registro por corrección

| INC | Requisito/caso afectado | Causa raíz | PR/SHA correctivo | Prueba de regresión | Ejecutor | Revisor | Resultado | Evidencia |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| INC-001/002 | Entorno integrado/backend | Docker ausente y Python incompatible en macOS inicial | SHA base + digest de RUN-D1-06; sin PR final | Python 3.11/PostgreSQL 16 y suites completas | Codex en apoyo a Daniel | Pablo/Josué pendientes | Desbloqueado en Linux; entorno histórico preservado | RUN-D1-06 summary/logs |
| INC-003 | Dependencias frontend | Avisos transitivos en Vitest3 | Lockfile Vitest 4.1.11; SHA base + digest | npm audit sin hallazgos;283 pruebas Node 22;lint/formato/build | Codex en apoyo a Daniel | Santiago pendiente | Verificado técnicamente | RUN-D1-06 frontend-audit/tests/build |
| INC-005 | Baseline: 32 fallos | 17 permisos media host;15 tests sin grants o fechas correctas | Aislamiento media test;admin_client selectivo; date en factory caller | 86 casos focalizados y1589suite completa | Codex en apoyo a Daniel | Pablo/Josué pendientes | Verificado; conserva negativos autorización | RUN-D1-05 y06 JUnit |
| INC-006 | Simulacro recuperación | Guardia solo nombre no vacío antes operación destructiva | Guard de destinos/manifiestos/checksums/version y backend Python 3 | 28 casos focalizados;restauración real incluida en suite de 1589 pruebas | Codex en apoyo a Daniel | Pablo/Roí pendientes | Verificado técnicamente;simulacro operativo pendiente | RUN-D1-06 backend JUnit |
| INC-004 | Visualización de fotografías | Se entregaba una cadena vacía como `src` de imagen. | `ImageDialog` y pantallas de alumnos/docentes usan `undefined` cuando no hay foto. | 285 pruebas frontend y formato aprobados en la corrida integrada. | Pablo | Estuardo pendiente | Verificado técnicamente | RUN-PAB-20261012-02 frontend-tests/format |
| INC-007 | Edición de persona vinculada | La UI enviaba `person.id`, aunque la API publica `person.public_id`. | Servicios y pantallas de alumnos, docentes y encargados envían `public_id`; pruebas de contrato agregadas. | Pruebas de módulos, 285 pruebas frontend y 1,596 backend aprobadas. | Pablo | Daniel/Josué pendientes | Verificado técnicamente | RUN-PAB-20261012-02; EJ-CQ-004 |
| INC-FMT-001 | Calidad de entrega frontend | La primera corrida de esta sesión detectó formato no conforme en `AttendancePage.jsx`. | Se aplicó el formateador del proyecto, sin modificar lógica. | `RUN-PAB-20261012-02`: formato frontend y 27 controles restantes aprobados. | Pablo | Daniel pendiente | Verificado técnicamente | RUN-PAB-20261012-01; RUN-PAB-20261012-02 |
| INC-PERF-001 | Presupuesto de carga frontend | La mayor ruta lazy tenía un margen de solo 30 bytes respecto del límite de 20,000 bytes gzip. | Ventanas operativas bajo demanda y chunk explícito para dependencias compartidas de Asistencia. | Pruebas de Asistencia/Matrículas y suite frontend completa; presupuesto: 13,716/20,000 bytes. | Pablo | Pendiente | Verificado técnicamente | RUN-PAB-20261012-04 |

Identificación exacta en [manifiesto](manifiesto-version.md). PR/commit correctivo
formal y revisión independiente pendientes; el digest de fuentes no es un commit.
PD-011 (versiones y controles locales) cuenta ahora con evidencia Docker Node 22;
la ejecución remota CI y su decisión de cierre siguen pendientes.

## Criterio de cierre

Cada fila debe enlazar la incidencia, la prueba que reproduce el fallo, el cambio integrado y una ejecución posterior sobre el candidato correcto. Un cambio que no cuenta con regresión no puede cerrarse como corregido.
