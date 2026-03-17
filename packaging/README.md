# Packaging — GDrive Mint

Este diretório contém os ficheiros necessários para criar pacotes instaláveis do GDrive Mint.
Dois formatos são distribuídos: **pacote .deb** (nativo do Linux Mint/Ubuntu) e **executável universal** (AppImage via PyInstaller, funciona em qualquer distro Linux).

---

## Estrutura

```
packaging/
├── build_deb.sh          # Gera o pacote .deb
├── build_appimage.sh     # Gera o executável universal (PyInstaller)
├── assets/
│   └── gdrive-mint.svg   # Ícone da aplicação
└── flatpak/              # Arquivos mantidos para referência futura
    └── ...               # (não usado na distribuição atual)
```

---

## Opção 1 — Pacote .deb *(recomendado para Linux Mint / Ubuntu)*

O `.deb` é a forma mais familiar para utilizadores do Linux Mint: basta fazer **duplo clique** no ficheiro para instalar pelo Gerenciador de Pacotes.

### Pré-requisitos

```bash
sudo apt install dpkg-dev fakeroot rsync
```

### Construir o .deb

```bash
# A partir do diretório raiz do projeto
bash packaging/build_deb.sh

# Com versão e arquitetura específicas
bash packaging/build_deb.sh --version 1.1.0 --arch amd64
```

O ficheiro `GDrive-Mint-Linux-Mint.deb` será criado em `Instaladores/`.

### O que o instalador faz

| Fase | Ação |
|------|------|
| **Cópia** | Instala o código em `/opt/gdrive-mint/` |
| **postinst** | Cria um venv Python isolado e instala as dependências via pip |
| **Menu** | Cria a entrada `GDrive Mint` no menu de aplicativos |
| **Ícone** | Instala o ícone SVG em `/usr/share/icons/hicolor/scalable/apps/` |

### Instalar o .deb

```bash
# Via terminal
sudo dpkg -i Instaladores/GDrive-Mint-Linux-Mint.deb

# Resolver dependências (se necessário)
sudo apt-get install -f
```

Ou abra o ficheiro `.deb` com o **Gerenciador de Pacotes Gdebi** (instalação com duplo clique).

### Desinstalar

```bash
sudo apt remove gdrive-mint        # remove o pacote
sudo apt purge  gdrive-mint        # remove também os dados em /opt
```

---

## Opção 2 — Executável universal *(AppImage via PyInstaller)*

Um único arquivo binário portátil que funciona em qualquer distribuição Linux sem instalar nada. Todas as dependências (Python 3.12, CustomTkinter, Google API, etc.) estão embutidas.

### Pré-requisitos

```bash
# python3-tk é necessário para o build (tkinter não está no venv)
sudo apt install python3-tk
```

### Construir

```bash
# A partir do diretório raiz do projeto
bash packaging/build_appimage.sh
```

O ficheiro `GDrive-Mint-Universal` será criado em `Instaladores/`.

### Usar o executável

```bash
# Dar permissão de execução (apenas uma vez)
chmod +x GDrive-Mint-Universal

# Executar
./GDrive-Mint-Universal
```

Ou clique com o botão direito no Gerenciador de Arquivos → **Propriedades → Permissões → Permitir executar como programa** → duplo clique.

---

## Gerar ambos de uma vez

```bash
bash gerar_instaladores.sh             # .deb + universal
bash gerar_instaladores.sh --so deb    # apenas .deb
bash gerar_instaladores.sh --so appimage # apenas universal
```

---

## Comparativo

| | `.deb` | Executável universal |
|--|--------|---------------------|
| **Instalação** | Duplo clique no Gerenciador de Pacotes | Dar permissão + duplo clique |
| **Dependências** | Venv criado no postinst | Embutidas no binário |
| **Isolamento** | Nenhum | Nenhum (processo nativo) |
| **Distribuição** | Linux Mint / Ubuntu | Qualquer distro Linux |
| **Tamanho** | ~52 KB (deps instaladas via pip) | ~44 MB (tudo incluso) |
| **Necessita instalação** | Sim (`dpkg`) | Não |

Para utilizadores do **Linux Mint**, o `.deb` é a opção mais simples.
Para **qualquer outra distro**, use o executável universal.
