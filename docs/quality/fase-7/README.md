# Expediente de calidad — Fase 7

Este directorio conserva evidencia de la Fase 7 para una versión identificable de SIGA-INEBI. Pablo coordina su consolidación; cada responsable de dominio entrega sus resultados, evidencias y regresiones.

RUN-D1-06 aprobó 28 controles locales con 1589 pruebas backend y283 frontend.
Codex ejecutó en apoyo a Daniel; revisión independiente y aceptación pendientes.
La instantánea incluye cambios sin commit: consultar SHA y digest en el
[manifiesto](manifiesto-version.md). QA cloud desplegado en RUN-CQ-01 con URL,
digests y revisiones en [despliegue cloud](despliegue-cloud-qa.md). Las líneas
base previas permanecen en los registros.

| Evidencia nueva | Propósito |
| --- | --- |
| [Entorno y datos](entorno-y-datos.md) | Versiones, recursos, aislamiento y pendientes cloud/teléfono |
| [Índice](indice-evidencias.csv) | Checksums de artefactos locales ignorados; exportación pendiente |
| [Rendimiento](informe-rendimiento.md) | Duraciones reales y mediciones de usuario pendientes |
| [Recuperación](informe-recuperacion.md) | Restauraciones sintéticas y límites de RPO/RTO |
| [Manifiesto](manifiesto-version.md) | Identidad verificable de la instantánea evaluada |
| [Despliegue cloud](despliegue-cloud-qa.md) | RUN-CQ-01: URL, imágenes, revisiones y verificaciones en Cloud Run |

## Estado al inicio

- Candidato evaluado inicialmente: pendiente de fijar en `manifiesto-version.md`.
- Aceptación institucional: pendiente. Ningún documento de este directorio equivale a una aceptación firmada.
- Datos: solo sintéticos. No guardar secretos, cookies, tokens, expedientes reales, respaldos ni volcados de base de datos.
- Resultados de pruebas: usar `ejecuciones.csv`; no sustituir un resultado real por una afirmación de conformidad en Markdown.

## Índice

| Archivo | Propósito | Responsable |
| --- | --- | --- |
| `alcance-y-decisiones.md` | Alcance, dependencias y decisiones que bloquean validación. | Pablo |
| `catalogo-casos.csv` | Universo de requisitos, clasificación inicial y vínculos de caso/ejecución. | Pablo + responsables de dominio |
| `matriz-final.csv` | Instantánea de validación por requisito sobre candidato final. | Pablo |
| `ejecuciones.csv` | Registro inmutable de cada corrida o caso manual. | Ejecutores; Pablo consolida |
| `incidencias.csv` | Registro y clasificación de defectos y bloqueos. | Reportante; Pablo hace triage |
| `correcciones-y-regresion.md` | Correcciones aprobadas y regresión posterior. | Pablo + autor/revisor |
| `informe-seguridad.md` | Resultado de controles de seguridad y dependencias disponibles. | Pablo coordina; Santiago/Daniel resuelven |
| `reporte-final-pruebas.md` | Informe de estado y recomendación QA. | Pablo |
| `acta-aceptacion.md` | Borrador de acta o reporte de aceptación institucional. | Pablo + autoridad institucional |
| `seguimiento-manuales.md` | Estado de manuales y verificación por versión. | Pablo + responsables |
| `../manuals/08-maintenance-and-support-plan.md` | Plan operativo de mantenimiento y soporte. | Pablo + Daniel |

## Actualización reproducible

Regenerar catálogo y matriz base después de cambios de requerimientos o catálogo:

```bash
python3 scripts/quality/generate_phase7_catalog.py
```

El generador no marca requisitos como aprobados: crea filas con resultado `No ejecutado` hasta que cada responsable agregue caso, corrida y evidencia reales.

## Corridas automatizadas con evidencia

Desde la raíz del repositorio, con Docker y Compose disponibles:

```bash
python3 scripts/quality/run_phase7_checks.py --run-id RUN-D1-06
```

La salida se guarda en `tmp/phase7/RUN-D1-06/`. Para elegir otro directorio local se admite `--evidence-root`. Un RUN-ID existente se rechaza para conservar su historial. El directorio contiene `summary.json`, logs por control, JUnit y cobertura backend/frontend y el build frontend. Los directorios `tmp/` y `docs/quality/fase-7/evidence/` están excluidos de Git; revisar los artefactos antes de compartirlos y referenciarlos desde `ejecuciones.csv`.

Cada corrida usa un proyecto Compose propio, PostgreSQL 16 con datos sintéticos y contenedores sin dependencias implícitas. Comprueba versiones, migraciones, suites y umbrales de cobertura, lint, formato, Bandit, auditorías de dependencias y build. La auditoría Python conserva las excepciones declaradas en Makefile; aprobar ese control no significa ausencia de todas las vulnerabilidades. Los reportes se verifican antes de retirar los contenedores. Las comprobaciones independientes continúan aunque una falle; la preparación fallida bloquea sus dependientes. La salida global es 0 solo si todos los controles aprobaron, incluidos los reportes requeridos y la limpieza.

`summary.json` registra el SHA base, si el árbol contiene cambios y un digest SHA-256 de los archivos versionados y no versionados no ignorados (incluye borrados y enlaces). Cuando el árbol está modificado, identificar la versión por SHA **y digest**, sin afirmar que los resultados pertenecen al commit limpio. El runner no captura contenidos de archivos fuente ni variables de entorno. Mantener el árbol estable durante la corrida: se toma otra instantánea al finalizar y cualquier diferencia invalida el resultado global (`source_stable: false`). Vitest usa como máximo dos trabajadores para limitar la carga sobre el host.

Estas corridas verifican controles automatizados; las pruebas de QR en teléfono, rendimiento de referencia, restauración y aceptación institucional requieren su evidencia específica.

Las pruebas del ejecutor no requieren Docker:

```bash
python3 -m unittest discover -s scripts/quality/tests -p 'test_run_phase7_checks.py'
```
