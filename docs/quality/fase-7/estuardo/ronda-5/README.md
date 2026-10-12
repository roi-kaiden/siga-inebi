# Quinta ronda de Estuardo: escritura de nota en ciclo cerrado

Corrida `RUN-EST-20261012-05`, 12 de octubre de 2026. Código probado:
`93e4c8004e0967551ce92427466421b14f9b1a9b` (rama del PR #556, aún no integrada en `develop`).
Edge 155.0.4283.45 headless, frontend Vite, Django 5.2.17 y PostgreSQL 16
en proyecto Docker aislado. Cuenta docente y estudiante sintéticos; dos notas
registradas desde la interfaz antes del cierre: 59 y 60. El cierre de las dos
unidades y del ciclo se preparó con los servicios de dominio en el entorno QA.

## Resultado observado

1. El docente inició sesión y abrió la pantalla de notas de la unidad cerrada.
   La acción «Registrar nota» seguía visible, pero el selector «Estudiante»
   apareció deshabilitado con el mensaje «El actor no tiene un alcance vigente
   asignado». No fue posible enviar el formulario desde la interfaz.
2. Con la misma sesión, una petición POST autenticada y con token CSRF válido
   para cambiar la primera nota a 90 respondió **403**: «Permission denied.
   No teaching assignment over this section and subject». Se generó un evento
   `evaluation.grade_write_denied`. Un intento previo sin token CSRF también
   produjo 403, pero se descartó de la conclusión porque no alcanzó la regla
   de autorización.
3. Una llamada directa al servicio de dominio con esa unidad y docente rechazó
   la escritura porque la ventana estaba cerrada y no había autorización
   excepcional. Se verificó que el ciclo seguía cerrado, que las dos notas
   seguían en 59 y 60 y que los identificadores originales no cambiaron.

**Interpretación:** las defensas observadas impidieron modificar notas de un
ciclo cerrado. La ruta de navegador quedó detenida por la pérdida del alcance
docente, y la API rechazó por la misma razón; no se observó un rechazo HTTP
atribuible exclusivamente a la regla de ciclo cerrado. El servicio sí rechazó
la escritura por unidad cerrada. Por ello, el caso del plan CP-INT-EVA-001 se
mantiene **parcial**; no se marca como completado ni se declara UAT aprobada.

Pendiente para este caso: ejecutar un recorrido de usuario autorizado que llegue
al control específico de ciclo cerrado, o documentar una decisión de alcance
que establezca que el bloqueo por permisos es el comportamiento esperado.
También falta revisión cruzada de Roí. El mensaje del formulario podría
explicar el estado del ciclo con más claridad; se registra como observación de
usabilidad, sin afirmar que sea un defecto funcional confirmado.

La evidencia original local ignorada por Git y sus hashes están en
[evidencias.md](evidencias.md). No se publicó la sesión ni su contraseña.
