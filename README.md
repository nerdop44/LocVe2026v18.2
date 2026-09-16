# LocVe 2026 v18.2 — Localización Venezolana para Odoo 18 (CE & EE)

**Desarrollador / Autor Principal:** Ing. Nerdo José Pulido Aguirre  
**Organización:** INVERPA  
**Versión:** 18.0.2.0.x (Unificada)  
**Compatibilidad:** Odoo 18 Community Edition (CE) **Y** Odoo 18 Enterprise Edition (EE)  
**Cumplimiento Fiscal:** Normativas SENIAT (Providencia 0071), Facturación Digital TFHKA, Retenciones IVA/ISLR/Municipal e IGTF.

---

## 🚀 Descripción General

**LocVe 2026** es la suite unificada y completa de localización fiscal venezolana para Odoo 18, diseñada y desarrollada por el **Ing. Nerdo José Pulido Aguirre** (INVERPA). Ofrece compatibilidad dual transparente para instalaciones en Community Edition y Enterprise Edition.

### 📦 Módulos Principales de la Suite

| Módulo | Nombre Técnico | Descripción |
|---|---|---|
| **Doble Moneda** | `account_dual_currency` | Motor de contabilidad bimonetaria (USD/VES) a tasa BCV dinámica con preservación de precios pactados. |
| **Impuestos SENIAT** | `l10n_ve_tax` | Configuración de impuestos nacionales (IVA 16%, 8%, 31%, Exento). |
| **Facturación Fiscal** | `l10n_ve_invoice` | Control de nro. de control/correlativo fiscal y cumplimiento estricto de Providencia 0071. |
| **Imprenta Digital TFHKA** | `l10n_ve_invoice_digital` | Emisión e integración en la nube con API REST de The Factory HKA (Facturas, N/C, N/D, Guías). |
| **Retenciones Fiscales** | `l10n_ve_payment_extension` | Emisión, cálculo y comprobantes de retención IVA (75%/100%), ISLR y Municipal. |
| **IGTF** | `l10n_ve_igtf` | Cálculo y retención del Impuesto a las Grandes Transacciones Financieras (IGTF 3%). |
| **Tasa BCV** | `l10n_ve_rate` | Sincronización automática de tasa de cambio oficial del Banco Central de Venezuela. |
| **POS Fiscal & Bimonetario** | `pos_fiscal_printer`, `pos_show_dual_currency` | Integración de Punto de Venta con impresoras fiscales HKA-NG y despliegue bimonetario. |
| **Nómina Venezuela** | `l10n_ve_payroll` | Adaptación de recibos y reglas salariales conforme a la LOTTT. |
| **Auditoría SENIAT** | `l10n_ve_audit` | Perfil de fiscalización y auditoría fiscal SENIAT. |

---

## ⚙️ Reglas de Compatibilidad y Arquitectura

1. **Dualidad CE/EE Obligatoria:** Todos los módulos funcionan nativamente en Odoo Community y Enterprise.
2. **Precisión Decimal:** Campos Float de tasa de cambio con `digits=(16, 4)` y redondeos a 4 decimales (`round(x, 4)`).
3. **Facturación Digital (TFHKA):**
   - Moneda: `"VES"`
   - Hora: Formato 12h `%I:%M:%S %p` (minúsculas).
   - Resiliencia: `_retry=False` en peticiones para evitar bucles recursivos en renovaciones de token.
4. **Providencia 0071 SENIAT:** Prohibición estricta de ítems a precio unitario 0.0. Las bonificaciones u obsequios se procesan conservando el precio de lista de referencia (`price_unit > 0.0`) y aplicando **Descuento del 100% (`discount = 100.0`)**.

---

## 📜 Licencia y Créditos

- **Autor / Arquitecto:** Ing. Nerdo José Pulido Aguirre
- **Organización:** INVERPA
- **Licencia:** LGPL-3 / Proprietary
