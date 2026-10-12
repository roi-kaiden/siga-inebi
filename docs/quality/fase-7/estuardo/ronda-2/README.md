# Segunda ronda de Estuardo — flujo en navegador

**Resultado: 6 casos aprobados, 1 fallido y 1 bloqueado sin ejecutar.**
La consulta de resultado final presenta un valor distinto del usado para
aprobar al estudiante. Se registró **INC-008**, abierta, con severidad S2/P1
propuesta para triage de Pablo. Esta ronda no aprueba el flujo completo.

## Entorno y alcance

- Fecha: 12 de octubre de 2026, America/Guatemala; timestamps técnicos en UTC.
- SHA: `3a4a8d2d488ea13e69471cc9637a36c81d72f010`, sin cambios de aplicación.
- Rama: `test/estuardo-evaluacion-ronda-2`, creada desde `origin/develop`.
- Operador: Codex para Estuardo; revisión de Roí/Josué pendiente.
- Navegador real: Microsoft Edge 155.0.4283.45 en modo headless, manejado por
  Playwright local temporal; viewport 1440 × 1000. No mocks de API.
- Frontend Vite 7.3.6 en `http://127.0.0.1:15173`, proxy al backend Django
  5.2.17/Python 3.11.17 en `http://127.0.0.1:18002` y PostgreSQL 16.15 en Docker.
- Proyecto aislado: `siga_inebi_estuardo_qa2`. HTTP de desarrollo, no medición de
  producción, TLS, rendimiento, dispositivos móviles ni prueba cloud.
- Login real con usuario activo vinculado a persona, sin superusuario.
  Permisos: `auth_login`, `auth_logout`, `grade_write`, `student_view_basic`;
  asignación vigente a una sección/subárea. Sin alcance de administrador.
- Datos sintéticos de factories: un estudiante matriculado, un docente, dos
  unidades con captura inicialmente abierta, Matematica QA propia y Subarea
  ajena QA sin asignación. Preparación mediante ORM solo en esta base QA.
- Ejecución técnica automatizada en navegador: **no es una sesión manual con
  Josué/Roí ni aceptación UAT institucional**. La plantilla manual queda lista
  para que ellos reproduzcan los mismos pasos.

## Casos y resultados

[Casos con pasos, esperado, observado y versión](casos-resultados.csv).

| Caso | Resultado |
| --- | --- |
| 201 — Login real del docente | Aprobado |
| 202 — Nota 101 | Aprobado: HTTP 400 |
| 203 — Nota 59 en unidad 1 | Aprobado: HTTP 201, visible y persistida |
| 204 — Nota en subárea ajena | Aprobado: HTTP 403, sin escritura ajena y con auditoría |
| 205 — Nota 60 en unidad 2 | Aprobado: HTTP 201, persisten ambas notas |
| 206 — Consulta final | **Fallido: muestra 59.5 cuando el final es 60** |
| 207 — Corrección con ventana vencida | Aprobado: HTTP 400, conserva 59 y 60 |
| 208 — Boleta | Bloqueado sin ejecutar: preparar ciclo cerrado/rol emisor y recorrido con Roí |

Las verificaciones ORM posteriores confirmaron exactamente dos notas propias
con valores 59 y 60, ninguna nota en subárea ajena y un rechazo auditado.
Para el caso 207 se cambió únicamente el fixture de ventana a fecha vencida;
no se cerró el ciclo ni se pretende haber probado el congelamiento de resultados.

## INC-008: reproducción del fallo

1. Iniciar sesión con docente asignado a la matrícula y subárea de prueba.
2. Registrar 59 en la primera unidad y 60 en la segunda, ambas con captura abierta.
3. En Evaluación, abrir **Consultar resultado**, seleccionar estudiante/subárea y consultar.
4. Comparar el número visible con la respuesta JSON de `final-grade/`.

Respuesta observada, sin identificadores personales:

```json
{"average":59.5,"graded_units":2,"pending_units":0,"total_units":2,"final_grade":60,"approved":true,"recovery_grade":null,"condition":"approved"}
```

La pantalla rotula el valor como nota final, pero muestra **59.5**.
`frontend/src/evaluation/FinalGradeWindow.jsx` renderiza `data.average`.
El [OpenSpec de resultados](../../../../requirements/openspec/evaluacion-resultados.md)
exige redondear una sola vez y usar el mismo valor visible y de aprobación
(RF-RES-002, relacionado con RF-RES-003). Esperado: **60**.

Corrección y regresión pendientes: presentar el resultado final contractual,
conservar la distinción sin calificar/cero y verificar con un test de componente
donde `average=59.5` y `final_grade=60`, seguido del mismo flujo de navegador.
No se modificaron componentes ni reglas de negocio durante esta ronda.

## Evidencia y límites

[Manifiesto con hashes](evidencias.md). Capturas, respuestas sanitizadas,
comprobaciones ORM y scripts auxiliares permanecen localmente en
`docs/quality/fase-7/evidence/RUN-EST-20261012-02/`, excluidos de Git.
No se publican contraseñas, cookies ni el archivo temporal de sesión.
La entrega de artefactos a revisores sigue pendiente; los hashes no sustituyen
su revisión. Capturas principales: `resultado-visible.png`, `subarea-ajena.png`
y `ventana-cerrada.png`.

Preparación y reintentos: se corrigieron nombres de campos/BOM del script de
datos y selectores del navegador; solo se reinició la base QA2 sintética durante
la preparación. El primer intento de enviar 59.5 recibió HTTP 400 porque captura
requiere entero; se usaron 59 y 60 para obtener el promedio 59.5. No se clasifican
estos errores auxiliares como defectos del sistema. Se conservan dos intentos
previos; los resultados consolidados corresponden al recorrido completado y
la verificación posterior de ventana. Los registros repetidos actualizaron la
misma nota, sin generar notas adicionales según la comprobación ORM.

La pantalla de resultado inspeccionada no ofrece emisión de boleta. Esto no
demuestra ausencia en todo el sistema: quedan por verificar con Roí el recorrido,
permisos de emisión y ciclo cerrado, además de corregir la discrepancia visible.

## Pendientes de entrega

- Estuardo: corrección de INC-008 con regresión; Roí revisa; Pablo confirma triage.
- Josué/Roí: reproducir flujo, preparar ciclo cerrado y validar boleta disponible.
- Usabilidad con personas, accesibilidad completa, UAT y videos: no ejecutados.
- PR anterior #551: `pr-validation` aprobó; `frontend-build` falló porque la ruta
  de asistencia pesa 20.025 bytes gzip frente al límite 20.000. Evidencia de CI:
  https://github.com/siga-inebi/siga-inebi/actions/runs/38284516610/job/114929565012.
  Ese check sigue pendiente de resolución, separado de INC-008.

El backend local y la base QA2 se detienen al cerrar la ronda. Los datos efímeros
de PostgreSQL no se consideran una copia persistente para una sesión posterior;
recrear el fixture y nuevas evidencias al repetir. No se alteró el entorno cloud.
