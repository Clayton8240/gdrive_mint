"""
Sistema de logging centralizado da aplicação.
Permite logs no arquivo, no console e callbacks para a UI.
"""

import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Callable


class AppLogger:
    """Logger centralizado com suporte a callbacks para atualização da UI."""

    _instance: "AppLogger | None" = None
    _lock = threading.Lock()

    def __new__(cls, log_dir: Path | None = None):
        with cls._lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance._initialized = False
                cls._instance = instance
        return cls._instance

    def __init__(self, log_dir: Path | None = None):
        if self._initialized:
            return
        self._initialized = True

        self.callbacks: list[Callable[[str, str], None]] = []
        self.log_entries: list[dict] = []
        self._cb_lock = threading.Lock()

        # Configura logger padrão do Python
        self.logger = logging.getLogger("GDriveMint")
        self.logger.setLevel(logging.DEBUG)

        if log_dir:
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "gdrive_mint.log"
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            fmt = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(fmt)
            self.logger.addHandler(file_handler)

        # Handler para console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(
            logging.Formatter("[%(levelname)s] %(message)s")
        )
        self.logger.addHandler(console_handler)

    def register_callback(self, cb: Callable[[str, str], None]) -> None:
        """Registra callback chamado a cada novo log. cb(level, message)."""
        with self._cb_lock:
            self.callbacks.append(cb)

    def unregister_callback(self, cb: Callable[[str, str], None]) -> None:
        """Remove callback registrado."""
        with self._cb_lock:
            if cb in self.callbacks:
                self.callbacks.remove(cb)

    def _emit(self, level: str, message: str) -> None:
        """Emite log e notifica callbacks."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = {"timestamp": timestamp, "level": level, "message": message}
        self.log_entries.append(entry)

        # Mantém no máximo 1000 entradas em memória
        if len(self.log_entries) > 1000:
            self.log_entries = self.log_entries[-1000:]

        formatted = f"[{timestamp}] [{level}] {message}"
        with self._cb_lock:
            for cb in self.callbacks:
                try:
                    cb(level, formatted)
                except Exception:
                    pass

    def info(self, message: str) -> None:
        self.logger.info(message)
        self._emit("INFO", message)

    def warning(self, message: str) -> None:
        self.logger.warning(message)
        self._emit("WARNING", message)

    def error(self, message: str) -> None:
        self.logger.error(message)
        self._emit("ERROR", message)

    def success(self, message: str) -> None:
        """Nível customizado para operações bem-sucedidas."""
        self.logger.info(f"[SUCCESS] {message}")
        self._emit("SUCCESS", message)

    def debug(self, message: str) -> None:
        self.logger.debug(message)
        self._emit("DEBUG", message)

    def get_recent_logs(self, limit: int = 200) -> list[dict]:
        """Retorna as últimas N entradas de log."""
        return self.log_entries[-limit:]


# Instância global (Singleton)
_logger_instance: AppLogger | None = None


def get_logger(log_dir: Path | None = None) -> AppLogger:
    """Retorna a instância global do logger."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = AppLogger(log_dir)
    return _logger_instance
