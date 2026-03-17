"""
Ícone na bandeja do sistema usando pystray.
Compatível com Cinnamon, MATE e XFCE no Linux Mint.
"""

import threading
from pathlib import Path
from typing import Callable, Optional

from app.utils.logger import get_logger

try:
    import pystray
    from PIL import Image, ImageDraw
    PYSTRAY_AVAILABLE = True
except ImportError:
    PYSTRAY_AVAILABLE = False


def _create_fallback_icon(size: int = 64, color: str = "#4285F4") -> "Image.Image":
    """Cria ícone simples como fallback quando não há arquivo de ícone."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Círculo azul estilo Google Drive
    draw.ellipse([4, 4, size - 4, size - 4], fill=color)
    # Letra G simplificada
    draw.rectangle([size // 2, size // 4, size - 8, size // 2], fill="white")
    draw.rectangle([size // 4, size // 4, size // 2, size * 3 // 4], fill="white")
    return img


class SystemTray:
    """Gerencia o ícone na bandeja do sistema via pystray."""

    def __init__(
        self,
        show_window_cb: Callable,
        quit_cb: Callable,
        sync_now_cb: Callable,
        icon_path: Optional[Path] = None,
    ):
        self.show_window_cb = show_window_cb
        self.quit_cb = quit_cb
        self.sync_now_cb = sync_now_cb
        self.icon_path = icon_path
        self.logger = get_logger()
        self._tray: Optional["pystray.Icon"] = None
        self._thread: Optional[threading.Thread] = None
        self._syncing = False

    def _load_icon(self) -> "Image.Image":
        """Carrega ícone do arquivo ou gera fallback."""
        if self.icon_path and self.icon_path.exists():
            try:
                return Image.open(self.icon_path).resize((64, 64))
            except Exception:
                pass
        return _create_fallback_icon()

    def _build_menu(self) -> "pystray.Menu":
        """Constrói o menu de contexto do ícone."""
        return pystray.Menu(
            pystray.MenuItem("GDrive Mint", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Abrir", self._on_open, default=True),
            pystray.MenuItem("Sincronizar agora", self._on_sync_now),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Sair", self._on_quit),
        )

    def start(self) -> None:
        """Inicia o ícone na bandeja em thread separada."""
        if not PYSTRAY_AVAILABLE:
            self.logger.warning("pystray não disponível. Bandeja desabilitada.")
            return

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        """Loop principal do ícone (bloqueante, roda em thread própria)."""
        try:
            icon_image = self._load_icon()
            self._tray = pystray.Icon(
                "gdrive_mint",
                icon_image,
                "GDrive Mint",
                menu=self._build_menu(),
            )
            self._tray.run()
        except Exception as e:
            self.logger.error(f"Erro na bandeja: {e}")

    def stop(self) -> None:
        """Remove o ícone da bandeja."""
        if self._tray:
            try:
                self._tray.stop()
            except Exception:
                pass

    def update_tooltip(self, text: str) -> None:
        """Atualiza o tooltip do ícone."""
        if self._tray:
            try:
                self._tray.title = text
            except Exception:
                pass

    def set_syncing(self, syncing: bool) -> None:
        """Altera ícone/tooltip para indicar sincronização em curso."""
        self._syncing = syncing
        tooltip = "GDrive Mint — Sincronizando..." if syncing else "GDrive Mint"
        self.update_tooltip(tooltip)

    # ── Handlers de menu ──────────────────────────────────────────────────

    def _on_open(self, icon, item) -> None:
        try:
            self.show_window_cb()
        except Exception as e:
            self.logger.error(f"Erro ao abrir janela: {e}")

    def _on_sync_now(self, icon, item) -> None:
        try:
            self.sync_now_cb()
        except Exception as e:
            self.logger.error(f"Erro ao sincronizar: {e}")

    def _on_quit(self, icon, item) -> None:
        self.stop()
        try:
            self.quit_cb()
        except Exception:
            pass
