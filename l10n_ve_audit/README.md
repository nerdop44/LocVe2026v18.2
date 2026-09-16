# Localización Venezolana - Auditoría Fiscal (SENIAT)

Este módulo provee la infraestructura requerida por el **SENIAT** para la evaluación de sistemas informáticos, garantizando el registro de eventos inmutables y la existencia de un usuario de tipo "Auditor" con permisos de solo lectura.

---

## 1. Funcionamiento de la Tabla de Auditoría

El módulo registra automáticamente de forma inmutable los siguientes eventos en el modelo `l10n_ve.audit.log`:

- **Creación (Borrador):** Se registra cuando se crea una factura de cliente, factura de proveedor, o nota de crédito/débito.
- **Publicación / Asentado:** Se registra cuando el documento pasa al estado "Publicado", guardando el número de control asignado y los montos totales (Bs y divisa).
- **Volver a Borrador:** Se registra si el documento se devuelve a borrador.
- **Cancelación:** Se registra si se anula la transacción.
- **Reversión (Nota de Crédito/Débito):** Se registra la generación de notas de crédito asociando el documento original afectado y los montos.
- **Eliminación Directa:** Si se elimina un registro (incluso en estado borrador), se guarda la trazabilidad completa del usuario, fecha, montos y número de documento eliminado antes de su destrucción.

> [!IMPORTANT]
> A nivel de base de datos y lógica ORM, las operaciones de edición (`write`) y eliminación (`unlink`) sobre los registros de la Tabla de Auditoría están **completamente bloqueadas**. Esto garantiza la inmutabilidad absoluta de los logs frente a cualquier usuario, incluido el administrador del sistema.

---

## 2. Guía de Configuración del Rol "Auditor Fiscal"

Para dar acceso al personal del SENIAT durante la evaluación de 4 horas, siga estos pasos:

1. Inicie sesión como **Administrador** y active el **Modo de Desarrollador**.
2. Vaya a **Ajustes** → **Administrar Usuarios**.
3. Haga clic en **Nuevo** para crear el usuario del auditor (ejemplo: `auditor.seniat@empresa.com`).
4. En la pestaña **Derechos de Acceso**, configure los siguientes campos:
   - **Contabilidad:** Deje este campo en **Blanco** (No asigne "Facturación", "Contable" ni "Administrador de Facturación").
   - **Localización Venezolana (Categoría Contabilidad):** Marque la opción **Auditor Fiscal (SENIAT)**.
   - Asegúrese de que no tiene permisos de escritura en Ventas, Compras ni Inventario (dejar en blanco o solo lectura).
5. Guarde el registro del usuario.

### Comprobación de Seguridad
Al iniciar sesión con las credenciales del Auditor Fiscal, el usuario podrá:
1. Acceder al menú **Contabilidad** y ver el menú **Auditoría Fiscal (SENIAT)**.
2. Ver todos los logs en la Tabla de Auditoría de forma detallada, sin botones de "Crear", "Editar" ni "Eliminar".
3. Consultar las facturas de clientes, proveedores y apuntes contables en modo estrictamente de **solo lectura**. Toda acción de creación, modificación o borrado le devolverá un error de permisos.
