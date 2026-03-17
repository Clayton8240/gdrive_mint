"""
Janela principal da aplicação GDrive Mint.
Gerencia a navegação entre telas e integra todos os serviços.
"""

from pathlib import Path
import customtkinter as ctk

from app.core.sync_engine import SyncEngine
from app.core.sync_state import SyncState
from app.linux.notifications import LinuxNotifier
from app.linux.tray import SystemTray
from app.services.drive_service import DriveService
from app.services.google_auth import GoogleAuthService
from app.ui.components.sidebar import Sidebar
from app.ui.components.status_bar import StatusBar
from app.ui.screens.dashboard_screen import DashboardScreen
from app.ui.screens.folders_screen import FoldersScreen
from app.ui.screens.login_screen import LoginScreen
from app.ui.screens.logs_screen import LogsScreen
from app.ui.screens.settings_screen import SettingsScreen
from app.ui.theme import ThemeManager
from app.utils.config_manager import ConfigManager
from app.utils.crypto import CryptoManager
from app.utils.logger import get_logger
from app.utils.notifications import NotificationManager


APP_DIR = Path.home() / ".config" / "gdrive_mint"
DATA_DIR = Path.home() / ".local" / "share" / "gdrive_mint"


class AppWindow(ctk.CTk):
    """Janela principal do GDrive Mint com navegação por sidebar."""

    def __init__(self):
        super().__init__()

        self.logger = get_logger(DATA_DIR / "logs")
        self.logger.info("Iniciando GDrive Mint...")

        # ── Inicializa serviços ────────────────────────────────────────────
        self.crypto = CryptoManager(APP_DIR)
        self.config = ConfigManager(APP_DIR)
        self.theme_mgr = ThemeManager(self.config.get("theme", "dark"))

        # Credenciais do OAuth — o credentials.json deve estar em APP_DIR
        creds_path = APP_DIR / "credentials.json"

        self.auth = GoogleAuthService(APP_DIR, self.crypto)
        self.drive = DriveService(self.auth)

        sync_state = SyncState(DATA_DIR / "sync_state.json")
        linux_notifier = LinuxNotifier()
        notifier = NotificationManager(self.logger)

        self.engine = SyncEngine(
            drive_service=self.drive,
            config=self.config,
            state=sync_state,
            notifications=linux_notifier,
        )
        self.engine.register_status_callback(self._on_engine_status)

        self._sync_state = sync_state

        # ── Configura janela ───────────────────────────────────────────────
        self.title("GDrive Mint")
        self.geometry("1100x700")
        self.minsize(900, 600)
        self.configure(fg_color=self.theme_mgr.c("bg_primary"))

        # Intercepta fechar janela (minimiza para bandeja se configurado)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # ── Constrói UI ────────────────────────────────────────────────────
        self._current_screen: ctk.CTkFrame | None = None
        self._screens: dict[str, ctk.CTkFrame] = {}
        self._authenticated = False

        self._setup_layout()

        # ── Bandeja do sistema ─────────────────────────────────────────────
        self.tray = SystemTray(
            show_window_cb=self._show_window,
            quit_cb=self._quit_app,
            sync_now_cb=lambda: self.engine.sync_now(),
        )
        self.tray.start()

        # ── Login silencioso ───────────────────────────────────────────────
        self.after(200, self._try_silent_login)

    # ── Layout base ────────────────────────────────────────────────────────

    def _setup_layout(self) -> None:
        """Configura grid principal da janela."""
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        # Status bar (rodapé)
        self.status_bar = StatusBar(self, self.theme_mgr)
        self.status_bar.grid(row=1, column=0, columnspan=2, sticky="ew")

        # Conteúdo principal (frame central)
        self._main_frame = ctk.CTkFrame(
            self, fg_color=self.theme_mgr.c("bg_primary"), corner_radius=0
        )
        self._main_frame.grid(row=0, column=1, sticky="nsew")
        self._main_frame.grid_rowconfigure(0, weight=1)
        self._main_frame.grid_columnconfigure(0, weight=1)

        # Sidebar (oculta até login)
        self.sidebar = Sidebar(
            self, self.theme_mgr, navigate_cb=self._navigate
        )

    def _show_sidebar(self) -> None:
        self.sidebar.grid(row=0, column=0, sticky="nsew")

    def _hide_sidebar(self) -> None:
        self.sidebar.grid_remove()

    # ── Navegação ──────────────────────────────────────────────────────────

    def _navigate(self, screen_name: str) -> None:
        """Exibe a tela correspondente ao nome."""
        if self._current_screen:
            self._current_screen.grid_remove()

        if screen_name not in self._screens:
            self._screens[screen_name] = self._build_screen(screen_name)

        screen = self._screens[screen_name]
        screen.grid(row=0, column=0, sticky="nsew")
        self._current_screen = screen
        self.sidebar.set_active(screen_name)

        # Atualiza dashboard ao entrar nele
        if screen_name == "dashboard" and isinstance(screen, DashboardScreen):
            screen.refresh()

    def _build_screen(self, name: str) -> ctk.CTkFrame:
        """Instancia e retorna a tela pelo nome."""
        parent = self._main_frame

        if name == "dashboard":
            return DashboardScreen(
                parent, self.theme_mgr, self.engine, self.drive, self.auth
            )
        if name == "folders":
            return FoldersScreen(parent, self.theme_mgr, self.config, self.engine)
        if name == "settings":
            return SettingsScreen(
                parent, self.theme_mgr, self.config, self.engine,
                self.auth,
                on_logout=self._on_logout,
                on_theme_toggle=self._on_theme_toggle,
            )
        if name == "logs":
            return LogsScreen(
                parent, self.theme_mgr,
                get_logger(), self._sync_state
            )

        # Fallback
        f = ctk.CTkFrame(parent, fg_color="transparent")
        ctk.CTkLabel(f, text=f"Tela '{name}' não encontrada.").pack(pady=32)
        return f

    # ── Autenticação ───────────────────────────────────────────────────────

    def _try_silent_login(self) -> None:
        """Tenta login silencioso sem abrir navegador."""
        if self.auth.try_silent_login():
            self._post_login(self.auth.user_email)
        else:
            self._show_login()

    def _show_login(self) -> None:
        """Exibe a tela de login."""
        self._hide_sidebar()
        if self._current_screen:
            self._current_screen.grid_remove()

        login_screen = LoginScreen(
            self._main_frame, self.theme_mgr, self.auth,
            on_login_success=self._post_login,
        )
        login_screen.grid(row=0, column=0, sticky="nsew")
        self._current_screen = login_screen

    def _post_login(self, email: str) -> None:
        """Executado após autenticação bem-sucedida."""
        self._authenticated = True
        self.sidebar.update_user(self.auth.user_name, email)
        self._show_sidebar()

        # Limpa tela de login
        if self._current_screen:
            self._current_screen.grid_remove()
            self._current_screen = None

        # Inicia motor de sincronização
        self.engine.start()
        self.status_bar.set_connected(True)
        self.status_bar.set_message(f"Conectado como {email}", "success")

        # Navega para dashboard
        self._navigate("dashboard")
        self.logger.success(f"Login realizado: {email}")

    def _on_logout(self) -> None:
        """Executa logout e volta para tela de login."""
        self.engine.stop()
        self.sidebar.clear_user()
        self._authenticated = False
        self.status_bar.set_connected(False)

        # Destrói telas cacheadas para forçar reconstrução após novo login
        for screen in self._screens.values():
            screen.destroy()
        self._screens.clear()
        self._current_screen = None

        self._show_login()

    # ── Engine status ──────────────────────────────────────────────────────

    def _on_engine_status(self, message: str, level: str) -> None:
        """Atualiza status bar com mensagens do motor."""
        self.after(0, lambda: self.status_bar.set_message(message, level))

        syncing = level in ("info",) and any(
            kw in message.lower() for kw in ("enviando", "baixando", "sincronizando")
        )
        self.after(0, lambda: self.status_bar.set_syncing(syncing, message if syncing else ""))

        if level == "success" and "concluída" in message.lower():
            from datetime import datetime
            self.after(0, lambda: self.status_bar.set_last_sync(
                datetime.now().strftime("%H:%M")
            ))

    # ── Tema ───────────────────────────────────────────────────────────────

    def _on_theme_toggle(self, theme_key: str) -> None:
        """Aplica novo tema — requer reinicialização para efeito completo."""
        self.theme_mgr.set(theme_key)
        self.configure(fg_color=self.theme_mgr.c("bg_primary"))
        self._main_frame.configure(fg_color=self.theme_mgr.c("bg_primary"))
        # Nota: rebuild completo de widgets é necessário para aplicação total;
        # informamos o usuário via log
        self.logger.info(f"Tema alterado para '{theme_key}'. Reinicie para aplicar completamente.")

    # ── Janela ─────────────────────────────────────────────────────────────

    def _on_close(self) -> None:
        """Minimiza para bandeja se configurado, caso contrário sai."""
        if self.config.get("minimize_to_tray", True):
            self.withdraw()
            self.logger.info("Minimizado para a bandeja do sistema.")
        else:
            self._quit_app()

    def _show_window(self) -> None:
        """Restaura a janela a partir da bandeja."""
        self.deiconify()
        self.lift()
        self.focus_force()

    def _quit_app(self) -> None:
        """Encerra a aplicação completamente."""
        self.logger.info("Encerrando GDrive Mint...")
        self.engine.stop()
        self.tray.stop()
        self.destroy()
