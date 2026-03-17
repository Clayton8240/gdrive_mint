"""
Autenticação OAuth 2.0 com o Google.
Gerencia o fluxo de login, refresh de token e logout.

Auditoria de segurança aplicada:
- Escopos OAuth com privilégio mínimo (drive.file, não drive completo)
- Escrita atômica do token criptografado (tempfile + os.replace)
- Verificação de permissões do credentials.json antes de abrir
- Exceções brutas não expostas na UI (apenas mensagem genérica)
- Email do usuário logado em nível DEBUG, não INFO
"""

import json
import os
import stat
import tempfile
import threading
from pathlib import Path
from typing import Callable, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from app.utils.crypto import CryptoManager
from app.utils.logger import get_logger

# Escopos com privilégio mínimo:
#   drive.file  — acesso apenas a arquivos criados/abertos PELO app
#   userinfo.email / profile / openid — identificação do usuário
# NÃO usar 'auth/drive' (acesso total ao Drive)
SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
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
        """Salva token criptografado no disco com escrita atômica."""
        if not self._creds:
            return
        token_json = self._creds.to_json()
        encrypted = self.crypto.encrypt(token_json)
        # Escrita atômica: evita arquivo parcialmente escrito em caso de crash
        fd, tmp_path = tempfile.mkstemp(
            dir=self.token_encrypted.parent, prefix=".token."
        )
        try:
            os.chmod(tmp_path, 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(encrypted)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, self.token_encrypted)  # atômico no POSIX
        except Exception:
            os.unlink(tmp_path)
            raise
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
            # DEBUG (não INFO) para não expor e-mail nos logs regulares
            self.logger.debug("Informações do usuário carregadas com sucesso.")
        except Exception as e:
            self.logger.warning("Não foi possível carregar dados do usuário.")

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

        # Verifica permissões do credentials.json antes de abrir
        cred_stat = self.credentials_file.stat()
        if cred_stat.st_mode & 0o077:
            # Corrige automaticamente: restringe a apenas o dono
            os.chmod(self.credentials_file, 0o600)
            self.logger.warning(
                "credentials.json tinha permissões abertas; corrigido para 600."
            )

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
            # Loga detalhe técnico internamente; UI recebe mensagem genérica
            self.logger.error(f"Falha na autenticação: {e}")
            on_error(
                "Falha na autenticação. Verifique os logs para mais detalhes."
            )

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
