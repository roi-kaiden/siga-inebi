# ADR-0010: Entorno QA en Google Cloud

## Estado

Aceptado para preparar QA a solicitud del usuario. Crear recursos y habilitar tráfico requiere revisar el plan concreto, costos y configuración. Este ADR no certifica despliegue ni aceptación institucional.

## Contexto

La Fase 7 requiere una URL HTTPS accesible desde un teléfono real, PostgreSQL y persistencia de archivos fuera de la base. El usuario eligió el proyecto existente `precise-blend-428821-e0` y una instancia Cloud SQL pequeña. El presupuesto de alertas permanece pendiente.

## Decisión

Usar Terraform para Cloud Run con dos contenedores en un servicio: Nginx entrega React y reenvía API al backend Gunicorn, conservando Host y HTTPS del origen. PostgreSQL 16 reside en Cloud SQL Enterprise `db-f1-micro` y los archivos en un bucket privado con URLs firmadas por identidad de servicio, sin llaves descargables. Secret Manager conserva las claves; el estado Terraform es sensible y debe permanecer en un bucket privado separado.

Preparar infraestructura primero, publicar imágenes por digest, ejecutar migraciones y siembra sintética como jobs explícitos y habilitar la web después de comprobarlos. El arranque de la web no migra ni siembra. Los jobs operativos de instalación no crean un sistema de colas ni alteran la decisión de ADR-0009 sobre procesamiento funcional diferido.

QA empieza en `us-central1`, mínimo 0/máximo 1 instancia y concurrencia 8. Backend 1 CPU/2 GiB más frontend 1 CPU/128 MiB: el total de 2 CPU/2.125 GiB es distinto del entorno de referencia RNF de 1 CPU/2 GiB y debe declararse al medir. Cloud SQL usa HDD 10 GB fijo (la opción más barata para staging; se reevaluará SSD con las mediciones de rendimiento), respaldo diario con 3 copias y protección contra borrado; bucket versionado, privado y sin borrado forzado. Estos valores son referencias QA, no políticas institucionales de retención, RPO o RTO.

## Consecuencias

- La URL HTTPS permite validar QR y sesión desde Android; cada resultado sigue requiriendo evidencia del candidato evaluado.
- Cloud SQL tiene costo continuo aunque Cloud Run no reciba tráfico. Alertas de presupuesto son opcionales y no limitan gasto; revisar costos antes de aplicar.
- La cuenta runtime obtiene permisos específicos de SQL, secretos, objetos del bucket y firma sobre sí misma. La pantalla pública de login no vuelve públicos los archivos ni sustituye los permisos del dominio.
- Planes y estado pueden contener secretos; no se versionan. Ninguna contraseña aparece en outputs, manuales ni logs de instalación.
- Cloud Run registra la URL completa de cada solicitud. Una exclusión de logging (`logging.tf`) descarta las entradas del servicio QA cuya URL lleva `token=`; Nginx y Gunicorn ya registran solo rutas. El resto de los logs de solicitud se conserva.
- Retirar QA requiere preservar evidencia y respaldos, y una decisión explícita para desactivar protecciones. Versionado de archivos y backups SQL no sustituyen las pruebas independientes de recuperación de Fase 7.

Implementación y secuencia: [Terraform QA](../../infra/terraform/qa/README.md). Costos y alternativas: [QA cloud: costos, optimización y alternativas](../planning/qa-cloud-costos-y-alternativas.md). Contratos públicos de la API y reglas de dominio mantienen su definición; esta decisión añade un perfil de instalación.
