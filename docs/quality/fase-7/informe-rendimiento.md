# Estado de las pruebas de rendimiento

RUN-D1-06 mide duración de controles automatizados, sin acreditar latencia de
usuario ni rendimiento sobre el perfil objetivo. Ejecutor: Codex en apoyo a
Daniel. Validación de Emilio y revisión de Pablo pendientes.

| Medida observada | Resultado |
| --- | --- |
| Corrida completa | 228,865 segundos, incluyendo preparación y limpieza |
| Suite backend | 1589 pruebas; 99,066 segundos JUnit; cobertura de líneas 94,45 % |
| Suite frontend | 283 pruebas en 32 archivos; 61,77 segundos de duración Vitest |
| Build/presupuesto frontend | Comando completo aprobado; log frontend-build |
| RAM/CPU de referencia | No aplicado límite de 1 vCPU/2 GB al host |
| Latencia QR y carga simultánea | No medidas; sin p50/p95/p99 ni tasa pico observada |

JUnit frontend suma 94,17 segundos de pruebas ejecutadas concurrentemente;
no representa duración de pared. Cobertura frontend: statements 73,02 %,
branches 67,99 %, functions 67,73 %, lines 73,67 %. Ver logs y reportes
del [índice de evidencias](indice-evidencias.csv). Estas cifras no se comparan
directamente con la cobertura histórica de Vitest 3 sin considerar el cambio V8.

## Latencia de escaneo en QA (RUN-CQ-03)

Medición del 12 de octubre de 2026 sobre Cloud Run `siga-inebi-qa`, revisión
`00004-fjj` (1 instancia máxima, concurrencia 8) y Cloud SQL `db-f1-micro`, con
datos sintéticos de `seed_demo_data`. Ejecutor: Claude Code en apoyo a Daniel;
validación de Emilio y revisión de Pablo pendientes. Las peticiones salieron
desde el navegador de Daniel por internet hasta `us-central1`, por lo que la
latencia incluye la red de ese equipo; no es latencia interna del servicio.
Procedimiento repetible: [`scripts/quality/load`](../../../scripts/quality/load/README.md).

| Campo | Valor |
| --- | --- |
| Operación | `POST /api/v1/attendance/scan/`, un movimiento `exit` por petición |
| Carga | 3 operadores concurrentes (referencia provisional de RNF-REN-002), 28 escaneos cada uno, sin pausa |
| Resultado | 84 de 84 creados; 0 errores, 0 eventos perdidos |
| p50 / p95 / p99 / máx | 287 / 393 / 438 / 438 ms |
| Throughput | 9,97 escaneos/s en 8,43 s |

Frente a RNF-REN-001 (p95 ≤ 2 s), el p95 observado fue 393 ms en este entorno y
perfil. Es evidencia direccional: muestra pequeña (84), una sola sesión de
usuario compartida por los tres operadores, sin repetir y sin medir CPU ni
memoria. No se probó el perfil de 1 vCPU/2 GB local ni se confirmó tasa pico
institucional (PD-010).

Una corrida previa de 120 entradas creó 84; los 36 rechazos fueron del dataset
(los estudiantes `EST-2026-0086` en adelante no tienen inscripción activa, solo
hay 85 inscritos). Sus latencias no se conservaron, por lo que no se reportan.
La corrida de salidas reutilizó a los 84 estudiantes con inscripción.

Hallazgo: `seed_demo_data` no concede `attendance_record_entry` ni
`attendance_record_exit` al rol `system-administrator`; con ese seed, el
administrador recibe «El actor no tiene los permisos requeridos» al escanear.
En QA se asignaron manualmente desde el admin de Django, junto con el punto de
control `LOAD-QA`. Corrección del seed pendiente, sin incidencia registrada.
Quedaron en QA 85 entradas y 84 salidas sintéticas.

Pendiente: acordar carga institucional, preparar dataset de referencia, aplicar
perfil objetivo, ejecutar teléfono por HTTPS y medir capturas QR exitosas,
percentiles, errores, CPU y memoria. Declarar dispositivo, navegador, red y
volumen; registrar falla de cámara/permisos como resultado, no aprobación.
La preparación Cloud Run/Cloud SQL tendrá costos y recursos declarados antes
de medir. Este informe no concede conformidad a requisitos de rendimiento.
