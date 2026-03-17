"""
Tela de gerenciamento de pastas sincronizadas.
"""

import tkinter.filedialog as fd
import customtkinter as ctk

from app.ui.theme import ThemeManager

SYNC_MODES = {
    "bidirectional": ("🔁", "Bidirecional"),
    "upload": ("⬆", "Somente Upload"),
    "download": ("⬇", "Somente Download"),
}


class FolderRow(ctk.CTkFrame):
    """Linha de uma pasta na lista de sincronização."""

    def __init__(self, parent, theme: ThemeManager, folder_cfg: dict, on_remove, on_mode_change, **kwargs):
        super().__init__(
            parent,
            corner_radius=8,
            fg_color=theme.c("bg_secondary"),
            border_color=theme.c("border"),
            border_width=1,
            **kwargs,
        )
        self.theme = theme
        self.folder_cfg = folder_cfg
        self.on_remove = on_remove
        self.on_mode_change = on_mode_change
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(1, weight=1)

        # Ícone
        ctk.CTkLabel(
            self, text="📁", font=ctk.CTkFont(size=20)
        ).grid(row=0, column=0, padx=(12, 8), pady=10)

        # Caminho
        path = self.folder_cfg.get("path", "")
        ctk.CTkLabel(
            self,
            text=path,
            font=self.theme.font(12),
            text_color=self.theme.c("text_primary"),
            anchor="w",
        ).grid(row=0, column=1, sticky="ew", pady=10)

        # Seletor de modo
        current_mode = self.folder_cfg.get("sync_mode", "bidirectional")
        mode_values = [v[1] for v in SYNC_MODES.values()]
        mode_keys = list(SYNC_MODES.keys())
        mode_labels = [f"{SYNC_MODES[k][0]}  {SYNC_MODES[k][1]}" for k in mode_keys]

        # Índice do modo atual
        try:
            idx = mode_keys.index(current_mode)
        except ValueError:
            idx = 0

        self._mode_var = ctk.StringVar(value=mode_labels[idx])

        mode_menu = ctk.CTkOptionMenu(
            self,
            values=mode_labels,
            variable=self._mode_var,
            fg_color=self.theme.c("bg_card"),
            button_color=self.theme.c("accent"),
            button_hover_color=self.theme.c("accent_hover"),
            text_color=self.theme.c("text_primary"),
            font=self.theme.font(12),
            width=180,
            command=self._on_mode_changed,
        )
        mode_menu.grid(row=0, column=2, padx=8, pady=8)

        # Toggle ativo
        self._enabled_var = ctk.BooleanVar(value=self.folder_cfg.get("enabled", True))
        ctk.CTkSwitch(
            self,
            text="",
            variable=self._enabled_var,
            onvalue=True,
            offvalue=False,
            progress_color=self.theme.c("accent"),
            command=self._on_toggle,
        ).grid(row=0, column=3, padx=8, pady=8)

        # Botão remover
        ctk.CTkButton(
            self,
            text="✕",
            width=32,
            height=32,
            corner_radius=8,
            fg_color=self.theme.c("accent_danger"),
            hover_color="#c0392b",
            font=self.theme.font(13, "bold"),
            command=lambda: self.on_remove(self.folder_cfg["path"]),
        ).grid(row=0, column=4, padx=(4, 12), pady=8)

    def _on_mode_changed(self, label: str) -> None:
        # Encontra a chave correspondente ao label
        for key, (icon, name) in SYNC_MODES.items():
            if name in label:
                self.on_mode_change(self.folder_cfg["path"], key)
                self.folder_cfg["sync_mode"] = key
                break

    def _on_toggle(self) -> None:
        enabled = self._enabled_var.get()
        self.on_mode_change(self.folder_cfg["path"], self.folder_cfg.get("sync_mode", "bidirectional"), enabled)


class FoldersScreen(ctk.CTkFrame):
    """Tela de gerenciamento de pastas de sincronização."""

    def __init__(self, parent, theme: ThemeManager, config, engine, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.theme = theme
        self.config = config
        self.engine = engine
        self._folder_rows: list[FolderRow] = []
        self._build()
        self._load_folders()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)

        # Cabeçalho
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=24, pady=(24, 8), sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Pastas Sincronizadas",
            font=self.theme.font_title(),
            text_color=self.theme.c("text_primary"),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            header,
            text="Gerencie quais pastas locais serão sincronizadas com o Google Drive",
            font=self.theme.font_small(),
            text_color=self.theme.c("text_secondary"),
        ).grid(row=1, column=0, sticky="w")

        # Botão adicionar pasta
        ctk.CTkButton(
            header,
            text="＋  Adicionar pasta",
            font=self.theme.font(13, "bold"),
            fg_color=self.theme.c("accent"),
            hover_color=self.theme.c("accent_hover"),
            width=180,
            height=38,
            corner_radius=10,
            command=self._add_folder,
        ).grid(row=0, column=1, rowspan=2, padx=(8, 0))

        # Legenda de modos
        legend = ctk.CTkFrame(self, fg_color=self.theme.c("bg_secondary"), corner_radius=8)
        legend.grid(row=1, column=0, padx=24, pady=(0, 12), sticky="ew")

        for i, (key, (icon, label)) in enumerate(SYNC_MODES.items()):
            ctk.CTkLabel(
                legend,
                text=f"{icon}  {label}",
                font=self.theme.font_small(),
                text_color=self.theme.c("text_secondary"),
            ).grid(row=0, column=i, padx=16, pady=8)

        # Área de lista (scrollável)
        self._scroll_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=self.theme.c("border"),
        )
        self._scroll_frame.grid(row=2, column=0, padx=24, pady=8, sticky="nsew")
        self._scroll_frame.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Placeholder (nenhuma pasta)
        self._empty_label = ctk.CTkLabel(
            self._scroll_frame,
            text="Nenhuma pasta adicionada ainda.\nClique em '+ Adicionar pasta' para começar.",
            font=self.theme.font(13),
            text_color=self.theme.c("text_muted"),
            justify="center",
        )

    def _load_folders(self) -> None:
        """Carrega pastas salvas na configuração."""
        self._clear_rows()
        folders = self.config.get_folders()
        if not folders:
            self._empty_label.pack(pady=48)
        else:
            self._empty_label.pack_forget()
            for folder in folders:
                self._add_row(folder)

    def _add_folder(self) -> None:
        """Abre diálogo para selecionar pasta."""
        path = fd.askdirectory(title="Selecionar pasta para sincronização")
        if not path:
            return

        added = self.config.add_folder(path, sync_mode="bidirectional")
        if added:
            self._empty_label.pack_forget()
            folder_cfg = {"path": path, "sync_mode": "bidirectional", "enabled": True}
            self._add_row(folder_cfg)
            if self.engine.is_running:
                self.engine.refresh_config()

    def _add_row(self, folder_cfg: dict) -> None:
        """Adiciona linha de pasta à lista."""
        row = FolderRow(
            self._scroll_frame,
            self.theme,
            folder_cfg,
            on_remove=self._remove_folder,
            on_mode_change=self._update_mode,
        )
        row.pack(fill="x", pady=4, padx=4)
        self._folder_rows.append(row)

    def _remove_folder(self, path: str) -> None:
        """Remove pasta da sincronização."""
        self.config.remove_folder(path)
        if self.engine.is_running:
            self.engine.watcher.remove_folder(path)

        # Remove row da UI
        for row in self._folder_rows[:]:
            if row.folder_cfg.get("path") == path:
                row.pack_forget()
                row.destroy()
                self._folder_rows.remove(row)
                break

        if not self._folder_rows:
            self._empty_label.pack(pady=48)

    def _update_mode(self, path: str, mode: str, enabled: bool = None) -> None:
        """Atualiza modo de sincronização de uma pasta."""
        update_kwargs = {"sync_mode": mode}
        if enabled is not None:
            update_kwargs["enabled"] = enabled
        self.config.update_folder(path, **update_kwargs)

    def _clear_rows(self) -> None:
        """Remove todas as linhas da lista."""
        for row in self._folder_rows:
            row.destroy()
        self._folder_rows.clear()
