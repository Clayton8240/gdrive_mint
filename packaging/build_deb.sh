#!/usr/bin/env bash
# =============================================================================
#  GDrive Mint — Gerador de pacote .deb
# =============================================================================
#  Cria um pacote .deb instalável para Linux Mint / Ubuntu 22.04+.
#  O app é instalado em /opt/gdrive-mint/; as dependências Python são
#  instaladas num venv isolado durante o postinst (após dpkg instalar).
#
#  Pré-requisitos:
#    sudo apt install dpkg-dev fakeroot rsync
#
#  Uso:
#    bash packaging/build_deb.sh
#    bash packaging/build_deb.sh --version 1.2.0 --arch amd64
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# ── Configurações do pacote ────────────────────────────────────────────────
PKG_NAME="gdrive-mint"
VERSION="1.1.0"
ARCH="amd64"
MAINTAINER="Clayton <https://github.com/Clayton8240>"
HOMEPAGE="https://github.com/Clayton8240/gdrive_mint"
INSTALL_DIR="/opt/gdrive-mint"
DESCRIPTION="Cliente Google Drive para Linux Mint com interface gráfica"
LONG_DESCRIPTION="GDrive Mint é um cliente Google Drive moderno construído com CustomTkinter.
 Suporta sincronização bidirecional, monitoramento em tempo real via watchdog,
 bandeja do sistema (pystray) e notificações nativas (notify-send) para
 Linux Mint e Ubuntu."

# ── Parse de argumentos ────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --version) VERSION="$2"; shift 2 ;;
        --arch)    ARCH="$2";    shift 2 ;;
        --help|-h)
            echo "Uso: $0 [--version X.Y.Z] [--arch amd64|arm64]"
            exit 0 ;;
        *) echo "[ERRO] Opção desconhecida: $1"; exit 1 ;;
    esac
done

PKG_FULL="${PKG_NAME}_${VERSION}_${ARCH}"
STAGING="${SCRIPT_DIR}/staging/${PKG_FULL}"
# Saída com nome simples para o usuário final
INSTALADORES_DIR="${ROOT_DIR}/Instaladores"
mkdir -p "$INSTALADORES_DIR"
OUTPUT="${INSTALADORES_DIR}/GDrive-Mint-Linux-Mint.deb"

# ── Cores ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
step()  { echo -e "\n${GREEN}[$1]${NC} $2"; }
error() { echo -e "${RED}[✗] ERRO:${NC} $1"; exit 1; }

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║       GDrive Mint — Build .deb           ║"
echo "╠══════════════════════════════════════════╣"
printf "║  Versão : %-31s║\n" "$VERSION"
printf "║  Arch   : %-31s║\n" "$ARCH"
printf "║  Saída  : %-31s║\n" "${PKG_FULL}.deb"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── Pré-requisitos ─────────────────────────────────────────────────────────
for cmd in dpkg-deb fakeroot rsync find md5sum; do
    command -v "$cmd" &>/dev/null || \
        error "'$cmd' não encontrado. Execute: sudo apt install dpkg-dev fakeroot rsync"
done

# ── Limpa build anterior ───────────────────────────────────────────────────
step "0/6" "Limpando build anterior..."
rm -rf "$STAGING"
mkdir -p "$STAGING"

# ── 1. Copia arquivos da aplicação → /opt/gdrive-mint/ ────────────────────
step "1/6" "Copiando arquivos da aplicação..."
APP_DEST="${STAGING}${INSTALL_DIR}"
mkdir -p "$APP_DEST"

rsync -a \
    --exclude='.git/' \
    --exclude='.venv/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='*.pyo' \
    --exclude='packaging/' \
    --exclude='*.egg-info/' \
    --exclude='.env' \
    --exclude='*.log' \
    "$ROOT_DIR/" "$APP_DEST/"

info "Aplicação copiada para $APP_DEST"

# ── 2. Ícone SVG ──────────────────────────────────────────────────────────
step "2/6" "Instalando ícone..."
ICON_DEST="${STAGING}/usr/share/icons/hicolor/scalable/apps"
mkdir -p "$ICON_DEST"

SVG_SRC="$SCRIPT_DIR/assets/gdrive-mint.svg"
if [[ -f "$SVG_SRC" ]]; then
    cp "$SVG_SRC" "$ICON_DEST/gdrive-mint.svg"
    info "Ícone SVG instalado."
else
    warn "Ícone não encontrado em $SVG_SRC — ignorando."
fi

# ── 3. Launcher e entrada .desktop ────────────────────────────────────────
step "3/6" "Criando launcher e entrada de menu..."

BINDIR="${STAGING}/usr/local/bin"
mkdir -p "$BINDIR"

# Script executável que usa o venv da instalação
cat > "${BINDIR}/gdrive-mint" << LAUNCHER
#!/usr/bin/env bash
# Launcher instalado pelo pacote gdrive-mint
VENV="${INSTALL_DIR}/.venv"
if [[ ! -d "\$VENV" ]]; then
    echo "[GDrive Mint] venv não encontrado. Reinstale o pacote." >&2
    exit 1
fi
exec "\${VENV}/bin/python3" "${INSTALL_DIR}/main.py" "\$@"
LAUNCHER
chmod 755 "${BINDIR}/gdrive-mint"

# Arquivo .desktop (integração com o menu de aplicativos)
APPDIR="${STAGING}/usr/share/applications"
mkdir -p "$APPDIR"
cat > "${APPDIR}/gdrive-mint.desktop" << DESKTOP
[Desktop Entry]
Type=Application
Name=GDrive Mint
GenericName=Cliente Google Drive
Comment=Sincronização com Google Drive para Linux Mint
Exec=gdrive-mint
Icon=gdrive-mint
Terminal=false
Categories=Network;FileTransfer;
Keywords=google;drive;sync;cloud;backup;
StartupNotify=true
StartupWMClass=gdrive-mint
DESKTOP
chmod 644 "${APPDIR}/gdrive-mint.desktop"

info "Launcher e .desktop criados."

# ── 4. Metadados DEBIAN/ ──────────────────────────────────────────────────
step "4/6" "Gerando metadados DEBIAN/..."
DEBIAN_DIR="${STAGING}/DEBIAN"
mkdir -p "$DEBIAN_DIR"

# Tamanho estimado após instalação (em KB)
INSTALLED_SIZE=$(du -sk "$APP_DEST" | awk '{print $1}')

cat > "${DEBIAN_DIR}/control" << CONTROL
Package: ${PKG_NAME}
Version: ${VERSION}
Architecture: ${ARCH}
Maintainer: ${MAINTAINER}
Installed-Size: ${INSTALLED_SIZE}
Depends: python3 (>= 3.10), python3-pip, python3-venv, python3-tk, libnotify-bin
Recommends: gir1.2-appindicator3-0.1
Section: net
Priority: optional
Homepage: ${HOMEPAGE}
Description: ${DESCRIPTION}
 ${LONG_DESCRIPTION}
CONTROL

# postinst: cria o venv isolado e instala dependências Python via pip
cat > "${DEBIAN_DIR}/postinst" << 'POSTINST'
#!/usr/bin/env bash
set -e

INSTALL_DIR="/opt/gdrive-mint"
VENV="${INSTALL_DIR}/.venv"

case "$1" in
    configure)
        echo "[GDrive Mint] Configurando ambiente Python em ${VENV}..."
        python3 -m venv "$VENV"
        "${VENV}/bin/pip" install --upgrade pip --quiet
        "${VENV}/bin/pip" install \
            --requirement "${INSTALL_DIR}/requirements.txt" \
            --quiet \
            --no-warn-script-location
        # Permissões: somente root escreve; qualquer usuário executa
        chmod -R o-w "$INSTALL_DIR"
        chmod -R a+rX "$INSTALL_DIR"

        # Atualiza cache de ícones do sistema
        if command -v gtk-update-icon-cache &>/dev/null; then
            gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
        fi
        if command -v update-desktop-database &>/dev/null; then
            update-desktop-database /usr/share/applications 2>/dev/null || true
        fi

        echo ""
        echo "╔══════════════════════════════════════════════════════════╗"
        echo "║  GDrive Mint instalado com sucesso!                      ║"
        echo "║                                                          ║"
        echo "║  Próximo passo: configure o OAuth 2.0                    ║"
        echo "║  Coloque o credentials.json em:                          ║"
        echo "║    ~/.config/gdrive_mint/credentials.json                ║"
        echo "║                                                          ║"
        echo "║  Guia completo: /opt/gdrive-mint/README.md               ║"
        echo "╚══════════════════════════════════════════════════════════╝"
        echo ""
        ;;
esac
POSTINST
chmod 755 "${DEBIAN_DIR}/postinst"

# prerm: limpeza antes de remover
cat > "${DEBIAN_DIR}/prerm" << 'PRERM'
#!/usr/bin/env bash
set -e

case "$1" in
    remove|purge)
        echo "[GDrive Mint] Removendo ambiente Python..."
        rm -rf "/opt/gdrive-mint/.venv"
        ;;
esac
PRERM
chmod 755 "${DEBIAN_DIR}/prerm"

# postrm: pós-remoção
cat > "${DEBIAN_DIR}/postrm" << 'POSTRM'
#!/usr/bin/env bash
set -e

case "$1" in
    purge)
        # Remove completamente o diretório
        rm -rf /opt/gdrive-mint
        ;;
esac

# Atualiza cache de ícones após remoção
if command -v gtk-update-icon-cache &>/dev/null; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
fi
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database /usr/share/applications 2>/dev/null || true
fi
POSTRM
chmod 755 "${DEBIAN_DIR}/postrm"

info "Metadados DEBIAN/ gerados."

# ── 5. Checksums md5sums ──────────────────────────────────────────────────
step "5/6" "Calculando checksums..."
(
    cd "$STAGING"
    find . -type f ! -path './DEBIAN/*' -exec md5sum {} \;
) > "${DEBIAN_DIR}/md5sums"
info "md5sums gerado."

# ── 6. Constrói o .deb ────────────────────────────────────────────────────
step "6/6" "Construindo o pacote .deb..."
fakeroot dpkg-deb --root-owner-group --build "$STAGING" "$OUTPUT"

# Verificação básica
dpkg-deb --info "$OUTPUT" > /dev/null
SIZE=$(du -sh "$OUTPUT" | awk '{print $1}')

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  Pacote .deb criado com sucesso!                             ║"
echo "╠══════════════════════════════════════════════════════════════╣"
printf "║  Arquivo : %-51s║\n" "${PKG_FULL}.deb"
printf "║  Tamanho : %-51s║\n" "$SIZE"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Como instalar:                                              ║"
echo "║  Clique duas vezes em GDrive-Mint-Linux-Mint.deb             ║"
echo "║  na pasta Instaladores/ para abrir no Gerenciador            ║"
echo "║  de Pacotes do Linux Mint e clique em Instalar.              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
