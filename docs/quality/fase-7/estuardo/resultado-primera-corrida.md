# Resultado de la primera corrida de evaluación

168 casos: 168 aprobados, 0 fallidos, 0 omitidos. Exit code 0.

Pytest reportó 11,17 segundos y cuatro advertencias `RemovedInDjango60Warning`
por `CheckConstraint.check` en modelos/migraciones de academics y enrolments.
No provocaron fallos; se conservan en el log para seguimiento de mantenimiento.

- Corrida: `RUN-EST-20261012-01`.
- SHA: `3bcca08860b07c7086ac11b914a7262e7a68d282`. Código de dominio sin cambios locales al comenzar.
- Inicio UTC: 2026-10-12T17:12:19.3037742+00:00; fin UTC: 2026-10-12T17:12:42.2706014+00:00.
- Ejecutó: Codex para Estuardo; revisión de Roí pendiente.
- Entorno: Windows, Docker Desktop/Linux, Python 3.11.17, Django 5.2.17, pytest 8.4.1 y PostgreSQL 16.15. Versiones efectivas en los archivos de evidencia.
- Datos: factories sintéticas, base de pruebas aislada, sin datos institucionales.
- Comando exacto: `environment.json`; consola en `execution.log`; resultados por caso en `junit.xml`.
- Alcance: unitarias, API e integración de evaluación. Sin cobertura global (`--no-cov`), navegador ni aceptación institucional.
- Preparación: Docker inicialmente detenido; se inició Docker Desktop y se construyó backend-test; no fue un fallo funcional.
- Al terminar se detuvo únicamente `db-test` del proyecto `siga_inebi_estuardo_qa`. Los contenedores de ejecución se eliminaron con `--rm`; logs y JUnit permanecen en el repositorio local. No se alteró la base de desarrollo.

[Resultados por prueba](resultados-pruebas.csv) · [Evidencia revisada y hashes](evidencia-revisada.md)

Los 24 requisitos del catálogo continúan sin aceptación: aprobar pruebas existentes no demuestra todos los criterios. Persisten las discrepancias y brechas documentadas en [la guía](README.md). No se modifica la clasificación institucional ni se cierra UAT.

Nota de publicación: la rama de este PR parte de `develop` en `3a4a8d2`; esta corrida sigue referida exclusivamente al SHA evaluado `3bcca08`. No certifica los cambios posteriores. El catálogo conserva la instantánea inicial y sus pendientes, no el estado actualizado de toda la entrega.
