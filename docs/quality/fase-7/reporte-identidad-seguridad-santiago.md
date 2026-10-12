# Reporte de validación de identidad y seguridad — Santiago

## Estado

Validación de línea base ejecutada el 12 de octubre de 2026 sobre el SHA
`450d0a805c34e779f3d2cd024cff8c2b985e133a`. Este reporte no constituye
aceptación final: el candidato de entrega, la revisión cruzada y varias
decisiones de alcance siguen pendientes.

## Alcance evaluado

- Autenticación, bloqueo temporal, cierre y expiración de sesiones.
- Cambio de contraseña y provisión administrativa de cuentas.
- Roles, permisos atómicos, denegación por defecto y vigencia inmediata.
- Alcances institucionales, docentes, de encargados y de ciclo activo.
- Controles frontend de login, logout, expiración, bloqueo y cambio de clave.
- Análisis estático y auditoría de dependencias backend/frontend.

El catálogo contiene 29 casos `CP-SEG-*`. Se ejecutaron los 17 clasificados
como incluidos o condicionados. Los 12 casos fuera del candidato conservan
estado `No ejecutado`; no se usaron sus pruebas existentes para declarar
aceptación.

## Resultados

| Ejecución | Control | Resultado |
| --- | --- | --- |
| EJ-D1-008 | Backend de identidad, autorización y alcance | Aprobado: 158 pruebas; cuatro advertencias de deprecación |
| EJ-D1-009 | Frontend de autenticación y sesiones | Aprobado: 33 pruebas en tres archivos |
| EJ-D1-010 | Bandit y `pip-audit` | Aprobado: sin hallazgos Bandit; cero vulnerabilidades conocidas y una excepción versionada |
| EJ-D1-011 | `npm audit --audit-level=high` | Fallido: 8 vulnerabilidades, vinculadas a INC-003 |

Catorce requisitos incluidos quedaron `Aprobado` en el catálogo. Tres
requisitos condicionados quedaron `Bloqueado`: sus controles pasan, pero el
estado de implementación/documentación y DEC-QA-002 impiden aceptarlos.

## Incidencias y riesgos

- **INC-003, abierta P0:** dos vulnerabilidades críticas, cuatro altas y dos
  moderadas en dependencias frontend, principalmente herramientas de prueba.
  La corrección total propuesta exige Vitest 5.0.3 y regresión completa; no se
  aplicó `npm audit fix --force`.
- **INC-005, abierta P0:** la suite backend global del PR obtuvo 15 fallos y
  1557 aprobaciones. La suite dirigida de identidad aprobó; coordinación debe
  hacer triage de los fallos en academics, audit y form suggestions.
- Cuatro advertencias `RemovedInDjango60Warning` no provocaron fallos, pero
  deben revisarse antes de migrar a Django 6.

## Pendientes para cierre

1. Diana debe realizar la revisión cruzada de casos y resultados.
2. Daniel debe revisar INC-003 y la excepción versionada de `pip-audit`.
3. Pablo y la contraparte deben resolver DEC-QA-002 y las discrepancias de
   clasificación entre catálogo y matriz canónica.
4. Daniel debe fijar el SHA y entorno del candidato final conforme DEC-QA-001.
5. Repetir EJ-D1-008 a EJ-D1-011 sobre el candidato final.
6. Verificar cookies y TLS en el entorno HTTPS de entrega.
7. Mantener AUT-005 y CTA-005 sin aceptación hasta contar con alcance y prueba
   verificable.

## Conclusión

Los controles automatizados de identidad y autorización ejecutados son
satisfactorios para esta línea base, pero el dominio no está listo para
aceptación final mientras INC-003, DEC-QA-001, DEC-QA-002 y la revisión cruzada
permanezcan abiertos.
