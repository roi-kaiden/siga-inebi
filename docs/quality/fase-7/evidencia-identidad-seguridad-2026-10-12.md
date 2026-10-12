# Evidencia de identidad y seguridad — 12 de octubre de 2026

## Contexto común

- SHA evaluado: `450d0a805c34e779f3d2cd024cff8c2b985e133a`.
- Ejecutor: Santiago.
- Zona horaria: America/Guatemala.
- Entorno: Docker Compose local, PostgreSQL 16, datos sintéticos generados por
  factories; no se utilizaron secretos ni datos institucionales reales.
- Revisión cruzada: pendiente de Diana para funcionalidad y Daniel para
  dependencias.

## EV-EJ-D1-008-01 — Backend dirigido

Comando: `docker compose exec -T backend pytest -q --no-cov` seguido de los 16
archivos API, permisos, unidad e integración vinculados en
`catalogo-casos.csv`.

Resultado observado: 158 pruebas aprobadas en 159.26 segundos, código de salida
0. Pytest informó cuatro `RemovedInDjango60Warning`; no hubo fallo funcional.

## EV-EJ-D1-009-01 — Frontend dirigido

Comando: `docker compose exec -T frontend npm run test --
src/test/App.test.jsx src/test/ChangePasswordWindow.test.jsx
src/test/apiClient.test.js`.

Resultado observado: tres archivos y 33 pruebas aprobadas en 23.86 segundos,
código de salida 0. Se comprobaron login, logout, expiración, bloqueo, cambio de
contraseña y manejo de sesión del cliente HTTP.

## EV-EJ-D1-010-01 — Seguridad backend

Comandos: `bandit -q -r apps config` y `pip-audit -r requirements/dev.txt` con
la lista de excepciones versionada en el `Makefile`.

Resultado observado: Bandit aprobó sin hallazgos; `pip-audit` informó cero
vulnerabilidades conocidas y una excepción ignorada. Código de salida conjunto
0. La excepción debe permanecer sujeta a revisión de Daniel.

## EV-EJ-D1-011-01 — Dependencias frontend

Comando: `docker compose exec -T frontend npm audit --audit-level=high`.

Resultado observado: código de salida 1; ocho vulnerabilidades: dos críticas,
cuatro altas y dos moderadas. La corrección total propuesta instala Vitest
5.0.3 y constituye un cambio mayor. No se ejecutó `npm audit fix` ni se modificó
el lockfile. Resultado vinculado a INC-003.

## Evidencia complementaria de CI

El job `backend-tests` del PR #547 ejecutó 1572 pruebas: 1557 aprobaron y 15
fallaron en módulos académicos, auditoría y sugerencias de formulario. El
hallazgo quedó separado como INC-005 porque la suite dirigida de identidad
aprobó. URL registrada en `incidencias.csv`.

## Limitaciones

Esta evidencia pertenece a una línea base local. No reemplaza la repetición
sobre el SHA candidato final, la revisión cruzada ni las comprobaciones de TLS
y cookies en el entorno HTTPS de entrega.
