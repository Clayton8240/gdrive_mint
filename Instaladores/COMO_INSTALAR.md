# Como instalar o GDrive Mint

## Baixar o instalador

Acesse a página de releases e baixe o arquivo para o seu sistema:

**https://github.com/Clayton8240/gdrive_mint/releases/latest**

| Arquivo | Para quem? |
|---|---|
| `GDrive-Mint-Linux-Mint.deb` | Linux Mint ou Ubuntu |
| `GDrive-Mint-Universal.flatpak` | Qualquer outra distribuição Linux |

---

## Linux Mint / Ubuntu — Instalador recomendado

**Arquivo:** `GDrive-Mint-Linux-Mint.deb`

1. **Duplo clique** no arquivo `GDrive-Mint-Linux-Mint.deb`
2. O Gerenciador de Pacotes abrirá automaticamente
3. Clique em **Instalar**
4. Digite sua senha de usuário quando solicitado
5. Aguarde a instalação terminar

Pronto! Procure por **GDrive Mint** no menu de aplicativos.

---

## Qualquer outra distribuição Linux — Instalador universal

**Arquivo:** `GDrive-Mint-Universal`

1. Clique com o botão direito no arquivo → **Propriedades → Permissões** → marque **"Permitir executar o arquivo como um programa"**
2. Duplo clique no arquivo para executar

Ou pelo terminal:

```bash
chmod +x GDrive-Mint-Universal
./GDrive-Mint-Universal
```

> Este arquivo já inclui o Python e todas as dependências. Não é necessário instalar nada.

---

## Após instalar — Passo obrigatório

Antes de usar o aplicativo pela primeira vez, você precisa configurar o acesso ao Google Drive.

Consulte o guia completo: [README.md](../README.md#configuração-do-google-oauth-20)

Em resumo:
1. Acesse [console.cloud.google.com](https://console.cloud.google.com/) e crie um projeto
2. Ative a **Google Drive API**
3. Crie uma credencial **OAuth 2.0 para computador** e baixe o JSON
4. Coloque o arquivo baixado em `~/.config/gdrive_mint/credentials.json`

---

## Problemas na instalação?

- Abra uma issue em: https://github.com/Clayton8240/gdrive_mint/issues
