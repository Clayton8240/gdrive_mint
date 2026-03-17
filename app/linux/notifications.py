"""
Notificações nativas no Linux usando notify-send.
Fallback para o sistema de notificações da aplicação.
"""

import shutil
import subprocess
import threading

from app.utils.logger import get_logger


class LinuxNotifier:
    """Envia notificações via notify-send (Linux nativo)."""

    ICONS = {
        "info": "dialog-information",
        "success": "emblem-default",
        "warning": "dialog-warning",
        "error": "dialog-error",
    }

    def __init__(self, app_name: str = "GDrive Mint"):
        self.app_name = app_name
        self.logger = get_logger()
        self._available = shutil.which("notify-send") is not None
        if not self._available:
            self.logger.warning("notify-send não encontrado. Usando log como fallback.")

    def notify(
        self,
        title: str,
        message: str,
        level: str = "info",
        timeout_ms: int = 5000,
    ) -> None:
        """Exibe notificação nativa de forma assíncrona."""
        t = threading.Thread(
            target=self._send,
            args=(title, message, level, timeout_ms),
            daemon=True,
        )
        t.start()

    def _send(self, title: str, message: str, level: str, timeout_ms: int) -> None:
        """Executa notify-send em processo separado."""
        if not self._available:
            self.logger.info(f"[{level.upper()}] {title}: {message}")
            return

        icon = self.ICONS.get(level, "dialog-information")
        try:
            subprocess.run(
                [
                    "notify-send",
                    "--app-name", self.app_name,
                    "--icon", icon,
                    f"--expire-time={timeout_ms}",
                    title,
                    message,
                ],
                check=False,
                timeout=5,
            )
        except Exception as e:
            self.logger.debug(f"notify-send falhou: {e}")

    def sync_complete(self, count: int) -> None:
        self.notify("Sincronização Concluída", f"{count} arquivo(s) sincronizado(s).", "success")

    def sync_error(self, error: str) -> None:
        self.notify("Erro de Sincronização", error, "error")

    def upload_complete(self, filename: str) -> None:
        self.notify("Upload Concluído", f"'{filename}' enviado.", "success")

    def download_complete(self, filename: str) -> None:
        self.notify("Download Concluído", f"'{filename}' baixado.", "success")
