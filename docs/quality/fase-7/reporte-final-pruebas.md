# Reporte final de pruebas — Fase 7

## Estado actual

**Controles automatizados locales aprobados; entrega institucional pendiente.**
RUN-PAB-20261012-04 aprobó 28/28 controles sobre SHA base y árbol modificado
estable. La optimización de entrega dejó la ruta lazy mayor en 13,716/20,000
bytes gzip. Pablo consolidó la evidencia técnica; revisión independiente, UAT y
aceptación institucional siguen pendientes.

| Evidencia actual | Resultado |
| --- | --- |
| Identificación | [Manifiesto](manifiesto-version.md): SHA 3a4a8d2 más digest completo; sin release final |
| Backend | 1,596 pruebas aprobadas; 0 fallos; cobertura 94.45 % líneas |
| Frontend | 285 pruebas/32 archivos; cobertura 73.32 % statements, 68.39 % branches, 68.03 % functions, 73.98 % líneas |
| Seguridad/build | Bandit,lint,formato,migraciones,build/presupuesto y npm audit aprobados; pip-audit: 1 ignorada conforme política existente |
| Recuperación | Restauraciones sintéticas y guardias verificadas en suite; simulacro operativo representativo y RPO/RTO institucional pendientes |
| QA cloud | [RUN-CQ-01](despliegue-cloud-qa.md): HTTPS, login, API, bucket y URL firmada verificados; descarga con token pendiente |
| Rendimiento/QR | Sin medición de 1 vCPU/2 GB, carga de 500 estudiantes ni teléfono HTTPS |
| Requisitos aprobados | Matriz por requisito pendiente de consolidación; ninguna aprobación institucional añadida |
| Incidencias | INC-004 e INC-007 cuentan con regresión técnica; su revisión independiente permanece pendiente. |
| Manuales/UAT | Borradores y revisión pendientes; autoridad de aceptación pendiente |

Registro [ejecuciones](ejecuciones.csv), [índice de evidencias](indice-evidencias.csv),
[entorno](entorno-y-datos.md), [rendimiento](informe-rendimiento.md) y
[recuperación](informe-recuperacion.md). Cloud Run/Terraform/Cloud SQL en proyecto
precise-blend-428821-e0 se registran en [RUN-CQ-01](despliegue-cloud-qa.md).
El detalle reproducible y la regresión de formato se registran en
[resultado integrado de Pablo](resultado-ejecucion-pablo-2026-10-12.md).

## Línea base histórica conservada

Las siguientes tablas y recomendación corresponden al intento inicial macOS;
se conservan como historial y no describen el estado Linux actual.

## Identificación de entrega

| Campo | Valor |
| --- | --- |
| Versión/identificador | Línea base local; no es release candidata |
| Commit SHA | 0c8f0d396231f46809b95cc088d5f2c557cb919f |
| Entorno QA | macOS local; Node 24.13.1/npm 11.8.0. Docker no disponible y backend Python 3.9.6 incompatible. |
| Periodo de pruebas | 8 de octubre de 2026 |
| Coordinador QA | Pablo |
| Autoridad de aceptación | Pendiente |

## Resultados

| Indicador | Resultado | Fuente |
| --- | --- | --- |
| Requisitos incluidos y aprobados | 0/87; ninguno con evidencia final aún | matriz-final.csv |
| Casos/controles ejecutados | 1 aprobado, 1 fallido, 2 bloqueados | ejecuciones.csv |
| Incidencias S1/S2 abiertas | 3: INC-001, INC-002 e INC-003 | incidencias.csv |
| Cobertura backend/frontend | Backend: no ejecutada. Frontend: 84.47% statements, 85.98% branches, 69.30% functions, 84.47% lines. | EJ-D1-003 |
| Regresión de correcciones | No hay correcciones verificadas | correcciones-y-regresion.md |
| UAT | Pendiente | `informe-aceptacion-usuarios.md` |
| Manuales aplicables | Pendiente | `seguimiento-manuales.md` |

## Recomendación QA histórica

**Recomendación de Pablo: No apto.** Antes de reconsiderarla se requiere: entorno Docker/PostgreSQL o CI remoto válido; entorno backend compatible; triage/corrección de INC-003; ejecución completa sobre candidato formal; UAT y aceptación institucional. La recomendación QA no sustituye la decisión institucional.
