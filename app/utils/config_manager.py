"""
Gerenciador de configurações da aplicação.
Salva e carrega configurações em JSON com validação.
"""

import json
import threading
from pathlib import Path
from typing import Any


# Configurações padrão
DEFAULT_CONFIG: dict[str, Any] = {
    "theme": "dark",
    "sync_interval_minutes": 15,
    "bandwidth_limit_kbps": 0,  # 0 = sem limite
    "start_with_system": False,
    "default_directory": str(Path.home() / "GoogleDrive"),
    "folders": [],  # Lista de {path, sync_mode, enabled}
    "minimize_to_tray": True,
    "notifications_enabled": True,
    "last_sync": None,
    "auto_resolve_conflicts": False,
}


class ConfigManager:
    """Gerencia configurações da aplicação com persistência em JSON."""

    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.config_file = config_dir / "config.json"
        self._config: dict[str, Any] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self) -> None:
        """Carrega configurações do disco."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                # Mescla com defaults para garantir novas chaves
                self._config = {**DEFAULT_CONFIG, **loaded}
            except (json.JSONDecodeError, IOError):
                self._config = DEFAULT_CONFIG.copy()
        else:
            self._config = DEFAULT_CONFIG.copy()
            self._save()

    def _save(self) -> None:
        """Salva configurações no disco (thread-safe)."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=2, ensure_ascii=False)

    def get(self, key: str, default: Any = None) -> Any:
        """Obtém valor de configuração."""
        with self._lock:
            return self._config.get(key, default)

    def set(self, key: str, value: Any, auto_save: bool = True) -> None:
        """Define valor de configuração e salva automaticamente."""
        with self._lock:
            self._config[key] = value
            if auto_save:
                self._save()

    def update(self, updates: dict[str, Any], auto_save: bool = True) -> None:
        """Atualiza múltiplos valores de uma vez."""
        with self._lock:
            self._config.update(updates)
            if auto_save:
                self._save()

    def get_all(self) -> dict[str, Any]:
        """Retorna cópia de todas as configurações."""
        with self._lock:
            return self._config.copy()

    # ── Atalhos para pastas ────────────────────────────────────────────────

    def get_folders(self) -> list[dict]:
        """Retorna lista de pastas configuradas."""
        return self.get("folders", [])

    def add_folder(self, path: str, sync_mode: str = "bidirectional") -> bool:
        """Adiciona pasta de sincronização. Retorna False se já existe."""
        with self._lock:
            folders = self._config.get("folders", [])
            if any(f["path"] == path for f in folders):
                return False
            folders.append({"path": path, "sync_mode": sync_mode, "enabled": True})
            self._config["folders"] = folders
            self._save()
        return True

    def remove_folder(self, path: str) -> bool:
        """Remove pasta de sincronização. Retorna False se não encontrada."""
        with self._lock:
            folders = self._config.get("folders", [])
            new_folders = [f for f in folders if f["path"] != path]
            if len(new_folders) == len(folders):
                return False
            self._config["folders"] = new_folders
            self._save()
        return True

    def update_folder(self, path: str, **kwargs) -> bool:
        """Atualiza configuração de uma pasta específica."""
        with self._lock:
            folders = self._config.get("folders", [])
            for folder in folders:
                if folder["path"] == path:
                    folder.update(kwargs)
                    self._config["folders"] = folders
                    self._save()
                    return True
        return False

    def save(self) -> None:
        """Salva configurações manualmente."""
        with self._lock:
            self._save()
