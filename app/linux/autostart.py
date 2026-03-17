"""
Gerenciamento de autostart no Linux Mint.
Cria/remove arquivo .desktop em ~/.config/autostart/.

Auditoria de seguranca aplicada:
- exec_cmd sanitizado para remover newlines (evita injecao em .desktop)
- Chaves { } removidas do exec_cmd (evita format-string injection)
- Caminho do executavel obtido via sys.executable (nao sys.argv[0])
- main_py derivado de __file__ do modulo raiz (mais confiavel que argv[0])
- Escrita atomica do arquivo .desktop (tempfile + rename)
"""

import os
import re
import sys
import tempfile
from pathlib import Path

from app.utils.logger import get_logger

AUTOSTART_DIR = Path.home() / ".config" / "autostart"
DESKTOP_FILE = AUTOSTART_DIR / "gdrive-mint.desktop"

# Template sem interpolacao Python: valores sao inseridos por substituicao
# segura (nao .format()) para evitar format-string injection residual.
_DESKTOP_LINES = [
    "[Desktop Entry]",
    "Type=Application",
    "Name=GDrive Mint",
    "Comment=Sincronizacao com Google Drive",
    "Exec=EXEC_PLACEHOLDER",
    "Icon=folder-google-drive",
    "Hidden=false",
    "NoDisplay=false",
    "X-GNOME-Autostart-enabled=true",
    "X-MATE-Autostart-enabled=true",
    "X-KDE-autostart-enabled=true",
]


def _sanitize_exec(cmd: str) -> str:
    """
    Remove caracteres perigosos de exec_cmd antes de inserir no .desktop.
    - Newlines (\n \r): impediriam injecao de novos campos no arquivo
    - Chaves ({ }): evitam format-string injection se o template fosse .format()
    """
    cmd = re.sub(r"[\n\r]", " ", cmd)   # sem injecao de campo .desktop
    cmd = re.sub(r"[{}]", "", cmd)      # sem format-string residual
    return cmd.strip()


class AutostartManager:
    """Gerencia a inicializacao automatica com o sistema no Linux Mint."""

    def __init__(self):
        self.logger = get_logger()

    def is_enabled(self) -> bool:
        """Verifica se o autostart esta ativo."""
        return DESKTOP_FILE.exists()

    def enable(self, exec_cmd: str | None = None) -> bool:
        """
        Cria o arquivo .desktop de autostart.
        Usa o executavel Python atual se exec_cmd nao for fornecido.
        """
        try:
            AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)

            if exec_cmd is None:
                # sys.executable e o interpretador Python — confiavel.
                # __file__ resolvido ate o main.py a partir do pacote raiz.
                # Nao usamos sys.argv[0] pois pode ser manipulado pelo chamador.
                main_py = (Path(__file__).parent.parent.parent / "main.py").resolve()
                exec_cmd = f"{sys.executable} {main_py}"

            # Sanitiza antes de escrever no arquivo .desktop
            safe_cmd = _sanitize_exec(exec_cmd)

            # Monta conteudo substituindo o placeholder de forma segura
            lines = [
                line.replace("EXEC_PLACEHOLDER", safe_cmd)
                if line == "Exec=EXEC_PLACEHOLDER"
                else line
                for line in _DESKTOP_LINES
            ]
            content = "\n".join(lines) + "\n"

            # Escrita atomica: evita arquivo .desktop corrompido em caso de crash
            fd, tmp_path = tempfile.mkstemp(dir=AUTOSTART_DIR, prefix=".gdrive-mint.")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_path, DESKTOP_FILE)  # atomico no POSIX
            except Exception:
                os.unlink(tmp_path)
                raise

            os.chmod(DESKTOP_FILE, 0o644)
            self.logger.info("Autostart ativado.")
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
