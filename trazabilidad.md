# TRAZABILIDAD — Krill Fiscal (LocVe v18.2 Unificado)
**Proyecto:** Localización Venezolana Unificada para Odoo v18 — Krill Energy  
**Directorio raíz:** `/home/nerdop/Laboratorio/Clientes Odoo/Por Cimas/Krill/Krill Fiscal/`  
**Proyecto Padre:** `/home/nerdop/Laboratorio/Clientes Odoo/Por Cimas/Krill/`  
**Repositorio Git:** `git@github.com:nerdop44/LocVe2026v18.2.git`  
**Estado actual:** FASE 1 — Inicialización de Contexto, Integración en Cerebro y Staging de Pruebas  
**Última actualización:** 2026-09-16  

---

## REGLAS DE SESIÓN Y ENTORNO
- Antes de cualquier acción, leer este archivo y `.cerebro/SESSION_BRIEF.md`.
- Si cambia el modelo de IA, detenerse y confirmar contexto.
- **RESTRICCIÓN ENTORNO ODOO.SH:** Producción (`34200710`) está **ESTRICTAMENTE BLOQUEADO**. Solo trabajar en el entorno de **PRUEBAS** (`38165808`).
- Prohibido modificar archivos fuera del directorio de este proyecto sin autorización explícita del usuario.
- Todo cambio debe registrarse aquí con fecha, descripción y archivos afectados.
- **Compatibilidad dual:** Todo cambio debe funcionar en CE Y EE.

---

## CONTEXTO DE UNIFICACIÓN

### Origen
Este proyecto nace de la unificación de dos versiones de la localización LocVe:
- **CE (Community):** `/home/nerdop/Laboratorio/Clientes Odoo/LocVe 2026 v18.2/` —Probada en Odoo 18 CE
- **EE (Enterprise):** `/home/nerdop/Laboratorio/Clientes Odoo/LocVe Fiscal 2026/LocVe/` — Probada en Odoo 18 EE

### Resultado del Análisis de Compatibilidad (2026-09-04)
- **28 módulos** idénticos en ambos proyectos.
- **17 archivos Python** y **5 archivos XML** con mejoras defensivas integradas en CE.
- **Conclusión:** El código unificado v18.2 es un superset mejorado para CE y EE.

---

## HISTORIAL DE SESIONES

### SESIÓN 001 — 2026-09-04
**Modelo:** opencode/mimo-v2-free  
**Objetivo:** Análisis de compatibilidad CE/EE y creación de documentación unificada.  
**Acciones realizadas:**
- [x] Análisis exhaustivo de 28 módulos CE vs EE.
- [x] Comparación de 17 archivos Python y 5 XML con diferencias.
- [x] Creación de `AGENTS.md`, `soul.md`, `agent.md`, `COMPATIBILITY.md`, `context.md` y `.cerebro/`.

---

### SESIÓN 002 — 2026-09-16
**Objetivo:** Auditoría general "con lupa", resguardo/backup previo y solución de errores en creación de facturas SO/PO, normativas SENIAT (Providencia 0071) y parches defensivos TFHKA.  
**Acciones realizadas:**
- [x] **Respaldo general del proyecto:** Snapshot en `backups/snapshot_20260916/`.
- [x] **Fix creación de facturas desde Purchase Order (PO):** En `account_dual_currency/models/purchase_order.py`, resuelta excepción `KeyError: 'invoice_line_ids'`.
- [x] **Fix conversión histórica en Sale Order (SO):** En `account_dual_currency/models/sale_order.py`, corregido `_compute_amount_total_dif` usando `date_order`.
- [x] **Alineación con Normativa SENIAT (Providencia 0071):** Permitir registro de líneas con `discount = 100.0` para muestras/bonificaciones a título gratuito.
- [x] **Parches defensivos TFHKA (Imprenta Digital):** Moneda `"VES"`, parámetro `_retry=False` para prevención de bucles recursivos 401 en `stock_picking.py`, `account_move.py` y `account_retention.py`.

---

### SESIÓN 003 — 2026-09-16
**Objetivo:** Inicialización de `Krill Fiscal`, sincronización con `git@github.com:nerdop44/LocVe2026v18.2.git`, creación/adaptación de archivos `.md` de contexto y definición de protocolo de pruebas Odoo.sh.  
**Acciones realizadas:**
- [x] **Clonación del Repositorio:** Sincronizado `git@github.com:nerdop44/LocVe2026v18.2.git` en la carpeta `/home/nerdop/Laboratorio/Clientes Odoo/Por Cimas/Krill/Krill Fiscal`.
- [x] **Creación y Actualización de Archivos `.md`:**
  - `AGENTS.md`: Protocolo unificado, jerarquía de contexto, regla de cautela para Producción y foco exclusivo en entorno de Pruebas (`38165808`).
  - `context.md`: Contexto técnico, multimoneda dual, normativas SENIAT 0071, TFHKA y especificaciones de Odoo.sh Pruebas.
  - `soul.md`: Misión e identidad de Antigravity como compañero de par-programming del Ing. Nerdo José Pulido Aguirre.
  - `agent.md`: Checklist pre-push y reglas de ejecución operativa.
  - `trazabilidad.md`: Actualizada esta bitácora con la Sesión 003.
  - `.cerebro/project.json` y `.cerebro/SESSION_BRIEF.md`: Actualizados con la identidad del proyecto `Krill_Fiscal` y rutas del laboratorio.
- [x] **Auditoría de Entornos SSH de Odoo.sh:** Confirmada conectividad y estructura en Prueba (`38165808`) y Producción (`34200710`), dejando este último **bloqueado de forma preventiva**.

**Archivos modificados/creados en esta sesión:**
- `AGENTS.md` (actualizado)
- `context.md` (actualizado)
- `soul.md` (actualizado)
- `agent.md` (actualizado)
- `trazabilidad.md` (este archivo — actualizado)
- `.cerebro/project.json` (actualizado)
- `.cerebro/SESSION_BRIEF.md` (actualizado)
