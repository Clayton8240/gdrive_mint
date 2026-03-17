# Changelog

Todas as mudanças relevantes deste projeto serão documentadas aqui.

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
aderindo ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

---

## [Não lançado]

### Adicionado
- Nada pendente.

---

## [1.2.0] — 2026-03-17

### Adicionado
- **Assistente de configuração OAuth** (`setup_wizard_screen.py`): na primeira execução (quando `credentials.json` não existe), o app exibe automaticamente um wizard guiado de 3 etapas:
  1. Boas-vindas com duas opções: importar o arquivo existente ou seguir o guia passo a passo.
  2. Guia interativo com botões que abrem diretamente o Google Cloud Console, a ativação da API do Drive e a criação das credenciais OAuth.
  3. Importação segura do arquivo (validação de conteúdo + `chmod 600`) e preview da tela de permissão do Google antes de autorizar.
- **Detecção automática na inicialização** (`app_window.py`): se `credentials.json` estiver ausente, o wizard abre antes da tela de login normalmente.
- **Link "Reconfigurar credenciais"** na tela de login (`login_screen.py`): permite acessar o wizard a qualquer momento. Em caso de erro por arquivo ausente, o botão muda automaticamente para "Configurar agora".

---

## [1.1.0] — 2026-03-17

### Segurança — Auditoria completa de código-fonte

Esta versão é dedicada exclusivamente a correções de segurança identificadas em auditoria interna sênior. Nenhuma funcionalidade foi removida; todas as alterações são compatíveis com versões anteriores da configuração.

#### Crítico
- **Path Traversal bloqueado** (`sync_engine.py`): nomes de arquivo recebidos da API do Google Drive agora são sanitizados com `Path(name).name` e validados com `resolve()` para garantir que o caminho final permaneça dentro do diretório de sincronização. Um arquivo remoto malicioso nomeado `../../etc/cron.d/evil` não consegue mais escapar do diretório alvo.

#### Alto
- **Symlinks ignorados no upload** (`sync_engine.py`): arquivos do tipo symlink são detectados com `is_symlink()` e pulados antes de qualquer leitura. Impede vazamento de arquivos fora da pasta de sync (ex.: `~/sync/shadow → /etc/shadow`).
- **Escopo OAuth reduzido** (`google_auth.py`): o escopo `auth/drive` (acesso total ao Google Drive) foi substituído por `auth/drive.file`, que restringe o acesso apenas a arquivos criados ou abertos pelo próprio aplicativo.

#### Médio
- **Escrita atômica do keystore** (`crypto.py`): uso de `tempfile.mkstemp` + `os.replace()` (atômico no POSIX) elimina a janela de race condition TOCTOU na criação/leitura da chave Fernet. Chave inválida ou corrompida é regenerada automaticamente.
- **Validação do tamanho da chave** (`crypto.py`): a chave lida do disco é verificada para ter exatamente 44 bytes (formato Base64 Fernet). Chave com tamanho incorreto é rejeitada e regenerada.
- **Permissões do diretório de dados** (`crypto.py`): o diretório `~/.local/share/gdrive_mint` é criado/verificado com `chmod 700` na inicialização do `CryptoManager`.
- **Exceção bruta ocultada da UI** (`google_auth.py`): `on_error(str(e))` substituído por mensagem genérica ao usuário; detalhes técnicos (caminhos, stack traces) ficam apenas no log interno.
- **Verificação de permissões do `credentials.json`** (`google_auth.py`): o arquivo de credenciais OAuth é verificado antes de ser aberto; se tiver permissões abertas, são corrigidas automaticamente para `0o600`.
- **Injeção de campo em `.desktop` bloqueada** (`linux/autostart.py`): o `exec_cmd` é sanitizado com `re.sub` para remover newlines (`\n`, `\r`) e chaves (`{`, `}`) antes de ser inserido no arquivo de autostart. Escrita atômica do `.desktop` via tempfile.
- **`sys.argv[0]` substituído** (`linux/autostart.py`): a detecção do caminho do executável agora usa `Path(__file__)` em vez de `sys.argv[0]`, que pode ser manipulado pelo processo chamador.
- **Race conditions nos contadores** (`sync_engine.py`): `uploaded_count`, `downloaded_count` e `error_count` agora são incrementados dentro de `threading.Lock()`, evitando condições de corrida entre threads de sync.
- **`sync_mode` validado contra allowlist** (`sync_engine.py`): valores inválidos no campo `sync_mode` da configuração de pasta são rejeitados silenciosamente, retornando ao padrão `"bidirectional"`.
- **Limite de tamanho no download** (`sync_engine.py`): arquivos remotos maiores que 512 MB são ignorados durante o download para evitar uso excessivo de disco/memória.
- **`config.json` com permissão restrita** (`config_manager.py`): o arquivo de configuração é criado e salvo com `chmod 600`; escrita atômica via `tempfile.mkstemp` + `os.replace()`.
- **Injeção na query do Drive** (`drive_service.py`): aspas simples em nomes de pasta são escapadas antes de montar a query `files().list()`.
- **SHA-256 substituindo MD5** (`drive_service.py`): o método `compute_md5()` agora usa `hashlib.sha256` internamente. MD5 é criptograficamente comprometido e não deve ser usado para verificação de integridade.

#### Baixo
- **Rotação de logs** (`logger.py`): `FileHandler` substituído por `RotatingFileHandler` com limite de 5 MB por arquivo e 3 backups, prevenindo crescimento ilimitado do arquivo de log.
- **Filtro de dados sensíveis nos logs** (`logger.py`): adicionado `_SensitiveDataFilter` que redaciona tokens JWT, `refresh_token`, `access_token`, `client_secret` e chaves de API antes de gravar no arquivo de log.
- **E-mail do usuário movido para nível DEBUG** (`google_auth.py`): o e-mail autenticado não é mais registrado em nível `INFO` (visível em produção), mas em `DEBUG`.

#### Novo módulo
- **`app/utils/security.py`**: módulo de hardening centralizado executado na inicialização da aplicação. Verifica e corrige permissões de diretórios/arquivos sensíveis, impede execução como root (UID 0), detecta ausência de ambiente gráfico e expõe `validate_local_path()` e `sanitize_filename()` como utilitários reutilizáveis.

#### Dependências atualizadas (`requirements.txt`)
| Pacote | Antes | Depois | Motivo |
|--------|-------|--------|--------|
| `Pillow` | `>=10.0.0` | `>=10.4.0` | Corrige CVEs de processamento de imagem |
| `google-auth` | `>=2.23.0` | `>=2.35.0` | Corrige vulnerabilidade de validação de token |
| `cryptography` | `>=41.0.0` | `>=43.0.0` | Inclui correções de segurança do OpenSSL |
| `requests` | `>=2.31.0` | `>=2.32.0` | Corrige CVE-2024-35195 (validação de URL) |
| `google-api-python-client` | `>=2.100.0` | `>=2.140.0` | Atualização geral |

---

## [1.0.0] — 2026-03-15

### Adicionado
- Interface gráfica completa com **CustomTkinter** (tema claro/escuro).
- Autenticação **OAuth 2.0** com Google via `google-auth-oauthlib`.
- Token OAuth armazenado criptografado com **Fernet (AES-128-CBC)** via `cryptography`.
- **Sincronização bidirecional, somente upload e somente download** configurável por pasta.
- Monitoramento em tempo real de alterações locais com **watchdog**.
- **Bandeja do sistema** (`pystray`) com menu de controle rápido.
- **Notificações nativas** do Linux via `notify-send` (com fallback para `plyer`).
- **Autostart** no login via arquivo `.desktop` em `~/.config/autostart/`.
- Tela de **Dashboard** com espaço utilizado no Drive, últimas sincronizações e status.
- Tela de **Pastas** para adicionar, remover e configurar pastas de sync.
- Tela de **Configurações** com intervalo de sync, limite de banda e preferências de UI.
- Tela de **Logs** com visualização em tempo real e filtro por nível.
- Tela de **Login** com fluxo OAuth completo e feedback visual.
- Script `install.sh` para instalação automática no **Linux Mint**.
- `README.md` com guia completo de configuração do Google Cloud Console.

[Não lançado]: https://github.com/Clayton8240/gdrive_mint/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/Clayton8240/gdrive_mint/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/Clayton8240/gdrive_mint/releases/tag/v1.0.0
