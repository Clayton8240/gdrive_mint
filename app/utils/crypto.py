"""
Módulo de criptografia para armazenamento seguro de credenciais.
Utiliza Fernet (AES-128-CBC) da biblioteca cryptography.
"""

import os
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken


class CryptoManager:
    """Gerencia a criptografia e descriptografia de dados sensíveis."""

    def __init__(self, app_dir: Path):
        self.app_dir = app_dir
        self.key_file = app_dir / ".keystore"
        self._fernet: Fernet | None = None

    def _get_or_create_key(self) -> bytes:
        """Obtém a chave existente ou cria uma nova."""
        if self.key_file.exists():
            with open(self.key_file, "rb") as f:
                return f.read()

        # Gera nova chave simétrica
        key = Fernet.generate_key()
        self.app_dir.mkdir(parents=True, exist_ok=True)

        with open(self.key_file, "wb") as f:
            f.write(key)

        # Permissão restrita: apenas o dono pode ler/escrever
        os.chmod(self.key_file, 0o600)
        return key

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
        """Criptografa um arquivo e salva no destino."""
        with open(source_path, "rb") as f:
            content = f.read()
        encrypted = self.fernet.encrypt(content)
        with open(dest_path, "wb") as f:
            f.write(encrypted)
        os.chmod(dest_path, 0o600)

    def decrypt_to_string(self, source_path: Path) -> str:
        """Lê e descriptografa um arquivo, retornando o conteúdo como string."""
        with open(source_path, "rb") as f:
            encrypted = f.read()
        return self.fernet.decrypt(encrypted).decode("utf-8")

    def is_valid_encrypted_file(self, path: Path) -> bool:
        """Verifica se o arquivo contém dados criptografados válidos."""
        try:
            with open(path, "rb") as f:
                data = f.read()
            self.fernet.decrypt(data)
            return True
        except (InvalidToken, Exception):
            return False
