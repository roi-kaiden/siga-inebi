# Ronda 4: regresión real de INC-008 y boleta

Fecha: 12 de octubre de 2026. Corrida: RUN-EST-20261012-04.
Código probado: `cd2333b6e780e20febead94152911d233e7550fc`, corrección del PR #555, sin cambios funcionales locales.
Ejecutor: Estuardo con ejecución asistida. Revisión de Roí pendiente.
Entorno: Edge 155.0.4283.45 headless, viewport 1440 × 1000, Vite local,
Django 5.2.17 y PostgreSQL 16 aislado. Cuenta docente sintética sin superusuario.

## Resultados

| Caso | Resultado | Evidencia observada |
| --- | --- | --- |
| Login real | Aprobado | Acceso mediante formulario institucional. |
| Nota fuera de rango | Aprobado | 101 rechazado HTTP 400 desde formulario. |
| Registro primera unidad | Aprobado | 59 guardado HTTP 201 y visible. |
| Subárea ajena | Aprobado | Registro rechazado HTTP 403. |
| Registro segunda unidad | Aprobado | 60 guardado HTTP 201. |
| INC-008, regresión real | Aprobado | API: average=59.5, final_grade=60, approved=true; encabezado visible: 60. |
| Descarga boleta por API | Aprobado | Con ciclo cerrado y permiso document_issue: HTTP 200, application/pdf y attachment boleta.pdf. |
| Contenido visual de boleta | Aprobado con limitación | En una subárea y dos unidades se ven 59, 60, final 60, Aprobado y Promovido; renderizado después de reparación automática. |
| Integridad del PDF | Fallido | PyMuPDF repara xref para abrirlo: cannot recognize xref format; is_repaired=true. Hallazgo QA4-PDF-01. |
| Descarga mediante interfaz del producto | Bloqueado | No se encontró llamada ni acción frontend para historical-cycle-reports; documentsService no expone ese endpoint. |

## Procedimiento y límites

Se registraron las notas mediante Playwright sobre la interfaz y API reales, sin
simular respuestas. Después se preparó el cierre en el backend de QA mediante
servicios de dominio, agregando el CurriculumPlan y el permiso de emisión al
usuario sintético. La descarga usó la sesión real del navegador mediante una
petición al endpoint; no se agregó un botón artificial ni se atribuye el cierre
a una interacción de usuario. PyMuPDF abrió y renderizó el archivo; se inspeccionó
la imagen resultante. No se probó impresión física, múltiples subáreas ni móvil.

Hubo dos incidencias de preparación: login anterior al arranque del backend y
colisión de slug al crear el rol de emisión. Se corrigió el fixture aislado y se
repitieron las operaciones. No son defectos del producto. El intento de descarga
sin el permiso asignado devolvió 403 antes de la ejecución exitosa.

INC-008 tiene regresión de componente y ahora de navegador real, pero su cierre
formal requiere revisión independiente e integración. La escritura en ciclo
cerrado desde navegador sigue pendiente. También siguen pendientes el flujo de
configuración/asignación por UI, usabilidad, UAT y videos.

## QA4-PDF-01: PDF con referencias internas inválidas

Requisito: RF-RES-008. Propuesta de severidad: media, pendiente de triage con Roí.
Reproducción: ciclo cerrado con notas 59 y 60; GET autenticado a
`/api/v1/documents/historical-cycle-reports/?enrolment_id=<matrícula sintética>`;
abrir el archivo con PyMuPDF e inspeccionar `is_repaired` y advertencias.
Esperado: PDF válido sin reparación. Observado: `is_repaired=true` y
`format error: cannot recognize xref format`, `trying to repair broken xref`.
El servicio escribe offsets xref y startxref constantes pese al contenido variable;
es un candidato a causa, no una corrección validada. No se modificó el generador.

Los archivos originales y sus hashes están descritos en [evidencias.md](evidencias.md).
No se publica información de sesión. Esta rama parte del PR #555 y depende de su
corrección; no representa una nueva corrida sobre develop sin ese cambio.
