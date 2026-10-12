# Preparación de usabilidad y UAT — Estuardo

Estado: **preparado, no ejecutado**. Este paquete organiza las tareas de Estuardo
según `docs/planning/tests_plan.md` (§5.3 y §10.5). No contiene respuestas de
usuarios ni representa aceptación institucional. Los informes finales
`informe-usabilidad.md` e `informe-aceptacion-usuarios.md` se redactarán después
de las sesiones, con el SHA, las observaciones y la decisión reales.

La [comprobación técnica previa](preflight-tecnico.md) de disposición visual ya
se ejecutó con Edge y emulación móvil. No modifica el estado de las tareas de
usabilidad/UAT de [casos.csv](casos.csv).

## Disponibilidad y decisiones previas

| Dependencia | Estado al preparar este paquete | Responsable |
| --- | --- | --- |
| Participantes institucionales y autoridad de aceptación | Sin confirmar | Pablo y Estuardo |
| Computadoras y Android | Disponibles según Estuardo; faltan modelo, versión de sistema y navegador | Estuardo y Daniel |
| Firefox, Safari y Android Chrome de versión anterior | Disponibilidad por confirmar; registrar el alcance real o el bloqueo | Estuardo y Daniel |
| Candidato de entrega y SHA | Pendiente de integración y congelación | Daniel y Pablo |
| Rol, permisos y alcance de cada cuenta sintética | Verificar contra el candidato antes de cada tarea | Responsable del dominio y Estuardo |
| Boleta en pantalla | Pendiente: no hay acción frontend para el reporte histórico; QA4-PDF-01 registra PDF que requiere reparación | Roí, con regresión de Estuardo |
| Criterios de duración de tareas | Acordar si se necesitan; el plan no fija metas institucionales | Pablo y usuarios |

No iniciar UAT de un flujo bloqueado ni sustituirlo por una llamada directa a
la API. Si una función sigue ausente en el candidato, registrar la tarea como
**Bloqueada**, el motivo y quién decide su alcance. Los ocho integrantes
técnicos pueden preparar datos y observar, pero no sustituyen a participantes
institucionales.

## Secuencia de preparación

1. Pablo confirma perfiles y agenda: secretaría/administración, docente,
   operador, dirección y encargado solo cuando su flujo esté incluido. Si una
   persona cubre varios perfiles, anotarlo como limitación.
2. Daniel fija el SHA y el entorno QA. Se crean solo cuentas y datos sintéticos:
   matrícula, dos unidades, una subárea asignada y otra ajena, y boleta de un
   ciclo cerrado cuando el flujo exista. Verificar permisos antes de la sesión.
3. Estuardo y el dueño del dominio prueban los casos de
   [casos.csv](casos.csv) una vez en QA para comprobar que las instrucciones son
   ejecutables. Esta preparación técnica no cuenta como UAT.
4. Durante usabilidad, dar una tarea concreta y observar el primer intento sin
   guiar. Registrar ayuda solo después de ese intento, con tiempo y errores.
5. Durante UAT, el participante ejecuta el escenario y registra su conformidad
   u observaciones en la [plantilla](plantilla-registro.md). Estuardo facilita,
   sin hacer las operaciones por él. Pablo consolida la decisión institucional.
6. Repetir tareas afectadas por correcciones sobre el nuevo SHA; conservar el
   resultado anterior, enlace a incidencia y nueva evidencia.

## Qué registrar en cada sesión

- Código de participante, perfil operativo y limitaciones de representación,
  sin nombre, documento ni contacto en el repositorio.
- Fecha/hora, SHA, entorno, navegador y versión, dispositivo y tamaño de
  pantalla. Para Android, indicar si se utilizó un equipo real o emulación.
- Por tarea: éxito sin ayuda, éxito con ayuda o fallo; tiempo, número de errores,
  paso confuso, mensaje no entendido, valoración 1–5 y comentario.
- Teclado/foco, etiquetas, mensajes en español, contraste y zoom al 200 % en
  las pantallas probadas. Estas observaciones no certifican un estándar completo
  de accesibilidad.
- Evidencia sanitizada, incidencia, resultado por escenario y confirmación del
  participante. Una captura de pantalla no equivale a esa confirmación.

No publicar contraseñas, cookies, datos personales ni grabaciones sin revisar.
Los artefactos grandes pueden conservarse fuera de Git con índice y checksum.

## Revisión y entregables

Emilio revisa el informe de usabilidad; Pablo coordina UAT y la autoridad de
aceptación. Roí revisa los resultados de evaluación y Estuardo revisa sus
pruebas de documentos/API. El [guion de video](guion-video-evaluacion.md) queda
listo para grabar cuando la pantalla y el candidato sean estables. Registrar la
revisión cruzada con nombre, fecha y observaciones antes de considerar cerrado
el trabajo de Estuardo.
