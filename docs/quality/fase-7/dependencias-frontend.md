# INC-003: corrección de dependencias frontend

El lockfile actualizado reduce los hallazgos de `npm audit --json` de ocho
(dos críticos, cuatro altos y dos moderados) a cero. Se fijaron Vitest y su
proveedor de cobertura en **4.1.11**, con actualización selectiva de dependencias
transitivas. La auditoría de paquetes no sustituye las pruebas de seguridad del
sistema ni la regresión sobre el entorno QA.

## Decisiones y compatibilidad

| Componente                      | Antes          | Después         | Decisión                                       |
| ------------------------------- | -------------- | --------------- | ---------------------------------------------- |
| `vitest`, `@vitest/coverage-v8` | 3.2.7          | 4.1.11          | Mantener las dos versiones iguales y fijadas.  |
| `@vitest/mocker`                | 3.2.7          | 4.1.11          | Parche de lectura arbitraria de archivos.      |
| `tinypool`                      | Presente       | Ausente         | Vitest 4 elimina esta dependencia.             |
| `brace-expansion`               | 1.1.16 / 5.0.8 | 1.1.21 / 5.0.12 | Actualización transitiva dentro de cada línea. |
| `js-yaml`                       | 4.3.1          | 4.3.2           | Actualización transitiva.                      |
| `nanoid`                        | 3.3.16         | 3.3.20          | Actualización transitiva.                      |
| `source-map-js`                 | 1.2.1          | 1.2.2           | Actualización transitiva.                      |

Se eligió Vitest 4.1.11 para resolver los avisos conservando compatibilidad con
Vite 7 y Node 22. Su manifiesto admite Node `^20.0.0 || ^22.0.0 || >=24.0.0`
y Vite `^6.0.0 || ^7.0.0 || ^8.0.0`. El aviso del mantenedor identifica 4.1.11
como versión corregida; no fue necesario migrar a Vitest 5 ni aplicar
`npm audit fix --force`.

La configuración existente ya declara `coverage.include`, exclusiones y umbrales.
Ese include conserva los archivos sin ejecutar en el cálculo de cobertura,
conforme a la migración a Vitest 4. Las cifras de versiones distintas deben
compararse considerando los cambios del proveedor V8.

## Verificación técnica

La primera comprobación local usó Node 24.16.0 y npm 11.13.0:

- `npm ci --no-audit --no-fund`: instalación reproducible aprobada.
- `npm audit --json`: cero hallazgos; salida 0.
- `npm run lint`: aprobado; salida 0.
- Build Vite con salida temporal: aprobado; salida 0. El control de presupuesto
  debe verificarse mediante el comando completo del entorno QA.
- Regresión completa inicial: 280 de 283 pruebas aprobadas. Dos previews esperan
  `blob:mock-url`, pero reciben una URL nativa de Node; el setup condicional de
  `URL.createObjectURL` requiere adaptación. La tercera prueba agotó 5 segundos
  en el envío del formulario de encargados. Se reintentó con dos workers para
  comprobar la influencia de la concurrencia.

Los directorios locales `coverage` y `dist` contenían artefactos con permisos de
otro usuario, por lo que cobertura y build se enviaron a directorios temporales.
Se corrigió el setup con stubs incondicionales para `createObjectURL` y
`revokeObjectURL`, conservando las expectativas de las pruebas de previews.
La repetición completa en Docker `node:22-alpine` (Node **22.23.3**), con dos
workers y sin ampliar timeouts, aprobó **283 pruebas en 32 archivos**. Cobertura:
73.02 % de sentencias, 68.04 % de ramas, 67.73 % de funciones y 73.67 % de líneas;
supera todos los umbrales configurados. Lint y compilación Vite también aprobaron
en Node 22. El ejecutor de Fase 7 conserva la evidencia formal del candidato;
esta comprobación técnica previa no sustituye su registro de SHA y diff.

## Fuentes

- [Migración oficial a Vitest 4](https://v4.vitest.dev/guide/migration.html).
- [Aviso del mantenedor para `@vitest/mocker`](https://github.com/vitest-dev/vitest/security/advisories/GHSA-82fw-gwwq-j7x9).
- Auditorías inicial y posterior de INC-003 y lockfile versionado; la matriz de
  ejecuciones conserva el contexto de la auditoría inicial.
