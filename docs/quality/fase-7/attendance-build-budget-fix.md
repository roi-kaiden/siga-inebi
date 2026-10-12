# Corrección del presupuesto de asistencia — PR #551 y #553

Los dos PR de documentación heredaron de `develop` una ruta de asistencia de
20.025 bytes gzip incrementales, superior al límite de 20.000 de RNF-COM-002.
Vite compilaba, pero el verificador de presupuesto hacía fallar `frontend-build`.

`AttendancePage` carga ahora `SectionClosureWindow` mediante `React.lazy` al
abrir el diálogo. Un indicador accesible muestra la espera. Las operaciones de
previsualización y cierre se pasan como callbacks desde la página para evitar
que el chunk del diálogo importe el de toda la ruta a través del servicio.
Solo cambia ese contrato interno de props; las operaciones HTTP, permisos,
confirmaciones y auditoría mantienen su contrato.

## Validación local, 12 de octubre de 2026

| Medición del manifiesto | Bytes gzip | Límite |
| --- | ---: | ---: |
| Recursos iniciales | 217.750 | 230.000 |
| Incremento asistencia | 19.256 | 20.000 |
| Incremento diálogo de cierre | 9.433 | 20.000 |
| Mayor incremento de ruta (matrícula) | 19.444 | 20.000 |
| Mayor página fría | 237.194 | 250.000 |

- `npm run build`: aprobado, sin modificar límites ni el verificador.
- `npm test -- src/test/AttendancePage.test.jsx scripts/check-build-budget.test.mjs`:
  13 pruebas aprobadas; incluye apertura/cierre/reapertura del diálogo sin
  operaciones y el flujo existente de confirmación de cobertura.
- `npm run lint` y Prettier en los tres archivos modificados: aprobados.
- Entorno local Windows, Node 24.19.0, Vite 7.3.6; CI usa su entorno Linux/Node 22.
  Los resultados definitivos de CI corresponden a cada PR.

Esta corrección resuelve el presupuesto de descarga; INC-008 (nota final visible)
permanece pendiente y las corridas históricas de evaluación conservan su SHA.
