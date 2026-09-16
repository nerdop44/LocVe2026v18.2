# TRAZABILIDAD — LocVe Unificado (CE + EE)
**Proyecto:** Localización Venezolana Unificada para Odoo v18  
**Directorio raíz:** `/home/nerdop/Laboratorio/Clientes Odoo/LocVe 2026 v18.2/`  
**Estado actual:** FASE 1 — Unificación CE/EE y Documentación  
**Última actualización:** 2026-09-04  

---

## REGLAS DE SESIÓN
- Antes de cualquier acción, leer este archivo.
- Si cambia el modelo de IA, detenerse y confirmar contexto.
- No modificar código de producción sin aprobación explícita del usuario.
- Todo cambio debe registrarse aquí con fecha, descripción y archivos afectados.
- **Compatibilidad dual:** Todo cambio debe funcionar en CE Y EE.

---

## CONTEXTO DE UNIFICACIÓN

### Origen
Este proyecto nace de la unificación de dos versiones de la localización LocVe:
- **CE (Community):** `/home/nerdop/Laboratorio/Clientes Odoo/LocVe 2026 v18.2/` —Probada en Odoo 18 CE
- **EE (Enterprise):** `/home/nerdop/Laboratorio/Clientes Odoo/LocVe Fiscal 2026/LocVe/` — Probada en Odoo 18 EE

### Resultado del Análisis de Compatibilidad (2026-09-04)
Se realizó un análisis exhaustivo comparando ambos proyectos:
- **28 módulos** idénticos en ambos proyectos (manifests byte-a-byte iguales)
- **17 archivos Python** con diferencias (todas mejoras defensivas en CE)
- **5 archivos XML** con diferencias (todas mejoras visuales/permisos en CE)
- **Conclusión:** El código CE es un superset mejorado del EE. Es seguro instalar en EE.

### Diferencias Clave CE vs EE (ya resueltas en unificación)
| Diferencia | CE | EE | Riesgo |
|-----------|----|----|--------|
| `digits=(16, 4)` | Presente | No | Ninguno — más precisión |
| `round(rate, 4)` | Presente | No | Ninguno — más precisión |
| Detección tasas obsoletas `<= 10.0` | Presente | `<= 1.0` | Ninguno — más robusto |
| `if new_rate and new_rate > 0` | Presente | `> 1.0` | Ninguno — más permisivo |
| Audit groups `account.group_account_invoice` | Presente | `base.group_no_one` | Ninguno — más permisivo |

### Pendiente de Migración del EE
| # | Archivo | Mejora | Estado |
|---|---------|--------|--------|
| 1 | `l10n_ve_invoice_digital/models/account_move.py` | Fix recursión `_retry=False` | **NO APLICADO** — Temporal en VPS, se perdió al reiniciar contenedor |
| 2 | `l10n_ve_invoice_digital/models/stock_picking.py` | Fix recursión `_retry=False` + moneda VES | **NO APLICADO** — Temporal en VPS, se perdió al reiniciar contenedor |
| 3 | `l10n_ve_invoice_digital/models/account_retention.py` | Fix recursión `_retry=False` | **NO APLICADO** — Temporal en VPS, se perdió al reiniciar contenedor |
| 4 | `l10n_ve_audit/models/account_move.py` | Override `_compute_show_reset_to_draft_button` | **NO APLICADO** — No existió en ningún proyecto |

> **Nota:** Los fixes 1-3 se documentaron en `mejoras locve 010926.md` como aplicados al VPS, pero fueron temporales (volumen read-only). Verificado en VPS el 2026-09-04: los archivos no los tienen. El fix 4 nunca se implementó en ningún proyecto.

---

## HISTORIAL DE SESIONES

### SESIÓN 001 — 2026-09-04
**Modelo:** opencode/mimo-v2-free  
**Objetivo:** Análisis de compatibilidad CE/EE y creación de documentación unificada.  
**Acciones realizadas:**
- [x] Análisis exhaustivo de 28 módulos CE vs EE
- [x] Comparación de 17 archivos Python con diferencias
- [x] Comparación de 5 archivos XML con diferencias
- [x] Verificación de documentación existente (soul.md, agent.md, AGENTS.md, trazabilidad.md)
- [x] Creación de AGENTS.md unificado con reglas de compatibilidad
- [x] Creación de soul.md con identidad del agente
- [x] Creación de agent.md con checklist pre-commit
- [x] Creación de COMPATIBILITY.md con reglas detalladas CE/EE
- [x] Creación de .cerebro/ con SESSION_BRIEF.md y conocimiento.md
- [x] Creación de trazabilidad.md (este archivo)

- [x] Búsqueda y replicación de documentación del proyecto EE (soul.md, agent.md, AGENTS.md, context.md, .cerebro/, trazabilidad.md)
- [x] Creación de context.md con reglas del proyecto
- [x] Creación de .cerebro/project.json con configuración del cerebro
- [x] Creación de scripts/cerebro-close.sh para cierre de sesión
- [x] Copia de graphify-out del proyecto EE
- [x] Actualización de .cerebro/SESSION_BRIEF.md con contexto completo del EE
- [x] Actualización de .cerebro/conocimiento.md con conocimiento adquirido
- [x] Cierre de sesión y guardado de conocimiento

**Archivos creados/modificados en esta sesión:**
- `AGENTS.md` (nuevo — protocolo unificado)
- `soul.md` (nuevo — identidad del agente)
- `agent.md` (nuevo — reglas operativas)
- `COMPATIBILITY.md` (nuevo — reglas CE/EE)
- `context.md` (nuevo — contexto del proyecto)
- `trazabilidad.md` (nuevo/actualizado — este archivo)
- `.cerebro/project.json` (nuevo — configuración del cerebro)
- `.cerebro/SESSION_BRIEF.md` (nuevo — contexto de sesión replicado de EE)
- `.cerebro/conocimiento.md` (nuevo — base de conocimiento replicada de EE)
- `scripts/cerebro-close.sh` (nuevo — script de cierre)
- `graphify-out/` (copiado de EE)

**Archivos pendientes de migrar del EE:**
- `l10n_ve_invoice_digital/models/account_move.py` — Fix recursión `_retry=False`
- `l10n_ve_invoice_digital/models/stock_picking.py` — Fix recursión + moneda VES
- `l10n_ve_invoice_digital/models/account_retention.py` — Fix recursión `_retry=False`
- `l10n_ve_audit/models/account_move.py` — Override `_compute_show_reset_to_draft_button`

---

### CIERRE DE SESIÓN — 2026-09-04
**Estado:** Documentación unificada completada. Verificación en VPS confirma que los fixes documentados en `mejoras locve 010926.md` (recursión TFHKA, moneda VES) fueron temporales y se perdieron al reiniciar el contenedor (volumen read-only). Código CE, EE y VPS están sincronizados — todos sin esos fixes.
**Próximo paso:** Decidir si se aplican los fixes de TFHKA al proyecto unificado de forma permanente.

---

### SESIÓN 002 — 2026-09-16
**Objetivo:** Auditoría general "con lupa", resguardo/backup previo y solución de errores en creación de facturas SO/PO, normativas SENIAT (Providencia 0071) y parches defensivos TFHKA.
**Acciones realizadas:**
- [x] **Respaldo general del proyecto:** Creada copia de resguardo y punto de rollback con fecha de hoy en `backups/snapshot_20260916/`.
- [x] **Fix creación de facturas desde Purchase Order (PO):** En `account_dual_currency/models/purchase_order.py`, resuelta excepción `KeyError: 'invoice_line_ids'` en `action_create_invoice()` garantizando la inicialización de `invoice_line_ids` como lista en diccionarios de agrupación.
- [x] **Fix conversión histórica en Sale Order (SO):** En `account_dual_currency/models/sale_order.py`, corregido `_compute_amount_total_dif` para usar la fecha del pedido (`date_order`) en la conversión multimoneda de importes referenciales.
- [x] **Alineación con Normativa SENIAT (Providencia 0071):**
  - Mantener la prohibición legal de registar líneas con `price_unit <= 0.0`.
  - Permitir el registro cuando la línea incluya un Descuento del 100% (`discount = 100.0`), que es el mecanismo fiscal reglamentario para transferir bienes a título gratuito (obsequios, bonificaciones o muestras sin valor comercial).
  - Enriquecer el mensaje de error de `ValidationError` en `l10n_ve_invoice/models/account_move.py`, `account_dual_currency/models/account_move_line.py` y `sale_order_line.py` explicando la Providencia 0071 del SENIAT y guiando al usuario.
- [x] **Parches defensivos TFHKA (Imprenta Digital):**
  - `stock_picking.py`: Reemplazada moneda obsoleta `"VEF"` por `"VES"` y agregado parámetro `_retry=False` en `call_tfhka_api` para evitar recursión en error 401.
  - `account_move.py` (digital) y `account_retention.py`: Agregado parámetro `_retry=False` para prevención de bucles recursivos en renovaciones de token.

**Archivos modificados en esta sesión:**
- `backups/snapshot_20260916/` (nuevo — snapshot de resguardo completo)
- `account_dual_currency/models/purchase_order.py` (corregido — `KeyError: invoice_line_ids`)
- `account_dual_currency/models/sale_order.py` (corregido — conversión por `date_order`)
- `l10n_ve_invoice/models/account_move.py` (actualizado — mensaje pedagógico Providencia 0071 SENIAT + soporte `discount == 100`)
- `account_dual_currency/models/account_move_line.py` (actualizado — soporte `discount == 100` SENIAT)
- `account_dual_currency/models/sale_order_line.py` (actualizado — soporte `discount == 100` SENIAT)
- `l10n_ve_invoice_digital/models/stock_picking.py` (corregido — moneda `"VES"` + `_retry=False`)
- `l10n_ve_invoice_digital/models/account_move.py` (corregido — `_retry=False` en TFHKA)
- `l10n_ve_invoice_digital/models/account_retention.py` (corregido — `_retry=False` en TFHKA)
- `trazabilidad.md` (actualizado — este archivo)

