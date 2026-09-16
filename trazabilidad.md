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

### SESIÓN 003 — 2026-09-16
**Objetivo:** Inicialización de `Krill Fiscal`, sincronización con `git@github.com:nerdop44/LocVe2026v18.2.git`, creación/adaptación de archivos `.md` de contexto y vinculación del entorno de Pruebas Odoo.sh (`38165808`) con el nuevo repositorio unificado.

**Acciones realizadas:**
- [x] **Clonación del Repositorio:** Sincronizado `git@github.com:nerdop44/LocVe2026v18.2.git` (HEAD `638ed65`) en la carpeta `Krill Fiscal`.
- [x] **Creación y Actualización de Archivos `.md`:**
  - `AGENTS.md` — Protocolo unificado con entornos Odoo.sh, regla Producción BLOQUEADO.
  - `context.md` — Contexto técnico Odoo 18.0, SENIAT 0071, TFHKA, SSH Pruebas.
  - `soul.md` — Identidad y misión de Antigravity en Krill Energy.
  - `agent.md` — Checklist pre-push focalizado en Pruebas (`38165808`).
  - `trazabilidad.md` — Bitácora operativa (este archivo).
  - `.cerebro/project.json` — ID `Krill_Fiscal`, rutas de Cerebro.
  - `.cerebro/SESSION_BRIEF.md` — Brief contextual completo con SSH y repos.
- [x] **Push Docs a LocVe2026v18.2/main:** Commit `3e024e2` enviado a `git@github-nerdop44:nerdop44/LocVe2026v18.2.git`.
- [x] **Diagnóstico de Divergencia Git:** Detectado que `lov18resp1/Prueba` contiene 268 commits únicos de Krill Energy. Se tomó la decisión (aprobada por Ing. Nerdo) de redirigir el submódulo del orquestador hacia `LocVe2026v18.2`, preservando `lov18resp1/Prueba` como respaldo histórico.
- [x] **Actualización del Orquestador `KE.git/Prueba`:**
  - `.gitmodules` actualizado: URL `lov18resp1.git` → `LocVe2026v18.2.git`, rama `Krill-Energy` → `main`.
  - Puntero del submódulo actualizado: `0545c0a` → `3e024e2`.
  - Commit `55de277` publicado en `KE.git/Prueba`.
  - Push a `git@github-nerdop44:nerdop44/KE.git` exitoso (`02befd7..55de277`).
- [x] **Nota Técnica:** `LocVe2026v18.2.git` es repositorio PÚBLICO, no requiere deploy key en Odoo.sh.
- [x] **Odoo.sh Prueba (`38165808`):** Trigger de redeploy activado. La plataforma Odoo.sh detectará el nuevo commit del orquestador en los próximos minutos y actualizará automáticamente el submódulo al nuevo repositorio unificado.

**Archivos modificados/creados en esta sesión:**
- `AGENTS.md`, `context.md`, `soul.md`, `agent.md` (actualizados — contexto Krill Fiscal)
- `trazabilidad.md` (este archivo — actualizado)
- `.cerebro/project.json`, `.cerebro/SESSION_BRIEF.md` (actualizados — ID `Krill_Fiscal`)
- **Repositorios Git modificados:**
  - `nerdop44/LocVe2026v18.2` rama `main` — commit `3e024e2` (docs)
  - `nerdop44/KE.git` rama `Prueba` — commit `55de277` (submódulo → LocVe2026v18.2)
- **Repositorios NO modificados (intactos):**
  - `nerdop44/lov18resp1` (todas las ramas, especialmente `Prueba` y `Produccion`)
  - `KE.git` rama `Produccion` (BLOQUEADO)

---

