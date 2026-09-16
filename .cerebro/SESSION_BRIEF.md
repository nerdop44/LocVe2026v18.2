# SESSION_BRIEF.md — Contexto del Cerebro para el Agente

> **LEE ESTE ARCHIVO COMPLETO ANTES DE CUALQUIER ACCIÓN.**

---

## Identidad del Proyecto

- **ID Cerebro**: LocVe_2026_v18.2
- **Proyecto**: LocVe Unificado (CE + EE) — Localización Venezolana para Odoo 18
- **Ruta Laboratorio**: Clientes Odoo/LocVe 2026 v18.2
- **Congelado**: No
- **Compatibilidad**: Odoo 18 CE **Y** Odoo 18 EE

## Resumen Declarativo

modelo_odoo: "LocVe Unificado (CE + EE)"
version_odoo: "18.0.2.0.x"
tipo_desarrollo: "herencia / localizacion fiscal completa"
id_cliente_origen: "Clientes Odoo/LocVe 2026 v18.2"
nivel_madurez_temporal: "Alta"
criterio_congelado_desarrollador: FALSE
fecha_indexacion: "2026-09-04"
total_modulos: 28

## Resumen

Proyecto unificado de localizacion venezolana para Odoo v18 con compatibilidad dual CE/EE. Contiene **28 modulos** organizados en una suite completa que cubre:

- Contabilidad bimonetaria (USD/VES) con tasas BCV dinamicas
- Retenciones fiscales (IVA, ISLR, Municipal, IGTF) con flujo de intermediacion
- POS (punto de venta) con doble moneda, impresion fiscal HKA y vendedor
- Nomina venezolana
- Facturacion con correlativo fiscal SENIAT
- Facturacion Digital en la Nube via API REST TFHKA
- Cierre de anio fiscal con motor dedicado y wizard de revaluacion cambiaria
- Reportes multi-moneda contables

### Modulos Principales

| Modulo | Nombre | Version |
|---|---|---|
| account_dual_currency | Doble Moneda Venezuela | 18.0.2.0.29 |
| l10n_ve_tax | Impuestos Venezuela (IVA/SENIAT) | 18.0.2.0.23 |
| l10n_ve_payment_extension | Retenciones Venezuela | 18.0.2.0.31 |
| l10n_ve_invoice | Facturacion Venezuela | 18.0.2.0.33 |
| l10n_ve_invoice_digital | Facturacion Digital TFHKA | 18.0.2.0.23 |
| l10n_ve_igtf | IGTF | 18.0.2.0.6 |
| l10n_ve_rate | Tasa de Cambio BCV | 18.0.2.0.0 |
| l10n_ve_audit | Auditoria Fiscal SENIAT | 18.0.1.0.2 |
| l10n_ve_payroll | Nomina Venezuela | 18.0.2.0.0 |

### Estado del Proyecto

- **Fase actual**: FASE 1 — Unificacion CE/EE, Estabilización y Documentación
- **Ultima sesion registrada**: 2026-09-16 (Sesion 002 — COMPLETADA)
- **Logros clave**: Resguardo general realizado en `backups/snapshot_20260916/`, fix `KeyError: invoice_line_ids` en facturas desde PO, alineación de validaciones con Providencia 0071 SENIAT (descuento 100% para muestras/bonificaciones) y parches defensivos TFHKA (`_retry=False`, moneda `"VES"`).
- **Proximo paso**: Pruebas funcionales integrales de emisión fiscal y retenciones.

## Referencia al Codigo Fuente

@[Clientes Odoo/LocVe 2026 v18.2/]

## Trazabilidad

Archivo de trazabilidad local: trazabilidad.md

## Mapa Estructural (Graphify)

- **Generado**: 2026-09-04 (modo code-only, AST local)
- **Estadisticas**: 10,299 nodos | 11,938 aristas | 1,098 comunidades
- **Archivos analizados**: 1,973 archivos de codigo

## Conocimiento Adquirido

Ver .cerebro/conocimiento.md

## Checklist Obligatorio del Agente

Antes de cualquier accion, verifica:

- [ ] **Lei este brief completo** (SESSION_BRIEF.md)
- [ ] **Conozco el ID del proyecto** y su estado (congelado/activo)
- [ ] **Si hay trazabilidad**, la memoria reciente esta presente
- [ ] **Aislamiento**: No usare informacion de otros proyectos
- [ ] **Prohibido browser_subagent** — no iniciare navegadores automaticos
- [ ] **Si aprendi algo nuevo**, lo capturare antes de cerrar
- [ ] **Revisé COMPATIBILITY.md** antes de modificar codigo

### Regla de Cambio de Modelo
Si mi identificador de modelo cambia durante esta sesion:
> "He cambiado de modelo por cuota. Por favor, indiqueme si debo leer la trazabilidad."
> NO realizar ninguna edicion antes de este paso.

### Regla de Congelado
Si congelado: true, tengo PROHIBIDO editar codigo sin aprobacion explicita del usuario.

### Regla de Dual Compatibility
TODO codigo nuevo debe funcionar en CE y EE. No hay excepciones.
Ver COMPATIBILITY.md para reglas detalladas.
