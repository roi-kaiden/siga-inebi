# Ronda 9: compatibilidad de consulta de resultado

Corrida `RUN-EST-20261012-09`, 12 de octubre de 2026, sobre
`b668903e505b67a73909bcb6316ba62c7dcd6b69`, rama de la ronda 8 aún
no integrada en `develop`. Firefox 157.0 y Playwright WebKit 27.2 en Windows,
ambos headless y a 1440 × 900. Frontend Vite, Django 5.2.17 y PostgreSQL 16
aislado; cuenta, matrícula, ciclo y subáreas sintéticos. Ejecución asistida de
Estuardo; revisión de Roí pendiente.

## Resultado

| Navegador o motor | Consulta por teclado y API | Foco y cierre | Estado |
| --- | --- | --- | --- |
| Firefox 157.0 | Se eligieron estudiante y subárea con teclado; Enter envió `final-grade/`, HTTP 200, `final_grade: null`, «Sin calificar» visible. | Foco inicial y cinco Tab dentro del diálogo; Escape lo cerró y devolvió foco al botón de apertura. | Aprobado para este recorrido técnico |
| Playwright WebKit 27.2 | Mismo recorrido y resultado. | Mismo comportamiento de foco y cierre. | Aprobado para este recorrido técnico del motor |

El conjunto no contenía notas, de modo que esta ronda comprueba la rama «Sin
calificar», no el redondeo de INC-008. La ronda 4 ya comprobó `59.5 → 60` con
Edge, API real y datos sintéticos de QA.

En ambos motores, después de cargar el resultado, el foco activo quedó en el
contenedor de presentación del modal (fuera del elemento con `role=dialog`).
El siguiente Tab volvió a un botón dentro del diálogo y Escape cerró la
ventana. Se registra como **observación de foco para revisión**; no se probó
lector de pantalla, por lo que no se infiere el anuncio o silencio del
resultado. La primera exploración en Firefox envió Escape antes de terminar la
transición del menú de selección y cerró ese menú, no el diálogo. Al esperar
su cierre visible, la repetición cerró el diálogo con un Escape.

## Evidencia y límites

El JSON original sanitizado está fuera de Git en
`docs/quality/fase-7/evidence/RUN-EST-20261012-09/compat-results.json`;
SHA-256 `8265F3156DE7D11B13089789673BBBEC7F7E070446777CAD6AB447F2D8768366`.
Contiene acciones, versiones, foco, HTTP y texto visible, sin credenciales ni
cookies. El script quedó local e ignorado en
`tmp/qa-browser/round9-compat.cjs`; el procedimiento anterior permite
repetir la prueba.

Playwright WebKit en Windows **no equivale a Safari en macOS o iOS**. Siguen
pendientes Safari real, Chrome/Edge móvil en Android real y su versión
anterior aplicable, y sesiones con usuarios institucionales. No se declara
cumplimiento completo de compatibilidad, accesibilidad o UAT.
