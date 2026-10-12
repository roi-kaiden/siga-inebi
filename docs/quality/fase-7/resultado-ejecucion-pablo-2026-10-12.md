# Resultado de ejecución integrada — Pablo

## Identificación

| Campo | Resultado |
| --- | --- |
| Corrida | `RUN-PAB-20261012-04` |
| Ejecutada | 12 de octubre de 2026, 17:12:57–17:15:20, America/Guatemala |
| Coordinación | Pablo |
| Entorno | Docker Compose aislado; PostgreSQL 16; Python 3.11; Node 22; datos sintéticos |
| SHA base | `3a4a8d2d488ea13e69471cc9637a36c81d72f010` |
| Estado del árbol | Modificado, con digest `d19e4f86fffe4791885eb778ebc6e27fa76ce4d0528c6478d4e7bd16d332e0b6` |
| Estabilidad | El SHA y el digest coincidieron al inicio y al final (`source_stable: true`). |
| Resultado global | **Aprobado: 28 de 28 controles, código de salida 0.** |

La identificación incluye SHA y digest porque la corrección aún no corresponde a
un commit de entrega. La corrida usa una base PostgreSQL efímera y no utiliza
datos institucionales ni credenciales reales.

## Resultados comprobados

| Área | Resultado |
| --- | --- |
| Migraciones y chequeos Django | Aplicación de migraciones, `check` y detección de migraciones pendientes aprobados. |
| Backend | 1,596 pruebas aprobadas; 0 fallos; cobertura de líneas 94.45 %. Se emitieron 10 advertencias no bloqueantes. |
| Frontend | 32 archivos de prueba y 285 pruebas aprobadas; 73.32 % statements, 68.39 % branches, 68.03 % functions y 73.98 % lines. |
| Calidad estática | Ruff, formato backend, lint y formato frontend aprobados. |
| Seguridad de dependencias | Bandit aprobado; `pip-audit` aprobado con las excepciones ya versionadas; `npm audit --audit-level=high` reportó 0 vulnerabilidades. |
| Build y rendimiento de entrega | Build aprobado. Carga inicial: 221,134 de 230,000 bytes gzip. Ruta lazy mayor: 13,716 de 20,000 bytes gzip (68.58 %). Página fría mayor: 234,850 de 250,000 bytes gzip. |

## Corrección y regresión de presupuesto

La ejecución anterior aprobaba el límite de ruta lazy con solo 30 bytes de
margen. Se movieron bajo demanda las ventanas operativas de Asistencia y
Matrículas, y se separaron en un chunk explícito los módulos compartidos de
Asistencia. La carga ya no arrastra código de la página al abrir esas ventanas.

La ruta mayor pasó de 19,970 a 13,716 bytes gzip: una reducción de 6,254 bytes
(31.27 % del límite). La prueba de cierre declarado por cobertura, las pruebas
de Matrículas y la suite completa del frontend verifican que los flujos de las
ventanas conservan su comportamiento.

## Evidencia

Los artefactos sin datos sensibles se conservan localmente en
`tmp/phase7/RUN-PAB-20261012-04/`. El archivo `summary.json` tiene SHA-256
`73c42d2cd43e76d9ff7849d824235ba173f9d221a2511fa857208862dc55fe1d`.
La exportación y conservación externa siguen el procedimiento de evidencias del
plan de pruebas.

## Límites de la conclusión

La corrida automatizada no sustituye UAT, aceptación institucional, pruebas con
teléfono/cámara real ni la revisión independiente requerida por el plan. Por
ello, este resultado acredita conformidad técnica automatizada, no autorización
de implementación.
