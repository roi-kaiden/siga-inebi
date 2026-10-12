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

Pendiente: acordar carga institucional, preparar dataset de referencia, aplicar
perfil objetivo, ejecutar teléfono por HTTPS y medir capturas QR exitosas,
percentiles, errores, CPU y memoria. Declarar dispositivo, navegador, red y
volumen; registrar falla de cámara/permisos como resultado, no aprobación.
La preparación Cloud Run/Cloud SQL tendrá costos y recursos declarados antes
de medir. Este informe no concede conformidad a requisitos de rendimiento.
