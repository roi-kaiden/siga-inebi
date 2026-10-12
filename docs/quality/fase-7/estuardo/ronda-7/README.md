# Ronda 7: consulta de resultado por teclado

Fecha: 12 de octubre de 2026. Corrida `RUN-EST-20261012-07`.
Código probado: `1649c98f96d3c52db5280feaaf5982f2cb4158ca`, rama
`test/estuardo-evaluacion-teclado`, basada en la corrección de INC-008 del
PR #555. Ejecución asistida de Estuardo; revisión independiente de Roí pendiente.

## Alcance y resultado

Se añadió y ejecutó una prueba de componente para la ventana «Consultar
resultado». En jsdom, desde el foco inicial del diálogo se pudo llegar con Tab
al selector «Estudiante», elegir una opción con flechas y Enter, pasar con Tab al selector
«Subarea», elegirla del mismo modo, pasar con Tab a «Consultar» y activar el
formulario con Enter. El botón estaba deshabilitado antes de elegir ambas
opciones. El servicio simulado recibió los identificadores seleccionados y la
ventana mostró `60`, la `final_grade` recibida para el promedio 59.5.

Resultado: **Aprobado para este recorrido de teclado a nivel de componente**.
`npx vitest run src/test/FinalGradeWindow.test.jsx`: 5/5 pruebas aprobadas;
`npx eslint src/test/FinalGradeWindow.test.jsx`: aprobado. La evidencia
reproducible es la prueba versionada en
`frontend/src/test/FinalGradeWindow.test.jsx` y el SHA anterior.

## Límites y siguientes comprobaciones

jsdom no representa por completo el foco, el lector de pantalla ni la
interacción del navegador y dispositivo reales. Sigue pendiente observar el
recorrido por teclado en navegador sobre el candidato final, comprobar foco al
cerrar la ventana y mensajes de error, y ejecutar con participantes
institucionales las tareas de usabilidad/UAT. Android real, Firefox y Safari
siguen sujetos a disponibilidad. Este resultado no cierra accesibilidad ni
aceptación de usuarios.
