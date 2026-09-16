# Project Context

## Proyecto
**LocVe Unificado (CE + EE)** - Localización Venezolana para Odoo v18.

## Entorno Técnico
- **Framework:** Odoo 18.0 (Community **Y** Enterprise).
- **Control de Versiones:** Git.
- **Sistema Multimoneda:** Odoo configurado para manejar escenarios duales en Venezuela (Base USD con Tasa BCV dinámica). Las soluciones deben ser agnósticas de la moneda base para evitar errores de tipo de cambio.

## Reglas de Arquitectura y Negocio
1. **Dual Compatibility Obligatoria:** Todo código debe funcionar en CE **Y** EE. No hay excepciones.
2. **Soluciones Escalables (Código sobre Interfaz):** Cualquier modificación en la lógica de negocio debe hacerse a nivel de código (modelos, vistas XML, actions), NUNCA modificando mediante la interfaz de Odoo.
3. **Cero Parcheo Invasivo:** No modificar el core de Odoo. Las funcionalidades deben extenderse estrictamente mediante la herencia del ORM (`_inherit`).
4. **Manejo Nativo:** Priorizar el uso de los métodos nativos de Odoo (por ejemplo, `reconcile()` de las `account.move.line`) para resolver operaciones contables.
5. **Cumplimiento SENIAT:** Las modificaciones contables y fiscales deben cumplir de manera estricta con las providencias vigentes de Venezuela.
6. **Precisión Decimal:** Campos Float de tasa de cambio: siempre `digits=(16, 4)` y `round(x, 4)`.
7. **Moneda TFHKA:** Siempre `"VES"` (nunca `"VEF"`). Hora: siempre formato 12h `%I:%M:%S %p` (minúsculas).
