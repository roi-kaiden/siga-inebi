# INC-008: nota final en la consulta de resultados

Corrección local del 12 de octubre de 2026, sobre la base
`3a4a8d2d488ea13e69471cc9637a36c81d72f010`.
Antecedente: ronda 2 de Estuardo, PR #553.

La consulta mostraba `average` (59.5) aunque la API devolvía
`final_grade: 60`. Ahora presenta `final_grade`, el mismo valor que el
backend compara con el umbral de aprobación, conforme a RF-RES-002.
No cambia el contrato API ni introduce cálculos de dominio en React.
La descripción de la ventana aclara que el promedio se presenta redondeado.

## Regresión

`frontend/src/test/FinalGradeWindow.test.jsx` consulta mediante los selectores
y el botón reales del componente, con servicio y catálogos simulados:

| Promedio API | Nota final API | Texto esperado |
| --- | --- | --- |
| 59.5 | 60 | 60 |
| 59.4 | 59 | 59 |
| 0 | 0 | 0 |
| null | null | Sin calificar |

El caso 59.5 reprodujo el fallo antes del cambio (esperado 60, recibido 59.5).
Después de la corrección, las cuatro pruebas aprobaron.
La comparación del texto es exacta para rechazar también 59.4 cuando se espera 59.

Validación desde `frontend/`:

```text
npx vitest run src/test/FinalGradeWindow.test.jsx
npx eslint src/test/FinalGradeWindow.test.jsx src/evaluation/FinalGradeWindow.jsx
```

Ambos controles aprobaron. Vite compiló la aplicación; el control posterior
de presupuesto falló: Asistencia ocupa 20,024 bytes gzip frente al límite
de 20,000. La base conserva el problema tratado en los PR #551 y #553;
no se cambió el límite ni se modificó Asistencia en esta corrección.

Estado: corregida localmente y verificada a nivel de componente. Pendientes
la regresión con API real en navegador, revisión independiente de Roí e
integración. No se declara cierre definitivo de la incidencia ni UAT aprobada.
