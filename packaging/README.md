# Packaging — GDrive Mint

Este diretório contém os ficheiros necessários para criar pacotes instaláveis do GDrive Mint.
Dois formatos são suportados: **pacote .deb** (nativo do Linux Mint/Ubuntu) e **Flatpak** (multiplataforma, com sandbox).

---

## Estrutura

```
packaging/
├── build_deb.sh                  # Gera o pacote .deb
├── assets/
│   └── gdrive-mint.svg           # Ícone da aplicação
└── flatpak/
    ├── io.github.gdrivemint.GDriveMint.yml          # Manifesto Flatpak
    ├── io.github.gdrivemint.GDriveMint.appdata.xml  # Metadados AppStream
    ├── io.github.gdrivemint.GDriveMint.desktop      # Entrada de menu
    ├── launcher.sh                                   # Script de lançamento
    ├── generate_sources.sh                           # Gera fontes pip para Flatpak
    └── build_flatpak.sh                              # Constrói o Flatpak
```

---

## Opção 1 — Pacote .deb *(recomendado para Linux Mint)*

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

O ficheiro `gdrive-mint_1.1.0_amd64.deb` será criado em `packaging/`.

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
sudo dpkg -i packaging/gdrive-mint_1.1.0_amd64.deb

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

## Opção 2 — Flatpak *(portável, com sandbox)*

O Flatpak oferece isolamento completo da aplicação do sistema, com todas as dependências embutidas. É a melhor opção para distribuição em múltiplas distribuições Linux.

### Pré-requisitos do sistema

```bash
# Instalar ferramentas Flatpak
sudo apt install flatpak flatpak-builder

# Adicionar repositório Flathub
flatpak remote-add --if-not-exists flathub \
    https://flathub.org/repo/flathub.flatpakrepo

# Instalar o runtime e SDK necessários
flatpak install flathub \
    org.freedesktop.Platform//24.08 \
    org.freedesktop.Sdk//24.08 \
    org.freedesktop.Sdk.Extension.python312//24.08
```

### Passo 1 — Gerar fontes pip

O Flatpak precisa de baixar os pacotes Python offline (no momento do build).
Execute o gerador de fontes **uma vez** (e sempre que o `requirements.txt` mudar):

```bash
bash packaging/flatpak/generate_sources.sh
```

Isto cria `packaging/flatpak/python3-requirements.json` com os hashes verificados de todos os pacotes pip.

### Passo 2 — Construir o Flatpak

```bash
# Build simples (para teste)
bash packaging/flatpak/build_flatpak.sh

# Build + instalação local
bash packaging/flatpak/build_flatpak.sh --install

# Build + gerar bundle .flatpak para distribuição
bash packaging/flatpak/build_flatpak.sh --bundle
```

### Instalar o bundle .flatpak

```bash
flatpak install --user packaging/flatpak/io.github.gdrivemint.GDriveMint.flatpak
```

### Executar

```bash
flatpak run io.github.gdrivemint.GDriveMint
```

### Desinstalar

```bash
flatpak --user uninstall io.github.gdrivemint.GDriveMint
```

### Publicar no Flathub *(opcional)*

1. Edite os metadados `io.github.gdrivemint.GDriveMint.appdata.xml`:
   - Substitua o `id`, URL do repositório e nome do desenvolvedor
   - Adicione capturas de ecrã reais
2. Abra um PR no repositório [flathub/flathub](https://github.com/flathub/flathub) seguindo o [guia oficial](https://docs.flathub.org/docs/for-app-authors/submission).

---

## Comparativo

| | `.deb` | Flatpak |
|--|--------|---------|
| **Instalação** | Duplo clique | `flatpak install` |
| **Dependências** | Venv criado no postinst | Embutidas no bundle |
| **Isolamento** | Nenhum | Sandbox completa |
| **Distribuição** | Linux Mint / Ubuntu | Qualquer distro com Flatpak |
| **Tamanho** | ~10 MB + deps via pip | ~150–200 MB (runtime incluído) |
| **Flathub** | Não aplicável | Sim |

Para utilizadores do **Linux Mint**, o `.deb` é a opção mais simples e integrada.
O **Flatpak** é preferível se pretender distribuir para outras distribuições.
