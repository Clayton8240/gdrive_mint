# Guia para Desenvolvedores — GDrive Mint

Este documento é a referência técnica completa do projeto. Cobre arquitetura, APIs internas, modelo de threads, segurança e workflows de contribuição.

---

## Sumário

1. [Configurando o ambiente de desenvolvimento](#1-configurando-o-ambiente-de-desenvolvimento)
2. [Arquitetura geral](#2-arquitetura-geral)
3. [Referência de módulos](#3-referência-de-módulos)
   - [main.py](#31-mainpy)
   - [SyncEngine](#32-syncengine)
   - [FileWatcher](#33-filewatcher)
   - [ConflictResolver](#34-conflictresolver)
   - [SyncState](#35-syncstate)
   - [DriveService](#36-driveservice)
   - [GoogleAuthService](#37-googleauthservice)
   - [CryptoManager](#38-cryptomanager)
   - [AppLogger](#39-applogger)
   - [ConfigManager](#310-configmanager)
   - [security.py](#311-securitypy)
4. [Arquitetura da UI](#4-arquitetura-da-ui)
5. [Modelo de threads](#5-modelo-de-threads)
6. [Guia de segurança](#6-guia-de-segurança)
7. [Como adicionar funcionalidades](#7-como-adicionar-funcionalidades)
8. [Empacotamento e releases](#8-empacotamento-e-releases)
9. [Workflow de contribuição](#9-workflow-de-contribuição)

---

## 1. Configurando o ambiente de desenvolvimento

### Dependências do sistema

```bash
sudo apt install python3 python3-pip python3-venv python3-tk libnotify-bin git
```

### Clone e venv

```bash
git clone https://github.com/Clayton8240/gdrive_mint
cd gdrive_mint
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Credenciais OAuth

Coloque `credentials.json` em `~/.config/gdrive_mint/` com permissão `600` antes de executar.  
Consulte a seção [Configuração do Google OAuth 2.0](../README.md#configuração-do-google-oauth-20) no README.

### Executar a partir do código-fonte

```bash
source .venv/bin/activate
python3 main.py
```

### Logs em tempo real

```bash
tail -f ~/.local/share/gdrive_mint/logs/gdrive_mint.log
```

### Estrutura de diretórios de dados (runtime)

```
~/.config/gdrive_mint/
├── credentials.json   # fornecido pelo dev (não versionado)
├── .token.enc         # token OAuth criptografado
├── .keystore          # chave Fernet (chmod 600)
└── config.json        # configurações da aplicação (chmod 600)

~/.local/share/gdrive_mint/
├── sync_state.json    # estado dos arquivos sincronizados
└── logs/
    └── gdrive_mint.log
```

---

## 2. Arquitetura geral

### Diagrama de componentes

```
┌─────────────────────────────────────────────────────────────┐
│                         main.py                             │
│  _run_security_preflight() ──► AppWindow().mainloop()       │
└──────────────────────────┬──────────────────────────────────┘
                           │
          ┌────────────────▼────────────────┐
          │           AppWindow             │
          │  (CTk – navegação + ciclo vida) │
          └──┬─────────────┬───────────────┘
             │             │
   ┌─────────▼──┐   ┌──────▼────────────────────────┐
   │  Screens   │   │         SyncEngine             │
   │ login      │   │  start/stop/pause/resume       │
   │ dashboard  │   │  _full_sync / _auto_sync_loop  │
   │ folders    │   └──┬─────────────┬───────────────┘
   │ settings   │      │             │
   │ logs       │  ┌───▼────┐  ┌────▼──────────┐
   └────────────┘  │FileWa- │  │  DriveService │
                   │tcher   │  │  (API v3)     │
                   └────────┘  └───────────────┘
                        │
               ┌────────▼────────────┐
               │  ConflictResolver   │
               │  SyncState          │
               └─────────────────────┘

   Utilitários transversais:
   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
   │ GoogleAuth   │  │ CryptoManager│  │ ConfigManager│
   │ Service      │  │ (Fernet)     │  │ (JSON+chmod) │
   └──────────────┘  └──────────────┘  └──────────────┘
   ┌──────────────┐  ┌──────────────┐
   │  AppLogger   │  │ security.py  │
   │  (singleton) │  │ (hardening)  │
   └──────────────┘  └──────────────┘
```

### Fluxo de inicialização

```
1. main.py: _run_security_preflight()
      └── security.run_startup_checks(config_dir, data_dir)
              ├── verifica permissões dos diretórios
              ├── valida integridade do credentials.json
              └── retorna SecurityCheckResult (erros fatais → sys.exit(1))

2. AppWindow.__init__()
      ├── _setup_layout()      # sidebar + frame de conteúdo
      ├── _try_silent_login()  # tenta reusar token salvo
      └── _navigate("login")  # ou "dashboard" se autenticado

3. Após login bem-sucedido (_post_login):
      ├── SyncEngine(config, auth, drive).start()
      └── _navigate("dashboard")
```

### Fluxo de sincronização

```
SyncEngine.start()
  └── Thread: _auto_sync_loop()
        └── a cada N minutos: sync_now()
                └── _full_sync()
                      ├── para cada pasta configurada:
                      │     _sync_folder(local_path, drive_folder_id)
                      │           ├── _upload_folder_recursive()
                      │           └── _download_folder_recursive()
                      └── atualiza SyncState

FileWatcher → evento de ficheiro → debounce 1.5s → _on_file_changed()
  └── _maybe_upload(path)
        ├── ConflictResolver.resolve()  (se necessário)
        └── DriveService.upload_file()
              └── SyncState.update_status()
```

---

## 3. Referência de módulos

### 3.1 `main.py`

```python
def _run_security_preflight() -> None
```

Executa verificações de segurança antes de iniciar a UI. Em caso de erro fatal, imprime para `stderr` e chama `sys.exit(1)`.

---

### 3.2 `SyncEngine`

**Arquivo:** `app/core/sync_engine.py`  
**Thread-safety:** `_counter_lock` protege `uploaded_count`, `downloaded_count`, `error_count`. `_sync_lock` serializa ciclos de sync.

#### Constantes

```python
_VALID_SYNC_MODES: frozenset = frozenset({"bidirectional", "upload", "download"})
_MAX_DOWNLOAD_SIZE: int = 512 * 1024 * 1024  # 512 MB
```

#### Construtor

```python
SyncEngine(
    config: ConfigManager,
    auth: GoogleAuthService,
    drive: DriveService,
)
```

#### Propriedades

| Propriedade | Tipo | Descrição |
|---|---|---|
| `is_running` | `bool` | Engine ativa (thread de auto-sync rodando) |
| `is_paused` | `bool` | Sync pausado pelo usuário |
| `uploaded_count` | `int` | Arquivos enviados desde o start |
| `downloaded_count` | `int` | Arquivos recebidos desde o start |
| `error_count` | `int` | Erros acumulados desde o start |
| `last_sync_time` | `datetime \| None` | Hora do último sync completo |

#### Métodos públicos

```python
def start() -> None
```
Inicia a thread de auto-sync e o `FileWatcher`. Idempotente (ignora se já rodando).

```python
def stop() -> None
```
Para a thread de auto-sync e o watcher. Aguarda a thread terminar.

```python
def pause() -> None
def resume() -> None
```
Controle temporário sem parar a thread.

```python
def sync_now(progress_callback: Callable[[str], None] | None = None) -> None
```
Dispara um ciclo de sync completo imediatamente (bloqueante, chamar em thread separada).

```python
def refresh_config() -> None
```
Relê `ConfigManager` e atualiza o `FileWatcher`. Chamar após o usuário salvar configurações.

```python
def register_status_callback(cb: Callable[[str], None]) -> None
```
Registra callback invocado com mensagens de status (ex.: "Sincronizando…", "Pronto").

#### Métodos internos (não usar externamente)

| Método | Descrição |
|---|---|
| `_full_sync()` | Itera por todas as pastas configuradas |
| `_sync_folder(local, drive_id)` | Resolve uma pasta (upload + download) |
| `_upload_folder_recursive(path, drive_id)` | Upload recursivo |
| `_download_folder_recursive(drive_id, local)` | Download recursivo + verificação de tamanho |
| `_maybe_upload(path)` | Upload condicional (verifica checksum antes) |
| `_auto_sync_loop()` | Loop com `threading.Event.wait()` (intervalo configurável) |
| `_on_file_changed(path, event_type, dest)` | Callback do FileWatcher |
| `_update_watcher_folders()` | Sincroniza pastas do `FileWatcher` com o config |

---

### 3.3 `FileWatcher`

**Arquivo:** `app/core/file_watcher.py`

#### Tipo de callback

```python
ChangeCallback = Callable[[str, str, str | None], None]
# args: (caminho, tipo_evento, destino_se_movido)
# tipo_evento: "created" | "modified" | "deleted" | "moved"
```

#### `_EventHandler` (interno)

Subclasse de `watchdog.FileSystemEventHandler`. Implementa debounce de **1,5 segundos** por caminho: cada evento agenda um `threading.Timer`; eventos repetidos cancelam e reagendam o timer.

#### `FileWatcher`

```python
FileWatcher(callback: ChangeCallback)
```

| Método | Descrição |
|---|---|
| `start() -> None` | Inicia o `Observer` do watchdog |
| `stop() -> None` | Para o `Observer` e aguarda |
| `add_folder(path: str) -> None` | Adiciona pasta ao monitoramento (recursivo) |
| `remove_folder(path: str) -> None` | Remove pasta do monitoramento |
| `update_folders(paths: list[str]) -> None` | Reconcilia lista completa (remove antigas, adiciona novas) |
| `monitored_folders` | `list[str]` — pastas atualmente monitoradas |

---

### 3.4 `ConflictResolver`

**Arquivo:** `app/core/conflict_resolver.py`

#### `ConflictStrategy` (enum)

```python
class ConflictStrategy(str, Enum):
    RENAME_LOCAL = "rename_local"   # renomeia local antes de baixar (padrão)
    KEEP_LOCAL   = "keep_local"     # descarta versão remota
    KEEP_REMOTE  = "keep_remote"    # descarta versão local
    SKIP         = "skip"           # não faz nada
```

#### `ConflictResolver`

```python
ConflictResolver(strategy: ConflictStrategy = ConflictStrategy.RENAME_LOCAL)
```

```python
def resolve(
    local_file: Path,
    local_hash: str,
    remote_hash: str,
    remote_modified_time: datetime,
) -> tuple[bool, Path | None]
```

**Retorno:** `(do_download, renamed_to)`

- `do_download=True` → o chamador deve baixar o arquivo remoto
- `renamed_to` → novo caminho do arquivo local renomeado (ou `None`)

```python
def _rename_with_suffix(path: Path) -> Path
```
Acrescenta sufixo `_conflito_YYYYMMDD_HHMMSS` antes da extensão.

---

### 3.5 `SyncState`

**Arquivo:** `app/core/sync_state.py`  
**Persistência:** `~/.local/share/gdrive_mint/sync_state.json` (escrita atômica via `tempfile` + `os.replace`)

#### `FileStatus` (enum)

```python
class FileStatus(str, Enum):
    PENDING     = "pending"
    UPLOADING   = "uploading"
    DOWNLOADING = "downloading"
    SYNCED      = "synced"
    ERROR       = "error"
    CONFLICT    = "conflict"
```

#### `SyncState`

```python
SyncState(data_dir: Path)
```

| Método | Descrição |
|---|---|
| `get(local_path: str) -> dict \| None` | Retorna entrada completa ou `None` |
| `set(local_path, drive_id, drive_parent_id, status, checksum) -> None` | Cria/atualiza entrada e persiste |
| `update_status(local_path, status) -> None` | Atalho para atualizar só o status |
| `remove(local_path: str) -> None` | Remove entrada |
| `get_drive_id(local_path: str) -> str \| None` | Retorna `drive_id` se existir |
| `get_by_status(status: FileStatus) -> list[str]` | Lista caminhos com determinado status |
| `count_by_status(status: FileStatus) -> int` | Contagem por status |

---

### 3.6 `DriveService`

**Arquivo:** `app/services/drive_service.py`

```python
DriveService(auth: GoogleAuthService)
```

| Método | Descrição |
|---|---|
| `get_storage_info() -> dict` | `{total, used, free}` em bytes |
| `list_files(parent_id: str, page_size: int = 100) -> list[dict]` | Lista arquivos numa pasta |
| `find_or_create_folder(name: str, parent_id: str \| None) -> str` | Retorna `id` da pasta (cria se não existir) |
| `upload_file(local_path, parent_id, existing_file_id, progress_callback) -> str` | Upload ou update; retorna `file_id` |
| `download_file(file_id, dest_path, progress_callback) -> None` | Download com verificação de tamanho |
| `delete_file(file_id: str) -> None` | Move para lixeira do Drive |
| `get_file_metadata(file_id: str) -> dict` | Metadados completos do arquivo |
| `compute_md5(file_path: Path) -> str` | **SHA-256** do arquivo local (nome mantido por compatibilidade) |
| `format_size(bytes: int) -> str` | Formata bytes como "1,23 GB" |

**Nota sobre `compute_md5`:** Apesar do nome histórico, esta função calcula **SHA-256** desde a v1.1.0 (auditoria de segurança). O nome será corrigido em v2.0.0.

---

### 3.7 `GoogleAuthService`

**Arquivo:** `app/services/google_auth.py`  
**Escopo OAuth:** `https://www.googleapis.com/auth/drive.file` (mínimo necessário — acesso somente a arquivos criados pelo app)

```python
GoogleAuthService(config_dir: Path)
```

| Método/Propriedade | Tipo | Descrição |
|---|---|---|
| `login(on_success, on_error)` | `None` | Inicia OAuth em thread separada; callbacks chamados ao fim |
| `logout() -> None` | — | Remove token persistido e invalida credencial |
| `get_credentials()` | `Credentials \| None` | Retorna credencial válida (renova se expirado) |
| `try_silent_login() -> bool` | — | Tenta reutilizar token salvo sem interação do usuário |
| `is_authenticated` | `bool` | Se há credencial ativa |
| `user_email` | `str \| None` | E-mail do usuário autenticado |
| `user_name` | `str \| None` | Nome de exibição |

**Fluxo de login:**
```
login()
  └── Thread: InstalledAppFlow.run_local_server(port=0)
        ├── abre browser automaticamente
        ├── aguarda callback OAuth
        └── salva token criptografado via CryptoManager
              └── on_success(email) ou on_error(msg)
```

---

### 3.8 `CryptoManager`

**Arquivo:** `app/utils/crypto.py`  
**Algoritmo:** Fernet (AES-128-CBC + HMAC-SHA256)

```python
CryptoManager(keystore_path: Path)
```

| Método | Descrição |
|---|---|
| `encrypt(data: str) -> bytes` | Criptografa string UTF-8 |
| `decrypt(data: bytes) -> str` | Descriptografa para string UTF-8 |
| `save_encrypted(path: Path, data: str) -> None` | Escrita atômica de arquivo criptografado |
| `load_encrypted(path: Path) -> str` | Lê e descriptografa arquivo |

**Comportamento da keystore:**
- Se não existir: gera nova chave com `Fernet.generate_key()` e persiste com `chmod 600`
- Escrita atômica: `tempfile.mkstemp` → `os.fchmod(600)` → `os.replace`
- Tamanho mínimo da chave: 44 bytes (base64 de 32 bytes)
- Limite de leitura: 64 MB (protege contra arquivos maliciosos)

---

### 3.9 `AppLogger`

**Arquivo:** `app/utils/logger.py`  
**Padrão:** Singleton — `AppLogger.get_instance()`

```python
AppLogger.get_instance() -> AppLogger
```

| Método | Descrição |
|---|---|
| `get_logger(name: str) -> logging.Logger` | Logger nomeado com handlers configurados |
| `add_ui_callback(cb: Callable[[str], None]) -> None` | Adiciona callback para exibir logs na UI |
| `remove_ui_callback(cb) -> None` | Remove callback |
| `set_level(level: int) -> None` | Altera nível global em runtime |

**Configuração:**
- Handler de arquivo: `RotatingFileHandler` (5 MB por arquivo, 3 backups)
- Filtro: `_SensitiveDataFilter` — redige automaticamente `refresh_token`, `client_secret`, `Bearer `, chaves JWT e API keys nos logs

**Uso recomendado:**

```python
from app.utils.logger import AppLogger

logger = AppLogger.get_instance().get_logger(__name__)
logger.info("mensagem")
logger.error("erro", exc_info=True)
```

---

### 3.10 `ConfigManager`

**Arquivo:** `app/utils/config_manager.py`

```python
ConfigManager(config_dir: Path)
```

**Arquivo gerado:** `config.json` com `chmod 600` (escrita atômica).

#### Chaves de configuração

| Chave | Tipo | Padrão | Descrição |
|---|---|---|---|
| `sync_interval` | `int` | `15` | Intervalo de auto-sync em minutos |
| `sync_mode` | `str` | `"bidirectional"` | `"bidirectional"`, `"upload"` ou `"download"` |
| `bandwidth_limit` | `int` | `0` | Limite de banda em KB/s (0 = sem limite) |
| `autostart` | `bool` | `false` | Iniciar com o sistema |
| `theme` | `str` | `"dark"` | `"dark"` ou `"light"` |
| `folders` | `list[dict]` | `[]` | Pastas sincronizadas |

**Estrutura de cada pasta:**

```json
{
  "local_path": "/home/user/Documentos",
  "drive_folder_id": "1AbCdEf...",
  "drive_folder_name": "Documentos",
  "sync_mode": "bidirectional"
}
```

| Método | Descrição |
|---|---|
| `get(key: str, default=None)` | Lê valor |
| `set(key: str, value) -> None` | Escreve e persiste |
| `update(data: dict) -> None` | Atualiza múltiplas chaves atomicamente |
| `get_folders() -> list[dict]` | Lista pastas configuradas |
| `add_folder(folder: dict) -> None` | Adiciona pasta (valida campos obrigatórios) |
| `remove_folder(local_path: str) -> None` | Remove por caminho local |
| `update_folder(local_path, updates: dict) -> None` | Atualiza campos de uma pasta |

---

### 3.11 `security.py`

**Arquivo:** `app/utils/security.py`

```python
def run_startup_checks(
    app_data_dir: Path,
    app_config_dir: Path,
) -> SecurityCheckResult
```

Executa ao inicializar o app. Retorna `SecurityCheckResult` com campos:
- `fatal_errors: list[str]` — se não vazio, o app deve abortar
- `warnings: list[str]` — registrados como `WARNING` no log

Verificações realizadas:
1. Permissões dos diretórios de dados e config (devem ser `700`)
2. Presença e permissões do `credentials.json` (deve ser `600`)
3. Integridade básica do JSON de credenciais

---

```python
def validate_local_path(path: str | Path, base_dir: Path) -> Path
```

Valida que `path` está dentro de `base_dir` (bloqueia path traversal com `resolve()` + verificação de prefixo). Lança `ValueError` se o caminho não for seguro.

---

```python
def sanitize_filename(name: str) -> str
```

Remove caracteres perigosos de nomes de arquivo vindos do Drive (`/`, `\`, `..`, `\0`, caracteres de controle). Retorna string segura para uso em `Path`.

---

## 4. Arquitetura da UI

### Estrutura de arquivos

```
app/ui/
├── app_window.py          # Janela principal (CTk)
├── theme.py               # Paletas de cores e fontes
├── components/
│   ├── sidebar.py         # Menu lateral com botões de navegação
│   └── status_bar.py      # Barra de status inferior
└── screens/
    ├── login_screen.py    # Fluxo OAuth
    ├── dashboard_screen.py
    ├── folders_screen.py
    ├── settings_screen.py
    └── logs_screen.py
```

### `AppWindow`

Subclasse de `customtkinter.CTk`. Gerencia:
- Navegação entre telas (`_navigate(screen_name: str)`)
- Ciclo de vida do `SyncEngine` (start/stop vinculado ao login/logout)
- Ícone da bandeja do sistema (`pystray`)
- Autostart

#### Telas disponíveis

| Nome | Classe | Descrição |
|---|---|---|
| `"login"` | `LoginScreen` | Botão de login OAuth |
| `"dashboard"` | `DashboardScreen` | Resumo, contadores, botão sync |
| `"folders"` | `FoldersScreen` | Gerenciar pastas sincronizadas |
| `"settings"` | `SettingsScreen` | Intervalo, banda, tema, autostart |
| `"logs"` | `LogsScreen` | Visualizador em tempo real com filtro de nível |

### Como adicionar uma nova tela

1. **Crie o arquivo** em `app/ui/screens/new_screen.py`:

```python
import customtkinter as ctk

class NewScreen(ctk.CTkFrame):
    def __init__(self, parent, app_window, **kwargs):
        super().__init__(parent, **kwargs)
        self._app = app_window
        self._build_ui()

    def _build_ui(self):
        ctk.CTkLabel(self, text="Nova Tela").pack(pady=20)

    def on_show(self):
        """Chamado automaticamente quando a tela se torna visível."""
        pass

    def on_hide(self):
        """Chamado quando a tela é substituída por outra."""
        pass
```

2. **Registre em `app_window.py`** no método `_build_screen`:

```python
from app.ui.screens.new_screen import NewScreen

def _build_screen(self, name: str) -> ctk.CTkFrame:
    screens = {
        "login": LoginScreen,
        "dashboard": DashboardScreen,
        # ...
        "new": NewScreen,      # adicione aqui
    }
    cls = screens[name]
    return cls(self._content_frame, self)
```

3. **Adicione botão na sidebar** em `app/ui/components/sidebar.py`:

```python
self._add_nav_button("Nova Tela", "new")
```

4. **Navegue para a tela** com:

```python
self._app._navigate("new")
```

---

## 5. Modelo de threads

O app usa `threading` puro (sem `asyncio`). A UI roda na **thread principal** (Tkinter exige isso). Operações demoradas rodam em threads separadas.

### Mapa de threads

| Thread | Proprietário | Descrição |
|---|---|---|
| Thread principal | Tkinter/CTk | UI event loop — único lugar onde widgets devem ser atualizados |
| `auth_thread` | `GoogleAuthService.login()` | Browser OAuth — bloqueante até o usuário autorizar |
| `sync_thread` | `SyncEngine._auto_sync_loop()` | Loop de auto-sync, dorme com `Event.wait()` |
| `watcher_thread` | `FileWatcher` / watchdog `Observer` | Monitoramento de sistema de arquivos |
| `dashboard_thread` | `DashboardScreen` | Refresh periódico de contadores de storage |

### Regras de thread-safety

1. **Nunca atualize widgets CTk de fora da thread principal.** Use `self.after(0, callback)`:

```python
# Em thread de background:
self.after(0, lambda: self._label.configure(text="atualizado"))
```

2. **Proteção de contadores compartilhados** com `threading.Lock`:

```python
with self._counter_lock:
    self._uploaded_count += 1
```

3. **Sinalizar parada de threads** com `threading.Event`:

```python
self._stop_event.set()   # sinaliza
thread.join(timeout=5)   # aguarda
```

4. **Callbacks de status do `SyncEngine`** são chamados da thread de sync — use `after(0, ...)` ao atualizar a UI.

---

## 6. Guia de segurança

Estas regras derivam da auditoria de segurança da v1.1.0. Todo código novo deve segui-las.

### Nomes de arquivo vindos do Drive

**Nunca** use o nome de arquivo retornado pela API diretamente em `Path`. Sempre sanitize:

```python
from app.utils.security import sanitize_filename

safe_name = sanitize_filename(remote_name)   # remove /, \, .., \0
local_path = base_dir / safe_name
```

E sempre valide que o caminho final não escapa do diretório-base:

```python
from app.utils.security import validate_local_path

final = validate_local_path(local_path, base_dir)  # lança ValueError se traversal
```

### Subprocessos

Sempre passe comandos como **lista** (nunca como string com `shell=True`):

```python
# CORRETO
subprocess.run(["notify-send", "título", mensagem], check=False)

# ERRADO — vulnerável a injeção
subprocess.run(f"notify-send 'título' '{mensagem}'", shell=True)
```

### Exceções e UI

Nunca exiba rastreamentos ou mensagens de exceção cru para o usuário:

```python
# CORRETO
try:
    ...
except Exception:
    logger.error("falha na operação", exc_info=True)
    self._show_error("Ocorreu um erro. Veja os logs para detalhes.")

# ERRADO
except Exception as e:
    self._show_error(str(e))  # pode vazar informações internas
```

### Escrita de arquivos sensíveis

Sempre use escrita atômica + `chmod 600`:

```python
import tempfile, os

fd, tmp = tempfile.mkstemp(dir=path.parent)
try:
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(conteudo)
    os.replace(tmp, path)
except Exception:
    os.unlink(tmp)
    raise
```

### Validação de `sync_mode`

Qualquer código que consume `sync_mode` deve validar contra o allowlist:

```python
_VALID_SYNC_MODES = frozenset({"bidirectional", "upload", "download"})

mode = config.get("sync_mode", "bidirectional")
if mode not in _VALID_SYNC_MODES:
    raise ValueError(f"sync_mode inválido: {mode!r}")
```

### Symlinks

Nunca faça upload de symlinks (podem apontar para arquivos fora da área permitida):

```python
if local_path.is_symlink():
    logger.warning("Symlink ignorado: %s", local_path)
    return
```

### Limites de tamanho

Sempre verifique o tamanho antes de baixar arquivos remotos:

```python
size = int(metadata.get("size", 0))
if size > _MAX_DOWNLOAD_SIZE:
    raise ValueError(f"Arquivo muito grande para download: {size} bytes")
```

---

## 7. Como adicionar funcionalidades

### Novo modo de sincronização

1. Adicione o valor ao allowlist em `sync_engine.py`:

```python
_VALID_SYNC_MODES = frozenset({"bidirectional", "upload", "download", "novo_modo"})
```

2. Adicione ao allowlist em `config_manager.py` (se houver validação explícita lá).

3. Implemente a lógica em `_sync_folder()`:

```python
if sync_mode == "novo_modo":
    ...
```

4. Adicione a opção na UI em `app/ui/screens/settings_screen.py`.

### Novo tipo de notificação

1. Adicione método em `app/linux/notifications.py`:

```python
def notify_novo_evento(info: str) -> None:
    _send("GDrive Mint", f"Novo evento: {info}", urgency="normal")
```

2. Chame de `SyncEngine` ou do lugar apropriado.

### Nova configuração

1. Adicione valor padrão no `ConfigManager.__init__` (ou em `_defaults`).
2. Adicione controle na `SettingsScreen`.
3. Documente a chave na tabela da [seção 3.10](#310-configmanager).

---

## 8. Empacotamento e releases

### Pacote .deb

```bash
# Gerar pacote (padrão: versão 1.1.0, amd64)
bash packaging/build_deb.sh

# Especificar versão e arquitetura
bash packaging/build_deb.sh --version 1.2.0 --arch arm64

# Saída
packaging/gdrive-mint_1.2.0_amd64.deb
```

O script cria:
- Estrutura `DEBIAN/` (control, postinst, prerm, postrm)
- `postinst`: cria venv em `/opt/gdrive-mint/.venv`, instala deps, ajusta permissões
- `prerm` / `postrm`: limpeza ao desinstalar

### Flatpak

```bash
# Pré-requisito: flatpak-builder
sudo apt install flatpak-builder

# Gerar fontes pip (uma vez, ou quando requirements.txt mudar)
bash packaging/flatpak/generate_sources.sh

# Construir
bash packaging/flatpak/build_flatpak.sh

# Construir, instalar localmente e criar bundle
bash packaging/flatpak/build_flatpak.sh --install --bundle
```

ID da aplicação: `io.github.gdrivemint.GDriveMint`

### Checklist de release

- [ ] Atualizar versão em `packaging/build_deb.sh` (`VERSION=X.Y.Z`)
- [ ] Atualizar versão em `packaging/flatpak/io.github.gdrivemint.GDriveMint.appdata.xml`
- [ ] Atualizar `CHANGELOG.md` (seguir [Keep a Changelog](https://keepachangelog.com))
- [ ] Atualizar badge de versão no `README.md`
- [ ] Rodar `python3 -m py_compile` em todos os arquivos `.py`
- [ ] Testar login OAuth do zero (deletar `.token.enc`)
- [ ] Testar upload, download e resolução de conflito
- [ ] Gerar `.deb` e testar instalação limpa
- [ ] Criar tag Git: `git tag -a v1.2.0 -m "Release v1.2.0"`

---

## 9. Workflow de contribuição

### Convenções de branches

| Prefixo | Uso |
|---|---|
| `feat/` | Nova funcionalidade |
| `fix/` | Correção de bug |
| `sec/` | Correção de segurança |
| `docs/` | Documentação |
| `refactor/` | Refatoração sem mudança de comportamento |
| `chore/` | Tarefas de build, CI, deps |

Exemplo: `feat/progress-bar-download`

### Convenções de commits

Seguir [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(sync): adicionar limite de taxa de upload por pasta
fix(auth): corrigir renovação de token expirado
sec(drive): bloquear path traversal no nome de arquivo remoto
docs: adicionar guia de contribuição
```

### Pull Request — checklist

- [ ] Branch criada a partir de `main` atualizada
- [ ] Nenhum arquivo de credenciais ou token incluído
- [ ] Sem `print()` de debug esquecido
- [ ] Novos módulos com logging via `AppLogger` (não `print`)
- [ ] Operações de arquivo sensíveis usando escrita atômica
- [ ] Subprocessos usando lista (não `shell=True`)
- [ ] `CHANGELOG.md` atualizado na seção `[Unreleased]`
- [ ] `README.md` atualizado se a mudança afeta o usuário final

### Verificação de sintaxe rápida

```bash
# Verificar todos os arquivos Python do projeto
find . -name "*.py" -not -path "./.venv/*" | xargs python3 -m py_compile && echo "OK"
```

### Estrutura de log para depuração

Ao depurar, use níveis de log adequados:

```python
logger.debug("Valor interno: %s", valor)     # detalhes de execução
logger.info("Sync concluído: %d arquivos", n) # eventos normais
logger.warning("Arquivo ignorado: %s", path) # condição inesperada mas recuperável
logger.error("Falha ao enviar", exc_info=True) # erro que impacta o usuário
```

---

*Documentação gerada para GDrive Mint v1.1.0. Abra uma issue se encontrar imprecisões.*
