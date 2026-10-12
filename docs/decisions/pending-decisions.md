# Pending Decisions

| ID | Decision pendiente | Impacto | Estado |
| --- | --- | --- | --- |
| PD-001 | Confirmar matricula real objetivo para dimensionamiento | Rendimiento, capacidad | Open |
| PD-002 | Definir RPO y RTO institucionales | Respaldo y recuperacion | Declarado (RNF-RES-002) |
| PD-003 | Definir politica de retencion por tipo documental y salud | Cumplimiento y storage | Open |
| PD-004 | Definir granularidad de acceso de encargados con multiples estudiantes | Autorizacion | Open |
| PD-005 | Definir politica de acceso para observaciones disciplinarias | Privacidad | Open |
| PD-006 | Definir datos visibles exactos en credencial | Privacidad y operacion | Open |
| PD-007 | Definir comportamiento de reapertura de ciclo sobre documentos ya emitidos | Integridad academica | Open |
| PD-008 | Definir regla de foliado ante reemision por correccion | Documentos oficiales | Open |
| PD-009 | Confirmar si inventario y programa de alimentos entran en roadmap cercano con RF formales | Alcance | Open |
| PD-010 | Medir tasa pico de porton y operadores concurrentes reales | Rendimiento de asistencia | Open |
| PD-011 | Acotar la guardia de archivos prohibidos de `pr-validation` a artefactos de datos | CI y contribucion | Open |
| PD-012 | Elegir respuesta si QA cloud resulta lento o caro: optimizar, ampliar Cloud SQL o cambiar de plataforma | Costo y rendimiento | Open |

## Notas

- **PD-002.** Se declaran RPO 24 h y RTO 4 h en
  `docs/architecture/backup-and-recovery.md`, con la misma regla que `RNF-CAP-001`
  aplico a la matricula: son una referencia explicita, no una cifra confirmada
  por el establecimiento, y viven en variables de entorno
  (`RECOVERY_POINT_OBJECTIVE_HOURS`, `RECOVERY_TIME_OBJECTIVE_HOURS`) para que
  reemplazarlas no toque codigo. Queda pendiente la confirmacion institucional
  de los valores, no su definicion.
- **PD-011.** La guardia de `.github/workflows/pr-validation.yml` rechaza toda
  ruta que contenga `backup` o `dump`, incluidos el codigo, las pruebas y la
  documentacion de la propia herramienta de respaldo que exige `RNF-RES-001`.
  Detalle y ajuste propuesto en `docs/architecture/backup-and-recovery.md`. Se
  deja aparte porque cambiar un control de CI merece su propia revision.
- **PD-012.** QA corre en Cloud Run con Cloud SQL `db-f1-micro` y HDD
  (ADR-0010), unos USD 10–12 al mes. Costos, alternativas (Cloudflare + Neon,
  VM) y orden de optimizacion en
  `docs/planning/qa-cloud-costos-y-alternativas.md`. Se decide despues de medir
  el rendimiento sobre ese entorno.
