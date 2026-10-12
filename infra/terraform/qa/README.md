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

## Costos, alertas y retiro

Cloud SQL factura mientras la instancia existe aunque Cloud Run escale a cero. Para `us-central1`, el precio de referencia `db-f1-micro` es aproximadamente **USD 0.0105/h ≈ 7.67/730 h de cómputo**, más disco HDD, backups y otros consumos; confirmar el importe vigente en [precios oficiales de Cloud SQL](https://cloud.google.com/sql/pricing) y la calculadora antes de aplicar. El tipo compartido no incluye la garantía SLA de los tipos dedicados. [Cloud Run](https://cloud.google.com/run/pricing), [Storage](https://cloud.google.com/storage/pricing), Artifact Registry, Secret Manager y logs pueden añadir cargos.

El presupuesto opcional usa la cuenta de facturación existente y alertas al 50 %, 90 % y 100 % con los destinatarios de facturación predeterminados. Una alerta **no corta el gasto**. Definir importe y permisos de Billing Budgets antes de activarlo. El filtro cubre el proyecto, por lo que incluirá cualquier otro recurso presente allí.

SQL tiene protección contra borrado en Terraform y en el servicio; Cloud Run y jobs también están protegidos. Un bucket no vacío no se elimina. El retiro requiere una decisión posterior que conserve respaldos, versiones y evidencia, revise el estado y desactive protecciones explícitamente; no usar `terraform destroy` como limpieza de una corrida QA.

Referencias: [servicio Cloud Run v2 en Terraform](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/cloud_run_v2_service), [contrato de contenedores](https://cloud.google.com/run/docs/container-contract), [secretos Cloud Run](https://cloud.google.com/run/docs/configuring/services/secrets), [CPU Cloud Run](https://cloud.google.com/run/docs/configuring/services/cpu).
