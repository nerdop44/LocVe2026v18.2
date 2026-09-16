# Conocimiento Adquirido — Aprendizajes del Proyecto

> **Proposito:** Capturar lecciones aprendidas, bugs resueltos, decisiones tecnicas
> y patrones descubiertos durante el desarrollo. Append-only — nunca se edita.
> Cada entrada puede requerir verificacion humana.

---

## [2026-09-04] Unificacion CE/EE — Analisis de Compatibilidad

### 1. Los proyectos CE y EE son clones identicos en manifests
- Los 28 modulos tienen manifests byte-a-byte identicos
- Las diferencias estan en codigo Python y XML views
- Conclusion: el codigo CE es un superset mejorado del EE

### 2. Mejoras CE seguras para EE
- `digits=(16, 4)` para campos de tasa de cambio
- `round(rate, 4)` en todos los calculos
- Deteccion de tasas obsoletas `<= 10.0` (fallback a BCV)
- Conditions mas permisivas (`new_rate > 0` vs `> 1.0`)
- Groups `account.group_account_invoice` (mas permisivo)

### 3. Dependencias EE en el proyecto
- `locve_multimoneda_reportes` requiere `account_reports` (EE)
- `l10n_ve_payroll` requiere `hr_payroll_account` (EE)
- XMLs heredan de `account_accountant`, `account_asset`, `hr_work_entry_contract_enterprise`
- En CE estos XMLs generan warnings pero no bloquean instalacion

---

## [2026-08-04] Estabilizacion de Libros de Compras/Ventas y Retenciones

### 1. `display_type` en `account.move.line` (Odoo 18)
- `line.display_type == 'product'` es un valor valido para lineas de producto
- No debe asumirse como inexistente

### 2. Doble Multiplicador de Signo en Libros Fiscales
- `_determinate_amount_taxeds()` retorna montos ya multiplicados por `multiplier = -1`
- `_fields_sale_book_line()` y `_fields_purchase_book_line()` NO deben volver a multiplicar

### 3. Discrepancia Nombres Aliacuota Exenta
- `l10n_ve_tax` usa `exent_aliquot_sale`
- `l10n_ve_binaural` usa `exempt_aliquot_sale`
- Fallback: `co.exempt_aliquot_sale or co.exent_aliquot_sale`

### 4. Referencia a Documento Afectado
- NC: `reversed_entry_id`
- ND: `debit_origin_id`

### 5. Auto-Calculo de Retenciones de Clientes
- Campos `retention_amount` e `invoice_amount` con `compute='_compute_amounts', store=True, readonly=False`
- Eliminar restriccion `type == 'in_invoice'` para clientes

### 6. Manejo Incremental de Correlativos
- 1a cancelacion: `NOMBRE-canc`
- 2a cancelacion: `NOMBRE-canc-01`
- 3a cancelacion: `NOMBRE-canc-02`

### 7. Arquitectura Bimonetaria
- Moneda Base sugerida: USD (Dolares)
- Moneda fiscal: VES (Bolivares) a tasa BCV

---

## [2026-09-04] Mejoras de Produccion (Sesiones 1-5)

### Fix TRM
- Condiciones corregidas: `if new_rate and new_rate > 0`
- Fallback para tasas obsoletas: `<= 10.0` usa `get_trm_systray()`
- Precision: `round(rate, 4)` en todo el stack

### Fix IGTF
- `return res` agregado en `_prepare_tax_totals`
- Variable `original_amount` para evitar doble conversion
- `elif` en `_compute_check_igtf` (no `if`)
- Eliminado guard `amount_with_igtf`

### Fix TFHKA
- Recursion: parametro `_retry=False` en `call_tfhka_api`
- Hora: formato 12h `%I:%M:%S %p` (minisculas)
- Moneda: siempre `"VES"` (nunca `"VEF"`)

### Fix Auditoria
- Groups: `account.group_account_invoice` (no `base.group_no_one`)
- Eliminado UserError en `button_draft`
- Override `_compute_show_reset_to_draft_button`

### Fix Cache
- `rec.foreign_inverse_rate = value` (no `rec._cache[...]`)

---

## [2026-09-04] Ecosistema de Documentación del Proyecto

### 1. Estructura de documentación replicada
- `soul.md` — Identidad del agente (Antigravity)
- `agent.md` — Reglas operativas + checklist pre-commit
- `AGENTS.md` — Protocolo del agente con orden de lectura
- `context.md` — Contexto del proyecto y reglas de arquitectura
- `COMPATIBILITY.md` — Reglas detalladas de compatibilidad CE/EE
- `trazabilidad.md` — Bitácora de sesiones (fuente única de verdad)
- `.cerebro/project.json` — Configuración del cerebro
- `.cerebro/SESSION_BRIEF.md` — Contexto completo de sesión
- `.cerebro/conocimiento.md` — Base de conocimiento (append-only)
- `scripts/cerebro-close.sh` — Script de cierre de sesión

### 2. Reglas de cierre de sesión
- Actualizar `trazabilidad.md` con los cambios realizados
- Guardar conocimiento adquirido en `.cerebro/conocimiento.md`
- Actualizar `.cerebro/SESSION_BRIEF.md` con el estado actual
- Ejecutar `scripts/cerebro-close.sh` si el ecosistema Cerebros Odoo está configurado

### 3. Proyectos de referencia consultados
- `LocVe Fiscal 2026/` — Proyecto EE principal
- `LocVe Fiscal 2026/.cerebro/` — Cerebro del proyecto EE
- `Fabrica de Modulos v18/IA_Suite/` — Ecosistema Cerebros Odoo (scripts)

### 4. Known issues del VPS (temporales, perdidos al reiniciar)
- `stock_picking.py` línea 180: todavía usa `"VEF"` — fix documentado pero perdido
- `call_tfhka_api`: falta parámetro `_retry=False` — fix documentado pero perdido
- `_compute_show_reset_to_draft_button`: no implementado en ningún proyecto
- **Verificado en VPS (2026-09-04):** Los archivos no tienen estos fixes
