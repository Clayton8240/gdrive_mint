#!/usr/bin/env bash
# =============================================================================
#  GDrive Mint — Gerador de fontes pip para o Flatpak
# =============================================================================
#  Este script usa flatpak-pip-generator para converter o requirements.txt
#  num arquivo JSON de fontes que o flatpak-builder pode baixar offline.
#
#  Precisa ser executado UMA VEZ antes de fazer o build Flatpak,
#  sempre que o requirements.txt for atualizado.
#
#  Pré-requisitos:
#    pip install flatpak-pip-generator          (ou)
#    sudo apt install flatpak-builder python3-aiohttp
#
#  Uso:
#    bash packaging/flatpak/generate_sources.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
OUTPUT="${SCRIPT_DIR}/python3-requirements.json"

echo "[1/3] Verificando flatpak-pip-generator..."
if ! command -v flatpak-pip-generator &>/dev/null; then
    echo "      Instalando flatpak-pip-generator via pip..."
    pip3 install --user flatpak-pip-generator
    # Garante que ~/.local/bin está no PATH
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "[2/3] Gerando $OUTPUT ..."
flatpak-pip-generator \
    --requirements-file "$ROOT_DIR/requirements.txt" \
    --output "${SCRIPT_DIR}/python3-requirements" \
    --runtime org.freedesktop.Sdk//24.08

echo "[3/3] Concluído: $OUTPUT"
echo ""
echo "  Agora execute o build Flatpak:"
echo "    bash packaging/flatpak/build_flatpak.sh"
