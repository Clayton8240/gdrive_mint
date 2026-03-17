"""
Tela de configurações gerais da aplicação.
"""

import tkinter.filedialog as fd
import customtkinter as ctk

from app.linux.autostart import AutostartManager
from app.ui.theme import ThemeManager


class SettingsScreen(ctk.CTkFrame):
    """Tela de configurações gerais da aplicação."""

    def __init__(self, parent, theme: ThemeManager, config, engine, auth_service, on_logout, on_theme_toggle, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.theme = theme
        self.config = config
        self.engine = engine
        self.auth = auth_service
        self.on_logout = on_logout
        self.on_theme_toggle = on_theme_toggle
        self.autostart = AutostartManager()
        self._build()
        self._load_values()

    def _section(self, title: str, row: int) -> ctk.CTkFrame:
        """Cria seção com título."""
        frame = ctk.CTkFrame(
            self,
            fg_color=self.theme.c("bg_secondary"),
            corner_radius=12,
            border_color=self.theme.c("border"),
            border_width=1,
        )
        frame.grid(row=row, column=0, padx=24, pady=6, sticky="ew")
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            frame,
            text=title,
            font=self.theme.font_subtitle(),
            text_color=self.theme.c("text_primary"),
        ).grid(row=0, column=0, padx=20, pady=(14, 6), sticky="w", columnspan=2)
        return frame

    def _row(self, parent, label: str, row: int, widget, col=1):
        """Adiciona linha de configuração com label à esquerda."""
        ctk.CTkLabel(
            parent,
            text=label,
            font=self.theme.font(13),
            text_color=self.theme.c("text_primary"),
        ).grid(row=row, column=0, padx=20, pady=8, sticky="w")
        widget.grid(row=row, column=col, padx=(8, 20), pady=8, sticky="e")

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)

        # Cabeçalho
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=24, pady=(24, 8), sticky="ew")

        ctk.CTkLabel(
            header,
            text="Configurações",
            font=self.theme.font_title(),
            text_color=self.theme.c("text_primary"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Personalize o comportamento do GDrive Mint",
            font=self.theme.font_small(),
            text_color=self.theme.c("text_secondary"),
        ).pack(anchor="w")

        # ── Seção: Sincronização ───────────────────────────────────────────
        sync_section = self._section("🔄  Sincronização", 1)
        sync_section.grid_columnconfigure(1, weight=1)

        # Intervalo
        self._interval_var = ctk.IntVar(value=15)
        interval_slider = ctk.CTkSlider(
            sync_section,
            from_=1, to=60,
            variable=self._interval_var,
            progress_color=self.theme.c("accent"),
            button_color=self.theme.c("accent"),
            width=200,
            command=self._on_interval_change,
        )
        self._row(sync_section, "Intervalo automático (min):", 1, interval_slider)

        self._interval_label = ctk.CTkLabel(
            sync_section,
            text="15 min",
            font=self.theme.font(12, "bold"),
            text_color=self.theme.c("accent"),
        )
        self._interval_label.grid(row=1, column=2, padx=(4, 20), pady=8)

        # Resolução de conflitos
        self._conflict_var = ctk.StringVar(value="Renomear local")
        conflict_menu = ctk.CTkOptionMenu(
            sync_section,
            values=["Renomear local", "Manter local", "Sobrescrever local", "Manter ambos"],
            variable=self._conflict_var,
            fg_color=self.theme.c("bg_card"),
            button_color=self.theme.c("accent"),
            text_color=self.theme.c("text_primary"),
            font=self.theme.font(12),
            width=200,
        )
        self._row(sync_section, "Resolução de conflitos:", 2, conflict_menu)

        # ── Seção: Diretório padrão ────────────────────────────────────────
        dir_section = self._section("📂  Diretório Padrão", 2)
        dir_section.grid_columnconfigure(1, weight=1)

        self._dir_var = ctk.StringVar(value="~/GoogleDrive")
        dir_entry = ctk.CTkEntry(
            dir_section,
            textvariable=self._dir_var,
            fg_color=self.theme.c("bg_card"),
            border_color=self.theme.c("border"),
            text_color=self.theme.c("text_primary"),
            font=self.theme.font(12),
            width=260,
        )
        self._row(dir_section, "Diretório padrão:", 1, dir_entry)

        ctk.CTkButton(
            dir_section,
            text="Procurar",
            width=80,
            height=28,
            fg_color=self.theme.c("bg_card"),
            border_color=self.theme.c("accent"),
            border_width=1,
            text_color=self.theme.c("accent"),
            font=self.theme.font(12),
            command=self._browse_dir,
        ).grid(row=1, column=2, padx=(4, 20), pady=8)

        # ── Seção: Sistema ─────────────────────────────────────────────────
        sys_section = self._section("🖥️  Sistema Linux", 3)
        sys_section.grid_columnconfigure(1, weight=1)

        # Autostart
        self._autostart_var = ctk.BooleanVar(value=self.autostart.is_enabled())
        autostart_sw = ctk.CTkSwitch(
            sys_section,
            text="",
            variable=self._autostart_var,
            progress_color=self.theme.c("accent"),
            command=self._on_autostart_toggle,
        )
        self._row(sys_section, "Inicializar com o sistema:", 1, autostart_sw)

        # Minimizar para bandeja
        self._tray_var = ctk.BooleanVar(value=True)
        tray_sw = ctk.CTkSwitch(
            sys_section,
            text="",
            variable=self._tray_var,
            progress_color=self.theme.c("accent"),
            command=lambda: self.config.set("minimize_to_tray", self._tray_var.get()),
        )
        self._row(sys_section, "Minimizar para bandeja:", 2, tray_sw)

        # Notificações
        self._notif_var = ctk.BooleanVar(value=True)
        notif_sw = ctk.CTkSwitch(
            sys_section,
            text="",
            variable=self._notif_var,
            progress_color=self.theme.c("accent"),
            command=lambda: self.config.set("notifications_enabled", self._notif_var.get()),
        )
        self._row(sys_section, "Notificações do sistema:", 3, notif_sw)

        # ── Seção: Aparência ───────────────────────────────────────────────
        appear_section = self._section("🎨  Aparência", 4)
        appear_section.grid_columnconfigure(1, weight=1)

        # Tema
        self._theme_var = ctk.StringVar(value="Escuro")
        theme_menu = ctk.CTkOptionMenu(
            appear_section,
            values=["Escuro", "Claro"],
            variable=self._theme_var,
            fg_color=self.theme.c("bg_card"),
            button_color=self.theme.c("accent"),
            text_color=self.theme.c("text_primary"),
            font=self.theme.font(12),
            width=160,
            command=self._on_theme_change,
        )
        self._row(appear_section, "Tema da interface:", 1, theme_menu)

        # ── Seção: Conta ───────────────────────────────────────────────────
        account_section = self._section("👤  Conta Google", 5)
        account_section.grid_columnconfigure(1, weight=1)

        email = self.auth.user_email or "Não conectado"
        ctk.CTkLabel(
            account_section,
            text=email,
            font=self.theme.font(13),
            text_color=self.theme.c("accent"),
        ).grid(row=1, column=0, padx=20, pady=8, sticky="w")

        ctk.CTkButton(
            account_section,
            text="Sair da conta",
            fg_color=self.theme.c("accent_danger"),
            hover_color="#c0392b",
            font=self.theme.font(12, "bold"),
            width=140,
            height=34,
            corner_radius=8,
            command=self._on_logout,
        ).grid(row=1, column=1, padx=20, pady=10, sticky="e")

        # Botão salvar
        ctk.CTkButton(
            self,
            text="💾  Salvar configurações",
            font=self.theme.font(13, "bold"),
            fg_color=self.theme.c("accent_success"),
            hover_color="#188038",
            width=220,
            height=42,
            corner_radius=10,
            command=self._save,
        ).grid(row=6, column=0, padx=24, pady=20, sticky="e")

    def _load_values(self) -> None:
        """Carrega valores das configurações salvas."""
        self._interval_var.set(self.config.get("sync_interval_minutes", 15))
        self._interval_label.configure(text=f"{self._interval_var.get()} min")
        self._tray_var.set(self.config.get("minimize_to_tray", True))
        self._notif_var.set(self.config.get("notifications_enabled", True))
        self._dir_var.set(self.config.get("default_directory", "~/GoogleDrive"))
        saved_theme = self.config.get("theme", "dark")
        self._theme_var.set("Escuro" if saved_theme == "dark" else "Claro")

    def _on_interval_change(self, value) -> None:
        v = int(value)
        self._interval_label.configure(text=f"{v} min")

    def _browse_dir(self) -> None:
        path = fd.askdirectory(title="Selecionar diretório padrão")
        if path:
            self._dir_var.set(path)

    def _on_autostart_toggle(self) -> None:
        if self._autostart_var.get():
            self.autostart.enable()
        else:
            self.autostart.disable()

    def _on_theme_change(self, value: str) -> None:
        theme_key = "dark" if value == "Escuro" else "light"
        self.on_theme_toggle(theme_key)
        self.config.set("theme", theme_key)

    def _on_logout(self) -> None:
        self.auth.logout()
        self.on_logout()

    def _save(self) -> None:
        """Salva todas as configurações."""
        self.config.update({
            "sync_interval_minutes": self._interval_var.get(),
            "default_directory": self._dir_var.get(),
            "minimize_to_tray": self._tray_var.get(),
            "notifications_enabled": self._notif_var.get(),
        })
        if self.engine.is_running:
            self.engine.refresh_config()

        # Feedback visual
        self.after(0, lambda: None)  # flush UI
