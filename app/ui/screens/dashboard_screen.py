"""
Tela de Dashboard — visão geral do status de sincronização.
"""

import threading
from datetime import datetime

import customtkinter as ctk

from app.ui.theme import ThemeManager


def _fmt_size(bytes_val: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if bytes_val < 1024:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} TB"


class _StatCard(ctk.CTkFrame):
    """Card de estatística individual."""

    def __init__(self, parent, theme: ThemeManager, icon: str, label: str, value: str, color: str = None):
        super().__init__(
            parent,
            corner_radius=12,
            fg_color=theme.c("bg_card"),
            border_color=theme.c("border"),
            border_width=1,
        )
        color = color or theme.c("accent")

        ctk.CTkLabel(self, text=icon, font=ctk.CTkFont(size=28), text_color=color).grid(
            row=0, column=0, padx=16, pady=(16, 4), sticky="w"
        )
        ctk.CTkLabel(self, text=label, font=theme.font_small(), text_color=theme.c("text_secondary")).grid(
            row=1, column=0, padx=16, sticky="w"
        )
        self._value_lbl = ctk.CTkLabel(
            self, text=value, font=theme.font(20, "bold"), text_color=theme.c("text_primary")
        )
        self._value_lbl.grid(row=2, column=0, padx=16, pady=(0, 16), sticky="w")

    def set_value(self, value: str) -> None:
        self._value_lbl.configure(text=value)


class DashboardScreen(ctk.CTkFrame):
    """Dashboard principal com métricas e controles de sincronização."""

    def __init__(self, parent, theme: ThemeManager, engine, drive_service, auth_service, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.theme = theme
        self.engine = engine
        self.drive = drive_service
        self.auth = auth_service
        self._build()
        self.refresh()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)

        # Cabeçalho
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=24, pady=(24, 8), sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Dashboard",
            font=self.theme.font_title(),
            text_color=self.theme.c("text_primary"),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            header,
            text="Visão geral da sincronização",
            font=self.theme.font_small(),
            text_color=self.theme.c("text_secondary"),
        ).grid(row=1, column=0, sticky="w")

        # Botão: Sincronizar agora
        self._sync_btn = ctk.CTkButton(
            header,
            text="↻  Sincronizar agora",
            font=self.theme.font(13, "bold"),
            fg_color=self.theme.c("accent"),
            hover_color=self.theme.c("accent_hover"),
            width=180,
            height=38,
            corner_radius=10,
            command=self._on_sync_now,
        )
        self._sync_btn.grid(row=0, column=1, rowspan=2, padx=(8, 0))

        # Botão: Pausar/Retomar
        self._pause_btn = ctk.CTkButton(
            header,
            text="⏸  Pausar",
            font=self.theme.font(13),
            fg_color=self.theme.c("bg_card"),
            hover_color=self.theme.c("border"),
            text_color=self.theme.c("text_primary"),
            width=120,
            height=38,
            corner_radius=10,
            command=self._on_toggle_pause,
        )
        self._pause_btn.grid(row=0, column=2, rowspan=2, padx=8)

        # Cards de estatística
        cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        cards_frame.grid(row=1, column=0, padx=24, pady=12, sticky="ew")
        for col in range(4):
            cards_frame.grid_columnconfigure(col, weight=1)

        self._card_status = _StatCard(
            cards_frame, self.theme, "●", "Status", "Conectado",
            color=self.theme.c("accent_success"),
        )
        self._card_status.grid(row=0, column=0, padx=6, pady=6, sticky="nsew")

        self._card_storage = _StatCard(
            cards_frame, self.theme, "💾", "Espaço Usado", "— GB",
            color=self.theme.c("accent"),
        )
        self._card_storage.grid(row=0, column=1, padx=6, pady=6, sticky="nsew")

        self._card_uploaded = _StatCard(
            cards_frame, self.theme, "⬆", "Uploads", "0",
            color=self.theme.c("accent_success"),
        )
        self._card_uploaded.grid(row=0, column=2, padx=6, pady=6, sticky="nsew")

        self._card_downloaded = _StatCard(
            cards_frame, self.theme, "⬇", "Downloads", "0",
            color=self.theme.c("accent_warning"),
        )
        self._card_downloaded.grid(row=0, column=3, padx=6, pady=6, sticky="nsew")

        # Barra de uso do Drive
        storage_section = ctk.CTkFrame(
            self,
            fg_color=self.theme.c("bg_secondary"),
            corner_radius=12,
            border_color=self.theme.c("border"),
            border_width=1,
        )
        storage_section.grid(row=2, column=0, padx=24, pady=8, sticky="ew")
        storage_section.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            storage_section,
            text="Armazenamento Google Drive",
            font=self.theme.font_subtitle(),
            text_color=self.theme.c("text_primary"),
        ).grid(row=0, column=0, padx=20, pady=(16, 8), sticky="w")

        self._storage_bar = ctk.CTkProgressBar(
            storage_section,
            height=12,
            progress_color=self.theme.c("accent"),
            fg_color=self.theme.c("progress_bg"),
            corner_radius=6,
        )
        self._storage_bar.set(0)
        self._storage_bar.grid(row=1, column=0, padx=20, pady=(0, 8), sticky="ew")

        self._storage_label = ctk.CTkLabel(
            storage_section,
            text="Carregando...",
            font=self.theme.font_small(),
            text_color=self.theme.c("text_secondary"),
        )
        self._storage_label.grid(row=2, column=0, padx=20, pady=(0, 16), sticky="w")

        # Progresso de sincronização
        sync_section = ctk.CTkFrame(
            self,
            fg_color=self.theme.c("bg_secondary"),
            corner_radius=12,
            border_color=self.theme.c("border"),
            border_width=1,
        )
        sync_section.grid(row=3, column=0, padx=24, pady=8, sticky="ew")
        sync_section.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            sync_section,
            text="Progresso de Sincronização",
            font=self.theme.font_subtitle(),
            text_color=self.theme.c("text_primary"),
        ).grid(row=0, column=0, padx=20, pady=(16, 8), sticky="w")

        self._sync_progress_bar = ctk.CTkProgressBar(
            sync_section,
            height=10,
            progress_color=self.theme.c("accent_success"),
            fg_color=self.theme.c("progress_bg"),
            corner_radius=5,
        )
        self._sync_progress_bar.set(0)
        self._sync_progress_bar.grid(row=1, column=0, padx=20, pady=(0, 8), sticky="ew")

        self._sync_progress_label = ctk.CTkLabel(
            sync_section,
            text="Nenhuma sincronização em curso",
            font=self.theme.font_small(),
            text_color=self.theme.c("text_secondary"),
        )
        self._sync_progress_label.grid(row=2, column=0, padx=20, pady=(0, 16), sticky="w")

        # Última sincronização
        self._last_sync_label = ctk.CTkLabel(
            self,
            text="Última sincronização: nunca",
            font=self.theme.font_small(),
            text_color=self.theme.c("text_muted"),
        )
        self._last_sync_label.grid(row=4, column=0, padx=28, pady=8, sticky="w")

    # ── Ações ──────────────────────────────────────────────────────────────

    def _on_sync_now(self) -> None:
        """Dispara sincronização manual."""
        if not self.engine.is_running:
            return
        self._sync_btn.configure(state="disabled", text="Sincronizando...")
        self._sync_progress_label.configure(text="Iniciando sincronização...")
        self._sync_progress_bar.configure(mode="indeterminate")
        self._sync_progress_bar.start()

        self.engine.sync_now(progress_callback=self._on_sync_progress)

    def _on_sync_progress(self, progress: float, message: str) -> None:
        """Atualiza barra de progresso de sincronização."""
        def update():
            if progress >= 1.0:
                self._sync_progress_bar.stop()
                self._sync_progress_bar.configure(mode="determinate")
                self._sync_progress_bar.set(1.0)
                self._sync_progress_label.configure(
                    text="Sincronização concluída ✓",
                    text_color=self.theme.c("accent_success"),
                )
                self._sync_btn.configure(state="normal", text="↻  Sincronizar agora")
                self._update_counters()
                self._update_last_sync()
            else:
                self._sync_progress_bar.configure(mode="determinate")
                self._sync_progress_bar.set(progress)
                self._sync_progress_label.configure(
                    text=message,
                    text_color=self.theme.c("text_secondary"),
                )
        self.after(0, update)

    def _on_toggle_pause(self) -> None:
        """Pausa ou retoma a sincronização."""
        if self.engine.is_paused:
            self.engine.resume()
            self._pause_btn.configure(text="⏸  Pausar")
        else:
            self.engine.pause()
            self._pause_btn.configure(text="▶  Retomar")

    # ── Atualização de dados ───────────────────────────────────────────────

    def refresh(self) -> None:
        """Atualiza todos os dados do dashboard."""
        self._update_counters()
        self._update_last_sync()
        threading.Thread(target=self._load_storage, daemon=True).start()

    def _update_counters(self) -> None:
        uploaded = getattr(self.engine, "uploaded_count", 0)
        downloaded = getattr(self.engine, "downloaded_count", 0)
        errors = getattr(self.engine, "error_count", 0)

        self._card_uploaded.set_value(str(uploaded))
        self._card_downloaded.set_value(str(downloaded))

        if errors > 0:
            self._card_status.set_value(f"⚠ {errors} erro(s)")
        elif self.engine.is_running:
            self._card_status.set_value("Ativo")
        else:
            self._card_status.set_value("Parado")

    def _update_last_sync(self) -> None:
        last = getattr(self.engine, "last_sync_time", None)
        if last:
            formatted = last.strftime("%d/%m/%Y %H:%M")
            self._last_sync_label.configure(text=f"Última sincronização: {formatted}")

    def _load_storage(self) -> None:
        """Carrega info de armazenamento do Drive em thread separada."""
        try:
            info = self.drive.get_storage_info()
            def update():
                self._storage_bar.set(min(info["used_pct"] / 100, 1.0))
                self._storage_label.configure(
                    text=f"{info['used_gb']:.2f} GB usados de {info['limit_gb']:.1f} GB ({info['used_pct']}%)"
                )
                self._card_storage.set_value(f"{info['used_gb']:.1f} GB")
            self.after(0, update)
        except Exception:
            pass
