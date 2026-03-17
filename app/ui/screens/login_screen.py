"""
Tela de Login com autenticação OAuth 2.0 do Google.
"""

import threading
import customtkinter as ctk

from app.ui.theme import ThemeManager


class LoginScreen(ctk.CTkFrame):
    """
    Tela de login exibida antes da autenticação.
    Abre o navegador para o fluxo OAuth 2.0.
    """

    def __init__(self, parent, theme: ThemeManager, auth_service, on_login_success, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.theme = theme
        self.auth = auth_service
        self.on_login_success = on_login_success
        self._build()

    def _build(self) -> None:
        # Layout centralizado
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        card = ctk.CTkFrame(
            self,
            width=420,
            corner_radius=16,
            fg_color=self.theme.c("bg_secondary"),
            border_color=self.theme.c("border"),
            border_width=1,
        )
        card.grid(row=0, column=0, padx=40, pady=40)
        card.grid_propagate(False)
        card.configure(height=500)

        # Ícone / logo
        ctk.CTkLabel(
            card,
            text="☁",
            font=ctk.CTkFont(size=72),
            text_color=self.theme.c("accent"),
        ).pack(pady=(48, 8))

        ctk.CTkLabel(
            card,
            text="GDrive Mint",
            font=self.theme.font_title(),
            text_color=self.theme.c("text_primary"),
        ).pack()

        ctk.CTkLabel(
            card,
            text="Sincronização com Google Drive para Linux Mint",
            font=self.theme.font_small(),
            text_color=self.theme.c("text_secondary"),
        ).pack(pady=(4, 32))

        # Botão de login
        self._login_btn = ctk.CTkButton(
            card,
            text="  Entrar com Google",
            font=self.theme.font(14, "bold"),
            fg_color=self.theme.c("accent"),
            hover_color=self.theme.c("accent_hover"),
            height=48,
            width=280,
            corner_radius=24,
            command=self._start_login,
        )
        self._login_btn.pack(pady=8)

        # Status / feedback
        self._status_label = ctk.CTkLabel(
            card,
            text="",
            font=self.theme.font_small(),
            text_color=self.theme.c("text_secondary"),
            wraplength=360,
        )
        self._status_label.pack(pady=(16, 8))

        # Spinner (barra de progresso oculta)
        self._progress = ctk.CTkProgressBar(
            card,
            width=280,
            height=4,
            progress_color=self.theme.c("accent"),
        )
        self._progress.set(0)

        # Rodapé
        ctk.CTkLabel(
            card,
            text="Seus dados são armazenados localmente.\nNenhum dado é enviado a terceiros.",
            font=self.theme.font(10),
            text_color=self.theme.c("text_muted"),
            justify="center",
        ).pack(side="bottom", pady=20)

    def _start_login(self) -> None:
        """Inicia o fluxo de autenticação."""
        self._login_btn.configure(state="disabled", text="Aguardando navegador...")
        self._status_label.configure(
            text="Abrindo navegador para autenticação...\nConclua o login e retorne.",
            text_color=self.theme.c("text_secondary"),
        )
        self._progress.pack(pady=4)
        self._progress.configure(mode="indeterminate")
        self._progress.start()

        self.auth.login(
            on_success=self._on_success,
            on_error=self._on_error,
        )

    def _on_success(self, email: str) -> None:
        """Chamado após login bem-sucedido (thread de auth)."""
        # Atualiza UI na thread principal
        self.after(0, lambda: self._handle_success(email))

    def _handle_success(self, email: str) -> None:
        self._progress.stop()
        self._progress.pack_forget()
        self._status_label.configure(
            text=f"✓ Conectado como {email}",
            text_color=self.theme.c("accent_success"),
        )
        self._login_btn.configure(text="✓ Conectado!", state="disabled")
        self.after(1200, lambda: self.on_login_success(email))

    def _on_error(self, error: str) -> None:
        """Chamado após erro no login (thread de auth)."""
        self.after(0, lambda: self._handle_error(error))

    def _handle_error(self, error: str) -> None:
        self._progress.stop()
        self._progress.pack_forget()
        self._status_label.configure(
            text=f"Erro: {error}",
            text_color=self.theme.c("accent_danger"),
        )
        self._login_btn.configure(state="normal", text="  Tentar novamente")
