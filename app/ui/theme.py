"""
Paleta de cores, configuração de tema e utilitários visuais.
Suporta tema claro/escuro com CustomTkinter.
"""

import customtkinter as ctk

# ── Paletas ────────────────────────────────────────────────────────────────

COLORS = {
    "dark": {
        "bg_primary": "#1a1a2e",
        "bg_secondary": "#16213e",
        "bg_card": "#0f3460",
        "sidebar_bg": "#12121f",
        "accent": "#4285F4",
        "accent_hover": "#5a95f5",
        "accent_danger": "#EA4335",
        "accent_success": "#34A853",
        "accent_warning": "#FBBC04",
        "text_primary": "#e0e0e0",
        "text_secondary": "#9e9e9e",
        "text_muted": "#616161",
        "border": "#2a2a4a",
        "progress_bg": "#2a2a4a",
    },
    "light": {
        "bg_primary": "#f5f5f5",
        "bg_secondary": "#ffffff",
        "bg_card": "#e8f0fe",
        "sidebar_bg": "#e0e0f0",
        "accent": "#1a73e8",
        "accent_hover": "#1557b0",
        "accent_danger": "#d93025",
        "accent_success": "#188038",
        "accent_warning": "#e37400",
        "text_primary": "#202124",
        "text_secondary": "#5f6368",
        "text_muted": "#9aa0a6",
        "border": "#dadce0",
        "progress_bg": "#e0e0e0",
    },
}

# Fonte padrão
FONT_FAMILY = "Segoe UI"

# Mapeamento CustomTkinter
_CTK_MODE = {"dark": "dark", "light": "light"}


class ThemeManager:
    """Gerencia o tema da aplicação (claro/escuro)."""

    def __init__(self, initial_theme: str = "dark"):
        self._theme = initial_theme
        self._apply_ctk_theme()

    def _apply_ctk_theme(self) -> None:
        """Aplica tema no CustomTkinter."""
        ctk.set_appearance_mode(_CTK_MODE.get(self._theme, "dark"))
        ctk.set_default_color_theme("blue")

    @property
    def current(self) -> str:
        return self._theme

    @property
    def colors(self) -> dict:
        return COLORS[self._theme]

    def toggle(self) -> str:
        """Alterna entre claro e escuro. Retorna o novo tema."""
        self._theme = "light" if self._theme == "dark" else "dark"
        self._apply_ctk_theme()
        return self._theme

    def set(self, theme: str) -> None:
        """Define tema explicitamente ('dark' ou 'light')."""
        if theme in COLORS:
            self._theme = theme
            self._apply_ctk_theme()

    def c(self, key: str) -> str:
        """Atalho para obter cor do tema atual."""
        return COLORS[self._theme].get(key, "#ffffff")

    # ── Fábricas de fontes ─────────────────────────────────────────────────

    def font(self, size: int = 13, weight: str = "normal") -> ctk.CTkFont:
        return ctk.CTkFont(family=FONT_FAMILY, size=size, weight=weight)

    def font_title(self) -> ctk.CTkFont:
        return self.font(22, "bold")

    def font_subtitle(self) -> ctk.CTkFont:
        return self.font(15, "bold")

    def font_body(self) -> ctk.CTkFont:
        return self.font(13)

    def font_small(self) -> ctk.CTkFont:
        return self.font(11)

    def font_mono(self, size: int = 12) -> ctk.CTkFont:
        return ctk.CTkFont(family="Monospace", size=size)


# Instância global compartilhada
theme = ThemeManager("dark")
