"""
Resolução de conflitos entre versões local e remota de arquivos.
Estratégias: renomear o local, manter ambos, sobrescrever.
"""

import shutil
from datetime import datetime
from pathlib import Path

from app.utils.logger import get_logger


class ConflictStrategy:
    RENAME_LOCAL = "rename_local"   # Renomeia o arquivo local e baixa o remoto
    KEEP_LOCAL = "keep_local"       # Mantém o local, descarta remoto
    KEEP_REMOTE = "keep_remote"     # Sobrescreve local com remoto
    KEEP_BOTH = "keep_both"         # Salva ambos com sufixo de data


class ConflictResolver:
    """Resolve conflitos entre versão local e remota de um arquivo."""

    def __init__(self, strategy: str = ConflictStrategy.RENAME_LOCAL):
        self.strategy = strategy
        self.logger = get_logger()

    def resolve(
        self,
        local_path: Path,
        local_checksum: str,
        remote_checksum: str,
        remote_modified: str,
    ) -> tuple[bool, str]:
        """
        Resolve o conflito de acordo com a estratégia configurada.

        Retorna (download_remote: bool, local_resolved_path: str)
        """
        if local_checksum == remote_checksum:
            # Sem conflito real — arquivos idênticos
            return False, str(local_path)

        self.logger.warning(
            f"Conflito detectado: {local_path.name} "
            f"(local vs remoto com hashes diferentes)"
        )

        if self.strategy == ConflictStrategy.KEEP_LOCAL:
            return False, str(local_path)

        if self.strategy == ConflictStrategy.KEEP_REMOTE:
            return True, str(local_path)

        if self.strategy == ConflictStrategy.RENAME_LOCAL:
            renamed = self._rename_with_suffix(local_path, "local")
            self.logger.info(f"Renomeado: {renamed}")
            return True, str(local_path)  # Baixa remoto no caminho original

        if self.strategy == ConflictStrategy.KEEP_BOTH:
            _ = self._rename_with_suffix(local_path, "local")
            return True, str(local_path)

        return False, str(local_path)

    def _rename_with_suffix(self, path: Path, suffix: str) -> Path:
        """Renomeia arquivo adicionando timestamp ao nome."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_name = f"{path.stem}.{suffix}.{timestamp}{path.suffix}"
        new_path = path.parent / new_name
        shutil.move(str(path), str(new_path))
        return new_path
