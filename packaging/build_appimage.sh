#!/usr/bin/env bash
# =============================================================================
#  GDrive Mint — Gerador de AppImage (instalador universal para Linux)
# =============================================================================
#  Cria um executável portátil que funciona em qualquer distribuição Linux.
#  O usuário não precisa instalar nada: basta dar permissão e executar.
#
#  Pré-requisitos (apenas python3-tk do sistema):
#    sudo apt install python3-tk
#
#  Uso:
#    bash packaging/build_appimage.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
DEST="${ROOT_DIR}/Instaladores"
BUILD_WORK="${SCRIPT_DIR}/appimage_work"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
step()  { echo -e "\n${GREEN}[$1]${NC} $2"; }
error() { echo -e "${RED}[✗] ERRO:${NC} $1"; exit 1; }

VENV="${ROOT_DIR}/.venv"
PYINSTALLER="${VENV}/bin/pyinstaller"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   GDrive Mint — Build AppImage           ║"
echo "║   Instalador universal para Linux        ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── Pré-requisitos ─────────────────────────────────────────────────────────
[[ -f "$PYINSTALLER" ]] || error "PyInstaller não encontrado em $PYINSTALLER. Execute: .venv/bin/pip install pyinstaller"
python3 -c "import tkinter" 2>/dev/null || error "python3-tk não instalado. Execute: sudo apt install python3-tk"

# ── Limpa build anterior ───────────────────────────────────────────────────
step "1/4" "Limpando build anterior..."
rm -rf "${ROOT_DIR}/build" "${ROOT_DIR}/dist" "${BUILD_WORK}"
mkdir -p "$DEST"

# ── Coleta dados de assets do CustomTkinter ───────────────────────────────
step "2/4" "Coletando assets do CustomTkinter e Pillow..."
CTK_PATH=$("${VENV}/bin/python3" -c "import customtkinter; import os; print(os.path.dirname(customtkinter.__file__))")
PILLOW_PATH=$("${VENV}/bin/python3" -c "import PIL; import os; print(os.path.dirname(PIL.__file__))")

info "CustomTkinter: $CTK_PATH"
info "Pillow: $PILLOW_PATH"

# ── PyInstaller ────────────────────────────────────────────────────────────
step "3/4" "Empacotando com PyInstaller (pode demorar 2–5 min)..."

cd "$ROOT_DIR"

"${VENV}/bin/pyinstaller" \
    --noconfirm \
    --onefile \
    --windowed \
    --name "GDrive-Mint-Universal" \
    --add-data "${CTK_PATH}:customtkinter" \
    --add-data "${PILLOW_PATH}:PIL" \
    --add-data "app:app" \
    --hidden-import "PIL._tkinter_finder" \
    --hidden-import "customtkinter" \
    --hidden-import "pystray._xorg" \
    --hidden-import "google.auth.transport.requests" \
    --hidden-import "google_auth_oauthlib.flow" \
    --hidden-import "googleapiclient.discovery" \
    --hidden-import "watchdog.observers" \
    --hidden-import "watchdog.observers.inotify" \
    --hidden-import "cryptography.fernet" \
    --hidden-import "plyer.platforms.linux.notification" \
    --collect-all "customtkinter" \
    --strip \
    main.py 2>&1

BINARY="${ROOT_DIR}/dist/GDrive-Mint-Universal"
[[ -f "$BINARY" ]] || error "Build falhou — binário não encontrado em dist/"

# ── Copia para Instaladores/ ───────────────────────────────────────────────
step "4/4" "Copiando para Instaladores/..."
cp "$BINARY" "${DEST}/GDrive-Mint-Universal"
chmod +x "${DEST}/GDrive-Mint-Universal"
SIZE=$(du -sh "${DEST}/GDrive-Mint-Universal" | awk '{print $1}')

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  AppImage criado com sucesso!                                ║"
echo "╠══════════════════════════════════════════════════════════════╣"
printf "║  Arquivo : %-51s║\n" "Instaladores/GDrive-Mint-Universal"
printf "║  Tamanho : %-51s║\n" "$SIZE"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Como usar:                                                  ║"
echo "║    chmod +x GDrive-Mint-Universal                            ║"
echo "║    ./GDrive-Mint-Universal                                   ║"
echo "║  Ou clique duas vezes no Gerenciador de Arquivos.            ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
