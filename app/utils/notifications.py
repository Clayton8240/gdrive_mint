"""
Sistema de notificações do desktop.
Usa plyer para notificações nativas ou fallback com tkinter.
"""

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.utils.logger import AppLogger


class NotificationManager:
    """Gerencia notificações de desktop para a aplicação."""

    def __init__(self, logger: "AppLogger"):
        self.logger = logger
        self._plyer_available = self._check_plyer()

    def _check_plyer(self) -> bool:
        """Verifica se plyer está disponível."""
        try:
            import plyer  # noqa: F401
            return True
        except ImportError:
            return False

    def notify(
        self,
        title: str,
        message: str,
        timeout: int = 5,
        level: str = "info",
    ) -> None:
        """Exibe notificação desktop de forma assíncrona."""
        thread = threading.Thread(
            target=self._send_notification,
            args=(title, message, timeout, level),
            daemon=True,
        )
        thread.start()

    def _send_notification(
        self, title: str, message: str, timeout: int, level: str
    ) -> None:
        """Envia notificação (executado em thread separada)."""
        if self._plyer_available:
            try:
                from plyer import notification  # type: ignore
                notification.notify(
                    title=title,
                    message=message,
                    app_name="GDrive Mint",
                    timeout=timeout,
                )
                return
            except Exception as e:
                self.logger.debug(f"plyer falhou: {e}")

        # Fallback: apenas loga a notificação
        self.logger.info(f"[Notificação] {title}: {message}")

    def sync_complete(self, files_count: int) -> None:
        """Notificação de sincronização completa."""
        self.notify(
            "Sincronização Concluída",
            f"{files_count} arquivo(s) sincronizado(s) com sucesso.",
            level="success",
        )

    def sync_error(self, error: str) -> None:
        """Notificação de erro de sincronização."""
        self.notify(
            "Erro de Sincronização",
            f"Ocorreu um erro: {error}",
            level="error",
        )

    def upload_complete(self, filename: str) -> None:
        """Notificação de upload concluído."""
        self.notify(
            "Upload Concluído",
            f"'{filename}' enviado ao Google Drive.",
        )

    def download_complete(self, filename: str) -> None:
        """Notificação de download concluído."""
        self.notify(
            "Download Concluído",
            f"'{filename}' baixado do Google Drive.",
        )
