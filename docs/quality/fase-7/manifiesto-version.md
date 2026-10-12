# Manifiesto de la versión evaluada localmente

RUN-PAB-20261012-04 es una evaluación técnica local consolidada por Pablo, no
una RC final ni una aceptación. Revisión independiente y aceptación
institucional pendientes.

| Campo | Identificación |
| --- | --- |
| Inicio UTC | 2026-10-12T23:12:57.390606+00:00 |
| Fin UTC | 2026-10-12T23:15:20.161005+00:00 |
| Fecha local | 2026-10-12, America/Guatemala |
| SHA base | `3a4a8d2d488ea13e69471cc9637a36c81d72f010` |
| Árbol | Modificado; no atribuir resultados al SHA limpio |
| Digest de fuentes | `d19e4f86fffe4791885eb778ebc6e27fa76ce4d0528c6478d4e7bd16d332e0b6` |
| Estabilidad | Mismo SHA/digest al inicio y al final; `source_stable: true` |
| Controles | 28/28 aprobados, cada código de salida 0 |
| Release formal | Pendiente commit/tag, paquete final y revisión independiente |

[Índice de evidencias](indice-evidencias.csv): rutas, tamaños y SHA-256 reales de
summary, logs, JUnit, cobertura y build disponibles localmente. Los artefactos
raw están ignorados; no están respaldados por el simple commit de este manifiesto.
Exportación a repositorio externo autorizado, permisos y retención pendientes.
Un digest identifica fuentes pero no almacena su contenido: conservar la copia
correspondiente o integrar cambios y repetir controles sobre el commit final.

Migraciones: aplicación y detección de pendientes aprobadas. Build y presupuesto
frontend aprobados. Backend 1,596 pruebas; frontend 285 pruebas en 32 archivos.
La auditoría npm no reportó vulnerabilidades; pip-audit aprobó con una ignorada
según excepciones existentes. Esto no acredita ausencia total de vulnerabilidades.

Manuales borradores: [técnico](../../manuals/02-technical-manual.md),
[instalación](../../manuals/03-installation-and-configuration.md) y
[respaldo](../../manuals/09-final-backup-and-recovery-plan.md); validación final
en [seguimiento](seguimiento-manuales.md). El resultado detallado de la corrida
se conserva en [resultado integrado](resultado-ejecucion-pablo-2026-10-12.md).
El despliegue QA cloud se identifica por commit y digest de imagen en
[RUN-CQ-01](despliegue-cloud-qa.md); este manifiesto no lo acredita.
