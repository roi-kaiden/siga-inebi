# Despliegue QA cloud — RUN-CQ-01

Primer despliegue QA en Cloud Run, 8 de octubre de 2026, 21:39–22:05,
America/Guatemala (2026-10-09 03:39–04:05 UTC). Ejecutores: Daniel (Terraform,
imágenes, prueba manual) y Claude Code en apoyo a Daniel (plan, verificación por
API y logs). Revisión de Pablo/Josué pendiente. Datos sintéticos de
`seed_demo_data`; sin datos reales. No constituye aceptación institucional.

Infraestructura y decisiones: [ADR-0010](../../decisions/ADR-0010-cloud-qa.md) e
[`infra/terraform/qa`](../../../infra/terraform/qa/README.md).

## Entorno

| Campo | Valor |
| --- | --- |
| URL | `https://siga-inebi-qa-bhaiw2sjla-uc.a.run.app` |
| Proyecto / región | `precise-blend-428821-e0` / `us-central1` |
| Servicio | Cloud Run `siga-inebi-qa`, mínimo 0 / máximo 1 instancia, concurrencia 8 |
| Base | Cloud SQL `siga-inebi-qa-pg16`: PostgreSQL 16, `db-f1-micro`, HDD 10 GB, 3 backups |
| Archivos | Bucket privado `precise-blend-428821-e0-siga-inebi-qa-media`, URLs firmadas de 300 s |
| Estado Terraform | `gs://precise-blend-428821-e0-siga-inebi-tfstate`, prefijo `siga-inebi/qa` |
| Presupuesto | Alertas al 50/90/100 % de USD 20 mensuales; no cortan el gasto |

## Imágenes

Artifact Registry `us-central1-docker.pkg.dev/precise-blend-428821-e0/siga-inebi-qa`.
Se publica un índice multiplataforma; Cloud Run y los jobs registran el
manifiesto `linux/amd64` que resuelven de ese índice.

| Commit | Imagen | Índice publicado | Manifiesto `linux/amd64` |
| --- | --- | --- | --- |
| `ea2c8a2` | backend | `sha256:3cc37b440380476d0de1dac2b1a08c0939b83608889b89a2a44b381c3fb1fe5d` | `sha256:987f211384543f21d3e0cf8556644ef37d8a9cd1d41b77c2662fcdb857f95cd0` |
| `ea2c8a2` | frontend | `sha256:34ad45c61ed311434a7b103e5e647e03e8e3a4acad813e171d9a5a8cc87058d1` | `sha256:02e70b92ef031718be1a912608d74d88218061280de4293c0a941a6a478fd085` |
| `bcc3068` | backend | `sha256:624327f93e093c3265a454d0cbb13644e233c90b4471a7722eabb1b2d6c8f5c6` | `sha256:e18ceed6f3af30c535b4e48c482beb7ba1dabddc4c54589fed34e67169be4ee7` |
| `bcc3068` | frontend | `sha256:4fb8318a04a5c592d261ca5722f25b25579ee5f2b9a7d8e663d52b6a13574572` | `sha256:82ce5816c5d8fcc55923919a5a75928fca3cac4aee0b2667e0d012a5617edcd0` |
| `47fdcc6` | frontend | `sha256:107869ce511a838ebec17eddade633c1abef2deb727e0476a74e8924bef3dd33` | `sha256:c62017dee3a33132f1dc077ca1658fbb501884a876571bf0209b76ca47115cd0` |

`47fdcc6` solo cambia el frontend; el backend de `bcc3068` es el vigente.

## Revisiones y jobs

| Recurso | Creación UTC | Backend | Frontend | Resultado |
| --- | --- | --- | --- | --- |
| Job `siga-inebi-qa-migrate-smc4v` | 03:42:58 (fin) | `ea2c8a2` | — | 1 tarea exitosa |
| Job `siga-inebi-qa-seed-nx2sk` | 03:44:28 (fin) | `ea2c8a2` | — | 1 tarea exitosa |
| Revisión `siga-inebi-qa-00001-88z` | 03:46:02 | `ea2c8a2` | `ea2c8a2` | Reemplazada |
| Revisión `siga-inebi-qa-00002-dgd` | 03:51:24 | `bcc3068` | `bcc3068` | Reemplazada; INC-007 |
| Revisión `siga-inebi-qa-00003-h4z` | 04:01:12 | `bcc3068` | `47fdcc6` | Vigente |

`bcc3068` no añade migraciones; no se volvieron a ejecutar los jobs.

## Verificaciones

| Control | Revisión | Resultado |
| --- | --- | --- |
| HTTPS y redirección | 00002 | `/` 200 por HTTPS; HTTP responde 302 a HTTPS |
| Health de base | 00002 | `/api/v1/health/` y `/api/v1/health/database/` 200 |
| Login `qa-admin` | 00002 | 200; cookies `csrftoken` y `sessionid` con `Secure`, `sessionid` `HttpOnly` |
| API autenticada | 00002 | `/auth/me/` 200; `/students/` 200 con 100 alumnos sintéticos |
| Foto en bucket | 00002 | `PATCH /students/<id>/` 200; objeto en `student_photos/` |
| URL firmada | 00002 | Con firma 200 `image/jpeg`; mismo objeto sin firma 403 |
| Documento | 00002 | `POST /documents/records/` 201; `POST .../verify/` 204; objeto en `documents/` |
| Logout | 00002 | 204; `/auth/me/` devuelve `authenticated: false` |
| Edición con foto, flujo de la interfaz | 00003 | `PATCH /people/<public_id>/` 200, foto 200, URL firmada 200 |
| Edición desde la interfaz | 00003 | Confirmación manual de Daniel; sin captura adjunta |
| Logs sin `token=` | 00001–00003 | 0 entradas con `token=` en logs del servicio hasta 04:10 UTC |

Las verificaciones por API se ejecutaron con un script local no versionado que
toma la contraseña de Secret Manager sin imprimirla.

## Validación del pipeline CI/CD — RUN-CQ-02

El 8 de octubre de 2026 (2026-10-09 04:44–04:50 UTC) se validó el workflow
CI/CD QA desde una rama temporal `deploy`, con la condición de Workload Identity
apuntando a esa rama solo durante la prueba.

| Campo | Valor |
| --- | --- |
| Run | [37885251733](https://github.com/siga-inebi/siga-inebi/actions/runs/37885251733) |
| Commit | `24d0e9a` |
| CI | 7 jobs aprobados: lint, pruebas, seguridad, build e integración Docker |
| Migración | `siga-inebi-qa-migrate-s7fmn`, 1 tarea exitosa |
| Revisión | `siga-inebi-qa-00004-fjj`, 100 % del tráfico |
| Backend | `sha256:b8ed99e22edfe5f24ac9aeaba5057f228e61f4ff3e1f6eec116f7395be4655c7` |
| Frontend | `sha256:d3a4e4d93b71b256cb05231d35a75882fe6d787beb7b843b8bd4726f9142c5ee` |
| Health | `/api/v1/health/database/` 200; `terraform plan` sin cambios después del despliegue |

El primer intento ([37884620008](https://github.com/siga-inebi/siga-inebi/actions/runs/37884620008))
aprobó el CI y la migración, pero falló al actualizar el servicio por el orden
de argumentos de `gcloud run services update`; el servicio no cambió. Se
corrigió antes del run anterior.

## Trazabilidad de commits

Los commits citados se hicieron en ramas que después se reorganizaron en PRs
apilados y se integran con squash. Para que sigan accesibles, cada uno tiene un
tag:

| Commit | Tag | Uso |
| --- | --- | --- |
| `ea2c8a2` | `evidence/run-cq-01/ea2c8a2` | Imágenes iniciales, jobs y revisión 00001 |
| `bcc3068` | `evidence/run-cq-01/bcc3068` | Revisión 00002 y backend vigente en 00003 |
| `47fdcc6` | `evidence/run-cq-01/47fdcc6` | Frontend de la revisión 00003 (INC-007) |
| `24d0e9a` | `evidence/run-cq-02/24d0e9a` | Validación del pipeline, revisión 00004 |

## Incidencias

- **INC-007:** en `00002` la edición de alumnos, docentes y encargados enviaba
  `PATCH /api/v1/people/undefined/` (404) y no llegaba a guardar la foto. La
  interfaz usaba `person.id`, que la API no expone. Corregida en `47fdcc6`;
  verificada en `00003`.

## Pendientes

- **Descarga con token:** Daniel confirmó descargas en la interfaz, pero los
  logs no registran ninguna solicitud a `/documents/records/<id>/download/`
  durante la corrida. El flujo de token y la exclusión de logs de
  `logging.tf` quedan sin verificar con una descarga real por esa ruta.
- Mediciones de rendimiento representativas sobre este entorno.
- Simulacro de recuperación en cloud: backups de Cloud SQL y versiones del bucket.
- QR desde un teléfono Android real por HTTPS.
- Revisión independiente y aceptación institucional.
