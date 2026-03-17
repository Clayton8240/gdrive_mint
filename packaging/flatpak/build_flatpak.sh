#!/usr/bin/env bash
# =============================================================================
#  GDrive Mint — Build Flatpak
# =============================================================================
#  Constrói e instala o Flatpak localmente para testes.
#
#  Pré-requisitos:
#    sudo apt install flatpak flatpak-builder
#    flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
#    flatpak install flathub org.freedesktop.Platform//24.08 org.freedesktop.Sdk//24.08
#    flatpak install flathub org.freedesktop.Sdk.Extension.python312//24.08
#
#  Uso:
#    bash packaging/flatpak/build_flatpak.sh [--install] [--bundle]
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
APP_ID="io.github.gdrivemint.GDriveMint"
MANIFEST="${SCRIPT_DIR}/${APP_ID}.yml"
BUILD_DIR="${SCRIPT_DIR}/.flatpak-build"
REPO_DIR="${SCRIPT_DIR}/.flatpak-repo"
# Saída com nome simples para o usuário final
INSTALADORES_DIR="${ROOT_DIR}/Instaladores"
mkdir -p "$INSTALADORES_DIR"
        --install) DO_INSTALL=true; shift ;;
        --bundle)  DO_BUNDLE=true;  shift ;;
        --help|-h)
            echo "Uso: $0 [--install] [--bundle]"
            echo "  --install  Instala o Flatpak no sistema após o build"
            echo "  --bundle   Gera um arquivo .flatpak para distribuição"
            exit 0 ;;
        *) echo "[ERRO] Opção desconhecida: $1"; exit 1 ;;
    esac
done

echo "[GDrive Mint] Verificando python3-requirements.json..."
if [[ ! -f "${SCRIPT_DIR}/python3-requirements.json" ]]; then
    echo "  ⚠  Arquivo de fontes pip não encontrado."
    echo "  Execute primeiro: bash packaging/flatpak/generate_sources.sh"
    exit 1
fi

echo "[GDrive Mint] Construindo Flatpak..."
flatpak-builder \
    --force-clean \
    --repo="$REPO_DIR" \
    "$BUILD_DIR" \
    "$MANIFEST"

if $DO_INSTALL; then
    echo "[GDrive Mint] Instalando para o usuário atual..."
    flatpak --user remote-add --no-gpg-verify --if-not-exists \
        gdrive-mint-local "$REPO_DIR"
    flatpak --user install --reinstall -y gdrive-mint-local "$APP_ID"
    echo "  Instalado! Execute: flatpak run $APP_ID"
fi

if $DO_BUNDLE; then
    BUNDLE="${INSTALADORES_DIR}/GDrive-Mint-Universal.flatpak"
    echo "[GDrive Mint] Gerando bundle $BUNDLE ..."
    flatpak build-bundle "$REPO_DIR" "$BUNDLE" "$APP_ID"
    SIZE=$(du -sh "$BUNDLE" | awk '{print $1}')
    echo "  Bundle gerado: $BUNDLE ($SIZE)"
    echo "  Para instalar: flatpak install --user $BUNDLE"
fi

echo ""
echo "[GDrive Mint] Build concluído."
