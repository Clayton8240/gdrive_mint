"""
Autenticação OAuth 2.0 com o Google.
Gerencia o fluxo de login, refresh de token e logout.
"""

import json
import threading
from pathlib import Path
from typing import Callable, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from app.utils.crypto import CryptoManager
from app.utils.logger import get_logger

# Escopos necessários para o Google Drive
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid",
]


class GoogleAuthService:
    """Serviço de autenticação OAuth 2.0 com o Google."""

    def __init__(self, app_dir: Path, crypto: CryptoManager):
        self.app_dir = app_dir
        self.crypto = crypto
        self.logger = get_logger()
        self.credentials_file = app_dir / "credentials.json"
        self.token_encrypted = app_dir / ".token.enc"
        self._creds: Optional[Credentials] = None
        self._user_info: dict = {}

    # ── Propriedades ──────────────────────────────────────────────────────

    @property
    def is_authenticated(self) -> bool:
        """Verifica se há credenciais válidas."""
        try:
            creds = self.get_credentials()
            return creds is not None and creds.valid
        except Exception:
            return False

    @property
    def user_email(self) -> str:
        """Retorna e-mail do usuário autenticado."""
        return self._user_info.get("email", "")

    @property
    def user_name(self) -> str:
        """Retorna nome do usuário autenticado."""
        return self._user_info.get("name", "")

    # ── Gerenciamento de credenciais ───────────────────────────────────────

    def get_credentials(self) -> Optional[Credentials]:
        """
        Obtém credenciais válidas.
        Tenta carregar do arquivo criptografado e renovar se expiradas.
        """
        # Usa cache se disponível e válido
        if self._creds and self._creds.valid:
            return self._creds

        # Tenta carregar token salvo
        if self.token_encrypted.exists():
            try:
                raw_json = self.crypto.decrypt_to_string(self.token_encrypted)
                token_data = json.loads(raw_json)
                self._creds = Credentials.from_authorized_user_info(token_data, SCOPES)
            except Exception as e:
                self.logger.warning(f"Erro ao carregar token: {e}")
                self._creds = None

        # Renova token se expirado mas com refresh_token disponível
        if self._creds and self._creds.expired and self._creds.refresh_token:
            try:
                self._creds.refresh(Request())
                self._save_token()
                self.logger.info("Token renovado com sucesso.")
            except Exception as e:
                self.logger.warning(f"Falha ao renovar token: {e}")
                self._creds = None

        return self._creds if (self._creds and self._creds.valid) else None

    def _save_token(self) -> None:
        """Salva token criptografado no disco."""
        if not self._creds:
            return
        token_json = self._creds.to_json()
        encrypted = self.crypto.encrypt(token_json)
        with open(self.token_encrypted, "wb") as f:
            f.write(encrypted)
        import os
        os.chmod(self.token_encrypted, 0o600)
        self.logger.debug("Token salvo de forma segura.")

    def _load_user_info(self) -> None:
        """Carrega informações do usuário via Google API."""
        if not self._creds:
            return
        try:
            import googleapiclient.discovery as discovery
            service = discovery.build("oauth2", "v2", credentials=self._creds)
            user_info = service.userinfo().get().execute()
            self._user_info = {
                "email": user_info.get("email", ""),
                "name": user_info.get("name", ""),
                "picture": user_info.get("picture", ""),
            }
            self.logger.info(f"Logado como: {self._user_info['email']}")
        except Exception as e:
            self.logger.warning(f"Não foi possível carregar dados do usuário: {e}")

    # ── Fluxo de autenticação ──────────────────────────────────────────────

    def login(
        self,
        on_success: Callable[[str], None],
        on_error: Callable[[str], None],
    ) -> None:
        """
        Inicia o fluxo de autenticação OAuth 2.0 em thread separada.
        Chama on_success(email) ou on_error(mensagem) ao concluir.
        """
        thread = threading.Thread(
            target=self._do_login,
            args=(on_success, on_error),
            daemon=True,
        )
        thread.start()

    def _do_login(
        self,
        on_success: Callable[[str], None],
        on_error: Callable[[str], None],
    ) -> None:
        """Executa o fluxo de login (rodar em thread separada)."""
        if not self.credentials_file.exists():
            on_error(
                "Arquivo 'credentials.json' não encontrado.\n"
                "Baixe-o no Google Cloud Console e coloque em:\n"
                f"{self.credentials_file}"
            )
            return

        try:
            self.logger.info("Iniciando autenticação OAuth 2.0...")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.credentials_file), SCOPES
            )
            # Abre o navegador para autenticação
            self._creds = flow.run_local_server(
                port=0,
                prompt="select_account",
                success_message=(
                    "Autenticação concluída! Pode fechar esta janela."
                ),
            )
            self._save_token()
            self._load_user_info()
            on_success(self._user_info.get("email", "Usuário"))
        except Exception as e:
            self.logger.error(f"Falha na autenticação: {e}")
            on_error(str(e))

    def logout(self) -> None:
        """Remove credenciais e encerra sessão."""
        self._creds = None
        self._user_info = {}
        if self.token_encrypted.exists():
            self.token_encrypted.unlink()
        self.logger.info("Usuário desconectado.")

    def try_silent_login(self) -> bool:
        """
        Tenta autenticação silenciosa (sem abrir navegador).
        Retorna True se bem-sucedido.
        """
        creds = self.get_credentials()
        if creds:
            self._load_user_info()
            return True
        return False
