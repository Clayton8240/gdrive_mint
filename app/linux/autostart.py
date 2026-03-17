"""
Gerenciamento de autostart no Linux Mint.
Cria/remove arquivo .desktop em ~/.config/autostart/.
"""

import os
from pathlib import Path
import sys

from app.utils.logger import get_logger

AUTOSTART_DIR = Path.home() / ".config" / "autostart"
DESKTOP_FILE = AUTOSTART_DIR / "gdrive-mint.desktop"

DESKTOP_TEMPLATE = """[Desktop Entry]
Type=Application
Name=GDrive Mint
Comment=Sincronização com Google Drive
Exec={exec_cmd}
Icon=folder-google-drive
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
X-MATE-Autostart-enabled=true
X-KDE-autostart-enabled=true
"""


class AutostartManager:
    """Gerencia a inicialização automática com o sistema no Linux Mint."""

    def __init__(self):
        self.logger = get_logger()

    def is_enabled(self) -> bool:
        """Verifica se o autostart está ativo."""
        return DESKTOP_FILE.exists()

    def enable(self, exec_cmd: str | None = None) -> bool:
        """
        Cria o arquivo .desktop de autostart.
        Usa o executável Python atual se exec_cmd não for fornecido.
        """
        try:
            AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)

            if exec_cmd is None:
                # Usa o interpreter Python atual com o main.py
                main_py = Path(sys.argv[0]).resolve()
                exec_cmd = f"{sys.executable} {main_py}"

            content = DESKTOP_TEMPLATE.format(exec_cmd=exec_cmd)
            with open(DESKTOP_FILE, "w", encoding="utf-8") as f:
                f.write(content)

            # Permissão de execução
            os.chmod(DESKTOP_FILE, 0o644)
            self.logger.info(f"Autostart ativado: {DESKTOP_FILE}")
            return True
        except Exception as e:
            self.logger.error(f"Falha ao ativar autostart: {e}")
            return False

    def disable(self) -> bool:
        """Remove o arquivo .desktop de autostart."""
        try:
            if DESKTOP_FILE.exists():
                DESKTOP_FILE.unlink()
                self.logger.info("Autostart desativado.")
            return True
        except Exception as e:
            self.logger.error(f"Falha ao desativar autostart: {e}")
            return False

    def toggle(self) -> bool:
        """Alterna o estado do autostart. Retorna True se agora está ativo."""
        if self.is_enabled():
            self.disable()
            return False
        else:
            self.enable()
            return True
