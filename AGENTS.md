# Protocolo del Agente — LocVe Unificado (CE + EE)

> **Regla de Oro:** Lee `.cerebro/SESSION_BRIEF.md` antes de cualquier acción.
> Si cambias de modelo, detente y pide al usuario confirmación de contexto.
> Prohibido usar información de otros proyectos. Prohibido browser_subagent.

## Orden de Lectura

1. `.cerebro/SESSION_BRIEF.md` — Contexto completo (Obsidian + Graphify + trazabilidad)
2. `trazabilidad.md` — Bitácora operativa local
3. `COMPATIBILITY.md` — Reglas de compatibilidad CE/EE
4. Código fuente — Solo después de entender el contexto

## Identidad del Proyecto

- **Nombre:** LocVe — Localización Venezolana para Odoo 18
- **Versión:** 18.0.2.0.x (unificada)
- **Compatibilidad:** Odoo 18 CE **Y** Odoo 18 EE
- **Autor:** Ing. Nerdo José Pulido Aguirre
- **Licencia:** LGPL-3 (mayoría), AGPL-3 (algunos), Proprietary (account_dual_currency, locve_multimoneda_reportes)

## Reglas de Compatibilidad CE/EE

### REGLA #1: Dual Compatibility Obligatoria
TODO código nuevo debe funcionar en **ambas** ediciones (CE y EE). No hay excepciones.

### REGLA #2: No romper dependencias EE
Los módulos dependen de módulos EE en sus manifests:
- `locve_multimoneda_reportes` → `account_reports` (EE)
- `l10n_ve_payroll` → `hr_payroll_account` (EE)
- XMLs heredan de `account_accountant`, `account_asset`, `hr_work_entry_contract_enterprise`

**NUNCA eliminar o modificar** las referencias a estos módulos sin aprobación.

### REGLA #3: Precisión decimal
Campos Float de tasa de cambio: **siempre** `digits=(16, 4)` y `round(x, 4)`.
Ver `COMPATIBILITY.md` § Precisión Decimal.

### REGLA #4: Moneda
- Facturación digital TFHKA: **siempre** `"VES"` (nunca `"VEF"`)
- Hora emisión: **siempre** formato 12h `%I:%M:%S %p` (minúsculas)

### REGLA #5: No eliminar funcionalidad existente
NUNCA eliminar campos, métodos o lógica sin aprobación explícita del usuario.

## Proyectos Congelados

Si `criterio_congelado_desarrollador: TRUE` en `.cerebro/conocimiento.md`, el código es solo lectura.
No editar sin aprobación explícita del usuario.

## Cierre de Sesión

Antes de finalizar:
1. Actualizar `trazabilidad.md` con los cambios realizados
2. Ejecutar lint/typecheck si aplica
3. Reportar archivos modificados al usuario
