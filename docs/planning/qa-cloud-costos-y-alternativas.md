# QA cloud: costos, optimización y alternativas

Estado al 8 de octubre de 2026. Documento de discusión para decidir qué hacer si
el entorno QA resulta lento o caro; la decisión queda registrada como PD-012 en
[decisiones pendientes](../decisions/pending-decisions.md). La arquitectura
vigente está en [ADR-0010](../decisions/ADR-0010-cloud-qa.md) y la evidencia del
despliegue en [RUN-CQ-01](../quality/fase-7/despliegue-cloud-qa.md).

Los precios son aproximados, en USD por mes, para uso bajo (QA o una sola
institución) y cambian con frecuencia. Confirmarlos en las calculadoras
oficiales antes de decidir.

## Cómo está hoy

- **Base de datos:** Cloud SQL PostgreSQL 16 gestionado por Google, instancia
  `db-f1-micro` (la más barata: CPU compartida y 0.6 GB de RAM), disco HDD de
  10 GB. Respaldos diarios automáticos con las últimas 3 copias, sin
  recuperación a un momento puntual.
- **Aplicación:** Cloud Run (serverless) con dos contenedores en el mismo
  servicio: Nginx con React y Django con Gunicorn. Escala de 0 a 1 instancia.
  Con 0 instancias no cobra, pero la primera visita después de un rato sin uso
  tarda unos segundos (arranque en frío).
- **Archivos:** fotos y documentos en un bucket privado, entregados con enlaces
  firmados que vencen a los 5 minutos.
- **Flujo de despliegue:** commit → dos imágenes Docker (backend y frontend)
  identificadas por digest → Terraform actualiza el servicio. Migraciones y
  carga de datos corren como jobs aparte. Hoy es manual; automatizarlo con
  GitHub Actions está pendiente.
- **Presupuesto:** alertas al 50, 90 y 100 % de USD 20 mensuales. Avisan, pero
  no cortan el gasto.

## Costos estimados

| Opción | Mensual | Notas |
| --- | --- | --- |
| **A. Actual: Cloud Run + Cloud SQL** | **~10–12** | Cloud SQL ≈ 7.7 de cómputo + 0.9 de disco + respaldos. Cloud Run, bucket, imágenes y logs quedan casi siempre dentro de la capa gratuita. |
| A1. Base con SSD en vez de HDD | +~0.80 | Con 10 GB la diferencia es mínima; ayuda poco si el cuello de botella es CPU o RAM. |
| A2. Base `db-g1-small` (1.7 GB RAM) | ~30 total | Mejora real de rendimiento de la base. |
| A3. Una instancia siempre encendida | +~10–20 | Elimina el arranque en frío. |
| **B. Cloudflare + Neon** | **~10–20** | Pages para el frontend (gratis), Django en Containers (plan de 5 más consumo), Neon por uso (~5–6 con poco tráfico) y archivos en R2 (10 GB gratis). |
| **C. VM con todo adentro** | **~6–9** Hetzner, **~15–27** GCP e2-small/e2-medium | Docker Compose actual en un servidor, sin Cloud SQL ni buckets, siempre encendido. |

## Lo que no se ve en el precio

**A. Actual.** Ya está hecho, probado y descrito en Terraform. Google se encarga
de respaldos, parches y HTTPS. Lo débil es la base mínima y el arranque en frío.

**B. Cloudflare + Neon.** Cloudflare Workers no puede ejecutar Django: los
Python Workers corren sobre Pyodide y no soportan este stack. La vía real es
Cloudflare Containers, un producto reciente. Hay que rehacer la infraestructura,
la configuración de Django y la conexión a la base (Neon requiere pooling de
conexiones y también se suspende, con su propio arranque en frío). R2 sigue
siendo un bucket. Ahorra poco frente a A.

**C. VM.** Es la más barata y la que da más rendimiento por dólar, pero pasan a
ser nuestra responsabilidad: respaldos y su copia fuera del servidor,
actualizaciones del sistema operativo, certificado HTTPS, monitoreo y
recuperación si la VM falla. RNF-RES-001 y RNF-RES-002 siguen aplicando; la
copia externa probablemente terminaría en un bucket o un Storage Box
(~€3–4 mensuales).

## Si el entorno resulta lento

En orden, de menor a mayor costo:

1. **Medir.** La prueba de rendimiento sobre este entorno está pendiente; sin
   datos no sabemos si el cuello de botella es la base, la aplicación o el
   arranque en frío.
2. **Optimizar sin gastar:** evitar consultas N+1 con
   `select_related`/`prefetch_related`, índices donde hagan falta, paginación,
   fotos en miniatura, lazy loading y división del código en React, y caché para
   lo que casi no cambia.
3. **Subir la base a `db-g1-small`** si la base resulta ser el cuello de
   botella.
4. **Una instancia siempre encendida** si la queja es la primera carga.
5. **Cambiar de plataforma** solo si el costo sigue siendo un problema después
   de lo anterior. En ese caso, la VM (C) es la alternativa con más sentido;
   Cloudflare + Neon no se justifica para Django.

## Recomendación

Mantener A para QA, ejecutar la medición de rendimiento pendiente y decidir con
datos. Queda para Pablo elegir la prioridad si el entorno resulta lento:
optimizar primero o pagar una base más grande.

## Fuentes

- [Precios oficiales de Cloud SQL](https://cloud.google.com/sql/pricing)
- [Guía de precios de Cloud SQL (NetApp)](https://www.netapp.com/blog/gcp-cvo-blg-google-cloud-sql-pricing-and-limits-a-cheat-sheet/)
- [Precios de Cloudflare Containers](https://developers.cloudflare.com/containers/pricing/)
- [Comparativa de precios de Neon 2026 (Prisma)](https://www.prisma.io/blog/prisma-postgres-vs-neon-pricing-2026)
- [Calculadora de precios de Neon (Makerkit)](https://makerkit.dev/pricing-calculator/neon)
- [Precios de Hetzner 2026](https://agentdeals.dev/hetzner-pricing-2026)
- [Precio de GCP e2-medium (Holori)](https://calculator.holori.com/gcp/vm/e2-medium)
