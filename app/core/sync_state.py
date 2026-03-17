"""
Rastreamento do estado de sincronização de cada arquivo.
Mantém o mapeamento entre arquivos locais ↔ IDs do Drive.
"""

import json
import threading
from enum import Enum
from pathlib import Path
from typing import Optional


class FileStatus(str, Enum):
    SYNCED = "synced"         # Sincronizado
    PENDING = "pending"       # Aguardando sincronização
    UPLOADING = "uploading"   # Enviando para o Drive
    DOWNLOADING = "downloading"  # Baixando do Drive
    CONFLICT = "conflict"     # Conflito detectado
    ERROR = "error"           # Erro na sincronização
    IGNORED = "ignored"       # Ignorado por regra


class SyncState:
    """
    Mantém estado de sincronização persistido em disco.
    Mapeia caminhos locais → metadados de sincronização.
    """

    def __init__(self, state_file: Path):
        self.state_file = state_file
        self._data: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self) -> None:
        """Carrega estado do disco."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._data = {}

    def _save(self) -> None:
        """Persiste estado no disco."""
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)

    def get(self, local_path: str) -> dict:
        """Retorna metadados de sync de um arquivo."""
        with self._lock:
            return self._data.get(local_path, {})

    def set(
        self,
        local_path: str,
        drive_id: Optional[str] = None,
        drive_parent_id: Optional[str] = None,
        status: FileStatus = FileStatus.SYNCED,
        checksum: Optional[str] = None,
        modified_time: Optional[str] = None,
    ) -> None:
        """Define ou atualiza o estado de um arquivo."""
        with self._lock:
            existing = self._data.get(local_path, {})
            self._data[local_path] = {
                **existing,
                "drive_id": drive_id or existing.get("drive_id"),
                "drive_parent_id": drive_parent_id or existing.get("drive_parent_id"),
                "status": status.value,
                "checksum": checksum or existing.get("checksum"),
                "modified_time": modified_time or existing.get("modified_time"),
            }
            self._save()

    def update_status(self, local_path: str, status: FileStatus) -> None:
        """Atualiza apenas o status de um arquivo."""
        with self._lock:
            if local_path in self._data:
                self._data[local_path]["status"] = status.value
            else:
                self._data[local_path] = {"status": status.value}
            self._save()

    def remove(self, local_path: str) -> None:
        """Remove entrada do estado."""
        with self._lock:
            self._data.pop(local_path, None)
            self._save()

    def get_drive_id(self, local_path: str) -> Optional[str]:
        """Atalho para obter o ID no Drive de um arquivo."""
        return self.get(local_path).get("drive_id")

    def get_all(self) -> dict[str, dict]:
        """Retorna cópia de todos os estados."""
        with self._lock:
            return self._data.copy()

    def get_by_status(self, status: FileStatus) -> list[str]:
        """Retorna caminhos de arquivos com determinado status."""
        with self._lock:
            return [
                path
                for path, meta in self._data.items()
                if meta.get("status") == status.value
            ]

    def count_by_status(self) -> dict[str, int]:
        """Contagem de arquivos por status."""
        with self._lock:
            counts: dict[str, int] = {}
            for meta in self._data.values():
                s = meta.get("status", "unknown")
                counts[s] = counts.get(s, 0) + 1
            return counts
