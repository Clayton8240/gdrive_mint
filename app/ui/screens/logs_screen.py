"""
Tela de logs e monitoramento em tempo real.
"""

import customtkinter as ctk

from app.ui.theme import ThemeManager

# Cores por nível de log
LEVEL_COLORS = {
    "INFO": "#9e9e9e",
    "SUCCESS": "#34A853",
    "WARNING": "#FBBC04",
    "ERROR": "#EA4335",
    "DEBUG": "#616161",
}


class LogsScreen(ctk.CTkFrame):
    """Tela de visualização de logs em tempo real."""

    def __init__(self, parent, theme: ThemeManager, logger, sync_state, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.theme = theme
        self.logger = logger
        self.sync_state = sync_state
        self._max_lines = 500
        self._paused = False
        self._build()
        self._load_existing_logs()
        self._register_callback()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Cabeçalho
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=24, pady=(24, 8), sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Logs e Monitoramento",
            font=self.theme.font_title(),
            text_color=self.theme.c("text_primary"),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            header,
            text="Acompanhe o status de sincronização em tempo real",
            font=self.theme.font_small(),
            text_color=self.theme.c("text_secondary"),
        ).grid(row=1, column=0, sticky="w")

        # Controles
        controls = ctk.CTkFrame(header, fg_color="transparent")
        controls.grid(row=0, column=1, rowspan=2)

        self._pause_btn = ctk.CTkButton(
            controls,
            text="⏸  Pausar",
            width=100,
            height=32,
            corner_radius=8,
            fg_color=self.theme.c("bg_card"),
            text_color=self.theme.c("text_primary"),
            font=self.theme.font(12),
            command=self._toggle_pause,
        )
        self._pause_btn.pack(side="left", padx=4)

        ctk.CTkButton(
            controls,
            text="🗑  Limpar",
            width=100,
            height=32,
            corner_radius=8,
            fg_color=self.theme.c("bg_card"),
            text_color=self.theme.c("text_primary"),
            font=self.theme.font(12),
            command=self._clear_logs,
        ).pack(side="left", padx=4)

        # Filtros por nível
        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.grid(row=1, column=0, padx=24, pady=(0, 8), sticky="ew")

        self._filter_vars: dict[str, ctk.BooleanVar] = {}
        for level, color in LEVEL_COLORS.items():
            var = ctk.BooleanVar(value=level != "DEBUG")
            self._filter_vars[level] = var
            ctk.CTkCheckBox(
                filter_frame,
                text=level,
                variable=var,
                font=self.theme.font(11),
                text_color=color,
                checkmark_color=color,
                border_color=self.theme.c("border"),
                fg_color=color,
                hover_color=self.theme.c("bg_card"),
            ).pack(side="left", padx=8, pady=4)

        # Área de logs (textbox scrollável)
        self._log_box = ctk.CTkTextbox(
            self,
            font=self.theme.font_mono(12),
            fg_color=self.theme.c("bg_secondary"),
            text_color=self.theme.c("text_primary"),
            border_color=self.theme.c("border"),
            border_width=1,
            corner_radius=8,
            wrap="word",
            state="disabled",
        )
        self._log_box.grid(row=2, column=0, padx=24, pady=(0, 8), sticky="nsew")

        # Painel de status por arquivo
        status_section = ctk.CTkFrame(
            self,
            fg_color=self.theme.c("bg_secondary"),
            corner_radius=12,
            border_color=self.theme.c("border"),
            border_width=1,
        )
        status_section.grid(row=3, column=0, padx=24, pady=(0, 24), sticky="ew")
        status_section.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            status_section,
            text="Resumo da Sincronização",
            font=self.theme.font_subtitle(),
            text_color=self.theme.c("text_primary"),
        ).grid(row=0, column=0, padx=20, pady=(14, 6), sticky="w")

        counts_frame = ctk.CTkFrame(status_section, fg_color="transparent")
        counts_frame.grid(row=1, column=0, padx=20, pady=(0, 14), sticky="ew")

        self._stat_labels: dict[str, ctk.CTkLabel] = {}
        stats = [
            ("synced", "✓ Sincronizados", "#34A853"),
            ("pending", "⏳ Pendentes", "#FBBC04"),
            ("error", "✕ Erros", "#EA4335"),
            ("uploading", "⬆ Enviando", "#4285F4"),
            ("downloading", "⬇ Baixando", "#4285F4"),
        ]
        for i, (key, label, color) in enumerate(stats):
            ctk.CTkLabel(
                counts_frame,
                text=label,
                font=self.theme.font(11),
                text_color=color,
            ).grid(row=0, column=i * 2, padx=(0, 4))
            lbl = ctk.CTkLabel(
                counts_frame,
                text="0",
                font=self.theme.font(13, "bold"),
                text_color=color,
            )
            lbl.grid(row=0, column=i * 2 + 1, padx=(0, 16))
            self._stat_labels[key] = lbl

        # Botão de refresh dos stats
        ctk.CTkButton(
            status_section,
            text="↻",
            width=32,
            height=32,
            fg_color="transparent",
            text_color=self.theme.c("text_secondary"),
            font=self.theme.font(16),
            command=self._refresh_stats,
        ).grid(row=0, column=1, padx=12, pady=8)

        self._refresh_stats()

    # ── Log entries ────────────────────────────────────────────────────────

    def _register_callback(self) -> None:
        """Registra callback no logger para receber novos logs."""
        self.logger.register_callback(self._on_new_log)

    def _load_existing_logs(self) -> None:
        """Carrega logs existentes na inicialização."""
        for entry in self.logger.get_recent_logs(200):
            level = entry.get("level", "INFO")
            msg = f"[{entry['timestamp']}] [{level}] {entry['message']}"
            self._append_line(level, msg)

    def _on_new_log(self, level: str, formatted: str) -> None:
        """Callback chamado pela thread de logger — atualiza UI via after()."""
        if self._paused:
            return
        if not self._filter_vars.get(level, ctk.BooleanVar(value=True)).get():
            return
        self.after(0, lambda: self._append_line(level, formatted))

    def _append_line(self, level: str, text: str) -> None:
        """Insere linha colorida no textbox."""
        try:
            self._log_box.configure(state="normal")
            color = LEVEL_COLORS.get(level, self.theme.c("text_secondary"))
            self._log_box.insert("end", text + "\n")

            # CTkTextbox não suporta tag_config completo; usamos inserção simples
            # Para colorir individualmente seria necessário tk.Text subjacente
            line_count = int(self._log_box.index("end").split(".")[0])
            if line_count > self._max_lines:
                self._log_box.delete("1.0", "2.0")

            self._log_box.see("end")
            self._log_box.configure(state="disabled")
        except Exception:
            pass

    def _clear_logs(self) -> None:
        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.configure(state="disabled")

    def _toggle_pause(self) -> None:
        self._paused = not self._paused
        self._pause_btn.configure(
            text="▶  Retomar" if self._paused else "⏸  Pausar"
        )

    def _refresh_stats(self) -> None:
        """Atualiza contadores de status de arquivos."""
        try:
            counts = self.sync_state.count_by_status()
            for key, lbl in self._stat_labels.items():
                lbl.configure(text=str(counts.get(key, 0)))
        except Exception:
            pass

    def destroy(self) -> None:
        """Limpa o callback ao destruir a tela."""
        try:
            self.logger.unregister_callback(self._on_new_log)
        except Exception:
            pass
        super().destroy()
