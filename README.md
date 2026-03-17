# GDrive Mint

**Cliente leve de sincronização com Google Drive para Linux Mint**

Interface gráfica moderna (CustomTkinter) com suporte a Cinnamon, MATE e XFCE.

[![Versão](https://img.shields.io/badge/versão-1.1.0-blue)](https://github.com/Clayton8240/gdrive_mint/releases)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![Licença](https://img.shields.io/badge/licença-MIT-green)](https://github.com/Clayton8240/gdrive_mint/blob/main/LICENSE)
[![Linux Mint](https://img.shields.io/badge/Linux%20Mint-21%2B-87cf3e)](https://linuxmint.com)

> Para documentação técnica e contribuição, veja [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md).

---

## Funcionalidades

- Autenticação OAuth 2.0 — abre o navegador automaticamente
- Sincronização bidirecional, somente upload ou somente download por pasta
- Monitoramento em tempo real com `watchdog` (1,5 s de debounce)
- Dashboard com uso de armazenamento do Drive
- Logs em tempo real com filtros por nível
- Ícone na bandeja do sistema (`pystray`)
- Inicialização automática com o sistema
- Notificações nativas via `notify-send`
- Resolução de conflitos configurável
- Credenciais criptografadas com AES-128 (Fernet)
- Tema claro/escuro

---

---

## Instalação

### Opção A — Pacote .deb (recomendado)

A forma mais simples: basta fazer **duplo clique** no ficheiro `.deb` para instalar pelo Gerenciador de Pacotes do Linux Mint.

```bash
# Pré-requisito para gerar o pacote
sudo apt install dpkg-dev fakeroot rsync

# Gerar o pacote
bash packaging/build_deb.sh

# Instalar
sudo dpkg -i packaging/gdrive-mint_1.1.0_amd64.deb
```

Ver [packaging/README.md](packaging/README.md) para mais detalhes.

### Opção B — Script de instalação

```bash
git clone https://github.com/Clayton8240/gdrive_mint
cd gdrive_mint
bash install.sh
```

### Opção C — Manual

```bash
sudo apt install python3-pip python3-venv python3-tk libnotify-bin
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Configuração do Google OAuth 2.0

> Este passo é obrigatório antes de executar o aplicativo.

### 1. Criar projeto no Google Cloud Console

1. Acesse [console.cloud.google.com](https://console.cloud.google.com/)
2. Crie um novo projeto (ex: `GDrive Mint`)

### 2. Ativar APIs

1. **APIs e Serviços → Biblioteca**
2. Ative `Google Drive API` e `Google People API`

### 3. Criar credenciais OAuth 2.0

1. **APIs e Serviços → Credenciais → Criar Credenciais → ID do cliente OAuth**
2. Tipo: **Aplicativo para computador**
3. Faça o download do JSON

### 4. Instalar o credentials.json

```bash
mkdir -p ~/.config/gdrive_mint
cp ~/Downloads/client_secret_*.json ~/.config/gdrive_mint/credentials.json
chmod 600 ~/.config/gdrive_mint/credentials.json
```

### 5. Tela de consentimento (apenas em desenvolvimento)

1. **APIs e Serviços → Tela de consentimento OAuth → Externo**
2. Em **Usuários de teste**, adicione seu e-mail Google

---

## Execução

```bash
# Após instalação com o script ou .deb
gdrive-mint

# Manualmente
source .venv/bin/activate
python3 main.py
```

---

## Estrutura do Projeto

```
gdrive_mint/
├── main.py                        # Ponto de entrada + verificações de segurança
├── requirements.txt
├── install.sh                     # Instalador automático (terminal)
├── packaging/                     # Geração de .deb e executável universal
│   ├── build_deb.sh
│   ├── build_appimage.sh
│   ├── assets/gdrive-mint.svg
│   └── flatpak/                   # Mantido para referência futura
├── app/
│   ├── core/
│   │   ├── sync_engine.py         # Orquestrador de sincronização
│   │   ├── sync_state.py          # Estado persistente dos arquivos
│   │   ├── file_watcher.py        # Monitoramento com watchdog
│   │   └── conflict_resolver.py   # Estratégias de conflito
│   ├── services/
│   │   ├── google_auth.py         # OAuth 2.0 + token management
│   │   └── drive_service.py       # Google Drive API v3
│   ├── linux/
│   │   ├── tray.py                # Bandeja do sistema (pystray)
│   │   ├── autostart.py           # ~/.config/autostart/
│   │   └── notifications.py       # notify-send
│   ├── ui/
│   │   ├── app_window.py          # Janela principal + navegação
│   │   ├── theme.py               # Paletas e fontes
│   │   ├── components/            # Sidebar, StatusBar
│   │   └── screens/               # Login, Dashboard, Pastas, Config, Logs
│   └── utils/
│       ├── config_manager.py      # Configurações JSON (chmod 600)
│       ├── crypto.py              # Fernet AES-128 (escrita atômica)
│       ├── logger.py              # RotatingFileHandler + filtro de tokens
│       └── security.py            # Hardening: permissões, sanitização
└── docs/
    └── CONTRIBUTING.md            # Guia completo para desenvolvedores
```

---

## Arquivos gerados em tempo de execução

| Caminho | Conteúdo |
|---|---|
| `~/.config/gdrive_mint/credentials.json` | Credenciais OAuth (você fornece) |
| `~/.config/gdrive_mint/.token.enc` | Token OAuth criptografado (Fernet) |
| `~/.config/gdrive_mint/.keystore` | Chave de criptografia — `chmod 600` |
| `~/.config/gdrive_mint/config.json` | Configurações da aplicação — `chmod 600` |
| `~/.local/share/gdrive_mint/sync_state.json` | Estado dos arquivos sincronizados |
| `~/.local/share/gdrive_mint/logs/gdrive_mint.log` | Logs com rotação (5 MB × 3) |
| `~/.config/autostart/gdrive-mint.desktop` | Autostart (se ativado) |

---

## Segurança

A versão 1.1.0 passou por uma auditoria completa de segurança. Destaques:

| Área | Medida |
|------|--------|
| **Credenciais** | Token OAuth criptografado com Fernet (AES-128-CBC); escrita atômica |
| **OAuth** | Escopo `drive.file` (mínimo necessário) em vez de `drive` (acesso total) |
| **Ficheiros** | `.keystore`, `.token.enc` e `config.json` com `chmod 600` |
| **Sync** | Path traversal bloqueado; symlinks ignorados no upload |
| **Logs** | Rotação 5 MB × 3 backups; tokens redacionados automaticamente |
| **Integridade** | SHA-256 para verificação de checksums |

Veja o [CHANGELOG.md](CHANGELOG.md) para a lista completa de correções.

---

## Solução de problemas

**"credentials.json não encontrado"**
Coloque o ficheiro em `~/.config/gdrive_mint/credentials.json`

**Tray não aparece no XFCE**
```bash
sudo apt install python3-gi gir1.2-appindicator3-0.1
```

**Erro de autenticação após atualização**
```bash
rm ~/.config/gdrive_mint/.token.enc
```
Faça login novamente pelo aplicativo.

**Interface não abre**
```bash
python3 -m tkinter   # deve abrir uma janela de teste
```

---

## Licença

MIT License — Uso livre para fins pessoais e comerciais.

---

## Links

- [Guia para Desenvolvedores](docs/CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)
- [Packaging (.deb e executável universal)](packaging/README.md)

