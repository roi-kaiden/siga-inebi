# QA en Google Cloud

Configuración para el proyecto **existente** `precise-blend-428821-e0`, región `us-central1`. No crea proyectos ni vincula facturación. Los valores iniciales preparan infraestructura; `deploy_jobs` y `deploy_service` están desactivados hasta disponer de imágenes reales fijadas por digest. El presupuesto mensual queda pendiente: `monthly_budget_usd = null` no crea alertas.

## Recursos y límites

- Un servicio Cloud Run con Nginx/React en 8080 y Django/Gunicorn en 8081, mismo origen HTTPS y arranque del backend antes del frontend. Concurrencia 8, mínimo 0 y máximo 1 instancia. Perfil total de **2 CPU y 2.125 GiB** (backend 1 CPU/2 GiB; frontend 1 CPU/128 MiB). Este perfil no demuestra el RNF de referencia de 1 CPU/2 GiB.
- PostgreSQL 16, Cloud SQL Enterprise `db-f1-micro`, una zona, HDD 10 GB (el disco más barato; evaluar SSD si el rendimiento lo exige), sin ampliación automática. Usa IP pública sin redes cliente autorizadas y el conector autenticado de Cloud SQL montado en `/cloudsql`; no se ofrece acceso público directo a PostgreSQL. Backups diarios a las 07:00 UTC, 3 copias retenidas como referencia QA, sin recuperación puntual. La política institucional y el RPO/RTO siguen pendientes.
- Bucket de archivos privado, acceso uniforme, prohibición de acceso público, versiones de objetos y sin borrado forzado. Versionar objetos conserva historia, pero no demuestra por sí solo un respaldo independiente ni una restauración verificable.
- Tres secretos (base, Django, administrador sintético), generados por Terraform. Los valores se conservan en el **estado sensible**; nunca se imprimen ni se exportan como outputs. Cloud Run consume versiones fijas. La web recibe base/Django; el job de siembra también recibe la clave del administrador `qa-admin`, correo `admin@example.invalid`.
- Exclusión de logging para entradas de solicitud de Cloud Run con `token=` en la URL (descargas firmadas).
- Cuenta de servicio sin llaves descargables: conexión SQL, acceso a esos secretos, objetos del bucket y firma sobre su propia cuenta, con concesiones específicas. Los jobs no tienen IAM público. La web permite invocación pública para presentar la pantalla de login; la autorización de Django protege los datos.

## Preparación y comprobaciones

Se requieren Terraform ≥1.9, credenciales Google del operador, permisos para los recursos e IAM declarados y facturación habilitada. El estado remoto requiere un bucket **privado independiente** revisado y creado previamente por el operador, con acceso restringido, versiones y cifrado de Google. No almacenar estado en el bucket de medios. La creación del bucket de estado no forma parte de este módulo y debe revisarse antes de efectuarla.

```bash
terraform -chdir=infra/terraform/qa init -backend=false
terraform -chdir=infra/terraform/qa fmt -check
terraform -chdir=infra/terraform/qa validate
```

Requisito previo, una sola vez por proyecto: `gcloud services enable serviceusage.googleapis.com cloudresourcemanager.googleapis.com --project=PROJECT_ID`. Terraform necesita Service Usage para activar las demás APIs y Resource Manager para leer el proyecto del presupuesto; ninguna de las dos puede activarse desde el mismo plan.

Copiar `terraform.tfvars.example` a `terraform.tfvars` y `backend.hcl.example` a `backend.hcl`, completar el bucket **real** de estado, después inicializar con `terraform init -backend-config=backend.hcl`. Las credenciales se obtienen por ADC o credenciales del proceso, nunca desde un archivo dentro del repositorio. No incluir planes binarios, estado, variables privadas, `.terraform/` ni claves en Git. Un plan puede contener datos sensibles aunque la salida humana los oculte.

## Secuencia de despliegue tras revisar y aprobar el plan

1. Revisar `terraform plan` con ambos flags en `false`, incluyendo los costos de SQL, almacenamiento, backups, imágenes y logs. Aplicar solo el plan aprobado. Activar APIs puede tardar; los recursos dependen explícitamente de su habilitación.
2. Construir los targets `backend` y `frontend` de `Dockerfile.cloud`, subirlos al repositorio indicado por `image_repository` y registrar sus digests junto al SHA y pruebas de la versión. No usar etiquetas flotantes ni imágenes de ejemplo para desplegar.
3. Configurar `backend_image` real y `deploy_jobs = true`, mantener `deploy_service = false`, revisar y aplicar ese plan. Ejecutar primero `siga-inebi-qa-migrate` y verificar éxito; ejecutar después `siga-inebi-qa-seed` y verificar éxito. Terraform crea jobs pero **no los ejecuta**. No ejecutar la siembra sobre datos institucionales. No migrar automáticamente al arrancar la web.
4. Configurar `frontend_image` real y `deploy_service = true` después de ambos jobs, revisar y aplicar el plan. Verificar health, login, permisos, carga de archivo privado, recuperación por URL firmada y QR desde Android con HTTPS. Guardar evidencias reales y registrar el URL de `service_url`.

Los jobs se ejecutan de forma explícita con `gcloud run jobs execute JOB --region=us-central1 --project=precise-blend-428821-e0 --wait`. Si fallan, la web permanece desactivada; conservar los logs sin secretos y corregir antes de habilitar tráfico. No existe una dependencia Terraform que certifique que esos comandos terminaron con éxito: la habilitación de la web es un paso operativo deliberado.

## Despliegue continuo desde GitHub Actions

Tras la puesta en marcha inicial, `.github/workflows/deploy-qa.yml` (CI/CD QA) despliega QA en cada push a `develop` (y con `workflow_dispatch`, solo sobre `develop`). Primero ejecuta la suite completa de `ci.yml` (lint, pruebas backend y frontend, seguridad, build e integración con Docker); el despliegue depende de ese job y **no corre si cualquier control falla**. Por eso `ci.yml` ya no se dispara por push a `develop`: en esa rama corre dentro de este pipeline. Después el flujo construye los targets `backend` y `frontend` de `Dockerfile.cloud`, los etiqueta con el SHA completo del commit, los sube a `image_repository` y resuelve sus digests. Después actualiza la imagen de `siga-inebi-qa-migrate` y `siga-inebi-qa-seed`, ejecuta **solo** la migración con `--wait` y, si termina con éxito, actualiza el servicio con ambos digests. La siembra recibe la imagen nueva pero el flujo **nunca la ejecuta**. Cierra con una comprobación de `/api/v1/health/database/` y un resumen del job con SHA, digests y revisión lista. Las ejecuciones no se cancelan entre sí: se encolan (`concurrency: deploy-qa`).

Autenticación sin llaves ni secretos de GitHub, mediante Workload Identity Federation (`deploy.tf`):

- Pool `siga-inebi-qa-github` y proveedor OIDC `github-actions` (`https://token.actions.githubusercontent.com`). La condición de confianza exige `assertion.repository == github_repository` **y** `assertion.ref == refs/heads/<deploy_branch>` (por defecto `siga-inebi/siga-inebi` y `develop`). Las PR, otras ramas y los forks no obtienen credenciales.
- Cuenta `siga-inebi-qa-deployer`, suplantable solo desde ese repositorio. Permisos mínimos: `roles/artifactregistry.writer` sobre el repositorio de imágenes; `roles/run.developer` a nivel de proyecto (gcloud espera operaciones de Cloud Run con alcance de proyecto, por lo que una concesión sobre el recurso no basta); `roles/iam.serviceAccountUser` únicamente sobre la cuenta runtime, para desplegar revisiones que se ejecutan con ella. Sin acceso a secretos, al bucket de estado Terraform ni a la administración de Cloud SQL.
- El proveedor y la cuenta aparecen como valores literales en el workflow; no son secretos y provienen de los outputs `github_workload_identity_provider` y `github_deployer_service_account`.

Terraform **ignora los cambios de imagen** del servicio y de los jobs (`lifecycle.ignore_changes`), además de `client`/`client_version` que escribe gcloud y los montajes de volumen, porque Cloud Run reporta el montaje de Cloud SQL en el contenedor de ingreso aunque Terraform lo declare en `backend`. `backend_image` y `frontend_image` quedan como imágenes iniciales; una vez activado el flujo, las actualizaciones de imagen pasan por GitHub Actions y Terraform conserva el resto de la configuración.

Orden de puesta en marcha: revisar y aplicar con `terraform apply` el plan que crea el pool, el proveedor, la cuenta deployer y sus permisos **antes** de fusionar el workflow en `develop`; de lo contrario la primera ejecución falla al autenticarse. Confirmar que los valores literales del workflow coinciden con los outputs.

Reversión: volver a ejecutar el workflow no sirve para desplegar un commit anterior, porque siempre construye la cabeza de `develop`. Para regresar a una revisión previa del servicio:

```bash
gcloud run revisions list --service=siga-inebi-qa --region=us-central1 --project=precise-blend-428821-e0
gcloud run services update-traffic siga-inebi-qa --to-revisions=REVISION=100 --region=us-central1 --project=precise-blend-428821-e0
```

La migración ya aplicada no se revierte con el tráfico; evaluar compatibilidad del esquema antes de regresar. Mientras el tráfico esté fijado, las revisiones nuevas no lo reciben; el workflow ejecuta `update-traffic --to-latest` después de cada despliegue para devolverlo a la revisión nueva.

Control de acceso: quien puede fusionar en `develop` puede desplegar en QA. Como medida opcional, un *environment* de GitHub con revisores obligatorios añade una aprobación manual; requiere permisos de administración del repositorio y ajustar la condición de confianza (el `sub` del token cambia a `repo:...:environment:...`, aunque `repository` y `ref` se mantienen).

## Costos, alertas y retiro

Cloud SQL factura mientras la instancia existe aunque Cloud Run escale a cero. Para `us-central1`, el precio de referencia `db-f1-micro` es aproximadamente **USD 0.0105/h ≈ 7.67/730 h de cómputo**, más disco HDD, backups y otros consumos; confirmar el importe vigente en [precios oficiales de Cloud SQL](https://cloud.google.com/sql/pricing) y la calculadora antes de aplicar. El tipo compartido no incluye la garantía SLA de los tipos dedicados. [Cloud Run](https://cloud.google.com/run/pricing), [Storage](https://cloud.google.com/storage/pricing), Artifact Registry, Secret Manager y logs pueden añadir cargos.

El presupuesto opcional usa la cuenta de facturación existente y alertas al 50 %, 90 % y 100 % con los destinatarios de facturación predeterminados. Una alerta **no corta el gasto**. Definir importe y permisos de Billing Budgets antes de activarlo. El filtro cubre el proyecto, por lo que incluirá cualquier otro recurso presente allí.

SQL tiene protección contra borrado en Terraform y en el servicio; Cloud Run y jobs también están protegidos. Un bucket no vacío no se elimina. El retiro requiere una decisión posterior que conserve respaldos, versiones y evidencia, revise el estado y desactive protecciones explícitamente; no usar `terraform destroy` como limpieza de una corrida QA.

Referencias: [servicio Cloud Run v2 en Terraform](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/cloud_run_v2_service), [contrato de contenedores](https://cloud.google.com/run/docs/container-contract), [secretos Cloud Run](https://cloud.google.com/run/docs/configuring/services/secrets), [CPU Cloud Run](https://cloud.google.com/run/docs/configuring/services/cpu).
