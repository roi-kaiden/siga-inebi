# Informe de seguridad — línea base D1

## Alcance y limitaciones

Pablo ejecutó la revisión inicial del frontend sobre el SHA
`0c8f0d396231f46809b95cc088d5f2c557cb919f`. Santiago repitió los controles
disponibles el 11 de octubre de 2026 sobre el SHA
`3bcca08860b07c7086ac11b914a7262e7a68d282`, usando Docker, Python 3.11 y
PostgreSQL 16. El 12 de octubre Santiago repitió la validación sobre
`450d0a805c34e779f3d2cd024cff8c2b985e133a`: 158 pruebas backend y 33 pruebas
frontend dirigidas aprobaron; Bandit y la auditoría backend también aprobaron.

Esta es una línea base local, no la certificación de la versión: siguen
pendientes la revisión cruzada, la repetición sobre el SHA candidato final y la
verificación de cookies/TLS en el entorno HTTPS de entrega.

## Resultado de dependencias frontend

`npm audit --json` informó 8 vulnerabilidades en el lockfile: 2 críticas,
4 altas y 2 moderadas.

| Componente | Severidad reportada | Hallazgo | Acción |
| --- | --- | --- | --- |
| `vitest` / `tinypool` | Crítica | Gadgets de contaminación de prototipo/RCE en opciones de worker de pruebas. | INC-003: Santiago y Daniel deben evaluar actualización mayor a Vitest 5.0.3 y ejecutar regresión completa. |
| `brace-expansion` | Alta | Denegación de servicio por expansión/recursión no acotada. | Trazar cadena transitiva y actualizar lockfile con revisión. |
| `js-yaml` | Alta | Uso excesivo de CPU mediante fuentes de combinación vacías. | Trazar cadena transitiva y actualizar lockfile con revisión. |
| `nanoid` | Alta | Generador personalizado puede iterar indefinidamente con tamaño cero. | Trazar cadena transitiva y actualizar lockfile con revisión. |
| `source-map-js` | Alta | Denegación de servicio por offsets de secciones de source maps. | Trazar cadena transitiva y actualizar lockfile con revisión. |
| `@vitest/coverage-v8` / `@vitest/mocker` | Moderada | Dependencias de la cadena de Vitest. | Resolver junto con actualización de Vitest. |

El audit no demuestra exposición en producción: los paquetes señalados pertenecen
principalmente a herramientas de desarrollo/prueba. Aun así, hay correcciones
disponibles y la política del repositorio exige atender hallazgos explotables
con fix disponible antes de PR. No se aplicó `npm audit fix` automático porque
ofrece actualización mayor y requiere revisión, lockfile controlado y regresión.

## Controles ejecutados

| Control | Resultado | Evidencia |
| --- | --- | --- |
| ESLint frontend | Aprobado | EJ-D1-003 |
| Pruebas frontend | 283 aprobadas; dos advertencias de `src=""` | EJ-D1-003, INC-004 |
| Build y presupuesto estático | Aprobado | EJ-D1-003 |
| Identidad, autorización y alcance backend | 158 pruebas aprobadas en PostgreSQL 16 | EJ-D1-008 |
| Autenticación y sesiones frontend | 33 pruebas aprobadas | EJ-D1-009 |
| Bandit y `pip-audit` backend | Aprobado; una excepción versionada ignorada | EJ-D1-010 |
| `npm audit --audit-level=high` | Fallido: 8 vulnerabilidades, reproducido en SHA actual | EJ-D1-011, INC-003 |
| Configuración de cookies | Revisión estática: sesión `HttpOnly`, `SameSite=Lax` y `Secure` fuera de desarrollo | `backend/config/settings/base.py`; falta entorno de entrega |
| CSRF y TLS integrados | No ejecutado | Requiere entorno QA HTTPS y SHA candidato confirmado |

## Conclusión

INC-003 permanece abierta con prioridad P0. La línea base backend ya es
ejecutable y aprobó los controles dirigidos, pero la seguridad del candidato no
puede aceptarse hasta contar con triage de dependencias, corrección o excepción
explícita sustentada, revisión cruzada y repetición en el entorno final HTTPS.
