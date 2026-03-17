"""
Assistente de configuração — exibido quando credentials.json não existe.

Guia o usuário em 3 etapas:
  1. Escolha: já tem o arquivo ou precisa criar
  2. Guia passo a passo para obter as credenciais no Google Cloud Console
  3. Importação do arquivo + fluxo OAuth (abre navegador com tela de permissão)

Após conclusão, chama on_setup_complete(email).
"""

import json
import os
import shutil
import webbrowser
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from app.ui.theme import ThemeManager

# URLs do Google Cloud Console
_GCP_CREDENTIALS_URL = "https://console.cloud.google.com/apis/credentials"
_GCP_DRIVE_API_URL = (
    "https://console.cloud.google.com/apis/library/drive.googleapis.com"
)
_GCP_NEW_PROJECT_URL = "https://console.cloud.google.com/projectcreate"


class SetupWizardScreen(ctk.CTkFrame):
    """
    Assistente de configuração para primeira execução.

    Fluxo:
        Welcome → (Já tenho) → [file dialog] → Ready → OAuth (browser)
        Welcome → (Preciso criar) → Guide → [file dialog] → Ready → OAuth
    """

    def __init__(
        self,
        parent,
        theme: ThemeManager,
        auth_service,
        on_setup_complete,
        **kwargs,
    ):
        super().__init__(parent, fg_color="transparent", **kwargs)

        self.theme = theme
        self.auth = auth_service
        self.on_setup_complete = on_setup_complete
        self._selected_file: Path | None = None

        # Layout: centraliza o card
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._card = ctk.CTkFrame(
            self,
            width=540,
            corner_radius=16,
            fg_color=self.theme.c("bg_secondary"),
            border_color=self.theme.c("border"),
            border_width=1,
        )
        self._card.grid(row=0, column=0, padx=40, pady=32)
        self._card.grid_propagate(False)
        self._card.configure(height=610)
        self._card.grid_rowconfigure(1, weight=1)
        self._card.grid_columnconfigure(0, weight=1)

        # Stepper (topo)
        self._stepper_frame = ctk.CTkFrame(
            self._card, fg_color="transparent", height=36
        )
        self._stepper_frame.grid(row=0, column=0, sticky="ew", padx=28, pady=(20, 0))

        # Área de conteúdo dinâmica
        self._content = ctk.CTkFrame(self._card, fg_color="transparent")
        self._content.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)

        self._show_welcome()

    # ── Stepper ───────────────────────────────────────────────────────────

    def _update_stepper(self, active_step: int) -> None:
        """Redesenha o indicador de progresso (passos 1, 2 ou 3)."""
        for w in self._stepper_frame.winfo_children():
            w.destroy()

        labels = ["Início", "Credenciais", "Autorizar"]
        items = []
        for i, label in enumerate(labels):
            step_num = i + 1
            done = step_num < active_step
            active = step_num == active_step

            circle_color = (
                self.theme.c("accent_success") if done
                else self.theme.c("accent") if active
                else self.theme.c("border")
            )
            text_color = (
                self.theme.c("text_primary") if (active or done)
                else self.theme.c("text_muted")
            )
            circle_text = "✓" if done else str(step_num)
            items.append((circle_color, circle_text, label, text_color, done))

        container = ctk.CTkFrame(self._stepper_frame, fg_color="transparent")
        container.pack(expand=True)

        for i, (c_color, c_text, label, t_color, done) in enumerate(items):
            # Bolinha
            circle = ctk.CTkFrame(
                container,
                width=26,
                height=26,
                corner_radius=13,
                fg_color=c_color,
                border_width=0,
            )
            circle.pack(side="left", padx=(0, 4))
            circle.pack_propagate(False)
            ctk.CTkLabel(
                circle,
                text=c_text,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="white",
                fg_color="transparent",
            ).place(relx=0.5, rely=0.5, anchor="center")

            # Rótulo do passo
            ctk.CTkLabel(
                container,
                text=label,
                font=self.theme.font(11),
                text_color=t_color,
            ).pack(side="left", padx=(0, 6))

            # Separador (exceto no último)
            if i < len(items) - 1:
                sep_color = self.theme.c("accent_success") if done else self.theme.c("border")
                ctk.CTkFrame(
                    container,
                    width=36,
                    height=2,
                    fg_color=sep_color,
                    corner_radius=1,
                ).pack(side="left", padx=(0, 6))

    # ── Helpers ───────────────────────────────────────────────────────────

    def _clear_content(self) -> None:
        for w in self._content.winfo_children():
            w.destroy()

    # ── Passo 1: Boas-vindas ──────────────────────────────────────────────

    def _show_welcome(self) -> None:
        self._update_stepper(1)
        self._clear_content()
        f = self._content

        ctk.CTkLabel(
            f,
            text="🔑",
            font=ctk.CTkFont(size=60),
        ).pack(pady=(20, 4))

        ctk.CTkLabel(
            f,
            text="Configurar acesso ao Google Drive",
            font=self.theme.font(18, "bold"),
            text_color=self.theme.c("text_primary"),
        ).pack()

        ctk.CTkLabel(
            f,
            text=(
                "Para sincronizar seus arquivos, o GDrive Mint precisa\n"
                "da sua autorização. O processo leva menos de 2 minutos\n"
                "e seus dados ficam 100% no seu computador."
            ),
            font=self.theme.font_small(),
            text_color=self.theme.c("text_secondary"),
            justify="center",
            wraplength=460,
        ).pack(pady=(10, 28))

        # Opção A: já tem o arquivo
        ctk.CTkButton(
            f,
            text="📂   Já tenho o arquivo credentials.json",
            font=self.theme.font(13, "bold"),
            fg_color=self.theme.c("accent"),
            hover_color=self.theme.c("accent_hover"),
            height=46,
            width=340,
            corner_radius=23,
            command=self._pick_credentials_file,
        ).pack(pady=(0, 12))

        # Opção B: precisa criar
        ctk.CTkButton(
            f,
            text="📖   Guia passo a passo (criar agora)",
            font=self.theme.font(13),
            fg_color="transparent",
            hover_color=self.theme.c("bg_primary"),
            text_color=self.theme.c("accent"),
            border_color=self.theme.c("accent"),
            border_width=1,
            height=46,
            width=340,
            corner_radius=23,
            command=self._show_guide,
        ).pack(pady=(0, 4))

        ctk.CTkLabel(
            f,
            text="🔒  Nenhum dado é enviado a terceiros. Conexão direta com o Google.",
            font=self.theme.font(10),
            text_color=self.theme.c("text_muted"),
            justify="center",
        ).pack(side="bottom", pady=20)

    # ── Passo 2: Guia do Google Cloud Console ─────────────────────────────

    def _show_guide(self) -> None:
        self._update_stepper(2)
        self._clear_content()
        f = self._content

        ctk.CTkLabel(
            f,
            text="Obtenha as credenciais do Google (≈ 2 min)",
            font=self.theme.font(15, "bold"),
            text_color=self.theme.c("text_primary"),
            wraplength=480,
            justify="center",
        ).pack(pady=(14, 10))

        # Área rolável com os passos
        scroll = ctk.CTkScrollableFrame(
            f,
            height=330,
            fg_color=self.theme.c("bg_primary"),
            corner_radius=8,
        )
        scroll.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        steps_data = [
            (
                "1.  Abra o Console do Google",
                "Clique no botão abaixo. Uma nova aba será aberta no navegador.",
                "🔗  Abrir Console do Google",
                lambda: webbrowser.open(_GCP_CREDENTIALS_URL),
            ),
            (
                "2.  Crie um projeto",
                'Clique em "Selecionar projeto" → "Novo projeto".\n'
                'Dê um nome (ex: "GDrive Mint") e clique em Criar.',
                "🔗  Criar novo projeto",
                lambda: webbrowser.open(_GCP_NEW_PROJECT_URL),
            ),
            (
                "3.  Ative a API do Google Drive",
                'No menu: APIs e Serviços → Biblioteca.\n'
                'Pesquise "Google Drive API", clique nela e depois em Ativar.',
                "🔗  Ativar API do Drive",
                lambda: webbrowser.open(_GCP_DRIVE_API_URL),
            ),
            (
                "4.  Crie as credenciais OAuth",
                'APIs e Serviços → Credenciais → Criar credenciais\n'
                '→ ID do cliente OAuth 2.0\n'
                '→ Tipo de aplicativo: Aplicativo para computador\n'
                '→ Nome: qualquer → Criar',
                None,
                None,
            ),
            (
                "5.  Baixe o arquivo",
                'Na lista de credenciais criadas, clique no ícone ⬇ (download).\n'
                'Salve como "credentials.json" (nome padrão do Google).',
                None,
                None,
            ),
        ]

        for title, desc, btn_text, btn_cmd in steps_data:
            card = ctk.CTkFrame(
                scroll,
                fg_color=self.theme.c("bg_secondary"),
                corner_radius=8,
                border_color=self.theme.c("border"),
                border_width=1,
            )
            card.pack(fill="x", padx=6, pady=4)

            ctk.CTkLabel(
                card,
                text=title,
                font=self.theme.font(12, "bold"),
                text_color=self.theme.c("text_primary"),
                anchor="w",
            ).pack(anchor="w", padx=14, pady=(10, 2))

            ctk.CTkLabel(
                card,
                text=desc,
                font=self.theme.font(11),
                text_color=self.theme.c("text_secondary"),
                anchor="w",
                justify="left",
                wraplength=400,
            ).pack(
                anchor="w",
                padx=14,
                pady=(0, 10 if not btn_text else 2),
            )

            if btn_text and btn_cmd:
                ctk.CTkButton(
                    card,
                    text=btn_text,
                    font=self.theme.font(11),
                    fg_color="transparent",
                    text_color=self.theme.c("accent"),
                    hover_color=self.theme.c("bg_primary"),
                    anchor="w",
                    height=28,
                    command=btn_cmd,
                ).pack(anchor="w", padx=8, pady=(0, 8))

        # Navegação
        nav = ctk.CTkFrame(f, fg_color="transparent")
        nav.pack(fill="x", padx=12, pady=(4, 4))
        nav.grid_columnconfigure(0, weight=1)
        nav.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            nav,
            text="← Voltar",
            font=self.theme.font(12),
            fg_color="transparent",
            text_color=self.theme.c("text_secondary"),
            hover_color=self.theme.c("bg_primary"),
            command=self._show_welcome,
            width=110,
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            nav,
            text="📂  Selecionar arquivo baixado",
            font=self.theme.font(12, "bold"),
            fg_color=self.theme.c("accent"),
            hover_color=self.theme.c("accent_hover"),
            corner_radius=20,
            command=self._pick_credentials_file,
            width=220,
        ).grid(row=0, column=1, sticky="e")

    # ── Seleção de arquivo ────────────────────────────────────────────────

    def _pick_credentials_file(self) -> None:
        """Abre o seletor de arquivos para escolher credentials.json."""
        filepath = filedialog.askopenfilename(
            parent=self,
            title="Selecionar credentials.json",
            filetypes=[
                ("Arquivo JSON", "*.json"),
                ("Todos os arquivos", "*.*"),
            ],
            initialdir=str(Path.home() / "Downloads"),
        )
        if not filepath:
            return  # Usuário cancelou

        self._import_credentials(Path(filepath))

    def _import_credentials(self, source: Path) -> None:
        """Valida e copia o credentials.json para o diretório de configuração."""
        # Valida conteúdo do arquivo
        try:
            with open(source, encoding="utf-8") as fh:
                data = json.load(fh)

            if "installed" not in data and "web" not in data:
                self._show_file_error(
                    "O arquivo selecionado não é um credentials.json válido.\n"
                    "Certifique-se de baixar o arquivo correto do Google Cloud Console."
                )
                return

            if "web" in data and "installed" not in data:
                self._show_file_error(
                    "Este arquivo é do tipo 'Aplicativo Web'.\n"
                    "O GDrive Mint precisa do tipo 'Aplicativo para computador'.\n\n"
                    "Crie novas credenciais do tipo correto no Console do Google."
                )
                return

        except json.JSONDecodeError:
            self._show_file_error("O arquivo selecionado não é um JSON válido.")
            return
        except OSError:
            self._show_file_error("Não foi possível ler o arquivo selecionado.")
            return

        # Copia com segurança para o diretório de configuração
        dest = self.auth.credentials_file
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(source), str(dest))
        os.chmod(dest, 0o600)

        self._selected_file = dest
        self._show_ready()

    def _show_file_error(self, msg: str) -> None:
        """Exibe diálogo de erro inline."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Arquivo inválido")
        dialog.geometry("400x220")
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.lift()

        ctk.CTkLabel(
            dialog,
            text="⚠️  Arquivo inválido",
            font=self.theme.font(14, "bold"),
            text_color=self.theme.c("accent_danger"),
        ).pack(pady=(28, 8))

        ctk.CTkLabel(
            dialog,
            text=msg,
            font=self.theme.font(12),
            text_color=self.theme.c("text_secondary"),
            wraplength=340,
            justify="center",
        ).pack(pady=(0, 20))

        ctk.CTkButton(
            dialog,
            text="Entendi",
            width=120,
            fg_color=self.theme.c("accent"),
            hover_color=self.theme.c("accent_hover"),
            command=dialog.destroy,
        ).pack()

    # ── Passo 3: Pronto para autorizar ────────────────────────────────────

    def _show_ready(self) -> None:
        self._update_stepper(3)
        self._clear_content()
        f = self._content

        ctk.CTkLabel(
            f,
            text="✅",
            font=ctk.CTkFont(size=52),
        ).pack(pady=(20, 4))

        ctk.CTkLabel(
            f,
            text="Credenciais importadas com sucesso!",
            font=self.theme.font(17, "bold"),
            text_color=self.theme.c("text_primary"),
        ).pack()

        ctk.CTkLabel(
            f,
            text=(
                "Ao clicar em Autorizar, o navegador abrirá com a\n"
                "tela de permissão do Google. Basta clicar em Permitir."
            ),
            font=self.theme.font_small(),
            text_color=self.theme.c("text_secondary"),
            justify="center",
            wraplength=440,
        ).pack(pady=(10, 16))

        # Preview visual da tela do Google
        preview = ctk.CTkFrame(
            f,
            fg_color=self.theme.c("bg_primary"),
            corner_radius=12,
            border_color=self.theme.c("border"),
            border_width=1,
        )
        preview.pack(padx=40, pady=(0, 18), fill="x")

        preview_header = ctk.CTkFrame(
            preview, fg_color=self.theme.c("border"), corner_radius=0, height=2
        )
        preview_header.pack(fill="x")

        ctk.CTkLabel(
            preview,
            text="🔒  accounts.google.com",
            font=self.theme.font(10),
            text_color=self.theme.c("text_muted"),
            anchor="w",
        ).pack(anchor="w", padx=14, pady=(8, 4))

        ctk.CTkLabel(
            preview,
            text="GDrive Mint quer acessar sua conta Google",
            font=self.theme.font(13, "bold"),
            text_color=self.theme.c("text_primary"),
            anchor="w",
        ).pack(anchor="w", padx=14, pady=(2, 8))

        for perm in [
            "✓  Ver e gerenciar arquivos criados por este app no Google Drive",
            "✓  Ver seu endereço de e-mail",
        ]:
            ctk.CTkLabel(
                preview,
                text=perm,
                font=self.theme.font(11),
                text_color=self.theme.c("accent_success"),
                anchor="w",
            ).pack(anchor="w", padx=14, pady=1)

        btn_row = ctk.CTkFrame(preview, fg_color="transparent")
        btn_row.pack(anchor="e", padx=14, pady=(8, 12))
        ctk.CTkLabel(
            btn_row,
            text="Cancelar",
            font=self.theme.font(11),
            text_color=self.theme.c("text_muted"),
        ).pack(side="left", padx=(0, 12))
        ctk.CTkLabel(
            btn_row,
            text="  Permitir  ",
            font=self.theme.font(11, "bold"),
            text_color="white",
            fg_color=self.theme.c("accent"),
            corner_radius=6,
        ).pack(side="left")

        # Botão de autorização
        self._auth_btn = ctk.CTkButton(
            f,
            text="  Autorizar com Google",
            font=self.theme.font(14, "bold"),
            fg_color=self.theme.c("accent"),
            hover_color=self.theme.c("accent_hover"),
            height=48,
            width=290,
            corner_radius=24,
            command=self._start_oauth,
        )
        self._auth_btn.pack(pady=(0, 6))

        self._status_lbl = ctk.CTkLabel(
            f,
            text="",
            font=self.theme.font_small(),
            text_color=self.theme.c("text_secondary"),
            wraplength=400,
        )
        self._status_lbl.pack()

        self._progress = ctk.CTkProgressBar(
            f,
            width=280,
            height=4,
            progress_color=self.theme.c("accent"),
        )
        self._progress.set(0)

        ctk.CTkButton(
            f,
            text="← Voltar",
            font=self.theme.font(11),
            fg_color="transparent",
            text_color=self.theme.c("text_muted"),
            hover_color=self.theme.c("bg_primary"),
            command=self._show_welcome,
        ).pack(side="bottom", pady=10)

    # ── OAuth ─────────────────────────────────────────────────────────────

    def _start_oauth(self) -> None:
        """Inicia o fluxo OAuth — abre navegador com tela de permissão do Google."""
        self._auth_btn.configure(state="disabled", text="⏳  Aguardando navegador...")
        self._status_lbl.configure(
            text="Abrindo navegador...\nConclua a autorização e retorne ao app.",
            text_color=self.theme.c("text_secondary"),
        )
        self._progress.pack(pady=4)
        self._progress.configure(mode="indeterminate")
        self._progress.start()

        self.auth.login(
            on_success=self._on_oauth_success,
            on_error=self._on_oauth_error,
        )

    def _on_oauth_success(self, email: str) -> None:
        self.after(0, lambda: self._handle_oauth_success(email))

    def _handle_oauth_success(self, email: str) -> None:
        self._progress.stop()
        self._progress.pack_forget()
        self._status_lbl.configure(
            text=f"✓  Conectado como {email}",
            text_color=self.theme.c("accent_success"),
        )
        self._auth_btn.configure(text="✓  Autorizado!", state="disabled")
        self.after(1200, lambda: self.on_setup_complete(email))

    def _on_oauth_error(self, error: str) -> None:
        self.after(0, lambda: self._handle_oauth_error(error))

    def _handle_oauth_error(self, error: str) -> None:
        self._progress.stop()
        self._progress.pack_forget()
        self._status_lbl.configure(
            text=f"Erro: {error}",
            text_color=self.theme.c("accent_danger"),
        )
        self._auth_btn.configure(state="normal", text="  Tentar novamente")
