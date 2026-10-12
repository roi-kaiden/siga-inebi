# Manifiesto de la versión evaluada localmente

RUN-D1-06 es una evaluación técnica local, no una RC final ni una aceptación.
Ejecutor: Codex en apoyo a Daniel. Revisores Pablo/Josué/Santiago pendientes.

| Campo | Identificación |
| --- | --- |
| Inicio UTC | 2026-10-09T03:00:18.005812+00:00 |
| Fin UTC | 2026-10-09T03:04:06.870492+00:00 |
| Fecha local | 2026-10-08, America/Guatemala |
| SHA base | `3bcca08860b07c7086ac11b914a7262e7a68d282` |
| Árbol | Modificado; no atribuir resultados al SHA limpio |
| Digest de fuentes | `ce64ff0cbf5c3db9a05cd41c186653b375b80aa947d09eed966b73cf503f5e5a` |
| Estabilidad | Mismo SHA/digest al inicio y al final; `source_stable: true` |
| Controles | 28/28 aprobados, cada código de salida 0 |
| Release formal | Pendiente commit/tag, paquete final y revisión independiente |

[Índice de evidencias](indice-evidencias.csv): rutas, tamaños y SHA-256 reales de
summary, logs, JUnit, cobertura y build disponibles localmente. Los artefactos
raw están ignorados; no están respaldados por el simple commit de este manifiesto.
Exportación a repositorio externo autorizado, permisos y retención pendientes.
Un digest identifica fuentes pero no almacena su contenido: conservar la copia
correspondiente o integrar cambios y repetir controles sobre el commit final.

Migraciones: aplicación y detección de pendientes aprobadas en RUN-D1-06.
Build y presupuesto frontend aprobados. Backend 1589 pruebas; frontend 283.
La auditoría npm no reportó vulnerabilidades; pip-audit aprobó con una ignorada
según excepciones existentes. Esto no acredita ausencia total de vulnerabilidades.

Manuales borradores: [técnico](../../manuals/02-technical-manual.md),
[instalación](../../manuals/03-installation-and-configuration.md) y
[respaldo](../../manuals/09-final-backup-and-recovery-plan.md); validación final
en [seguimiento](seguimiento-manuales.md). Las modificaciones posteriores a la
corrida no forman parte de esta instantánea. El despliegue QA cloud se identifica
por commit y digest de imagen en [RUN-CQ-01](despliegue-cloud-qa.md); este
manifiesto no lo acredita.
