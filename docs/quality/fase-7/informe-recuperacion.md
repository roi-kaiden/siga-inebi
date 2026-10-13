# Verificación de respaldo y recuperación

La suite RUN-D1-06 aprobó las pruebas de respaldo y recuperación, incluida
restauración real en PostgreSQL 16 y extracción independiente de archivos
sintéticos. Codex ejecutó en apoyo a Daniel; Roí auditó la integridad del
almacenamiento documental y el caso CP-INT-REC-001; revisión de Pablo pendiente.

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
| Integridad de almacenamiento documental (RNF-RES-003, CP-INT-REC-001) | Aprobada en integración backend (EJ-ROI-20261012-001); comando automatizado `check_document_storage_integrity` verifica hashes SHA-256 de archivos persistidos frente a registros en BD |
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
UTC) por Claude Code en apoyo a Daniel. Revisión de Roí efectuada en lo referente
a almacenamiento documental y sincronía de pilas; revisión de Pablo pendiente. Se
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

## Verificación de almacenamiento documental y caso CP-INT-REC-001 (Roí)

Como responsable de documentos y almacenamiento de Fase 7 (RF-DOC, RF-ARC, RF-PLA, RF-EMI, RNF-RES-003), Roí auditó los procedimientos de respaldo y recuperación de ambas pilas y validó el caso **CP-INT-REC-001** (*Respaldar DB/archivos por separado → restaurar en destino QA → verificar relaciones, binarios e integridad*):

### 1. Independencia y correspondencia entre pilas (RNF-RES-001)
- La base de datos (PostgreSQL 16) almacena metadatos inmutables de los documentos (`DocumentRecord`: `public_id`, `storage_key`, `checksum` SHA-256, `size_bytes`, `content_type`, `version_number`).
- Los binarios residen exclusivamente en el backend de almacenamiento configurado (`MEDIA_ROOT` local o bucket en Cloud Storage), nunca embebidos en tablas de PostgreSQL.
- Los artefactos de respaldo (`database/*.dump` y `files/*.tar.gz`) son estrictamente independientes y cuentan con manifiestos JSON y sumas de comprobación aisladas.
- Restaurar únicamente la base de datos sin la pila de archivos deja registros con archivos inexistentes (`status: missing`); restaurar únicamente los archivos deja binarios no asociados sin acceso contractual.

### 2. Detección de inconsistencias post-restauración y orfandad
- **Archivos faltantes (`missing`)**: Si se restaura la base de datos pero el almacenamiento documental queda rezagado o incompleto, las entidades en PostgreSQL referenciarán rutas en storage que no existen físicamente.
- **Corrupción o alteración de binarios (`corrupted`)**: Si un archivo en almacenamiento sufre corrupción de datos o alteración maliciosa, el cálculo de su hash SHA-256 discrepará con el `checksum` inmutable registrado en el `DocumentRecord`.
- **Archivos huérfanos**: Binarios presentes en el medio de almacenamiento sin un `DocumentRecord` asociado en base de datos. Por arquitectura (RNF-SEG-005), las descargas públicas directas están estrictamente bloqueadas y solo se emiten a través de endpoints seguros autenticados con tokens efímeros firmados por el backend.

### 3. Verificación automatizada con `check_document_storage_integrity` (RNF-RES-003)
- La verificación periódica y post-restauración de integridad documental se ejecuta mediante el comando de gestión monitoreado:
  ```sh
  python manage.py check_document_storage_integrity [--institution-id=<ID>] [--json]
  ```
- **Flujo de verificación**:
  1. Itera sobre cada registro activo de `DocumentRecord` (con soporte para acotar al ámbito de una institución específica vía `--institution-id`).
  2. Valida la existencia física mediante `default_storage.exists(storage_key)`.
  3. Lee el archivo y calcula `hashlib.sha256(payload).hexdigest()`.
  4. Compara el hash calculado con el checksum guardado en base de datos.
  5. Si detecta archivos faltantes (`missing`), no legibles (`unreadable`) o corruptos (`corrupted`), termina con código de salida `1` (`SystemExit(1)`).
  6. Registra métricas detalladas en la tabla `TaskRun` (`total_checked`, `ok`, `missing`, `corrupted`, `unreadable`).

### 4. Cobertura de pruebas automatizadas (CP-INT-REC-001)
En `backend/tests/integration/test_backup_and_recovery.py` se incorporaron 4 pruebas automáticas de integración que validan el ciclo completo:
- `test_post_restore_document_storage_integrity_verifies_all_files_match`: Validación exitosa cuando ambas pilas están sincronizadas (100% OK, TaskRun `SUCCEEDED`).
- `test_post_restore_document_storage_integrity_detects_missing_file_when_storage_desynchronized`: Detección precisa de archivo faltante por desincronización de storage (código 1, TaskRun `FAILED`, `missing=1`).
- `test_post_restore_document_storage_integrity_detects_corrupted_file_with_altered_checksum`: Detección de alteración o corrupción de archivo en storage (código 1, TaskRun `FAILED`, `corrupted=1`).
- `test_post_restore_document_storage_integrity_scoped_to_institution`: Verificación acotada al ámbito institucional mediante el parámetro `--institution-id`.

Ejecución registrada en `docs/quality/fase-7/ejecuciones.csv` como **EJ-ROI-20261012-001** (corrida RUN-ROI-20261012-01).

