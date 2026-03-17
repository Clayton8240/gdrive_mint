#!/usr/bin/env bash
# =============================================================================
#  GDrive Mint — Gerar instaladores para usuários finais
# =============================================================================
#  Constrói o pacote .deb e o executável universal (AppImage) e os coloca em Instaladores/
#  com nomes simples e claros.
#
#  Pré-requisitos (instalar uma vez):
#    sudo apt install dpkg-dev fakeroot rsync
#    python3 -m pip install pyinstaller   # ou instalar no venv
#
#  Uso:
#    bash gerar_instaladores.sh               # gera .deb + executável universal
#    bash gerar_instaladores.sh --so deb      # apenas .deb
#    bash gerar_instaladores.sh --so appimage # apenas executável universal
# =============================================================================

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${ROOT_DIR}/Instaladores"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
info()  { echo -e "${GREEN}[✓]${NC} $1"; }
step()  { echo -e "\n${BOLD}>>> $1${NC}"; }
error() { echo -e "${RED}[✗] ERRO:${NC} $1"; exit 1; }

BUILD_DEB=true
BUILD_APPIMAGE=true

while [[ $# -gt 0 ]]; do
    case "$1" in
        --so)
            case "$2" in
                deb)      BUILD_APPIMAGE=false ;;
                appimage) BUILD_DEB=false ;;
                *) error "Valor inválido para --so: '$2'. Use 'deb' ou 'appimage'." ;;
            esac
            shift 2 ;;
        --help|-h)
            echo "Uso: $0 [--so deb|appimage]"
            exit 0 ;;
        *) error "Opção desconhecida: $1" ;;
    esac
done

mkdir -p "$DEST"

echo ""
echo "╔════════════════════════════════════════════════════╗"
echo "║        GDrive Mint — Gerador de Instaladores       ║"
echo "║     Os arquivos serão salvos em: Instaladores/     ║"
echo "╚════════════════════════════════════════════════════╝"

# ── .deb ──────────────────────────────────────────────────────────────────
if $BUILD_DEB; then
    step "Construindo instalador para Linux Mint / Ubuntu (.deb)..."

    for cmd in dpkg-deb fakeroot rsync; do
        command -v "$cmd" &>/dev/null || \
            error "'$cmd' não encontrado. Execute: sudo apt install dpkg-dev fakeroot rsync"
    done

    bash "${ROOT_DIR}/packaging/build_deb.sh"
    info "Instalador .deb pronto: Instaladores/GDrive-Mint-Linux-Mint.deb"
fi

# ── AppImage (universal) ─────────────────────────────────────────────────────
if $BUILD_APPIMAGE; then
    step "Construindo instalador universal (AppImage)..."

    if [[ ! -d "${ROOT_DIR}/.venv" ]]; then
        python3 -m venv "${ROOT_DIR}/.venv"
    fi
    "${ROOT_DIR}/.venv/bin/pip" install -q -r "${ROOT_DIR}/requirements.txt"
    "${ROOT_DIR}/.venv/bin/pip" install -q pyinstaller

    bash "${ROOT_DIR}/packaging/build_appimage.sh"
    info "Instalador universal pronto: Instaladores/GDrive-Mint-Universal"
fi

# ── Resumo ─────────────────────────────────────────────────────────────────
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  Instaladores gerados em: Instaladores/                        ║"
echo "╠════════════════════════════════════════════════════════════════╣"

if $BUILD_DEB && [[ -f "${DEST}/GDrive-Mint-Linux-Mint.deb" ]]; then
    SIZE=$(du -sh "${DEST}/GDrive-Mint-Linux-Mint.deb" | awk '{print $1}')
    printf "║  %-55s║\n" "GDrive-Mint-Linux-Mint.deb  ($SIZE)"
fi
if $BUILD_APPIMAGE && [[ -f "${DEST}/GDrive-Mint-Universal" ]]; then
    SIZE=$(du -sh "${DEST}/GDrive-Mint-Universal" | awk '{print $1}')
    printf "║  %-55s║\n" "GDrive-Mint-Universal  ($SIZE)"
fi

echo "╠════════════════════════════════════════════════════════════════╣"
echo "║  Leia Instaladores/COMO_INSTALAR.md para instruções simples.   ║"
echo "╔════════════════════════════════════════════════════════════════╝"
echo "║  Para publicar uma release oficial no GitHub:                   ║"
echo "║   1. Atualize a versão em packaging/build_deb.sh               ║"
echo "║   2. Atualize o CHANGELOG.md                                   ║"
echo "║   3. git tag v1.2.0 && git push origin v1.2.0                  ║"
echo "║   O GitHub Actions irá construir e publicar os instaladores.    ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
