"""
Motor principal de sincronizacao.
Orquestra upload, download, monitoramento e resolucao de conflitos.

Auditoria de seguranca aplicada:
- Path Traversal bloqueado: nomes de arquivo do Drive sao sanitizados
  (Path(name).name + verificacao que o resultado esta dentro do diretorio alvo)
- Symlinks ignorados no upload (evita vazar /etc/shadow ou similar)
- Contadores de sessao protegidos por lock (evita race conditions)
- sync_mode validado contra allowlist
- Limite de tamanho no download (512 MB por arquivo como padrao)
"""

import hashlib
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from app.core.conflict_resolver import ConflictResolver, ConflictStrategy
from app.core.file_watcher import FileWatcher
from app.core.sync_state import FileStatus, SyncState
from app.services.drive_service import DriveService
from app.utils.config_manager import ConfigManager
from app.utils.logger import get_logger
from app.utils.notifications import NotificationManager

# Callback de status: (message, level)
StatusCallback = Callable[[str, str], None]

# Modos de sincronizacao permitidos (allowlist)
_VALID_SYNC_MODES = frozenset({"bidirectional", "upload", "download"})

# Limite padrao de tamanho de arquivo para download: 512 MB
_MAX_DOWNLOAD_SIZE = 512 * 1024 * 1024


class SyncEngine:
    """
    Orquestrador central de sincronização.
    Gerencia monitoramento, upload, download e conflitos.
    """

    def __init__(
        self,
        drive_service: DriveService,
        config: ConfigManager,
        state: SyncState,
        notifications: NotificationManager,
    ):
        self.drive = drive_service
        self.config = config
        self.state = state
        self.notifications = notifications
        self.logger = get_logger()

        self._running = False
        self._paused = False
        self._lock = threading.Lock()
        self._auto_sync_thread: Optional[threading.Thread] = None

        self._status_callbacks: list[StatusCallback] = []

        self.conflict_resolver = ConflictResolver(
            strategy=ConflictStrategy.RENAME_LOCAL
        )

        # FileWatcher é inicializado sem pastas; adicionadas via update_folders()
        self.watcher = FileWatcher(callback=self._on_file_changed)

        # Contadores de sessao protegidos por lock (multiplos threads)
        self._counter_lock = threading.Lock()
        self.uploaded_count = 0
        self.downloaded_count = 0
        self.error_count = 0
        self.last_sync_time: Optional[datetime] = None

    # ── Callbacks de status ────────────────────────────────────────────────

    def register_status_callback(self, cb: StatusCallback) -> None:
        """Registra callback chamado a cada mudança de status."""
        self._status_callbacks.append(cb)

    def _emit_status(self, message: str, level: str = "info") -> None:
        """Emite evento de status para todos os callbacks registrados."""
        for cb in self._status_callbacks:
            try:
                cb(message, level)
            except Exception:
                pass

    # ── Ciclo de vida ──────────────────────────────────────────────────────

    def start(self) -> None:
        """Inicia o motor: watcher e loop de sync automático."""
        if self._running:
            return
        self._running = True
        self._paused = False

        self.watcher.start()
        self._update_watcher_folders()
        self._start_auto_sync_loop()
        self.logger.info("Motor de sincronização iniciado.")
        self._emit_status("Motor de sincronização iniciado.", "success")

    def stop(self) -> None:
        """Para o motor e todas as threads."""
        self._running = False
        self.watcher.stop()
        if self._auto_sync_thread and self._auto_sync_thread.is_alive():
            self._auto_sync_thread.join(timeout=5)
        self.logger.info("Motor de sincronização parado.")

    def pause(self) -> None:
        """Pausa a sincronização automática (watcher continua em fila)."""
        self._paused = True
        self._emit_status("Sincronização pausada.", "warning")

    def resume(self) -> None:
        """Retoma a sincronização."""
        self._paused = False
        self._emit_status("Sincronização retomada.", "info")

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_paused(self) -> bool:
        return self._paused

    # ── Sincronização manual ───────────────────────────────────────────────

    def sync_now(self, progress_callback: Optional[Callable[[float, str], None]] = None) -> None:
        """Executa sincronização completa em thread separada."""
        thread = threading.Thread(
            target=self._full_sync,
            args=(progress_callback,),
            daemon=True,
        )
        thread.start()

    def _full_sync(self, progress_cb: Optional[Callable[[float, str], None]] = None) -> None:
        """Executa ciclo completo de sincronização por todas as pastas."""
        folders = self.config.get_folders()
        if not folders:
            self._emit_status("Nenhuma pasta configurada para sincronização.", "warning")
            return

        enabled_folders = [f for f in folders if f.get("enabled", True)]
        total = len(enabled_folders)

        self._emit_status("Iniciando sincronização...", "info")

        for i, folder_cfg in enumerate(enabled_folders):
            if not self._running or self._paused:
                break

            folder_path = folder_cfg["path"]
            # Valida sync_mode contra allowlist antes de usar
            raw_mode = folder_cfg.get("sync_mode", "bidirectional")
            sync_mode = raw_mode if raw_mode in _VALID_SYNC_MODES else "bidirectional"
            if raw_mode not in _VALID_SYNC_MODES:
                self.logger.warning(
                    f"sync_mode invalido '{raw_mode}' para '{Path(folder_path).name}'; "
                    "usando 'bidirectional'."
                )

            progress = i / total
            if progress_cb:
                progress_cb(progress, f"Sincronizando: {Path(folder_path).name}")

            try:
                self._sync_folder(folder_path, sync_mode)
            except Exception as e:
                with self._counter_lock:
                    self.error_count += 1
                self.logger.error(f"Erro ao sincronizar {Path(folder_path).name}: {e}")

        self.last_sync_time = datetime.now()
        self.config.set("last_sync", self.last_sync_time.isoformat())

        if progress_cb:
            progress_cb(1.0, "Sincronização concluída")

        msg = (
            f"Sincronização concluída — "
            f"↑{self.uploaded_count} ↓{self.downloaded_count} "
            f"Erros:{self.error_count}"
        )
        self._emit_status(msg, "success")
        self.notifications.sync_complete(self.uploaded_count + self.downloaded_count)
        self.logger.success(msg)

    def _sync_folder(self, folder_path: str, sync_mode: str) -> None:
        """Sincroniza uma pasta específica com o Drive."""
        local_root = Path(folder_path)
        if not local_root.exists():
            self.logger.warning(f"Pasta não encontrada: {folder_path}")
            return

        folder_name = local_root.name
        self.logger.info(f"Sincronizando pasta: {folder_name} [{sync_mode}]")

        # Garante pasta raiz no Drive
        drive_folder_id = self.drive.find_or_create_folder(folder_name)

        if sync_mode in ("bidirectional", "upload"):
            self._upload_folder_recursive(local_root, drive_folder_id)

        if sync_mode in ("bidirectional", "download"):
            self._download_folder_recursive(drive_folder_id, local_root)

    def _upload_folder_recursive(self, local_dir: Path, drive_parent_id: str) -> None:
        """Faz upload recursivo de arquivos locais para o Drive."""
        try:
            items = list(local_dir.iterdir())
        except PermissionError:
            self.logger.warning(f"Sem permissão: {local_dir}")
            return

        for item in items:
            if not self._running:
                return
            if item.name.startswith("."):
                continue

            # Ignora symlinks: seguir um link poderia expor arquivos fora
            # da pasta de sincronizacao (ex.: link para /etc/shadow)
            if item.is_symlink():
                self.logger.warning(f"Symlink ignorado (seguranca): {item}")
                continue

            if item.is_dir():
                sub_id = self.drive.find_or_create_folder(item.name, drive_parent_id)
                self._upload_folder_recursive(item, sub_id)
            elif item.is_file():
                self._maybe_upload(item, drive_parent_id)

    def _maybe_upload(self, local_file: Path, drive_parent_id: str) -> None:
        """Faz upload somente se o arquivo mudou desde a última sync."""
        local_path_str = str(local_file)
        local_hash = DriveService.compute_md5(local_file)
        state_info = self.state.get(local_path_str)
        stored_hash = state_info.get("checksum")
        drive_id = state_info.get("drive_id")

        if stored_hash == local_hash and drive_id:
            return  # Sem mudanças

        self.state.update_status(local_path_str, FileStatus.UPLOADING)
        self._emit_status(f"Enviando: {local_file.name}", "info")

        try:
            new_id = self.drive.upload_file(
                local_file,
                parent_id=drive_parent_id,
                existing_file_id=drive_id,
            )
            self.state.set(
                local_path_str,
                drive_id=new_id,
                drive_parent_id=drive_parent_id,
                status=FileStatus.SYNCED,
                checksum=local_hash,
            )
            with self._counter_lock:
                self.uploaded_count += 1
            self.notifications.upload_complete(local_file.name)
        except Exception as e:
            self.state.update_status(local_path_str, FileStatus.ERROR)
            with self._counter_lock:
                self.error_count += 1
            self.logger.error(f"Falha no upload de {local_file.name}: {e}")

    def _download_folder_recursive(self, drive_folder_id: str, local_dir: Path) -> None:
        """Baixa arquivos do Drive que não existam ou estejam desatualizados localmente."""
        try:
            remote_files = self.drive.list_files(drive_folder_id)
        except Exception as e:
            self.logger.error(f"Erro ao listar Drive (id={drive_folder_id}): {e}")
            return

        for remote in remote_files:
            if not self._running:
                return

            name = remote["name"]
            mime = remote.get("mimeType", "")
            item_id = remote["id"]

            # ── PATH TRAVERSAL: sanitiza nome vindo da API do Drive ──────
            # Path(name).name extrai apenas o componente final (sem ../ etc.)
            safe_name = Path(name).name
            if not safe_name or safe_name in (".", ".."):
                self.logger.error(
                    "[SEGURANCA] Nome de arquivo invalido bloqueado da API."
                )
                continue
            # Confirma que o caminho resolvido permanece dentro de local_dir
            candidate = (local_dir / safe_name).resolve()
            local_dir_resolved = local_dir.resolve()
            if not str(candidate).startswith(str(local_dir_resolved) + "/"):
                self.logger.error(
                    "[SEGURANCA] Path traversal bloqueado para arquivo remoto."
                )
                continue

            if mime == "application/vnd.google-apps.folder":
                sub_dir = local_dir / safe_name
                sub_dir.mkdir(parents=True, exist_ok=True)
                self._download_folder_recursive(item_id, sub_dir)
                continue

            # Pula Google Docs nativos (nao exportaveis diretamente aqui)
            if mime.startswith("application/vnd.google-apps"):
                continue

            # Verifica limite de tamanho antes de baixar
            try:
                remote_size = int(remote.get("size", 0))
            except (ValueError, TypeError):
                remote_size = 0
            if remote_size > _MAX_DOWNLOAD_SIZE:
                self.logger.warning(
                    f"Arquivo '{safe_name}' ({remote_size // (1024 * 1024)} MB) "
                    f"excede o limite de {_MAX_DOWNLOAD_SIZE // (1024 * 1024)} MB; ignorado."
                )
                continue

            local_file = candidate  # ja validado contra path traversal acima
            remote_hash = remote.get("md5Checksum", "")
            local_path_str = str(local_file)

            # Compara hashes
            if local_file.exists():
                local_hash = DriveService.compute_md5(local_file)
                if local_hash == remote_hash:
                    continue  # Arquivo idêntico

                # Conflito: versões diferentes
                do_download, _ = self.conflict_resolver.resolve(
                    local_file, local_hash, remote_hash,
                    remote.get("modifiedTime", "")
                )
                if not do_download:
                    continue

            self.state.update_status(local_path_str, FileStatus.DOWNLOADING)
            self._emit_status(f"Baixando: {name}", "info")

            try:
                self.drive.download_file(item_id, local_file)
                self.state.set(
                    local_path_str,
                    drive_id=item_id,
                    drive_parent_id=drive_folder_id,
                    status=FileStatus.SYNCED,
                    checksum=remote_hash,
                )
                with self._counter_lock:
                    self.downloaded_count += 1
                self.notifications.download_complete(safe_name)
            except Exception as e:
                self.state.update_status(local_path_str, FileStatus.ERROR)
                with self._counter_lock:
                    self.error_count += 1
                self.logger.error(f"Falha no download de {safe_name}: {e}")

    # ── Loop automático ────────────────────────────────────────────────────

    def _start_auto_sync_loop(self) -> None:
        """Inicia thread do loop de sincronização automática."""
        self._auto_sync_thread = threading.Thread(
            target=self._auto_sync_loop,
            daemon=True,
            name="AutoSyncLoop",
        )
        self._auto_sync_thread.start()

    def _auto_sync_loop(self) -> None:
        """Loop que executa sincronização em intervalos configurados."""
        while self._running:
            interval_min = self.config.get("sync_interval_minutes", 15)
            interval_sec = max(1, interval_min) * 60

            # Aguarda em fatias de 5s para reagir rapidamente ao stop()
            for _ in range(interval_sec // 5):
                if not self._running:
                    return
                time.sleep(5)

            if self._running and not self._paused:
                self._full_sync()

    # ── Eventos do watcher ─────────────────────────────────────────────────

    def _on_file_changed(self, event_type: str, src_path: str, dest_path: str | None) -> None:
        """Chamado pelo FileWatcher quando um arquivo muda."""
        if self._paused:
            self.state.update_status(src_path, FileStatus.PENDING)
            return

        if event_type in ("created", "modified"):
            path = Path(src_path)
            if path.is_file():
                state_info = self.state.get(src_path)
                parent_id = state_info.get("drive_parent_id", "root")
                self._maybe_upload(path, parent_id or "root")

        elif event_type == "deleted":
            self.state.update_status(src_path, FileStatus.IGNORED)

    def _update_watcher_folders(self) -> None:
        """Atualiza as pastas monitoradas pelo FileWatcher."""
        folders = self.config.get_folders()
        enabled = [f["path"] for f in folders if f.get("enabled", True)]
        self.watcher.update_folders(enabled)

    def refresh_config(self) -> None:
        """Relê configurações e atualiza pastas monitoradas."""
        self._update_watcher_folders()
