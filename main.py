#!/usr/bin/env python3
"""
GDrive Mint — Ponto de entrada principal.
Sincronizacao com Google Drive para Linux Mint.

Uso:
    python main.py

Requisitos:
    - credentials.json em ~/.config/gdrive_mint/
    - Ver README.md para configuracao completa
"""

import sys
import os

# Garante que o diretorio raiz do projeto esteja no PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path

from app.utils.security import run_startup_checks


def _run_security_preflight() -> None:
    """
    Executa verificacoes de seguranca antes de inicializar a UI.
    Erros fatais encerram a aplicacao; avisos sao impressos no stderr.
    """
    app_data_dir = Path.home() / ".local" / "share" / "gdrive_mint"
    app_config_dir = Path.home() / ".config" / "gdrive_mint"

    result = run_startup_checks(app_data_dir, app_config_dir)

    for warning in result.warnings:
        print(f"[SEGURANCA AVISO] {warning}", file=sys.stderr)

    if not result.passed:
        for error in result.errors:
            print(f"[SEGURANCA ERRO] {error}", file=sys.stderr)
        sys.exit(1)


from app.ui.app_window import AppWindow


def main() -> None:
    """Ponto de entrada principal da aplicacao."""
    _run_security_preflight()
    app = AppWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
