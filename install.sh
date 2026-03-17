#!/usr/bin/env bash
# =============================================================================
#  GDrive Mint — Script de Instalação para Linux Mint / Ubuntu
# =============================================================================
#  Uso:
#    chmod +x install.sh
#    ./install.sh
# =============================================================================

set -euo pipefail

APP_NAME="gdrive_mint"
APP_DIR="$HOME/.config/$APP_NAME"
DATA_DIR="$HOME/.local/share/$APP_NAME"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()    { echo -e "${GREEN}[INFO]${NC} $1"; }
warning() { echo -e "${YELLOW}[AVISO]${NC} $1"; }
error()   { echo -e "${RED}[ERRO]${NC} $1"; exit 1; }

echo "========================================"
echo "  GDrive Mint — Instalador"
echo "========================================"
echo ""

# ── 1. Verificar Python 3.10+ ─────────────────────────────────────────────
info "Verificando Python..."
if ! command -v python3 &>/dev/null; then
    error "Python 3 não encontrado. Instale com: sudo apt install python3"
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
REQUIRED="3.10"

if python3 -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)"; then
    info "Python $PYTHON_VERSION ✓"
else
    error "Python $REQUIRED+ é necessário. Encontrado: $PYTHON_VERSION"
fi

# ── 2. Instalar dependências do sistema ───────────────────────────────────
info "Verificando dependências do sistema..."

SYSTEM_PACKAGES=(
    python3-pip
    python3-venv
    python3-tk
    libnotify-bin
    libgirepository1.0-dev
    gir1.2-appindicator3-0.1
)

MISSING=()
for pkg in "${SYSTEM_PACKAGES[@]}"; do
    if ! dpkg -l "$pkg" &>/dev/null 2>&1; then
        MISSING+=("$pkg")
    fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
    info "Instalando pacotes do sistema: ${MISSING[*]}"
    sudo apt-get update -qq
    sudo apt-get install -y "${MISSING[@]}"
fi

# ── 3. Criar ambiente virtual ─────────────────────────────────────────────
VENV_DIR="$SCRIPT_DIR/.venv"

if [ ! -d "$VENV_DIR" ]; then
    info "Criando ambiente virtual em $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# ── 4. Instalar dependências Python ──────────────────────────────────────
info "Instalando dependências Python..."
pip install --upgrade pip -q
pip install -r "$SCRIPT_DIR/requirements.txt" -q
info "Dependências instaladas ✓"

# ── 5. Criar diretórios da aplicação ─────────────────────────────────────
info "Criando diretórios..."
mkdir -p "$APP_DIR" "$DATA_DIR/logs"
chmod 700 "$APP_DIR"

# ── 6. Criar script executável ────────────────────────────────────────────
LAUNCHER="$HOME/.local/bin/gdrive-mint"
mkdir -p "$HOME/.local/bin"

cat > "$LAUNCHER" << EOF
#!/usr/bin/env bash
source "$VENV_DIR/bin/activate"
exec python3 "$SCRIPT_DIR/main.py" "\$@"
EOF

chmod +x "$LAUNCHER"
info "Launcher criado em $LAUNCHER ✓"

# ── 7. Criar ícone .desktop ───────────────────────────────────────────────
DESKTOP_DIR="$HOME/.local/share/applications"
mkdir -p "$DESKTOP_DIR"

cat > "$DESKTOP_DIR/gdrive-mint.desktop" << EOF
[Desktop Entry]
Type=Application
Name=GDrive Mint
GenericName=Google Drive Client
Comment=Sincronização com Google Drive para Linux Mint
Exec=$LAUNCHER
Icon=folder-google-drive
Terminal=false
Categories=Network;FileTransfer;
Keywords=google;drive;sync;cloud;
StartupNotify=true
EOF

chmod 644 "$DESKTOP_DIR/gdrive-mint.desktop"
info "Ícone de aplicativo criado ✓"

# ── 8. Verificar credentials.json ────────────────────────────────────────
echo ""
if [ ! -f "$APP_DIR/credentials.json" ]; then
    warning "credentials.json NÃO encontrado em $APP_DIR/"
    echo ""
    echo "  Para configurar o OAuth 2.0:"
    echo "  1. Acesse: https://console.cloud.google.com/"
    echo "  2. Crie um projeto e ative a Google Drive API"
    echo "  3. Crie credenciais OAuth 2.0 (Aplicativo de Desktop)"
    echo "  4. Baixe o JSON e renomeie para 'credentials.json'"
    echo "  5. Copie para: $APP_DIR/credentials.json"
    echo "  6. Execute: chmod 600 $APP_DIR/credentials.json"
    echo ""
else
    chmod 600 "$APP_DIR/credentials.json"
    info "credentials.json encontrado ✓"
fi

# ── Conclusão ──────────────────────────────────────────────────────────────
echo ""
echo "========================================"
info "Instalação concluída!"
echo "========================================"
echo ""
echo "  Para executar:"
echo "    gdrive-mint"
echo ""
echo "  Ou pelo menu de aplicativos: GDrive Mint"
echo ""
