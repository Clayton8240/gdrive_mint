"""
Barra de status inferior com indicador de conexão, última sync e progresso.
"""

import customtkinter as ctk

from app.ui.theme import ThemeManager


class StatusBar(ctk.CTkFrame):
    """Barra de status exibida no rodapé da janela principal."""

    def __init__(self, parent, theme: ThemeManager, **kwargs):
        super().__init__(
            parent,
            height=32,
            corner_radius=0,
            fg_color=theme.c("bg_secondary"),
            **kwargs,
        )
        self.theme = theme
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(2, weight=1)

        # Indicador de status (bolinha colorida)
        self._status_dot = ctk.CTkLabel(
            self,
            text="●",
            font=self.theme.font(12),
            text_color=self.theme.c("text_muted"),
        )
        self._status_dot.grid(row=0, column=0, padx=(12, 4), pady=4)

        self._status_label = ctk.CTkLabel(
            self,
            text="Desconectado",
            font=self.theme.font(11),
            text_color=self.theme.c("text_secondary"),
        )
        self._status_label.grid(row=0, column=1, padx=(0, 16), pady=4)

        # Barra de progresso (oculta por padrão)
        self._progress = ctk.CTkProgressBar(
            self,
            height=6,
            progress_color=self.theme.c("accent"),
            fg_color=self.theme.c("progress_bg"),
            width=160,
        )
        self._progress.set(0)

        # Label central (mensagem de ação)
        self._action_label = ctk.CTkLabel(
            self,
            text="",
            font=self.theme.font(11),
            text_color=self.theme.c("text_secondary"),
        )
        self._action_label.grid(row=0, column=2, padx=8, pady=4, sticky="ew")

        # Última sincronização
        self._last_sync_label = ctk.CTkLabel(
            self,
            text="",
            font=self.theme.font(11),
            text_color=self.theme.c("text_muted"),
        )
        self._last_sync_label.grid(row=0, column=3, padx=12, pady=4)

    def set_connected(self, connected: bool) -> None:
        """Atualiza indicador de conexão."""
        if connected:
            self._status_dot.configure(text_color=self.theme.c("accent_success"))
            self._status_label.configure(text="Conectado")
        else:
            self._status_dot.configure(text_color=self.theme.c("accent_danger"))
            self._status_label.configure(text="Desconectado")

    def set_syncing(self, syncing: bool, message: str = "") -> None:
        """Exibe/oculta barra de progresso de sincronização."""
        if syncing:
            self._status_dot.configure(text_color=self.theme.c("accent_warning"))
            self._status_label.configure(text="Sincronizando")
            self._progress.grid(row=0, column=4, padx=(0, 12), pady=4)
            self._progress.configure(mode="indeterminate")
            self._progress.start()
            if message:
                self._action_label.configure(text=message)
        else:
            self._progress.stop()
            self._progress.grid_remove()
            self._action_label.configure(text="")

    def set_progress(self, value: float, message: str = "") -> None:
        """Atualiza barra de progresso determinística (0.0 a 1.0)."""
        self._progress.configure(mode="determinate")
        self._progress.set(value)
        self._progress.grid(row=0, column=4, padx=(0, 12), pady=4)
        if message:
            self._action_label.configure(text=message)

    def set_last_sync(self, time_str: str) -> None:
        """Atualiza label da última sincronização."""
        self._last_sync_label.configure(text=f"Última sync: {time_str}")

    def set_message(self, message: str, level: str = "info") -> None:
        """Exibe mensagem de ação temporária."""
        colors = {
            "info": self.theme.c("text_secondary"),
            "success": self.theme.c("accent_success"),
            "warning": self.theme.c("accent_warning"),
            "error": self.theme.c("accent_danger"),
        }
        color = colors.get(level, self.theme.c("text_secondary"))
        self._action_label.configure(text=message, text_color=color)
