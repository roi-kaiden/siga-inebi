# Manual de administración

## 1. Propósito y audiencia

Este manual describe las operaciones disponibles para personal administrativo
autorizado en SIGA-INEBI. Aplica a la versión candidata de Fase 7 y no sustituye
el manual técnico, el plan de respaldo ni una autorización institucional.

Use únicamente datos institucionales autorizados. En desarrollo y pruebas use
datos ficticios. Nunca copie contraseñas, códigos temporales, cookies, tokens o
datos personales en incidencias, capturas o mensajes.

## 2. Principios de administración

- El sistema deniega por defecto. Un rol no concede acceso si no contiene el
  permiso atómico necesario y un alcance vigente aplicable.
- Una cuenta siempre debe estar vinculada a una persona institucional.
- Una persona puede tener varios roles. Sus permisos y alcances efectivos se
  evalúan en cada operación.
- Los cambios de autorización surten efecto sin exigir un nuevo inicio de
  sesión.
- Las bajas, revocaciones, cierres y reasignaciones conservan historia. No se
  eliminan registros auditables para corregir una operación.
- El frontend ayuda a ocultar opciones no disponibles, pero la autorización
  definitiva siempre se aplica en el backend.

## 3. Acceso y navegación

1. Abra la URL entregada por el responsable técnico.
2. Inicie sesión con su cuenta institucional individual.
3. No comparta la sesión ni use cuentas genéricas en operación institucional.
4. Use el menú lateral para acceder únicamente a los módulos visibles para su
   autorización.
5. Al finalizar, abra el menú de usuario y cierre la sesión. Use **Cerrar todas
   las sesiones** cuando sospeche que otra sesión quedó abierta.

En desarrollo local, la documentación interactiva de API está en
`/api/v1/docs/`. Su existencia no concede autorización: cada operación conserva
las mismas comprobaciones de sesión, permiso y alcance.

## 4. Estado de disponibilidad administrativa

| Capacidad | Disponibilidad actual |
| --- | --- |
| Listar cuentas, restablecer acceso, cerrar sesiones y desactivar | Pantalla **Seguridad > Cuentas** |
| Cambiar la contraseña propia | Menú de la cuenta autenticada |
| Crear cuentas y emitir activación | API de identidad |
| Crear o modificar roles y asignarlos | API de identidad |
| Declarar alcances | Servicio/API de identidad; sin pantalla administrativa completa |
| Consultar y exportar bitácora | API de auditoría; sin pantalla administrativa completa |
| Configurar estructura académica | Pantallas de Ciclo escolar, Sedes, Aulas, Niveles, Cursos y Asignaciones docentes |
| Gestionar plantillas y tipos documentales | Pantallas de Documentos y control |

No improvise cambios directos en la base de datos para suplir una pantalla que
no existe. Registre la necesidad como incidencia o solicitud de cambio.

## 5. Cuentas y acceso

### 5.1 Consultar cuentas

- **Permiso requerido:** `account.disable` o condición de superusuario.
- **Ruta visual:** **Seguridad > Cuentas**.
- **Precondición:** sesión administrativa vigente.
- **Procedimiento:** localice la persona o el usuario y revise su estado:
  Activo, Pendiente, Desactivado o Bloqueado.
- **Resultado esperado:** se presenta la cuenta vinculada a su persona sin
  mostrar contraseñas ni códigos.
- **Auditoría:** las operaciones sensibles posteriores se registran; la lista
  no debe usarse para extraer información fuera de la necesidad administrativa.

### 5.2 Crear y activar una cuenta

Esta operación está disponible por API y todavía no tiene un formulario
administrativo completo.

- **Permisos requeridos:** `account.create` para provisionar y
  `account.activate` para reemitir el código inicial.
- **Precondiciones:** la persona institucional ya existe y no está vinculada a
  otra cuenta; el nombre de usuario es único.
- **Procedimiento autorizado:** use `POST /api/v1/identity/accounts/`. Entregue
  el código de activación solamente a la persona titular por un canal aprobado.
  Si vence, use la reemisión de desafío de activación.
- **Resultado esperado:** la cuenta nace pendiente e inactiva; el código se
  muestra una sola vez, dura 15 minutos y permite tres intentos.
- **Auditoría:** `identity.account.created` e
  `identity.activation_challenge.issued`; los rechazos también generan evento.

La administración nunca define ni conoce la contraseña final de la persona.

### 5.3 Restablecer acceso

- **Permiso requerido:** `account.disable` en el contrato actual.
- **Ruta visual:** **Seguridad > Cuentas > Restablecer acceso**.
- **Precondición:** cuenta identificada y titular verificado por el
  procedimiento institucional.
- **Procedimiento:** confirme la cuenta, genere el enlace o clave temporal y
  entréguelo una sola vez a la persona titular. No lo copie a una incidencia.
- **Resultado esperado:** el titular define una contraseña nueva; las sesiones
  anteriores quedan invalidadas al consumir el restablecimiento.
- **Auditoría:** `identity.password_reset.issued`,
  `identity.password_reset.consumed` o su evento de rechazo.

### 5.4 Cerrar sesiones de otra cuenta

- **Permiso requerido:** `account.disable`.
- **Ruta visual:** **Seguridad > Cuentas > Cerrar sesiones**.
- **Precondición:** confirmar que la cuenta objetivo es correcta.
- **Procedimiento:** lea la advertencia y confirme **Cerrar sesiones**.
- **Resultado esperado:** las sesiones existentes de esa cuenta dejan de
  operar; la cuenta no se desactiva.
- **Auditoría:** `identity.session.closed_administratively` o evento de rechazo.

### 5.5 Desactivar una cuenta

- **Permiso requerido:** `account.disable`.
- **Ruta visual:** **Seguridad > Cuentas > Desactivar**.
- **Precondiciones:** verificar identidad, motivo y dependencias operativas.
- **Procedimiento:** solicite la desactivación. Si existen asignaciones docentes
  vigentes, reasígnelas antes de continuar. Forzar la operación solo procede con
  decisión institucional expresa y plan de continuidad.
- **Resultado esperado:** estado Desactivado, sin borrar la cuenta ni su
  historial.
- **Auditoría:** `identity.account.disabled`; intentos denegados también quedan
  registrados.

El sistema impide desactivar la última cuenta capaz de administrar cuentas.

## 6. Roles, permisos y alcances

Estas operaciones están disponibles mediante la API de identidad y aún no
cuentan con una pantalla administrativa completa.

### 6.1 Crear o modificar un rol

- **Permiso requerido:** `role.assign` con alcance administrativo vigente.
- **Precondición:** justificar la necesidad y elegir únicamente permisos del
  catálogo atómico publicado por `/api/v1/identity/permissions/`.
- **Procedimiento:** use `/api/v1/identity/roles/`; defina nombre, descripción,
  duración de inactividad y permisos. Revise el efecto antes de guardar.
- **Resultado esperado:** el rol queda disponible sin recrear cuentas ni
  asignaciones existentes.
- **Auditoría:** `identity.role.created`, `identity.role.updated` o evento de
  rechazo, con estado anterior y posterior cuando aplique.

No cambie un rol para resolver una excepción individual si un alcance más
restringido satisface la necesidad.

### 6.2 Asignar o revocar un rol

- **Permiso requerido:** `role.assign`.
- **Precondiciones:** cuenta objetivo correcta, rol justificado, vigencia y al
  menos una dimensión de alcance aplicable.
- **Procedimiento:** asigne mediante
  `/api/v1/identity/accounts/{id}/role-assignments/`. Para retirar acceso,
  revoque la asignación existente; no elimine la fila histórica.
- **Resultado esperado:** el cambio se aplica en las sesiones activas desde la
  siguiente operación.
- **Auditoría:** `identity.role_assignment.created`,
  `identity.role_assignment.revoked` o sus eventos de rechazo.

No se permite autoasignación, autorevocación ni retirar la última capacidad de
administración de cuentas.

### 6.3 Declarar alcances

- **Permiso requerido:** `scope.assign`.
- **Precondición:** rol asignado y objeto institucional identificado.
- **Regla:** todo permiso contextual necesita alcance. Puede corresponder a
  institución, ciclo, grado, sección, curso, asignación docente, estudiante o
  módulo, con vigencia cuando aplique.
- **Resultado esperado:** la cuenta solo opera sobre los datos incluidos. Un
  permiso sin alcance efectivo sigue denegado.
- **Auditoría:** conserve actor, objeto, alcance, vigencia y resultado.

El alcance docente se deriva de asignaciones docentes vigentes y el del
encargado de relaciones vigentes con estudiantes; no duplique esos alcances sin
una razón documentada.

## 7. Configuración institucional y académica

### 7.1 Orden recomendado

1. Registre sedes y jornadas.
2. Registre aulas.
3. Revise niveles y grados.
4. Registre cursos y vínculos con niveles.
5. Prepare el ciclo escolar siguiente.
6. Configure oferta, secciones y plan de estudios.
7. Asigne docentes.
8. Configure evaluación y horarios.
9. Active el ciclo únicamente cuando el sistema no reporte brechas.

Las escrituras de catálogo y estructura requieren `scope.assign` con alcance
institucional coincidente. Los cambios deben ejecutarse desde las pantallas
correspondientes y nunca mediante SQL manual.

### 7.2 Ciclos escolares

- **Ruta visual:** **Estructura académica > Ciclo escolar**.
- **Crear:** **Nuevo ciclo** registra un borrador vacío.
- **Clonar:** el icono de copia crea un ciclo nuevo a partir de un ciclo cerrado,
  con oferta, secciones y plan; las asignaciones docentes son opcionales.
- **Activar:** valide antes grados, secciones, plan de estudios, asignaciones y
  unidades de evaluación. Activar cierra la preparación estructural ordinaria.
- **Cerrar o reabrir:** use únicamente los contratos autorizados. La reapertura
  requiere `academic_cycle.reopen`, motivo y auditoría; no descarta resultados
  congelados.
- **Auditoría esperada:** creación, clonación, activación, cierre y reapertura
  registran actor y ciclo afectado.

La pantalla de detalle histórico es de consulta. La versión actual no ofrece una
pantalla completa para cargar manualmente toda la estructura de un ciclo vacío.
No active un ciclo incompleto.

### 7.3 Sedes, jornadas, aulas, niveles y cursos

- Use **Sedes** para registrar una sede y sus jornadas.
- Use **Aulas** para registrar espacios físicos asociados a una sede.
- Use **Niveles** para administrar niveles, grados y vínculos de cursos.
- Use **Cursos** para mantener el catálogo institucional.
- Prefiera desactivar antes que eliminar. Revise dependencias mostradas por la
  interfaz y confirme que la operación corresponde a la institución correcta.
- **Resultado esperado:** el catálogo conserva identidad e historial y deja de
  estar disponible para nuevas operaciones cuando se desactiva.

### 7.4 Asignaciones docentes

- **Ruta visual:** **Estructura académica > Asignaciones docentes**.
- Seleccione ciclo, sección, curso, docente y fecha de inicio.
- Puede asignar individualmente, por lote o clonar desde otro ciclo cuando la
  estructura destino coincide.
- Para cambiar docente use **Reasignar**: la asignación anterior se cierra y se
  abre una nueva. Nunca sobrescriba el historial.
- **Permiso requerido:** `scope.assign` y alcance institucional coincidente.
- **Resultado esperado:** la asignación vigente determina el alcance docente.
- **Auditoría:** alta y reasignación conservan actor, vigencia y registros
  anterior/nuevo.

## 8. Plantillas, documentos y reportes

- Use **Plantillas** y **Tipos de documento** solo con autorización funcional.
- No introduzca código ejecutable en plantillas. Utilice exclusivamente los
  marcadores admitidos por el catálogo cerrado.
- Las descargas sensibles requieren permiso y alcance; deben usar el mecanismo
  temporal entregado por el sistema.
- No comparta enlaces de descarga ni documentos fuera del canal institucional.
- Las lecturas y descargas sensibles deben generar auditoría según su tipo.

## 9. Auditoría y conservación de historia

La consulta y exportación están disponibles por API:

- `GET /api/v1/audit/events/`
- `GET /api/v1/audit/events/export/`

- **Permiso requerido:** `audit.read` con alcance válido.
- **Precondición:** propósito autorizado y filtros mínimos necesarios.
- **Resultado esperado:** eventos dentro del alcance; una exportación genera
  `audit.export.created`.

La bitácora es inmutable. Una corrección crea un nuevo asiento o registro de
ajuste; nunca se modifica ni elimina el evento original. No exporte bitácoras a
equipos personales ni las adjunte completas a incidencias.

## 10. Incidencias y escalamiento

| Situación | Acción inmediata |
| --- | --- |
| Acceso indebido o posible exposición | Cierre sesiones si corresponde, preserve evidencia sanitizada y escale como S1/S2. No investigue usando datos reales fuera del sistema. |
| Cuenta bloqueada | Confirme identidad y espere el desbloqueo automático de 10 minutos. No desactive controles ni altere contadores en base de datos. |
| Contraseña olvidada | Use **Restablecer acceso** y entregue la clave temporal solo al titular. |
| Datos inconsistentes | Detenga la operación afectada, registre pasos y SHA/versión; no borre registros para volver a intentar. |
| Operación sensible fallida | Capture el mensaje sin secretos, verifique autorización y alcance, y registre incidencia si es reproducible. |
| Pérdida o corrupción de datos | Suspenda escrituras afectadas y escale a Daniel y Pablo. No improvise una restauración. |

GitHub Issues es el registro técnico oficial hasta que la institución designe
otro canal. Siga el [plan de mantenimiento y soporte](08-maintenance-and-support-plan.md)
y el plan final de respaldo y recuperación. Una incidencia se cierra solo con
corrección revisada, prueba de regresión y evidencia sobre un SHA identificado.

## 11. Revisión periódica

En cada revisión de accesos:

1. Liste cuentas activas, pendientes, bloqueadas y desactivadas.
2. Confirme que cada cuenta siga vinculada a una persona vigente.
3. Revise roles, permisos atómicos, alcances y fechas de vigencia.
4. Compare asignaciones docentes y relaciones de encargados con su realidad
   institucional.
5. Revoque accesos vencidos conservando historia.
6. Registre responsable, fecha, hallazgos y acciones.
7. Solicite revisión independiente de cambios privilegiados.

No marque la revisión como completada si quedan excepciones sin responsable,
justificación y fecha de reevaluación.
