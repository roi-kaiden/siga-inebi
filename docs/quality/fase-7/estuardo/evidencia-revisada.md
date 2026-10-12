# Evidencia revisada — RUN-EST-20261012-01

Esta referencia publica resultados sintéticos revisados. Los artefactos crudos
permanecen locales en `docs/quality/fase-7/evidence/RUN-EST-20261012-01/`,
ignorados por Git conforme a la política actual. Su entrega a revisores está
pendiente; los hashes permiten comprobar integridad, no sustituyen su acceso.

- SHA evaluado: `3bcca08860b07c7086ac11b914a7262e7a68d282`.
- Inicio UTC: 2026-10-12T17:12:19.3037742+00:00.
- Fin UTC: 2026-10-12T17:12:42.2706014+00:00.
- Python 3.11.17, Django 5.2.17, pytest 8.4.1, PostgreSQL 16.15.
- Resultado: 168 aprobados, cero fallos y cero omitidos; cuatro advertencias de deprecación.
- [Resultados por caso](resultados-pruebas.csv), transcritos de JUnit y cotejados con las 168 funciones del inventario.
- Operador técnico: Codex para Estuardo. Revisión de Roí pendiente.

## Comando ejecutado

Desde la raíz del repositorio; el marcador de directorio representa la ruta
absoluta local del directorio de esta corrida. La imagen se construyó con
`docker compose -p siga_inebi_estuardo_qa -f compose.yml -f compose.test.yml build backend-test`.
Se inició únicamente `db-test` del mismo proyecto. Para reproducir, usar el SHA
evaluado en un checkout separado y una carpeta de evidencia nueva.

```text
docker compose -p siga_inebi_estuardo_qa -f compose.yml -f compose.test.yml run --rm -v <absolute-evidence-directory>:/evidence backend-test sh -lc 'python --version > /evidence/runtime-versions.txt && python -m django --version >> /evidence/runtime-versions.txt && pytest --version >> /evidence/runtime-versions.txt && python manage.py migrate --noinput && pytest tests/unit/test_evaluation_services.py tests/api/test_evaluation_api.py tests/integration/test_evaluation.py --no-cov --junitxml=/evidence/junit.xml -q'
```

## Integridad de artefactos locales

Checksums posteriores a normalizar logs a UTF-8, sin cambiar su contenido.

| Archivo local | Bytes | SHA-256 |
| --- | ---: | --- |
| `build-exit-code.txt` | 2 | `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa` |
| `build.log` | 79500 | `445ef1d39930b3bac28ceba6c1b946955d9bae81e4468e526d68d0114c97cfa5` |
| `database-exit-code.txt` | 2 | `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa` |
| `database-start.log` | 781 | `c362750e4e5eb3624983a2e0ca86972851c550800af9776cdede9ec837c11343` |
| `environment.json` | 1060 | `034b13c1bcf069da856be26a77a35e16ce92ca57a99462f3a31df9aff0bf9568` |
| `execution.log` | 8900 | `0e93f2d8367d449afa16ee67d5b3ff92fcfbba8a0dea4f439d1ce1842c9cd7cd` |
| `exit-code.txt` | 2 | `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa` |
| `junit.xml` | 24699 | `d712a7f9ce1bd4b1bb7b89d7b6305c68856407689d94eec1f2f740f9771c1967` |
| `postgresql-version.txt` | 92 | `e8e2fe070e1e675c6d04f984f060f4f5294d5fd5dc1998eedd6c59c4b4886d9a` |
| `runtime-versions.txt` | 35 | `5098d735f48e5a9834a10243524dec162e571a6374b711ff416743bd75a3c0aa` |
