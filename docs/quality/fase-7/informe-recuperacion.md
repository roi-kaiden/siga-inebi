# Verificación de respaldo y recuperación

La suite RUN-D1-06 aprobó las pruebas de respaldo y recuperación, incluida
restauración real en PostgreSQL 16 y extracción independiente de archivos
sintéticos. Codex ejecutó en apoyo a Daniel; revisión de Roí/Pablo pendiente.

El módulo `backend/tests/integration/test_backup_and_recovery.py` comprueba
independencia por pila, manifiestos, SHA-256, frescura/RPO y rechazo de destinos
inválidos. La regresión del guard incluyó 28 casos focalizados; la suite completa
posterior conservó evidencia JUnit y no omitió pruebas. La prueba
`test_drill_restores_both_stacks_into_disposable_destinations` confirma restauración
en base desechable y directorio separado, con consulta del contenido recuperado.

Se corrigió un riesgo previo: `recovery-drill.sh` solo exigía un nombre no vacío.
Ahora verifica nombre de base desechable diferente del origen, destino de archivos
separado, manifiestos, checksums y compatibilidad antes de reemplazar la base.
Las pruebas negativas comprueban que PostgreSQL no se contacta para operaciones
destructivas cuando la validación falla. Ver INC-006 y
[correcciones](correcciones-y-regresion.md).

| Meta o evidencia | Estado |
| --- | --- |
| RPO 24 horas / RTO 4 horas | Referencias técnicas; confirmación institucional pendiente |
| Restauración funcional sintética | Aprobada en tests de RUN-D1-06; JUnit indexado |
| Tiempo de incidente hasta reapertura | No medido; duración de suite no equivale a RTO |
| Volumen de ciclo real o representativo | No medido; datasets pequeños de pruebas |
| Simulacro operativo cloud | Pendiente despliegue y recursos desechables |
| Cifrado, almacenamiento externo, retención | Pendientes configuración y confirmación institucional |

No extrapolar resultados sintéticos a recuperación institucional. El
[plan de respaldo](../../manuals/09-final-backup-and-recovery-plan.md) contiene
procedimiento y pendientes. Mantener dumps/archivos fuera de Git; el
[índice](indice-evidencias.csv) enlaza solo evidencias locales y checksums.
