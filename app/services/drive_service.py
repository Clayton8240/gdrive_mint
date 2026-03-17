"""
Serviço de integração com a Google Drive API v3.
Encapsula todas as operações de arquivo e informações da conta.
"""

import hashlib
import io
import mimetypes
import os
from pathlib import Path
from typing import Callable, Optional

import googleapiclient.discovery as discovery
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

from app.services.google_auth import GoogleAuthService
from app.utils.logger import get_logger

# Mime type para pastas no Drive
FOLDER_MIME = "application/vnd.google-apps.folder"


class DriveService:
    """Wrapper sobre a Google Drive API v3 com operações de alto nível."""

    def __init__(self, auth_service: GoogleAuthService):
        self.auth = auth_service
        self.logger = get_logger()
        self._service = None

    # ── Serviço ───────────────────────────────────────────────────────────

    def _get_service(self):
        """Obtém (ou reconstrói) o serviço Drive autenticado."""
        creds = self.auth.get_credentials()
        if creds is None:
            raise RuntimeError("Usuário não autenticado.")
        if self._service is None:
            self._service = discovery.build("drive", "v3", credentials=creds)
        return self._service

    def invalidate_service(self) -> None:
        """Invalida o serviço para forçar reconstrução na próxima chamada."""
        self._service = None

    # ── Informações da conta ───────────────────────────────────────────────

    def get_storage_info(self) -> dict:
        """
        Retorna informações de armazenamento do Drive.
        {used: int, limit: int, used_pct: float}
        """
        try:
            svc = self._get_service()
            about = svc.about().get(fields="storageQuota").execute()
            quota = about.get("storageQuota", {})
            used = int(quota.get("usageInDrive", 0))
            limit = int(quota.get("limit", 0)) or 1
            return {
                "used": used,
                "limit": limit,
                "used_pct": round(used / limit * 100, 1),
                "used_gb": round(used / 1e9, 2),
                "limit_gb": round(limit / 1e9, 2),
            }
        except Exception as e:
            self.logger.error(f"Erro ao obter espaço: {e}")
            return {"used": 0, "limit": 1, "used_pct": 0.0, "used_gb": 0, "limit_gb": 0}

    # ── Operações com arquivos ─────────────────────────────────────────────

    def list_files(
        self,
        parent_id: str = "root",
        page_size: int = 100,
    ) -> list[dict]:
        """Lista arquivos de uma pasta no Drive."""
        try:
            svc = self._get_service()
            query = f"'{parent_id}' in parents and trashed = false"
            results = (
                svc.files()
                .list(
                    q=query,
                    pageSize=page_size,
                    fields="files(id, name, mimeType, modifiedTime, size, md5Checksum, parents)",
                )
                .execute()
            )
            return results.get("files", [])
        except HttpError as e:
            self.logger.error(f"Erro ao listar arquivos: {e}")
            return []

    def find_or_create_folder(self, name: str, parent_id: str = "root") -> str:
        """
        Busca pasta pelo nome no parent; cria se nao existir.
        Retorna o ID da pasta.
        """
        try:
            svc = self._get_service()
            # Escapa aspas simples no nome para evitar injecao na query do Drive
            safe_name = name.replace("'", "\\'").replace("\\", "")
            query = (
                f"name = '{safe_name}' and mimeType = '{FOLDER_MIME}' "
                f"and '{parent_id}' in parents and trashed = false"
            )
            results = svc.files().list(q=query, fields="files(id)").execute()
            files = results.get("files", [])
            if files:
                return files[0]["id"]

            # Cria nova pasta
            metadata = {
                "name": name,
                "mimeType": FOLDER_MIME,
                "parents": [parent_id],
            }
            folder = svc.files().create(body=metadata, fields="id").execute()
            folder_id = folder["id"]
            self.logger.info(f"Pasta criada no Drive (id={folder_id})")
            return folder_id
        except HttpError as e:
            self.logger.error(f"Erro ao criar pasta: {e}")
            raise

    def upload_file(
        self,
        local_path: Path,
        parent_id: str = "root",
        existing_file_id: Optional[str] = None,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> str:
        """
        Faz upload de um arquivo. Atualiza se existing_file_id fornecido.
        Retorna o ID do arquivo no Drive.
        """
        mime_type, _ = mimetypes.guess_type(str(local_path))
        mime_type = mime_type or "application/octet-stream"

        media = MediaFileUpload(
            str(local_path),
            mimetype=mime_type,
            resumable=True,
        )

        try:
            svc = self._get_service()

            if existing_file_id:
                # Atualiza arquivo existente
                request = svc.files().update(
                    fileId=existing_file_id,
                    media_body=media,
                    fields="id",
                )
            else:
                # Cria novo arquivo
                metadata = {
                    "name": local_path.name,
                    "parents": [parent_id],
                }
                request = svc.files().create(
                    body=metadata,
                    media_body=media,
                    fields="id",
                )

            # Executa upload com progresso
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status and progress_callback:
                    progress_callback(status.progress())

            if progress_callback:
                progress_callback(1.0)

            file_id = response.get("id", existing_file_id or "")
            self.logger.success(f"Upload concluído: {local_path.name} → {file_id}")
            return file_id

        except HttpError as e:
            self.logger.error(f"Erro no upload de {local_path.name}: {e}")
            raise

    def download_file(
        self,
        file_id: str,
        dest_path: Path,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> None:
        """Baixa um arquivo do Drive para o disco local."""
        try:
            svc = self._get_service()
            request = svc.files().get_media(fileId=file_id)
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            with open(dest_path, "wb") as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    if status and progress_callback:
                        progress_callback(status.progress())

            if progress_callback:
                progress_callback(1.0)
            self.logger.success(f"Download concluído: {dest_path.name}")

        except HttpError as e:
            self.logger.error(f"Erro no download (id={file_id}): {e}")
            raise

    def delete_file(self, file_id: str) -> None:
        """Move arquivo para a lixeira do Drive."""
        try:
            svc = self._get_service()
            svc.files().trash(fileId=file_id).execute()
            self.logger.info(f"Arquivo movido para lixeira: {file_id}")
        except HttpError as e:
            self.logger.error(f"Erro ao deletar (id={file_id}): {e}")
            raise

    def get_file_metadata(self, file_id: str) -> dict:
        """Retorna metadados de um arquivo pelo ID."""
        try:
            svc = self._get_service()
            return (
                svc.files()
                .get(
                    fileId=file_id,
                    fields="id, name, mimeType, modifiedTime, size, md5Checksum",
                )
                .execute()
            )
        except HttpError as e:
            self.logger.error(f"Erro ao obter metadados (id={file_id}): {e}")
            return {}

    # ── Utilitários ───────────────────────────────────────────────────────

    @staticmethod
    def compute_md5(file_path: Path) -> str:
        """
        Calcula SHA-256 de um arquivo local para comparacao de integridade.

        NOTA: o nome do metodo e mantido para compatibilidade com o restante
        do codigo; internamente usa SHA-256 pois MD5 e criptograficamente
        comprometido (ataques de colisao conhecidos).
        O campo 'md5Checksum' da API do Drive continua sendo comparado apenas
        para deteccao de mudancas (nao para autenticidade criptografica).
        """
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def format_size(size_bytes: int) -> str:
        """Formata tamanho em bytes para string legível."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"
