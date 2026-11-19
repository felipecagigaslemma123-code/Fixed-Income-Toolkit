#!/bin/zsh

# Iniciador local para macOS. Busca un Python compatible sin modificar el
# entorno virtual existente y abre el panel DLR en Google Chrome.

set -u

TOOLKIT_ROOT="${0:A:h}"
cd "$TOOLKIT_ROOT" || exit 1

PYTHON_CANDIDATES=(
  ".venv/bin/python"
  "python3.12"
  "python3.11"
  "python3.10"
  "python3.9"
  "python3"
)

for candidate in "${PYTHON_CANDIDATES[@]}"; do
  if [[ "$candidate" == */* ]]; then
    resolved="$candidate"
    [[ -x "$resolved" ]] || continue
  else
    resolved="$(command -v "$candidate" 2>/dev/null)"
    [[ -n "$resolved" ]] || continue
  fi

  if "$resolved" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
    exec "$resolved" tools/run_futures_toolkit.py
  fi
done

echo "No se encontró Python 3.9 o superior."
echo "El panel no fue iniciado y ningún dato fue modificado."
echo "Presioná Enter para cerrar."
read
exit 2
