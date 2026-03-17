"""
Monitoramento de alterações no sistema de arquivos local usando watchdog.
Emite eventos para o motor de sincronização processar.
"""

import threading
import time
from pathlib import Path
from typing import Callable

from watchdog.events import (
    FileCreatedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileMovedEvent,
    FileSystemEventHandler,
)
from watchdog.observers import Observer

from app.utils.logger import get_logger

# Tipo de callback: (event_type, src_path, dest_path?)
ChangeCallback = Callable[[str, str, str | None], None]

# Extensões ignoradas (temporários, locks, etc.)
IGNORED_EXTENSIONS = {
    ".tmp", ".temp", ".swp", ".swo", ".lock",
    "~", ".DS_Store", ".part",
}
IGNORED_PREFIXES = {".", "~"}


def _should_ignore(path: str) -> bool:
    """Verifica se o arquivo deve ser ignorado."""
    p = Path(path)
    name = p.name
    # Ignora arquivos ocultos e temporários
    if any(name.startswith(prefix) for prefix in IGNORED_PREFIXES):
        return True
    if p.suffix.lower() in IGNORED_EXTENSIONS:
        return True
    return False


class _EventHandler(FileSystemEventHandler):
    """Handler de eventos do watchdog com debounce."""

    def __init__(self, callback: ChangeCallback, debounce_secs: float = 1.5):
        super().__init__()
        self.callback = callback
        self.debounce_secs = debounce_secs
        self.logger = get_logger()
        self._pending: dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

    def _schedule(self, event_type: str, src: str, dest: str | None = None) -> None:
        """Agenda chamada com debounce para evitar disparos múltiplos."""
        if _should_ignore(src):
            return

        key = src
        with self._lock:
            if key in self._pending:
                self._pending[key].cancel()

            timer = threading.Timer(
                self.debounce_secs,
                self._fire,
                args=(event_type, src, dest),
            )
            self._pending[key] = timer
            timer.start()

    def _fire(self, event_type: str, src: str, dest: str | None) -> None:
        """Dispara o callback após o debounce."""
        with self._lock:
            self._pending.pop(src, None)
        try:
            self.callback(event_type, src, dest)
        except Exception as e:
            self.logger.error(f"Erro no callback de mudança: {e}")

    def on_created(self, event):
        if not event.is_directory:
            self._schedule("created", event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._schedule("modified", event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            self._schedule("deleted", event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self._schedule("moved", event.src_path, event.dest_path)


class FileWatcher:
    """
    Gerencia observers do watchdog para múltiplas pastas.
    Chama o callback sempre que arquivos são criados, modificados,
    deletados ou movidos.
    """

    def __init__(self, callback: ChangeCallback):
        self.callback = callback
        self.logger = get_logger()
        self._observer: Observer | None = None
        self._watches: dict[str, object] = {}  # path → Watch
        self._lock = threading.Lock()
        self._running = False

    def start(self) -> None:
        """Inicia o observer."""
        if self._running:
            return
        self._observer = Observer()
        self._observer.start()
        self._running = True
        self.logger.info("FileWatcher iniciado.")

    def stop(self) -> None:
        """Para todos os observers."""
        self._running = False
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
        self.logger.info("FileWatcher parado.")

    def add_folder(self, folder_path: str) -> bool:
        """Adiciona pasta ao monitoramento. Retorna False se já monitorada."""
        path = str(Path(folder_path).resolve())
        with self._lock:
            if path in self._watches:
                return False
            if not self._observer:
                return False

            handler = _EventHandler(self.callback)
            watch = self._observer.schedule(handler, path, recursive=True)
            self._watches[path] = watch
            self.logger.info(f"Monitorando: {path}")
        return True

    def remove_folder(self, folder_path: str) -> bool:
        """Remove pasta do monitoramento."""
        path = str(Path(folder_path).resolve())
        with self._lock:
            watch = self._watches.pop(path, None)
            if watch and self._observer:
                self._observer.unschedule(watch)
                self.logger.info(f"Parou de monitorar: {path}")
                return True
        return False

    def update_folders(self, folder_paths: list[str]) -> None:
        """Sincroniza o conjunto de pastas monitoradas com a lista fornecida."""
        desired = {str(Path(p).resolve()) for p in folder_paths}
        current = set(self._watches.keys())

        for p in desired - current:
            self.add_folder(p)
        for p in current - desired:
            self.remove_folder(p)

    @property
    def monitored_folders(self) -> list[str]:
        """Lista de pastas atualmente monitoradas."""
        with self._lock:
            return list(self._watches.keys())
