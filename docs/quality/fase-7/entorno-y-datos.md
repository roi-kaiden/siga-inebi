# Entorno y datos de Fase 7

La corrida local RUN-D1-06 aprobó el 8 de octubre de 2026, 21:00–21:04,
America/Guatemala. Ejecutor: Codex en apoyo a Daniel; revisión de Pablo/Josué
pendiente. No constituye validación institucional ni despliegue cloud.

| Componente | Entorno observado |
| --- | --- |
| Host | CachyOS/Linux, 16 CPU, 33 427 566 592 bytes de RAM. Sin límites de 1 vCPU/2 GB. |
| Docker / Compose | 29.8.2 / 5.6.0 |
| Backend | Python 3.11.17, Django 5.2.17, settings test, cliente PostgreSQL 16 |
| Frontend | Node 22.23.3; Vitest 4.1.11; máximo dos workers |
| Base | PostgreSQL 16.15; servicio db-test desechable, datos sintéticos de factories |
| Aislamiento | Proyecto Compose exclusivo; archivos de test temporales fuera del media vigente; limpieza registrada |
| HTTPS/teléfono | HTTPS verificado en [RUN-CQ-01](despliegue-cloud-qa.md); teléfono pendiente |

SHA base `3bcca08860b07c7086ac11b914a7262e7a68d282`, árbol modificado, digest
`ce64ff0cbf5c3db9a05cd41c186653b375b80aa947d09eed966b73cf503f5e5a`.
El digest fue idéntico al inicio y al final (`source_stable: true`). Cambios
posteriores, incluida documentación/cloud, requieren otra identificación.

Los datasets son fixtures sintéticos aislados por prueba. No se midió un
dataset de 500 estudiantes ni volumen documental representativo de un ciclo.
RUN-D1-05 conserva el intento previo con errores de permisos del media del host
y preparación de fixtures; los registros iniciales macOS conservan su entorno.

Reproducción desde la raíz, con fuentes equivalentes y un identificador nuevo:

```sh
python3 scripts/quality/run_phase7_checks.py --run-id RUN-D1-07
```

No reutilizar IDs. Registrar SHA, digest y versiones de cada repetición.
El índice [indice-evidencias.csv](indice-evidencias.csv) identifica artefactos
locales ignorados y sus checksums. Exportación externa/retención pendientes.

QA cloud solicitado: Cloud Run con Terraform y Cloud SQL pequeño, proyecto
`precise-blend-428821-e0`. Desplegado en la corrida separada
[RUN-CQ-01](despliegue-cloud-qa.md), con URL, imágenes y revisiones propias.
Presupuesto con alertas de USD 20 mensuales. Mediciones pendientes.
