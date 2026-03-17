# GDrive Mint 🐧☁

**Cliente leve de sincronização com Google Drive para Linux Mint**

Interface gráfica moderna (CustomTkinter) com suporte a Cinnamon, MATE e XFCE.

---

## 📋 Funcionalidades

- ✅ Autenticação OAuth 2.0 (abre navegador automaticamente)
- ✅ Sincronização bidirecional, somente upload ou somente download
- ✅ Monitoramento em tempo real com `watchdog`
- ✅ Dashboard com uso de armazenamento do Drive
- ✅ Logs em tempo real com filtros por nível
- ✅ Ícone na bandeja do sistema (pystray)
- ✅ Inicialização automática com o sistema
- ✅ Notificações nativas via `notify-send`
- ✅ Resolução de conflitos configurável
- ✅ Credenciais criptografadas com AES-128 (Fernet)
- ✅ Tema claro/escuro

---

## 🚀 Instalação

### Pré-requisitos

- Linux Mint 21+ (ou Ubuntu 22.04+)
- Python 3.10+

### Instalação automática

```bash
git clone https://github.com/seu-usuario/gdrive_mint
cd gdrive_mint
./install.sh
```

O script instala automaticamente todas as dependências.

### Instalação manual

```bash
# Dependências do sistema
sudo apt update
sudo apt install python3-pip python3-venv python3-tk libnotify-bin

# Ambiente virtual e dependências Python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 🔐 Configuração do Google OAuth 2.0

> Este passo é obrigatório antes de executar o aplicativo.

### 1. Criar projeto no Google Cloud Console

1. Acesse [console.cloud.google.com](https://console.cloud.google.com/)
2. Crie um novo projeto (ex: `GDrive Mint`)

### 2. Ativar a Google Drive API

1. No menu lateral: **APIs e Serviços → Biblioteca**
2. Busque `Google Drive API` e clique em **Ativar**
3. Repita para `Google People API` (para obter nome/e-mail)

### 3. Criar credenciais OAuth 2.0

1. Vá em **APIs e Serviços → Credenciais**
2. Clique em **Criar Credenciais → ID do cliente OAuth**
3. Tipo: **Aplicativo para computador**
4. Clique em **Criar**
5. Faça o download do JSON

### 4. Instalar o credentials.json

```bash
mkdir -p ~/.config/gdrive_mint
cp ~/Downloads/client_secret_*.json ~/.config/gdrive_mint/credentials.json
chmod 600 ~/.config/gdrive_mint/credentials.json
```

### 5. Configurar tela de consentimento (apenas em desenvolvimento)

1. Vá em **APIs e Serviços → Tela de consentimento OAuth**
2. Tipo: **Externo**
3. Preencha nome do app
4. Em **Usuários de teste**, adicione seu e-mail Google

---

## ▶️ Execução

```bash
# Após instalação com install.sh:
gdrive-mint

# Ou manualmente:
source .venv/bin/activate
python3 main.py
```

---

## 🗂️ Estrutura do Projeto

```
gdrive_mint/
├── main.py                    # Ponto de entrada
├── requirements.txt
├── install.sh
├── app/
│   ├── core/
│   │   ├── sync_engine.py     # Motor de sincronização
│   │   ├── sync_state.py      # Estado dos arquivos
│   │   ├── file_watcher.py    # Monitoramento com watchdog
│   │   └── conflict_resolver.py
│   ├── services/
│   │   ├── google_auth.py     # OAuth 2.0
│   │   └── drive_service.py   # Google Drive API v3
│   ├── linux/
│   │   ├── tray.py            # Bandeja do sistema (pystray)
│   │   ├── autostart.py       # ~/.config/autostart/
│   │   └── notifications.py   # notify-send
│   ├── ui/
│   │   ├── app_window.py      # Janela principal
│   │   ├── theme.py           # Paletas e fontes
│   │   ├── components/
│   │   │   ├── sidebar.py
│   │   │   └── status_bar.py
│   │   └── screens/
│   │       ├── login_screen.py
│   │       ├── dashboard_screen.py
│   │       ├── folders_screen.py
│   │       ├── settings_screen.py
│   │       └── logs_screen.py
│   └── utils/
│       ├── config_manager.py  # Configurações em JSON
│       ├── crypto.py          # Criptografia AES (Fernet)
│       ├── logger.py          # Sistema de logs
│       └── notifications.py
```

---

## 📂 Arquivos gerados em tempo de execução

| Caminho | Conteúdo |
|---|---|
| `~/.config/gdrive_mint/credentials.json` | Credenciais OAuth (você fornece) |
| `~/.config/gdrive_mint/.token.enc` | Token OAuth criptografado |
| `~/.config/gdrive_mint/.keystore` | Chave de criptografia (segura) |
| `~/.config/gdrive_mint/config.json` | Configurações da aplicação |
| `~/.local/share/gdrive_mint/sync_state.json` | Estado dos arquivos sincronizados |
| `~/.local/share/gdrive_mint/logs/gdrive_mint.log` | Logs da aplicação |
| `~/.config/autostart/gdrive-mint.desktop` | Autostart (se ativado) |

---

## 🔒 Segurança

- O token OAuth é criptografado com **AES-128-CBC (Fernet)** antes de salvo
- A chave de criptografia fica em `~/.config/gdrive_mint/.keystore` com permissão `600`
- Nenhum dado é enviado a servidores de terceiros
- Toda comunicação é diretamente com as APIs do Google

---

## 🛠️ Solução de problemas

### "credentials.json não encontrado"
Verifique se o arquivo está em `~/.config/gdrive_mint/credentials.json`

### Tray não aparece no XFCE
Instale: `sudo apt install python3-gi gir1.2-appindicator3-0.1`

### Erro de autenticação
Delete `~/.config/gdrive_mint/.token.enc` e faça login novamente

### Interface não abre
Verifique se `tkinter` está instalado: `python3 -m tkinter`

---

## 📄 Licença

MIT License — Uso livre para fins pessoais e comerciais.
