# COMPATIBILITY.md — Reglas de Compatibilidad CE/EE

## Visión General

Este proyecto (`LocVe 2026 v18.2`) es la versión **unificada** de la localización venezolana para Odoo 18. Debe funcionar correctamente en:
- **Odoo 18 CE** (Community Edition)
- **Odoo 18 EE** (Enterprise Edition)

---

## Módulos con Dependencias EE

Los siguientes módulos dependen de módulos que **solo existen en EE**:

| Módulo | Depende de | Disponible en CE |
|--------|-----------|-----------------|
| `locve_multimoneda_reportes` | `account_reports` | **NO** |
| `l10n_ve_payroll` | `hr_payroll_account` | **NO** (en contexto EE) |

### Implicaciones
- `locve_multimoneda_reportes` **no se puede instalar en CE** (pendiente de terminar en ambos proyectos)
- `l10n_ve_payroll` **no se puede instalar en CE** sin el módulo EE correspondiente

---

## XML Views que Heredan de EE

Los siguientes archivos XML heredan de vistas de módulos EE:

| Archivo | Hereda de | Existe en CE |
|---------|----------|-------------|
| `account_dual_currency/views/view_bank_statement_line_tree_bank_rec_widget.xml` | `account_accountant` | **NO** |
| `account_dual_currency/views/account_asset.xml` | `account_asset` | **NO** |
| `l10n_ve_payroll/views/hr_employee_loan_type.xml` | `hr_work_entry_contract_enterprise` | **NO** |
| `l10n_ve_payroll/views/report_templates.xml` | `account_reports.main_template` | **NO** |
| `l10n_ve_payment_extension/views/menu.xml` | `account.account_reports_management_menu` | **NO** (viene de `account_reports`) |

### Implicaciones
- Estos XMLs **funcionan en EE** porque los módulos existen
- En CE, estos XMLs **generarán warnings** pero no bloquearán la instalación (Odoo maneja herencias faltantes con logs)

---

## Reglas de Código

### Precisión Decimal
```python
# SIEMPRE usar digits=(16, 4) para campos de tasa de cambio
tax_today = fields.Float(digits=(16, 4))

# SIEMPRE usar round(x, 4) en cálculos de tasa
rec.tax_today = round(new_rate, 4)

# SIEMPRE usar precision_digits=4 en float_round
val = float_round(amount / rate, precision_digits=4)
```

### Moneda TFHKA
```python
# SIEMPRE "VES" (nunca "VEF")
"moneda": "VES"
```

### Hora TFHKA
```python
# SIEMPRE formato 12h con am/pm minúsculas
emission_time = now.astimezone(user_tz).strftime("%I:%M:%S %p").lower()
# Produce: "02:30:00 pm"
```

### Recursión TFHKA
```python
# SIEMPRE usar parámetro _retry para evitar recursión infinita
def call_tfhka_api(self, endpoint_key, payload, _retry=False):
    ...
    if response.status_code == 401 and not _retry:
        self.company_id.generate_token_tfhka()
        return self.call_tfhka_api(endpoint_key, payload, _retry=True)
    elif response.status_code == 401:
        raise UserError(_("Token expirado y no se pudo renovar automáticamente."))
```

---

## Pruebas de Compatibilidad

### Antes de cada cambio
1. Verificar que el código no dependa de módulos EE para funcionar
2. Verificar que los `digits` sean `(16, 4)` para campos de tasa
3. Verificar que la moneda sea `"VES"` en TFHKA
4. Verificar que la hora sea formato 12h en TFHKA
5. Ejecutar tests si existen

### Para verificar en CE
```bash
odoo -d test_ce -i l10n_ve_invoice,l10n_ve_tax,l10n_ve_rate --stop-after-init
```

### Para verificar en EE
```bash
odoo -d test_ee -i l10n_ve_invoice,l10n_ve_tax,l10n_ve_rate --stop-after-init
```

---

## Historial de Cambios de Compatibilidad

| Fecha | Cambio | Impacto |
|-------|--------|---------|
| 2026-09-04 | Unificación CE/EE | Proyecto base creado |
