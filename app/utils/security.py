"""
Modulo centralizado de hardening de seguranca.

Executado na inicializacao da aplicacao para verificar e corrigir
condicoes inseguras antes de qualquer operacao sensivel.

Checks implementados:
  1. Permissoes do diretorio de dados (~/.local/share/gdrive_mint) — 700
  2. Permissoes do diretorio de config (~/.config/gdrive_mint)     — 700
  3. Permissoes de arquivos sensiveis (.keystore, .token.enc, config.json) — 600
  4. Versao minima do Python (3.10) para garantir recursos de seguranca
  5. Variaveis de ambiente que possam indicar execucao em contexto perigoso
  6. Integridade basica do diretorio HOME (sem acesso mundial a gravacao)
"""

import os
import stat
import sys
from pathlib import Path
from typing import NamedTuple


class SecurityCheckResult(NamedTuple):
    passed: bool
    warnings: list[str]
    errors: list[str]


# Permissoes desejadas para diferentes tipos de recurso
_DIR_MODE = 0o700   # drwx------
_FILE_MODE = 0o600  # -rw-------

# Arquivos que exigem permissao restrita
_SENSITIVE_FILE_NAMES = frozenset({
    ".keystore",
    ".token.enc",
    "config.json",
    "credentials.json",
})


def _check_mode(path: Path, expected_mode: int, label: str) -> tuple[bool, str]:
    """Verifica permissao de um arquivo/diretorio. Retorna (ok, mensagem)."""
    try:
        current = path.stat().st_mode & 0o777
        if current & ~expected_mode:  # bits a mais alem do esperado
            return False, (
                f"{label} '{path.name}' tem permissao {oct(current)}; "
                f"esperado {oct(expected_mode)}."
            )
        return True, ""
    except FileNotFoundError:
        return True, ""  # nao existe ainda: sem problema
    except OSError as e:
        return False, f"Nao foi possivel verificar {label} '{path}': {e}"


def _enforce_mode(path: Path, mode: int) -> None:
    """Aplica permissao ao path, se ele existir."""
    try:
        if path.exists():
            os.chmod(path, mode)
    except OSError:
        pass


def run_startup_checks(app_data_dir: Path, app_config_dir: Path) -> SecurityCheckResult:
    """
    Executa todos os checks de seguranca na inicializacao.

    Args:
        app_data_dir:   caminho base dos dados (~/.local/share/gdrive_mint)
        app_config_dir: caminho das configs (~/.config/gdrive_mint)

    Returns:
        SecurityCheckResult com listas de avisos e erros.
        Erros sao fatais; avisos nao bloqueiam a execucao mas devem ser logados.
    """
    warnings: list[str] = []
    errors: list[str] = []

    # 1. Versao minima do Python
    if sys.version_info < (3, 10):
        errors.append(
            f"Python {sys.version_info.major}.{sys.version_info.minor} detectado; "
            "requer Python 3.10+."
        )

    # 2. HOME nao deve ter permissao de escrita para outros (world-writable)
    home = Path.home()
    try:
        home_mode = home.stat().st_mode
        if home_mode & stat.S_IWOTH:
            warnings.append(
                f"Diretorio HOME '{home}' tem permissao de escrita para 'outros'. "
                "Isso e incomum e potencialmente inseguro."
            )
    except OSError:
        pass

    # 3. Diretorios de dados e config devem ter 700
    for d in (app_data_dir, app_config_dir):
        ok, msg = _check_mode(d, _DIR_MODE, "diretorio")
        if not ok:
            warnings.append(msg + " Corrigindo automaticamente.")
            _enforce_mode(d, _DIR_MODE)

    # 4. Arquivos sensiveis devem ter 600
    for search_dir in (app_data_dir, app_config_dir):
        if not search_dir.exists():
            continue
        for f in search_dir.iterdir():
            if f.name in _SENSITIVE_FILE_NAMES and f.is_file():
                ok, msg = _check_mode(f, _FILE_MODE, "arquivo")
                if not ok:
                    warnings.append(msg + " Corrigindo automaticamente.")
                    _enforce_mode(f, _FILE_MODE)

    # 5. Variavel DISPLAY ou WAYLAND_DISPLAY deve existir (ambiente grafico)
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        warnings.append(
            "Nenhuma variavel DISPLAY ou WAYLAND_DISPLAY encontrada. "
            "A interface grafica pode nao funcionar corretamente."
        )

    # 6. Verifica se executa como root (nao recomendado)
    if os.getuid() == 0:
        errors.append(
            "A aplicacao esta sendo executada como root (UID 0). "
            "Isso e altamente nao recomendado por razoes de seguranca."
        )

    passed = len(errors) == 0
    return SecurityCheckResult(passed=passed, warnings=warnings, errors=errors)


def validate_local_path(path: str | Path, base_dir: Path) -> Path:
    """
    Valida e normaliza um caminho local, garantindo que esteja dentro de base_dir.

    Uso tipico: validar caminhos de pasta de sincronizacao provenientes da UI
    ou do arquivo de configuracao antes de usa-los.

    Raises:
        ValueError: se o caminho resolvido escapar de base_dir.
    """
    resolved = Path(path).expanduser().resolve()
    base_resolved = base_dir.resolve()
    # Permite o proprio base_dir ou qualquer subdiretorio dele
    if resolved != base_resolved and not str(resolved).startswith(
        str(base_resolved) + "/"
    ):
        raise ValueError(
            f"Caminho '{resolved}' esta fora do diretorio permitido '{base_resolved}'."
        )
    return resolved


def sanitize_filename(name: str) -> str:
    """
    Retorna apenas o componente final de um nome de arquivo,
    removendo qualquer componente de diretorio (../, /, etc.).

    Uso: sanitizar nomes recebidos de APIs externas antes de criar
    arquivos locais.
    """
    safe = Path(name).name
    if not safe or safe in (".", ".."):
        raise ValueError(f"Nome de arquivo invalido: {name!r}")
    return safe
