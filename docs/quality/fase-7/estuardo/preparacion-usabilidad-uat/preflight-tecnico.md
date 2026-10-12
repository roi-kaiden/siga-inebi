# Comprobación técnica previa de la pantalla de Evaluación

Corrida `RUN-EST-20261012-06`, 12 de octubre de 2026. Ejecutada sobre el
frontend/backend de `develop` en
`3a4a8d2d488ea13e69471cc9637a36c81d72f010`, con datos sintéticos y
PostgreSQL 16 en Docker aislado. Edge 155.0.4283.45 en modo headless; Vite local.
Esta comprobación técnica **no es usabilidad institucional ni UAT**.

| Escenario | Observación | Resultado de esta comprobación |
| --- | --- | --- |
| Escritorio, 1440 × 900 | Login sintético y apertura de Evaluación y «Consultar resultado»; ancho de documento 1440/1440 px y diálogo entre x=460 y x=980 | Sin desbordamiento horizontal medido; diálogo visible |
| Escritorio, zoom CSS 200 % | Ancho de documento 1440/1440 px y diálogo entre x=200 y x=1240 | Sin desbordamiento horizontal medido; diálogo visible |
| Ventana móvil emulada, 360 × 640 | `isMobile=true`, DPR=2; ancho de documento 360/360 px y diálogo de x=0 a x=360 | Sin desbordamiento horizontal medido; diálogo visible |

Se revisaron visualmente las capturas de la pantalla y del diálogo después de
terminar la animación de apertura. En las tres condiciones, título, selectores,
acción «Consultar» y botón de cierre quedaron visibles. No se registraron notas
en esta corrida, no se midió contraste ni se ejecutó una tarea con teclado o con
un participante.

**Límites:** `document.body.style.zoom = "200%"` aproxima la ampliación, pero
no equivale a comprobar manualmente el zoom del navegador. La ventana móvil
emula tamaño y DPR en Edge de escritorio: falta ejecutar en un Android real y
anotar modelo, RAM, navegador y versión. Tampoco se ejecutaron Firefox, Safari
ni Android Chrome de versión anterior. La pantalla de esta base no incorpora
todavía la corrección INC-008 del PR #555; esta corrida solo examina disposición
visual, no el resultado académico.

Las capturas y el JSON de medidas están excluidos de Git en
`docs/quality/fase-7/evidence/RUN-EST-20261012-06/`. Sus SHA-256 se publican
en [evidencias-preflight.md](evidencias-preflight.md). No se copió el archivo de
sesión ni la contraseña. Las tareas de usabilidad `US-COM-01` y `US-COM-02`
permanecen **No ejecutado** hasta que participen usuarios con los dispositivos
y el candidato final.
