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
| Simulacro operativo cloud | Ejecutado el 12 de octubre de 2026 (RUN-CQ-04): restauración de respaldo de Cloud SQL en instancia desechable, 896 s; ver sección siguiente |
| Cifrado, almacenamiento externo, retención | Pendientes configuración y confirmación institucional |

No extrapolar resultados sintéticos a recuperación institucional. El
[plan de respaldo](../../manuals/09-final-backup-and-recovery-plan.md) contiene
procedimiento y pendientes. Mantener dumps/archivos fuera de Git; el
[índice](indice-evidencias.csv) enlaza solo evidencias locales y checksums.

## Simulacro de restauración en Cloud SQL (RUN-CQ-04)

Ejecutado el 12 de octubre de 2026, 11:12–11:27 (America/Guatemala; 17:12–17:27
UTC) por Claude Code en apoyo a Daniel. Revisión de Roí y Pablo pendiente. Se
restauró el respaldo automático de `<INSTANCIA_QA>` en una instancia nueva y
desechable, sin tocar la instancia de QA. Datos sintéticos de `seed_demo_data`.

| Paso | Resultado |
| --- | --- |
| Respaldo usado | `<BACKUP_ID>` (el más reciente), ventana 2026-10-12 07:00 UTC, estado SUCCESSFUL |
| Crear instancia `<INSTANCIA_SIMULACRO>` (PostgreSQL 16, `db-f1-micro`, HDD 10 GB) | 361 s |
| Restaurar el respaldo en ella | 535 s |
| Tiempo total hasta base restaurada | 896 s (≈ 15 min) |
| Instancia eliminada al terminar | Sí |

Verificación sobre la base restaurada (`siga_inebi_qa`), contra QA en vivo:

| Tabla | Restaurada | QA en vivo | Lectura |
| --- | --- | --- | --- |
| `people_person` | 147 | 147 | Igual |
| `students_student` | 100 | 100 | Igual |
| `teachers_teacher` | 12 | 12 | Igual |
| `enrolments_enrolment` | 85 | — | Coincide con los 85 inscritos observados |
| `attendance_attendanceevent` | 0 | 169 | Esperado: el respaldo es de las 07:00 UTC y los 169 eventos de la prueba de carga son posteriores |
| `django_migrations` | 112 | — | Última aplicada 2026-10-09 03:42 UTC |

El conteo de eventos demuestra que la restauración devuelve el estado del
respaldo y no el actual: se pierde todo lo escrito después del último respaldo
diario (coherente con el RPO de referencia de 24 h). No hay recuperación a un
punto en el tiempo (`pointInTimeRecoveryEnabled: false`).

Limitaciones: se midió creación más restauración porque el destino no existía;
con una instancia ya creada, el tiempo de restauración fue 535 s. No se probó
la restauración de archivos del bucket ni el cambio de tráfico de Cloud Run a la
base restaurada, por lo que 896 s no equivale a un RTO de incidente completo.
Volumen sintético y pequeño; con datos reales el tiempo será mayor. La
verificación usó un usuario con contraseña temporal fijada en la instancia
desechable, ya eliminada; no se leyeron secretos de QA. Costo: una instancia
`db-f1-micro` durante unos 20 minutos.

Procedimiento repetible (la instancia destino debe existir antes de restaurar):

```sh
P=<PROJECT_ID>
gcloud sql backups list --instance=<INSTANCIA_QA> --project=$P
gcloud sql instances create <INSTANCIA_SIMULACRO> --project=$P --region=us-central1 \
  --database-version=POSTGRES_16 --edition=ENTERPRISE --tier=db-f1-micro \
  --storage-type=HDD --storage-size=10 --no-backup
gcloud sql backups restore <BACKUP_ID> --backup-instance=<INSTANCIA_QA> \
  --restore-instance=<INSTANCIA_SIMULACRO> --project=$P
# verificar con cloud-sql-proxy y psql (contraseña temporal solo en la instancia desechable)
gcloud sql instances delete <INSTANCIA_SIMULACRO> --project=$P
```
