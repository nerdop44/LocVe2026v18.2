# SESSION_BRIEF.md — Contexto del Cerebro para el Agente (Krill Fiscal)

> **LEE ESTE ARCHIVO COMPLETO ANTES DE CUALQUIER ACCIÓN.**

---

## Identidad del Proyecto

- **ID Cerebro**: Krill_Fiscal
- **Proyecto**: Krill Fiscal — Localización Venezolana Odoo 18 Unificada (CE + EE)
- **Ruta Laboratorio**: Clientes Odoo/Por Cimas/Krill/Krill Fiscal
- **Proyecto Padre**: Clientes Odoo/Por Cimas/Krill
- **Congelado**: No
- **Compatibilidad**: Odoo 18 CE **Y** Odoo 18 EE
- **Repositorio Oficial**: `git@github.com:nerdop44/LocVe2026v18.2.git`
- **SSH Entorno Pruebas (Permitido)**: `ssh 38165808@krillenergy-prueba-38165808.dev.odoo.com`
- **SSH Entorno Producción (DELICADO / Bloqueado)**: `ssh 34200710@krillenergy.odoo.com`

## Resumen Declarativo

modelo_odoo: "Krill Fiscal — LocVe Unificado (CE + EE)"
version_odoo: "18.0.2.0.x"
tipo_desarrollo: "herencia / localización fiscal completa venezuela"
id_cliente_origen: "Clientes Odoo/Por Cimas/Krill/Krill Fiscal"
nivel_madurez_temporal: "Alta"
criterio_congelado_desarrollador: FALSE
fecha_indexacion: "2026-09-16"
total_modulos: 28

## Resumen

Proyecto de localización venezolana v18.2 para **Krill Energy (`Krill Fiscal`)** con compatibilidad dual CE/EE. Contiene **28 módulos** organizados en una suite completa que cubre:

- Contabilidad bimonetaria (USD/VES) con tasas BCV dinámicas y blindaje de tasa en SO/PO
- Retenciones fiscales (IVA, ISLR, Municipal, IGTF) con flujo de intermediación
- POS (punto de venta) con doble moneda, impresión fiscal HKA y vendedor
- Nómina venezolana
- Facturación con correlativo fiscal SENIAT y soporte a muestras gratuitas con 100% descuento (Providencia 0071)
- Facturación Digital en la Nube vía API REST TFHKA con parámetros defensivos contra recursión 401 (`_retry=False`)
- Cierre de año fiscal con motor dedicado y wizard de revaluación cambiaria
- Reportes multi-moneda contables

### Módulos Principales

| Módulo | Nombre | Versión |
|---|---|---|
| account_dual_currency | Doble Moneda Venezuela | 18.0.2.0.29 |
| l10n_ve_tax | Impuestos Venezuela (IVA/SENIAT) | 18.0.2.0.23 |
| l10n_ve_payment_extension | Retenciones Venezuela | 18.0.2.0.31 |
| l10n_ve_invoice | Facturación Venezuela | 18.0.2.0.33 |
| l10n_ve_invoice_digital | Facturación Digital TFHKA | 18.0.2.0.23 |
| l10n_ve_igtf | IGTF | 18.0.2.0.6 |
| l10n_ve_rate | Tasa de Cambio BCV | 18.0.2.0.0 |
| l10n_ve_audit | Auditoría Fiscal SENIAT | 18.0.1.0.2 |
| l10n_ve_payroll | Nómina Venezuela | 18.0.2.0.0 |

### Estado del Proyecto

- **Fase actual**: FASE 1 — Inicialización de Contexto, Integración en Cerebro y Staging de Pruebas
- **Última sesión registrada**: 2026-09-16 (Sesión 003 — COMPLETADA)
- **Logros clave**: Creación y adaptación de archivos `.md` (`AGENTS.md`, `context.md`, `soul.md`, `agent.md`, `trazabilidad.md`, `.cerebro/`), configuración de políticas de entorno (Producción bloqueado, Pruebas activo).
- **Próximo paso**: Sincronización de remotos Git e implementación de pruebas en Odoo.sh Pruebas (`38165808`).

## Referencia al Código Fuente

@[Clientes Odoo/Por Cimas/Krill/Krill Fiscal/]

## Trazabilidad

Archivo de trazabilidad local: trazabilidad.md

## Checklist Obligatorio del Agente

Antes de cualquier acción, verifica:

- [ ] **Leí este brief completo** (SESSION_BRIEF.md)
- [ ] **Conozco el ID del proyecto** (`Krill_Fiscal`) y su estado (activo)
- [ ] **Sé que Producción (`34200710`) está BLOQUEADO** y solo se trabaja en Pruebas (`38165808`)
- [ ] **Aislamiento**: No modificaré ningún archivo fuera de la carpeta de este proyecto sin autorización
- [ ] **Prohibido browser_subagent** — no iniciaré navegadores automáticos
- [ ] **Revisé COMPATIBILITY.md** antes de modificar código

### Regla de Cambio de Modelo
Si mi identificador de modelo cambia durante esta sesión:
> "He cambiado de modelo por cuota. Por favor, indícame si debo leer la trazabilidad."
> NO realizar ninguna edición antes de este paso.

### Regla de Dual Compatibility
TODO código nuevo debe funcionar en CE y EE. No hay excepciones.
