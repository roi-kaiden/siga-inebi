# Primera ronda de Estuardo — evaluación

Fecha: 12 de octubre de 2026, America/Guatemala.
Código evaluado: `3bcca08860b07c7086ac11b914a7262e7a68d282`.
Responsable: Estuardo. Ejecución técnica asistida por Codex; revisión de Roí pendiente.
Diagnóstico local; no constituye candidato formal, aceptación institucional ni UAT.

## Archivos de trabajo

- [Resultado de la primera corrida](resultado-primera-corrida.md): **168 pruebas aprobadas**, cero fallos y cero omitidas (71 unitarias, 65 API y 32 integración); revisión humana pendiente.
- [Catálogo inicial](catalogo-inicial.csv): 24 requisitos EVC/CAL/RES, criterios originales y referencias candidatas por función.
- [Inventario de pruebas](inventario-pruebas.csv): funciones encontradas en las tres suites de evaluación; la cantidad ejecutada se obtiene de JUnit, incluyendo parametrizaciones.
- [Evidencia revisada](evidencia-revisada.md): comando, versiones y hashes de los logs/JUnit locales. Los artefactos crudos no se publican en Git; su entrega a revisores está pendiente.
- El catálogo general y sus resultados históricos se conservan. Este catálogo complementario no aprueba requisitos ni modifica el alcance institucional.

## Primeros cinco casos

Todos usan datos sintéticos de las factories existentes y una base PostgreSQL de pruebas. Ejecutor técnico: Codex, para Estuardo; revisor propuesto: Roí. El estado inicial se reconstruye por los fixtures de pytest y sus transacciones; no se modifica la base de desarrollo. Las referencias siguientes son relativas a `backend/`.

| Caso | Requisito / fuente | Precondición y pasos | Resultado esperado | Prueba reutilizada |
| --- | --- | --- | --- | --- |
| CP-API-CAL-EST-001 | RF-CAL-001; OpenSpec calificaciones, registro de nota | Matrícula y unidad del mismo ciclo, ventana abierta, permiso y alcance; enviar nota 85 y comprobar respuesta y persistencia. | HTTP 201, valor 85 y nota vinculada a matrícula/subárea/unidad. | `tests/api/test_evaluation_api.py::TestGradeAPI::test_register_grade_success` |
| CP-API-CAL-EST-002 | RF-CAL-002; OpenSpec calificaciones, escala | Con sesión y ventana abierta, enviar valores negativos, superiores a 100 y texto; con permiso y alcance, probar límites 0/100. | Rechazo de valores inválidos y aceptación de ambos límites. | `tests/api/test_evaluation_api.py::TestGradeScaleAPI` (funciones individuales en inventario) |
| CP-API-CAL-EST-003 | RF-CAL-006; OpenSpec calificaciones, alcance | Probar registro con asignación coincidente, subárea ajena y sin permiso; consultar listado de notas. | Permitir ámbito propio; denegar escritura ajena/sin permiso, acotar consulta y auditar rechazo según prueba. | `tests/api/test_evaluation_api.py::TestGradeAuthorizationAPI` |
| CP-API-CAL-EST-004 | RF-CAL-005, RF-EVC-002/004/007; OpenSpec corrección y ventanas | Corregir con ventana abierta; repetir cerrada sin brecha; verificar cierre y brecha vigente en integración. | Corrección auditada cuando corresponde; rechazo sin brecha; excepción limitada y vigente. | `tests/api/test_evaluation_api.py::TestGradeCorrectionAPI`; `tests/integration/test_evaluation.py::TestCloseEvaluationUnitIntegration::test_close_unit_then_correction_requires_active_grant` |
| CP-API-RES-EST-001 | RF-RES-001/002/003, RF-CAL-003; OpenSpec resultados | Calcular promedio, probar pendientes, fracción 59.5 y umbral de aprobación 60. | Excluir pendientes del promedio en curso; redondear solo el resultado final, 59.5 → 60; condición coherente. | `tests/api/test_evaluation_api.py::TestCurrentAverageAPI`, `TestFinalSubjectGradeAPI`, `TestFinalGradeRoundingAPI`, `TestSubjectApprovalAPI` |

Las clases agrupan varios casos automatizados; el inventario enumera sus nodos precisos. Revisar las aserciones por criterio antes de afirmar cobertura completa. La corrida ejecuta las tres suites completas de evaluación, no solo estos cinco grupos.

## Brechas y decisiones para Pablo / Roí

1. El catálogo canónico indica `Not implemented` en requisitos con pruebas candidatas. Reconciliar documentación, implementación y evidencia; no cambiar automáticamente el estado por una suite aprobada.
2. RF-EVC-001 tiene criterio estructurado vacío. OpenSpec ofrece escenarios de unidades y solapamiento; confirmar el criterio de aceptación antes de cierre.
3. RF-CAL-007: el criterio estructurado exige publicación/cierre de captura para visibilidad; OpenSpec describe asociación y alcance. Las pruebas de alcance no resuelven el momento de publicación. Requiere decisión explícita del responsable.
4. RF-RES-006/007/008/009 no tienen referencia asignada en estas tres suites. Revisar promoción, congelamiento, boleta y trazabilidad en otros módulos y pruebas manuales antes de concluir ausencia de implementación.
5. El plan menciona pesos; OpenSpec describe nota consolidada y promedio de unidades. No introducir ponderaciones ni criterios nuevos sin decisión.
6. Esta ronda no evalúa pantalla, cámara, login real, usabilidad, UAT ni cobertura global. `--no-cov` es intencional para un subconjunto.
7. Existe INC-004 en el registro general, asignada a Estuardo: advertencias React por imágenes con `src` vacío. Sigue fuera de esta corrida backend; verificarla en una sesión frontend posterior, sin asumir que continúa reproducible ni que está resuelta.

## Siguiente sesión manual

Con Josué: preparar docente asignado, estudiante sintético matriculado y unidad abierta; recorrer captura → consulta del resultado → reporte disponible. Con Roí: verificar contenido y permisos del documento si existe en el alcance. Registrar pasos, esperado/observado, SHA, evidencias e incidencias; no dar por disponible la boleta solo porque pasan las pruebas de cálculo.

Después, Estuardo prepara agenda con Pablo para usuarios institucionales. Las sesiones de usabilidad y UAT permanecen no ejecutadas. Cada resultado se entrega a Pablo y las evidencias técnicas a Daniel; Roí verifica la revisión cruzada.

Nota de publicación: la rama de este PR parte de `develop` en `3a4a8d2`; esta corrida sigue referida exclusivamente al SHA evaluado `3bcca08`. No certifica los cambios posteriores. El catálogo conserva la instantánea inicial y sus pendientes, no el estado actualizado de toda la entrega.
