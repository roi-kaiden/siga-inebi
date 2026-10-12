# Tercera ronda de evaluación de Estuardo

Corrida `RUN-EST-20261012-03`, ejecutada el 12 de octubre de 2026 sobre `3a4a8d2d488ea13e69471cc9637a36c81d72f010` (árbol limpio al ejecutar), desde `origin/develop`. Responsable: Estuardo; revisión cruzada de Roí pendiente.

**Resultado: 43 aprobadas, 0 fallidas; 413 deseleccionadas.** Pytest informó 6.41 segundos y cuatro advertencias `RemovedInDjango60Warning` por `CheckConstraint.check`. Distribución: 22 unitarias, 17 de API y 4 de integración. PostgreSQL 16, entorno Docker `backend-test`, configuración `config.settings.test`, datos sintéticos creados por factories; proyecto aislado `siga_inebi_estuardo_qa3`.

## Alcance y evidencia

| Requisito de referencia | Verificación ejecutada |
| --- | --- |
| RF-RES-006 | Promoción con todas las subáreas aprobadas; rechazo con subárea reprobada o sin nota; recuperación; consulta por API. |
| RF-RES-007 | Congelación al cerrar, conservación ante cambios de configuración, inmutabilidad, corrección autorizada que conserva el valor anterior y rechazo sin permiso. |
| RF-RES-008 | Boleta de ciclo cerrado: notas por unidad, nota final, condición y promoción; lectura del resultado congelado; rechazo de ciclo abierto, matrícula inexistente y usuario sin permiso de emisión. |
| RF-RES-009 | Traza de notas, recuperación y correcciones con valor anterior, nuevo valor, motivo y autor. |

También se verificaron restricciones del cierre: ciclo no activo, unidad abierta, plazo de recuperación vigente, autenticación y alcance. Los identificadores anteriores expresan cobertura de esta selección, no aceptación completa de requisitos.

El detalle de las 43 pruebas está en [resultados.csv](resultados.csv). El [manifiesto](evidencias.md) identifica los artefactos locales mediante SHA-256.

## Reproducción

Desde la raíz del repositorio, con Docker activo:

```powershell
docker compose -p siga_inebi_estuardo_qa3 -f compose.yml -f compose.test.yml run --build --rm backend-test pytest -q --no-cov tests/unit/test_academics_services.py tests/unit/test_enrolments_services.py tests/unit/test_documents_services.py tests/unit/test_audit_services.py tests/api/test_academics_api.py tests/api/test_enrolments_api.py tests/api/test_documents_api.py tests/integration/test_academics.py tests/integration/test_enrolments.py tests/integration/test_documents.py -k "Frozen or Promotion or HistoricalCycleReport or historical_cycle_report or closed_cycle_history_report or boleta or close_cycle or closing_a_cycle or trace_includes"
```

La ejecución original añadió un volumen hacia `/evidence` y `--junitxml=/evidence/results.xml`; conservó salida y código de proceso en el directorio local de evidencia. No se midió cobertura porcentual (`--no-cov`).

## Límites y pendientes

- La boleta antes bloqueada en la ronda 2 ahora tiene evidencia automatizada de API e integración. No se reemplaza ni se modifica aquella ejecución histórica.
- Falta descargar y abrir la boleta desde la interfaz para revisar presentación, legibilidad e impresión. Las aserciones de contenido y `Content-Type` no demuestran por sí solas la validez visual del PDF.
- INC-008, documentada en el [PR #553](https://github.com/siga-inebi/siga-inebi/pull/553), permanece pendiente: la pantalla muestra el promedio en lugar de la nota final redondeada. Esta ronda no cambia código funcional ni verifica su corrección.
- Faltan usabilidad con participantes, aceptación institucional, videos de evaluación y revisión de Roí. No se declara UAT aprobada ni se cierran requisitos.
- Esta rama parte de `develop`; los PR #551 y #553 aún no integrados no forman parte del SHA probado.
