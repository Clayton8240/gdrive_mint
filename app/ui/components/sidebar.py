"""
Barra lateral de navegação da aplicação.
"""

import customtkinter as ctk

from app.ui.theme import ThemeManager


class NavItem:
    """Representa um item de navegação na sidebar."""

    def __init__(self, label: str, icon: str, screen_name: str):
        self.label = label
        self.icon = icon
        self.screen_name = screen_name


NAV_ITEMS = [
    NavItem("Dashboard", "⊞", "dashboard"),
    NavItem("Pastas", "📁", "folders"),
    NavItem("Configurações", "⚙", "settings"),
    NavItem("Logs", "📋", "logs"),
]


class Sidebar(ctk.CTkFrame):
    """
    Barra lateral fixa com botões de navegação e informações do usuário.
    """

    def __init__(self, parent, theme: ThemeManager, navigate_cb, **kwargs):
        super().__init__(
            parent,
            width=200,
            corner_radius=0,
            fg_color=theme.c("sidebar_bg"),
            **kwargs,
        )
        self.theme = theme
        self.navigate_cb = navigate_cb
        self._active = "dashboard"
        self._buttons: dict[str, ctk.CTkButton] = {}
        self._build()

    def _build(self) -> None:
        self.grid_rowconfigure(len(NAV_ITEMS) + 2, weight=1)

        # Logo / cabeçalho
        logo_frame = ctk.CTkFrame(self, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=16, pady=(20, 16), sticky="ew")

        ctk.CTkLabel(
            logo_frame,
            text="☁  GDrive",
            font=self.theme.font(18, "bold"),
            text_color=self.theme.c("accent"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            logo_frame,
            text="Mint",
            font=self.theme.font(13),
            text_color=self.theme.c("text_secondary"),
        ).pack(anchor="w")

        # Separador
        sep = ctk.CTkFrame(self, height=1, fg_color=self.theme.c("border"))
        sep.grid(row=1, column=0, sticky="ew", padx=12, pady=4)

        # Botões de navegação
        for i, item in enumerate(NAV_ITEMS):
            btn = ctk.CTkButton(
                self,
                text=f"  {item.icon}  {item.label}",
                anchor="w",
                fg_color="transparent",
                hover_color=self.theme.c("bg_card"),
                text_color=self.theme.c("text_secondary"),
                font=self.theme.font(13),
                corner_radius=8,
                height=40,
                command=lambda name=item.screen_name: self._on_click(name),
            )
            btn.grid(row=i + 2, column=0, padx=10, pady=3, sticky="ew")
            self._buttons[item.screen_name] = btn

        # Espaçador
        spacer = ctk.CTkFrame(self, fg_color="transparent")
        spacer.grid(row=len(NAV_ITEMS) + 3, column=0, sticky="nsew")
        self.grid_rowconfigure(len(NAV_ITEMS) + 3, weight=1)

        # Frame do usuário (rodapé)
        self._user_frame = ctk.CTkFrame(
            self, fg_color=self.theme.c("bg_card"), corner_radius=8
        )
        self._user_frame.grid(
            row=len(NAV_ITEMS) + 4, column=0, padx=10, pady=14, sticky="ew"
        )

        self._user_avatar = ctk.CTkLabel(
            self._user_frame,
            text="●",
            font=self.theme.font(22),
            text_color=self.theme.c("accent"),
            width=32,
        )
        self._user_avatar.grid(row=0, column=0, padx=(8, 4), pady=8)

        self._user_info_frame = ctk.CTkFrame(self._user_frame, fg_color="transparent")
        self._user_info_frame.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self._user_frame.grid_columnconfigure(1, weight=1)

        self._user_name_label = ctk.CTkLabel(
            self._user_info_frame,
            text="Não conectado",
            font=self.theme.font(12, "bold"),
            text_color=self.theme.c("text_primary"),
            anchor="w",
        )
        self._user_name_label.pack(anchor="w")

        self._user_email_label = ctk.CTkLabel(
            self._user_info_frame,
            text="",
            font=self.theme.font(10),
            text_color=self.theme.c("text_secondary"),
            anchor="w",
        )
        self._user_email_label.pack(anchor="w")

        # Indica tela ativa inicial
        self.set_active("dashboard")

    def _on_click(self, screen_name: str) -> None:
        self.set_active(screen_name)
        self.navigate_cb(screen_name)

    def set_active(self, screen_name: str) -> None:
        """Destaca o botão da tela ativa."""
        for name, btn in self._buttons.items():
            is_active = name == screen_name
            btn.configure(
                fg_color=self.theme.c("accent") if is_active else "transparent",
                text_color=(
                    "#ffffff" if is_active else self.theme.c("text_secondary")
                ),
                font=self.theme.font(13, "bold" if is_active else "normal"),
            )
        self._active = screen_name

    def update_user(self, name: str, email: str) -> None:
        """Atualiza informações do usuário na sidebar."""
        display_name = name if name else email.split("@")[0] if email else "Usuário"
        self._user_name_label.configure(text=display_name[:20])
        self._user_email_label.configure(text=email[:26] if email else "")
        self._user_avatar.configure(text_color=self.theme.c("accent_success"))

    def clear_user(self) -> None:
        """Remove informações do usuário (logout)."""
        self._user_name_label.configure(text="Não conectado")
        self._user_email_label.configure(text="")
        self._user_avatar.configure(text_color=self.theme.c("text_muted"))
