# Ronda 8: foco y consulta por teclado en Edge real

Corrida `RUN-EST-20261012-08`, 12 de octubre de 2026. Código probado:
`ece3dcc9016dc95e59e3a709c43d90da5ca52835`, rama del PR #559, aún
sin integrar en `develop`. Edge 155.0.4283.45 headless, viewport 1440 × 900,
Vite local, Django 5.2.17 y PostgreSQL 16 en proyecto Docker aislado.
Cuenta docente, matrícula, ciclo y subáreas sintéticos. Estuardo ejecutó la
prueba con asistencia; revisión independiente de Roí pendiente.

## Procedimiento y resultados

Tras iniciar sesión mediante el formulario real, se abrió «Consultar resultado».
El foco inicial quedó dentro del diálogo. Siete pulsaciones sucesivas de Tab
recorrieron cierre, estudiante, subárea y cierre de pie, sin salir del diálogo;
el recorrido volvió a los controles iniciales. Con Shift+Tab, flechas, End y
Enter se seleccionaron matrícula y subárea; se esperó el cierre visible de
cada menú antes de continuar. Tab llegó a «Consultar» y Enter envió la petición
real a `final-grade/`.

La API devolvió **HTTP 200** y `final_grade: null` porque no se registraron
notas en este conjunto de datos. La pantalla mostró **«Sin calificar»**.
Al pulsar Escape, el diálogo se cerró y el foco volvió al botón «Consultar
resultado» que lo abrió. Resultado: **Aprobado** para este recorrido técnico de
teclado y foco en Edge con API real.

En intentos exploratorios se enviaron teclas antes de que terminara la
transición del menú de selección: quedó un menú abierto y el primer Escape lo
cerró, antes de cerrar el diálogo. La corrida concluyente esperó explícitamente
que el menú desapareciera y el primer Escape cerró el diálogo. No se clasificó
ese intento acelerado como defecto del producto.

## Evidencia y límites

El JSON original está excluido de Git en
`docs/quality/fase-7/evidence/RUN-EST-20261012-08/focus-results.json` y tiene
SHA-256 `AAF5D3C25A428CB645AA9E97FFF4A4CF4BACAF7488BE91A15AED29704AAA0E7F`.
Registra foco, acciones, HTTP y texto visible; no incluye credenciales ni
cookies. El script de ejecución está en el entorno local ignorado
`tmp/qa-browser/round8-focus.cjs`; la secuencia anterior permite repetirlo
sin ese archivo.

No se probó lector de pantalla, contraste, error de API, Android real,
Firefox ni Safari. Tampoco hubo participante institucional: esta corrida no
constituye sesión de usabilidad ni UAT. Sigue pendiente observar el mismo
recorrido en el candidato final y recibir revisión cruzada de Roí.
