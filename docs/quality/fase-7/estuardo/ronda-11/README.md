# Ronda 11: cierre de ciclo y regresión de INC-009

Ejecución asistida de Estuardo, 12 de octubre de 2026. Se utilizaron datos
sintéticos y PostgreSQL 16 aislado para la prueba de API. La revisión
independiente de Roí y Emilio sigue pendiente.

## Escritura en ciclo cerrado (CP-INT-EVA-001)

`test_closed_cycle_denies_grade_write_and_preserves_frozen_result` registra
una nota de 70 con asignación docente válida, cierra la unidad y el ciclo
mediante sus servicios y luego intenta cambiar la nota a 90 por la API.
Comprueba HTTP 403 y que tanto la nota de unidad como el resultado congelado
conservan 70. La prueba existente
`test_correction_with_closed_window_and_no_grant_is_rejected_api` comprueba
por separado el rechazo HTTP 400 cuando solo se cerró la ventana de captura.

El ciclo cerrado revoca el permiso de escritura en la política central antes
de evaluar la ventana; por eso el HTTP 403 no debe interpretarse como un error
de ventana. La observación de la ronda 5 queda cubierta técnicamente por
ambas pruebas, cada una en la capa que le corresponde. Sigue pendiente la
validación con usuarios institucionales.

## Recuperación de red (INC-009)

La prueba de `apiClient` simula los errores `Failed to fetch` de Edge y
`NetworkError when attempting to fetch resource.` de Firefox. Antes del
cambio fallaron ambos casos porque la interfaz mostraba esos textos en inglés.
Ahora comprueba un aviso en español que indica verificar la conexión y
reintentar, seguido de una consulta exitosa sin recargar. La corrección solo
traduce los rechazos de `fetch` de tipo `TypeError`; las respuestas HTTP del
servidor y las cancelaciones mantienen su tratamiento existente.

Se repitió además el flujo completo en Edge 155 y Firefox 157 headless:
login, selección de estudiante y subárea, corte de red mediante Playwright,
consulta, reconexión y reintento sin recargar. Ambos mostraron el aviso en
español; el diálogo permaneció abierto, el reintento devolvió HTTP 200 y
«Sin calificar», y desapareció la alerta. La evidencia JSON sintética queda
excluida de Git en `tmp/qa11/network-results.json`, SHA-256
`AB7E59A106A8B29282A8BBC7C818200DFA2061C229BDAC22EB4CB9B7D19F37CD`.
El primer intento comenzó antes de que Django estuviera listo y falló en el
login; se repitió con el backend activo y solo esta segunda ejecución cuenta
como regresión válida.

Faltan el triage de Pablo, la revisión de Emilio y sesiones con usuarios
institucionales antes de cerrar INC-009 o considerar aceptada la usabilidad.
