# Correcciones y regresión — Fase 7

## Estado

Correcciones verificadas técnicamente en RUN-D1-06 por Codex en apoyo a Daniel;
revisión independiente de Pablo/Josué/Santiago pendiente. Ninguna fila representa
cierre institucional. La línea base inicial no tenía correcciones registradas.

## Registro por corrección

| INC | Requisito/caso afectado | Causa raíz | PR/SHA correctivo | Prueba de regresión | Ejecutor | Revisor | Resultado | Evidencia |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| INC-001/002 | Entorno integrado/backend | Docker ausente y Python incompatible en macOS inicial | SHA base + digest de RUN-D1-06; sin PR final | Python 3.11/PostgreSQL 16 y suites completas | Codex en apoyo a Daniel | Pablo/Josué pendientes | Desbloqueado en Linux; entorno histórico preservado | RUN-D1-06 summary/logs |
| INC-003 | Dependencias frontend | Avisos transitivos en Vitest3 | Lockfile Vitest 4.1.11; SHA base + digest | npm audit sin hallazgos;283 pruebas Node 22;lint/formato/build | Codex en apoyo a Daniel | Santiago pendiente | Verificado técnicamente | RUN-D1-06 frontend-audit/tests/build |
| INC-005 | Baseline: 32 fallos | 17 permisos media host;15 tests sin grants o fechas correctas | Aislamiento media test;admin_client selectivo; date en factory caller | 86 casos focalizados y1589suite completa | Codex en apoyo a Daniel | Pablo/Josué pendientes | Verificado; conserva negativos autorización | RUN-D1-05 y06 JUnit |
| INC-006 | Simulacro recuperación | Guardia solo nombre no vacío antes operación destructiva | Guard de destinos/manifiestos/checksums/version y backend Python 3 | 28 casos focalizados;restauración real incluida en suite de 1589 pruebas | Codex en apoyo a Daniel | Pablo/Roí pendientes | Verificado técnicamente;simulacro operativo pendiente | RUN-D1-06 backend JUnit |

Identificación exacta en [manifiesto](manifiesto-version.md). PR/commit correctivo
formal y revisión independiente pendientes; el digest de fuentes no es un commit.
PD-011 (versiones y controles locales) cuenta ahora con evidencia Docker Node 22;
la ejecución remota CI y su decisión de cierre siguen pendientes.

## Criterio de cierre

Cada fila debe enlazar la incidencia, la prueba que reproduce el fallo, el cambio integrado y una ejecución posterior sobre el candidato correcto. Un cambio que no cuenta con regresión no puede cerrarse como corregido.
