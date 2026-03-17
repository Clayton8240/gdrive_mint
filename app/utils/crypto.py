"""
Módulo de criptografia para armazenamento seguro de credenciais.
Utiliza Fernet (AES-128-CBC) da biblioteca cryptography.

Auditoria de segurança aplicada:
- Escrita atômica da chave (evita TOCTOU)
- Validação do tamanho da chave ao ler do disco
- Permissões 700 no diretório e 600 nos arquivos sensíveis
- Leitura limitada para evitar DoS por arquivo gigante
"""

import os
import tempfile
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken

# Fernet usa chaves de 32 bytes codificados em Base64 URL-safe (44 chars)
_KEY_SIZE_BYTES = 44
# Limite de leitura de arquivo criptografado (64 MB)
_MAX_ENCRYPTED_SIZE = 64 * 1024 * 1024


class CryptoManager:
    """Gerencia a criptografia e descriptografia de dados sensíveis."""

    def __init__(self, app_dir: Path):
        self.app_dir = app_dir
        self.key_file = app_dir / ".keystore"
        self._fernet: Fernet | None = None
        # Garante diretório com permissões restritas na inicialização
        self._ensure_secure_dir()

    def _ensure_secure_dir(self) -> None:
        """Cria o diretório de dados com permissão 700 (somente dono)."""
        self.app_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.app_dir, 0o700)

    def _get_or_create_key(self) -> bytes:
        """
        Obtém a chave existente ou cria uma nova.
        Usa escrita atômica (write + rename) para evitar TOCTOU:
        nenhum outro processo vê um arquivo de chave parcialmente escrito.
        """
        if self.key_file.exists():
            key = self._read_key_safe()
            if key:
                return key
            # Chave corrompida — recria
            self.key_file.unlink(missing_ok=True)

        # Gera nova chave simétrica aleatória
        key = Fernet.generate_key()

        # Escrita atômica: escreve em arquivo temporário, depois renomeia
        fd, tmp_path = tempfile.mkstemp(dir=self.app_dir, prefix=".keystore.")
        try:
            os.chmod(tmp_path, 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(key)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, self.key_file)  # atômico no POSIX
        except Exception:
            os.unlink(tmp_path)
            raise

        os.chmod(self.key_file, 0o600)
        return key

    def _read_key_safe(self) -> bytes | None:
        """Lê e valida a chave do disco. Retorna None se inválida."""
        try:
            stat = self.key_file.stat()
            # Rejeita chaves com permissões abertas (group/other leem)
            if stat.st_mode & 0o077:
                raise PermissionError(
                    f"Keystore com permissões inseguras: {oct(stat.st_mode)}"
                )
            with open(self.key_file, "rb") as f:
                key = f.read(_KEY_SIZE_BYTES + 1)  # +1 para detectar excesso
            if len(key) != _KEY_SIZE_BYTES:
                raise ValueError(f"Chave com tamanho inválido: {len(key)} bytes")
            return key
        except (PermissionError, ValueError) as e:
            import logging
            logging.getLogger("GDriveMint").error(f"Keystore inválido: {e}")
            return None

    @property
    def fernet(self) -> Fernet:
        """Retorna instância Fernet inicializada."""
        if self._fernet is None:
            key = self._get_or_create_key()
            self._fernet = Fernet(key)
        return self._fernet

    def encrypt(self, data: str) -> bytes:
        """Criptografa uma string e retorna bytes."""
        return self.fernet.encrypt(data.encode("utf-8"))

    def decrypt(self, data: bytes) -> str:
        """Descriptografa bytes e retorna string."""
        return self.fernet.decrypt(data).decode("utf-8")

    def encrypt_file(self, source_path: Path, dest_path: Path) -> None:
        """Criptografa um arquivo e salva com escrita atômica."""
        with open(source_path, "rb") as f:
            content = f.read()
        encrypted = self.fernet.encrypt(content)
        # Escrita atômica para evitar arquivo corrompido em caso de crash
        fd, tmp_path = tempfile.mkstemp(dir=dest_path.parent)
        try:
            os.chmod(tmp_path, 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(encrypted)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, dest_path)
        except Exception:
            os.unlink(tmp_path)
            raise
        os.chmod(dest_path, 0o600)

    def decrypt_to_string(self, source_path: Path) -> str:
        """Lê (com limite de tamanho) e descriptografa um arquivo."""
        size = source_path.stat().st_size
        if size > _MAX_ENCRYPTED_SIZE:
            raise ValueError(
                f"Arquivo criptografado excede o limite seguro: {size} bytes"
            )
        with open(source_path, "rb") as f:
            encrypted = f.read()
        return self.fernet.decrypt(encrypted).decode("utf-8")

    def is_valid_encrypted_file(self, path: Path) -> bool:
        """Verifica se o arquivo contém dados criptografados válidos."""
        try:
            with open(path, "rb") as f:
                data = f.read(_MAX_ENCRYPTED_SIZE)
            self.fernet.decrypt(data)
            return True
        except (InvalidToken, Exception):
            return False
