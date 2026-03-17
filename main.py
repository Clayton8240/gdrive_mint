#!/usr/bin/env python3
"""
GDrive Mint — Ponto de entrada principal.
Sincronização com Google Drive para Linux Mint.

Uso:
    python main.py

Requisitos:
    - credentials.json em ~/.config/gdrive_mint/
    - Ver README.md para configuração completa
"""

import sys
import os

# Garante que o diretório raiz do projeto esteja no PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.ui.app_window import AppWindow


def main() -> None:
    """Ponto de entrada principal da aplicação."""
    app = AppWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
