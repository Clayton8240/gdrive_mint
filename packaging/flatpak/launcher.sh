#!/usr/bin/env bash
# Lançador da aplicação dentro do ambiente Flatpak.
# Instalado em /app/bin/gdrive-mint pelo manifesto YAML.

export PYTHONPATH=/app/lib/python3.12/site-packages:$PYTHONPATH
exec python3 /app/gdrive-mint/main.py "$@"
