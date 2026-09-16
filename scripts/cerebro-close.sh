#!/bin/bash
# ==============================================================================
# cerebro-close.sh (LocVe Unificado) — Wrapper de cierre de sesion del
# ecosistema Cerebros Odoo, adaptado para el proyecto LocVe 2026 v18.2.
#
# Delega el cierre real al script del ecosistema (graphify + trazabilidad +
# brief), pero evita el bloqueo del paso de sync.
# ==============================================================================
set -e

PROJECT="LocVe_2026_v18.2"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# --- Resolver CEREBRO_ROOT ---
CEREBRO_ROOT="${CEREBRO_ROOT:-$HOME/Cerebros Odoo}"
if [ ! -d "$CEREBRO_ROOT" ]; then
    echo "Error: no se encontro CEREBRO_ROOT en '$CEREBRO_ROOT'."
    echo "  Configuralo con: export CEREBRO_ROOT=\"/ruta/a/Cerebros Odoo\""
    exit 1
fi

CLOSE_SCRIPT="$CEREBRO_ROOT/scripts/cerebro-close.sh"
MANIFEST="$CEREBRO_ROOT/cerebro_manifest.json"

# --- Help ---
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Uso: cerebro-close.sh"
    echo ""
    echo "Cierra la sesion de $PROJECT delegando al ecosistema Cerebros Odoo:"
    echo "  - Regenera el grafo (graphify)"
    echo "  - Actualiza la trazabilidad local"
    echo "  - Regenera SESSION_BRIEF.md"
    echo ""
    echo "Variables: CEREBRO_ROOT (por defecto: ~/Cerebros Odoo)"
    exit 0
fi

# --- Validaciones ---
if [ ! -f "$CLOSE_SCRIPT" ]; then
    echo "Error: no se encontro '$CLOSE_SCRIPT'."
    echo "  El ecosistema Cerebros Odoo no esta completo en '$CEREBRO_ROOT'."
    exit 1
fi

if [ ! -f "$MANIFEST" ]; then
    echo "Error: no se encontro el manifiesto '$MANIFEST'."
    exit 1
fi

if ! python3 -c "import json; m=json.load(open('$MANIFEST')); assert '$PROJECT' in m" 2>/dev/null; then
    echo "Error: el proyecto '$PROJECT' no esta registrado en el manifiesto Cerebros."
    exit 1
fi

# --- Verificar daemon de sync ---
SYNC_DAEMON="$(pgrep -f "CerebroSync.sh" | head -1 || true)"
if [ -n "$SYNC_DAEMON" ]; then
    echo "  Daemon CerebroSync ya activo (PID $SYNC_DAEMON); sync en segundo plano."
else
    echo "  No se detecto el daemon CerebroSync; el sync no se ejecutara."
fi

echo ""
echo "=== Cerebro Close (wrapper LocVe Unificado) ==="
echo "  Proyecto  : $PROJECT"
echo "  Ecosistema: $CEREBRO_ROOT"
echo "  Delegando pasos 1-3 al script original (graphify + trazabilidad + brief)..."
echo ""

# --- Ejecutar el cierre del ecosistema en su propio grupo de procesos ---
TIMEOUT_S="${CLOSE_TIMEOUT_S:-300}"
LOG_FILE="$(mktemp)"
setsid bash "$CLOSE_SCRIPT" "$PROJECT" > "$LOG_FILE" 2>&1 &
CLOSE_PID=$!

# --- Vigilar el grupo: esperar hasta que no queden procesos del grupo ---
CLOSE_GROUP="-${CLOSE_PID}"
START_TS=$(date +%s)
while kill -0 "$CLOSE_PID" 2>/dev/null; do
    NOW_TS=$(date +%s)
    if [ $((NOW_TS - START_TS)) -ge "$TIMEOUT_S" ]; then
        echo "  Timeout tras ${TIMEOUT_S}s en el paso 4 (sync infinito)."
        kill -TERM -- "$CLOSE_GROUP" 2>/dev/null || true
        sleep 2
        kill -KILL -- "$CLOSE_GROUP" 2>/dev/null || true
        break
    fi
    sleep 2
done

# --- Mostrar la salida del cierre (pasos 1-3) ---
cat "$LOG_FILE"
rm -f "$LOG_FILE"

# --- Estado final ---
if ! kill -0 "$CLOSE_PID" 2>/dev/null; then
    echo ""
    echo "  Pasos 1-3 completados (graphify + trazabilidad + brief)."
    echo "  El sync continua via el daemon CerebroSync en segundo plano."
else
    echo ""
    echo "  El cierre termino de forma inesperada."
fi

echo ""
echo "=== Cierre finalizado para $PROJECT ==="
echo ""
