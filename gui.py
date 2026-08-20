# gui.py
# Interface gráfica do DocOrganizer – Versão 1.3
# Inclui: análise, revisão com paginação, gerenciamento de temas, histórico, ajuda, cancelamento e undo.

import hashlib
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
import threading
import logging
import shutil
from pathlib import Path

# Importa os módulos do projeto
import scanner
import extractor
import classifier
import planner
from history import HistorySQLite
import config
import database
import user_themes


def calcular_hash_arquivo(caminho):
    """Calcula o hash SHA-256 de um arquivo."""
    h = hashlib.sha256()
    with open(caminho, 'rb') as f:
        for bloco in iter(lambda: f.read(4096), b''):
            h.update(bloco)
    return h.hexdigest()


class DocOrganizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DocOrganizer")
        self.root.geometry("780x700")
        self.root.resizable(True, True)

        # Variáveis de interface
        self.origem_var = tk.StringVar()
        self.destino_var = tk.StringVar()
        self.incluir_subpastas_var = tk.BooleanVar(value=True)
        self.usar_ocr_var = tk.BooleanVar(value=True)
        self.incluir_texto_simples_var = tk.BooleanVar(value=config.INCLUIR_TEXTO_SIMPLES_PADRAO)

        # Dados da análise
        self.documentos = []
        self.classificacoes = []
        self.plano = []

        # Controle de cancelamento
        self.cancelar = False

        # Lista de botões de ação (para desabilitar durante operações)
        self.botoes_acao = []

        # Referência para a janela de revisão
        self.janela_revisao = None
        self.tree_revisao = None
        self.mapeamento_revisao = []
        self.pagina_atual = 0
        self.itens_por_pagina = 50

        # Cria a interface
        self.criar_menu()
        self.criar_widgets()

        # Configura o log para aparecer na interface
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.log_handler = LogHandler(self.txt_log)
        logging.getLogger().addHandler(self.log_handler)

        # Atualiza estado inicial do botão Desfazer e Revisar
        self.atualizar_estado_desfazer()
        self.atualizar_estado_revisar()

    def criar_menu(self):
        menubar = tk.Menu(self.root)

        menu_ajuda = tk.Menu(menubar, tearoff=0)
        menu_ajuda.add_command(label="Ajuda", command=self.mostrar_ajuda)
        menu_ajuda.add_command(label="Sobre", command=self.mostrar_sobre)
        menu_ajuda.add_separator()
        menu_ajuda.add_command(label="Histórico de operações", command=self.mostrar_historico)
        menubar.add_cascade(label="Menu", menu=menu_ajuda)

        self.root.config(menu=menubar)

    def criar_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Pasta de origem
        ttk.Label(main_frame, text="Pasta de origem:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.origem_var, width=65).grid(row=0, column=1, padx=5)
        btn_origem = ttk.Button(main_frame, text="Procurar", command=self.selecionar_origem)
        btn_origem.grid(row=0, column=2)

        # Pasta de destino
        ttk.Label(main_frame, text="Pasta de destino:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.destino_var, width=65).grid(row=1, column=1, padx=5)
        btn_destino = ttk.Button(main_frame, text="Procurar", command=self.selecionar_destino)
        btn_destino.grid(row=1, column=2)

        # Opções
        opcoes_frame = ttk.Frame(main_frame)
        opcoes_frame.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=5)
        ttk.Checkbutton(opcoes_frame, text="Incluir subpastas", variable=self.incluir_subpastas_var).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(opcoes_frame, text="Ativar OCR (PDFs escaneados)", variable=self.usar_ocr_var).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(opcoes_frame, text="Incluir arquivos de texto (.txt, .md)", variable=self.incluir_texto_simples_var).pack(side=tk.LEFT, padx=5)

        # Botões principais
        botoes_frame = ttk.Frame(main_frame)
        botoes_frame.grid(row=3, column=0, columnspan=3, pady=10)

        btn_analisar = ttk.Button(botoes_frame, text="Analisar", command=self.analisar)
        btn_analisar.pack(side=tk.LEFT, padx=5)
        self.botoes_acao.append(btn_analisar)

        btn_organizar = ttk.Button(botoes_frame, text="Organizar", command=self.organizar)
        btn_organizar.pack(side=tk.LEFT, padx=5)
        self.botoes_acao.append(btn_organizar)

        btn_temas = ttk.Button(botoes_frame, text="Gerenciar Temas", command=self.abrir_gerenciador_temas)
        btn_temas.pack(side=tk.LEFT, padx=5)

        # Barra de progresso
        self.progresso = ttk.Progressbar(main_frame, orient=tk.HORIZONTAL, length=680, mode='determinate')
        self.progresso.grid(row=4, column=0, columnspan=3, pady=5)

        # Área de log
        log_frame = ttk.LabelFrame(main_frame, text="Log de atividades", padding=5)
        log_frame.grid(row=5, column=0, columnspan=3, sticky=tk.NSEW, pady=5)
        self.txt_log = tk.Text(log_frame, height=20, width=85)
        scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.txt_log.yview)
        self.txt_log.configure(yscrollcommand=scroll.set)
        self.txt_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Frame inferior para botões secundários
        frame_inferior = ttk.Frame(main_frame)
        frame_inferior.grid(row=6, column=0, columnspan=3, sticky=tk.EW, pady=(10, 0))

        self.btn_desfazer = ttk.Button(frame_inferior, text="Desfazer última organização", command=self.desfazer)
        self.btn_desfazer.pack(side=tk.LEFT, padx=5)

        self.btn_cancelar = ttk.Button(frame_inferior, text="Cancelar", command=self.cancelar_operacao, state='disabled')
        self.btn_cancelar.pack(side=tk.LEFT, padx=5)

        self.btn_revisar = ttk.Button(frame_inferior, text="Revisar pendências", command=self.mostrar_plano_treeview, state='disabled')
        self.btn_revisar.pack(side=tk.LEFT, padx=5)

        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(5, weight=1)

    def abrir_gerenciador_temas(self):
        GerenciadorTemas(self.root)

    def selecionar_origem(self):
        pasta = filedialog.askdirectory(title="Selecione a pasta de origem")
        if pasta:
            self.origem_var.set(pasta)

    def selecionar_destino(self):
        pasta = filedialog.askdirectory(title="Selecione a pasta de destino")
        if pasta:
            self.destino_var.set(pasta)

    def analisar(self):
        origem = self.origem_var.get().strip()
        destino = self.destino_var.get().strip()

        if not origem or not Path(origem).exists():
            messagebox.showerror("Erro", "Selecione uma pasta de origem válida.")
            return

        if not destino:
            messagebox.showerror("Erro", "Selecione uma pasta de destino antes de analisar.")
            return
        if not Path(destino).exists():
            try:
                Path(destino).mkdir(parents=True, exist_ok=True)
                self.destino_var.set(destino)
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível criar a pasta de destino: {e}")
                return

        self.limpar_log()
        self.progresso['value'] = 0
        self.cancelar = False
        self.set_estado_operacao(True)
        threading.Thread(target=self._analisar_thread, args=(origem, destino), daemon=True).start()

    def _analisar_thread(self, origem, destino):
        try:
            logging.info(f"Analisando pasta: {origem}")
            incluir_subpastas = self.incluir_subpastas_var.get()
            incluir_txt = self.incluir_texto_simples_var.get()
            self.documentos = scanner.encontrar_documentos(
                origem,
                incluir_subpastas=incluir_subpastas,
                incluir_texto_simples=incluir_txt
            )
            total = len(self.documentos)
            logging.info(f"Documentos encontrados: {total}")
            self.classificacoes = []

            for i, doc in enumerate(self.documentos):
                if self.cancelar:
                    logging.info("Análise cancelada pelo usuário.")
                    break
                try:
                    conteudo = extractor.extrair_metadados_e_texto(doc.path, usar_ocr=self.usar_ocr_var.get())
                    result = classifier.classificar(
                        texto=conteudo['texto'],
                        metadados=conteudo['metadados'],
                        nome_arquivo=doc.name
                    )
                    self.classificacoes.append(result)
                except Exception as e:
                    logging.error(f"Erro ao processar {doc.name}: {e}")
                    self.classificacoes.append(None)

                progresso = (i + 1) / total * 100
                self.root.after(0, self._atualizar_progresso, progresso)

            if self.cancelar:
                return

            seguras = sum(1 for c in self.classificacoes if c and c.level == 'SEGURA')
            revisao = sum(1 for c in self.classificacoes if c and c.level == 'REVISAO')
            triagem = sum(1 for c in self.classificacoes if c and c.level == 'TRIAGEM')
            logging.info(f"Classificação concluída: {seguras} seguras, {revisao} revisão, {triagem} triagem.")

            self.plano = planner.criar_plano(self.documentos, self.classificacoes, destino)
            self.atualizar_estado_revisar()

            if revisao > 0:
                self.pagina_atual = 0
                self.root.after(0, self.mostrar_plano_treeview)
            else:
                self.root.after(0, lambda: messagebox.showinfo(
                    "Análise concluída",
                    "A análise foi concluída e não há documentos que requeiram revisão.\n"
                    "Você pode clicar em Organizar para mover os arquivos classificados como SEGURA e TRIAGEM."
                ))

        finally:
            self.root.after(0, self._operacao_finalizada)

    def _atualizar_progresso(self, valor):
        self.progresso['value'] = valor

    def _operacao_finalizada(self):
        self.set_estado_operacao(False)
        self.cancelar = False
        self.atualizar_estado_desfazer()
        self.atualizar_estado_revisar()

    def mostrar_plano_treeview(self):
        if not self.plano:
            messagebox.showinfo("Sem plano", "Execute uma análise primeiro.")
            return

        if self.janela_revisao and self.janela_revisao.winfo_exists():
            self.janela_revisao.lift()
            self.janela_revisao.focus_force()
            return

        self.janela_revisao = tk.Toplevel(self.root)
        self.janela_revisao.title("Revisão dos documentos incertos")
        self.janela_revisao.geometry("1000x600")

        frame_principal = ttk.Frame(self.janela_revisao)
        frame_principal.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        colunas = ("origem", "tema", "acao", "destino", "nivel")
        self.tree_revisao = ttk.Treeview(frame_principal, columns=colunas, show="headings", selectmode="browse")
        self.tree_revisao.heading("origem", text="Arquivo")
        self.tree_revisao.heading("tema", text="Tema")
        self.tree_revisao.heading("acao", text="Ação")
        self.tree_revisao.heading("destino", text="Destino")
        self.tree_revisao.heading("nivel", text="Nível original")

        self.tree_revisao.column("origem", width=250)
        self.tree_revisao.column("tema", width=120)
        self.tree_revisao.column("acao", width=90)
        self.tree_revisao.column("destino", width=400)
        self.tree_revisao.column("nivel", width=80)

        scroll = ttk.Scrollbar(frame_principal, orient=tk.VERTICAL, command=self.tree_revisao.yview)
        self.tree_revisao.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_revisao.pack(fill=tk.BOTH, expand=True)

        frame_botoes = ttk.Frame(self.janela_revisao)
        frame_botoes.pack(fill=tk.X, pady=5)

        self.btn_revisar_item = ttk.Button(frame_botoes, text="Revisar selecionado", command=self.revisar_item)
        self.btn_revisar_item.pack(side=tk.LEFT, padx=5)

        self.btn_anterior = ttk.Button(frame_botoes, text="Anterior", command=self.pagina_anterior, state='disabled')
        self.btn_anterior.pack(side=tk.LEFT, padx=5)

        self.lbl_pagina = ttk.Label(frame_botoes, text="")
        self.lbl_pagina.pack(side=tk.LEFT, padx=10)

        self.btn_proxima = ttk.Button(frame_botoes, text="Próxima", command=self.pagina_proxima)
        self.btn_proxima.pack(side=tk.LEFT, padx=5)

        btn_fechar = ttk.Button(frame_botoes, text="Fechar", command=self.fechar_janela_revisao)
        btn_fechar.pack(side=tk.RIGHT, padx=5)

        self.carregar_pagina(0)

    def carregar_pagina(self, pagina):
        total_itens = len(self.plano)
        total_paginas = max(1, (total_itens + self.itens_por_pagina - 1) // self.itens_por_pagina)

        pagina = max(0, min(pagina, total_paginas - 1))
        self.pagina_atual = pagina

        inicio = pagina * self.itens_por_pagina
        fim = min(inicio + self.itens_por_pagina, total_itens)

        for item in self.tree_revisao.get_children():
            self.tree_revisao.delete(item)

        self.mapeamento_revisao = list(range(inicio, fim))

        for idx_global in self.mapeamento_revisao:
            item = self.plano[idx_global]
            origem = Path(item['origem']).name
            self.tree_revisao.insert("", tk.END, values=(
                origem,
                item['tema'],
                item['action'],
                item['destino'] if item['destino'] else '—',
                item.get('nivel', '')
            ))

        self.lbl_pagina.config(text=f"Página {pagina + 1} de {total_paginas}")
        self.btn_anterior.config(state='normal' if pagina > 0 else 'disabled')
        self.btn_proxima.config(state='normal' if pagina < total_paginas - 1 else 'disabled')

    def pagina_anterior(self):
        self.carregar_pagina(self.pagina_atual - 1)

    def pagina_proxima(self):
        self.carregar_pagina(self.pagina_atual + 1)

    def fechar_janela_revisao(self):
        if self.janela_revisao:
            self.janela_revisao.destroy()
            self.janela_revisao = None

    def revisar_item(self):
        if not hasattr(self, 'tree_revisao'):
            return
        selecionado = self.tree_revisao.selection()
        if not selecionado:
            messagebox.showwarning("Nenhum item selecionado", "Selecione um item na lista.")
            return

        item_id = selecionado[0]
        indice_na_pagina = self.tree_revisao.index(item_id)
        if indice_na_pagina >= len(self.mapeamento_revisao):
            return
        idx_global = self.mapeamento_revisao[indice_na_pagina]
        item = self.plano[idx_global]

        if item.get('nivel') != 'REVISAO':
            messagebox.showinfo("Item não revisável", "Este item não requer revisão (nível original não é REVISAO).")
            return

        decisao_janela = tk.Toplevel(self.janela_revisao)
        decisao_janela.title(f"Revisar: {Path(item['origem']).name}")
        decisao_janela.geometry("500x320")
        decisao_janela.transient(self.janela_revisao)

        ttk.Label(decisao_janela, text=f"Arquivo: {Path(item['origem']).name}", font=("Arial", 10, "bold")).pack(anchor=tk.W, padx=10, pady=5)
        ttk.Label(decisao_janela, text=f"Tema sugerido: {item['tema']}").pack(anchor=tk.W, padx=10)
        ttk.Label(decisao_janela, text=f"Confiança: {item['reason']}").pack(anchor=tk.W, padx=10, pady=5)

        frame_opcoes = ttk.Frame(decisao_janela)
        frame_opcoes.pack(pady=10)

        acao_atual = item['action']
        var = tk.StringVar(value="naomover")
        if acao_atual == 'MOVE' and item.get('destino'):
            var.set("aprovar")
        elif acao_atual == 'SKIP':
            var.set("naomover")

        ttk.Radiobutton(frame_opcoes, text="Aprovar sugestão (mover)", variable=var, value="aprovar").pack(anchor=tk.W)
        ttk.Radiobutton(frame_opcoes, text="Alterar tema", variable=var, value="alterar").pack(anchor=tk.W)
        ttk.Radiobutton(frame_opcoes, text="Enviar para Triagem", variable=var, value="triagem").pack(anchor=tk.W)
        ttk.Radiobutton(frame_opcoes, text="Não mover", variable=var, value="naomover").pack(anchor=tk.W)

        def confirmar():
            decisao = var.get()
            if decisao == "aprovar":
                destino_pasta = Path(self.destino_var.get()) / item['tema']
                item['action'] = 'MOVE'
                item['destino'] = str(destino_pasta / Path(item['origem']).name)
                item['reason'] = 'Aprovado pelo usuário (revisão)'
            elif decisao == "alterar":
                novo_tema = simpledialog.askstring("Novo tema", "Digite o nome do tema:")
                if novo_tema and novo_tema.strip():
                    tema = novo_tema.strip()
                    destino_pasta = Path(self.destino_var.get()) / tema
                    item['tema'] = tema
                    item['action'] = 'MOVE'
                    item['destino'] = str(destino_pasta / Path(item['origem']).name)
                    item['reason'] = f'Tema alterado para {tema}'
            elif decisao == "triagem":
                destino_pasta = Path(self.destino_var.get()) / config.PASTA_TRIAGEM
                item['tema'] = config.PASTA_TRIAGEM
                item['action'] = 'MOVE'
                item['destino'] = str(destino_pasta / Path(item['origem']).name)
                item['reason'] = 'Enviado para Triagem pelo usuário'
            elif decisao == "naomover":
                item['action'] = 'SKIP'
                item['destino'] = ''
                item['reason'] = 'Ignorado pelo usuário (revisão)'

            self.tree_revisao.item(item_id, values=(
                Path(item['origem']).name,
                item['tema'],
                item['action'],
                item['destino'] if item['destino'] else '—',
                item.get('nivel', '')
            ))

            decisao_janela.destroy()
            self.janela_revisao.lift()
            self.janela_revisao.focus_force()

        ttk.Button(decisao_janela, text="Confirmar", command=confirmar).pack(pady=10)

    def organizar(self):
        if not self.plano:
            messagebox.showwarning("Aviso", "Nenhum plano disponível. Execute a análise primeiro.")
            return
        plano_execucao = [item for item in self.plano if item['action'] != 'SKIP']
        if not plano_execucao:
            messagebox.showinfo("Nada a mover", "Nenhum arquivo selecionado para mover.")
            return
        if not messagebox.askyesno("Confirmar", f"Deseja realmente mover {len(plano_execucao)} arquivo(s)?"):
            return
        self.plano = plano_execucao
        self.cancelar = False
        self.set_estado_operacao(True)
        threading.Thread(target=self._organizar_thread, daemon=True).start()

    def _organizar_thread(self):
        hist = HistorySQLite()
        op_id = hist.start_operation(total=len(self.plano))
        success = failed = skipped = 0
        total = len(self.plano)

        for i, item in enumerate(self.plano):
            if self.cancelar:
                logging.info("Organização cancelada pelo usuário.")
                break

            if item['action'] == 'MOVE' or item['action'] == 'RENAME_CONFLICT':
                origem = Path(item['origem'])
                destino = Path(item['destino'])

                # Verifica conflito de destino (pode ter sido criado por outro arquivo)
                if destino.exists():
                    hash_origem = calcular_hash_arquivo(origem)
                    hash_destino = calcular_hash_arquivo(destino)

                    if hash_origem == hash_destino:
                        logging.info(f"Duplicado ignorado: {origem}")
                        hist.record_item(op_id, str(origem), str(destino), '', 'SKIPPED')
                        skipped += 1
                        progresso = (i + 1) / total * 100
                        self.root.after(0, self._atualizar_progresso, progresso)
                        continue
                    else:
                        # Conteúdo diferente: gera novo nome com sufixo
                        base = destino.stem
                        ext = destino.suffix
                        contador = 1
                        novo_destino = destino.parent / f"{base}_{contador}{ext}"
                        while novo_destino.exists():
                            contador += 1
                            novo_destino = destino.parent / f"{base}_{contador}{ext}"
                        destino = novo_destino
                        item['destino'] = str(destino)
                        item['action'] = 'MOVE'
                        logging.info(f"Conflito resolvido: {origem} -> {destino}")

                destino.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.move(str(origem), str(destino))
                    logging.info(f"Movido: {origem} -> {destino}")
                    hist.record_item(op_id, str(origem), str(destino), '', 'SUCCESS')
                    success += 1
                except Exception as e:
                    logging.error(f"Erro ao mover {origem}: {e}")
                    hist.record_item(op_id, str(origem), str(destino), '', 'FAILED')
                    failed += 1

            elif item['action'] == 'SKIP_DUPLICATE':
                logging.info(f"Duplicado ignorado: {item['origem']}")
                hist.record_item(op_id, item['origem'], item['destino'], '', 'SKIPPED')
                skipped += 1

            progresso = (i + 1) / total * 100
            self.root.after(0, self._atualizar_progresso, progresso)

        hist.finish_operation(op_id, 'SUCCESS' if failed == 0 else 'PARTIAL', success, failed, skipped)
        logging.info(f"Execução concluída: sucesso={success}, falhas={failed}, ignorados={skipped}")

        self.root.after(0, self._operacao_finalizada)

    def desfazer(self):
        if not messagebox.askyesno("Desfazer", "Deseja desfazer a última organização?"):
            return
        hist = HistorySQLite()
        sucesso = hist.undo_last_operation()
        if sucesso:
            messagebox.showinfo("Desfeito", "Operação desfeita com sucesso.")
        else:
            messagebox.showinfo("Nada para desfazer", "Não há operação válida para desfazer.")
        self.atualizar_estado_desfazer()

    def cancelar_operacao(self):
        self.cancelar = True
        logging.info("Cancelamento solicitado...")
        self.btn_cancelar.config(state='disabled')

    def set_estado_operacao(self, em_andamento):
        estado_acao = 'disabled' if em_andamento else 'normal'
        estado_cancelar = 'normal' if em_andamento else 'disabled'
        for btn in self.botoes_acao:
            btn.config(state=estado_acao)
        self.btn_cancelar.config(state=estado_cancelar)

    def atualizar_estado_desfazer(self):
        hist = HistorySQLite()
        if hist.has_undoable_operation():
            self.btn_desfazer.config(state='normal')
        else:
            self.btn_desfazer.config(state='disabled')

    def atualizar_estado_revisar(self):
        if any(item.get('nivel') == 'REVISAO' for item in self.plano):
            self.btn_revisar.config(state='normal')
        else:
            self.btn_revisar.config(state='disabled')

    def mostrar_ajuda(self):
        janela = tk.Toplevel(self.root)
        janela.title("Ajuda do DocOrganizer")
        janela.geometry("600x500")
        texto = tk.Text(janela, wrap=tk.WORD, padx=10, pady=10)
        scroll = ttk.Scrollbar(janela, orient=tk.VERTICAL, command=texto.yview)
        texto.configure(yscrollcommand=scroll.set)
        texto.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        conteudo = """
        BEM-VINDO AO DOCORGANIZER

        Como usar:

        1. Selecione a pasta de origem.
        2. Selecione a pasta de destino.
        3. Escolha as opções desejadas.
        4. Clique em "Analisar".
           - Ao terminar, se houver documentos com classificação REVISÃO, uma janela abrirá automaticamente.
           - Você pode reabrir essa janela a qualquer momento usando o botão "Revisar pendências".
        5. Para cada item REVISÃO, escolha Aprovar, Alterar tema, Triagem ou Não mover.
           - Você pode alterar sua decisão depois, bastando selecionar o item novamente.
        6. Clique em "Organizar" para mover os arquivos.
        7. Use "Desfazer última organização" para reverter a última operação.

        Níveis:
        - SEGURA: será movido automaticamente.
        - REVISÃO: requer sua decisão.
        - TRIAGEM: será movido para a pasta Triagem.

        O aplicativo é 100% offline e não envia dados para a nuvem.
        """
        texto.insert(tk.END, conteudo)
        texto.config(state=tk.DISABLED)

    def mostrar_sobre(self):
        messagebox.showinfo(
            "Sobre o DocOrganizer",
            "DocOrganizer\nVersão 1.3\n\nAplicativo local para organização de documentos.\n"
            "100% offline, sem IA, sem nuvem.\nLicença MIT.\n\nDesenvolvido com Python e Tkinter."
        )

    def mostrar_historico(self):
        janela = tk.Toplevel(self.root)
        janela.title("Histórico de operações")
        janela.geometry("800x400")

        colunas = ("id", "data", "status", "total", "sucesso", "falhas", "ignorados")
        tree = ttk.Treeview(janela, columns=colunas, show="headings")
        tree.heading("id", text="ID")
        tree.heading("data", text="Data/Hora")
        tree.heading("status", text="Status")
        tree.heading("total", text="Total")
        tree.heading("sucesso", text="Sucesso")
        tree.heading("falhas", text="Falhas")
        tree.heading("ignorados", text="Ignorados")

        tree.column("id", width=40)
        tree.column("data", width=150)
        tree.column("status", width=80)
        tree.column("total", width=60)
        tree.column("sucesso", width=80)
        tree.column("falhas", width=80)
        tree.column("ignorados", width=80)

        tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        try:
            conn = database.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM operations ORDER BY id DESC LIMIT 50')
            for op in cursor.fetchall():
                tree.insert("", tk.END, values=(
                    op['id'], op['timestamp'], op['status'],
                    op['total'], op['success'], op['failed'], op['skipped']
                ))
            conn.close()
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar histórico: {e}")

        btn_fechar = ttk.Button(janela, text="Fechar", command=janela.destroy)
        btn_fechar.pack(pady=5)

    def limpar_log(self):
        self.txt_log.delete(1.0, tk.END)


class GerenciadorTemas:
    """Janela para adicionar, editar e remover temas personalizados."""

    def __init__(self, parent):
        self.parent = parent
        self.janela = tk.Toplevel(parent)
        self.janela.title("Gerenciar Temas Personalizados")
        self.janela.geometry("600x500")
        self.janela.resizable(True, True)

        self.criar_widgets()
        self.carregar_temas()

    def criar_widgets(self):
        main_frame = ttk.Frame(self.janela, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Temas existentes:").grid(row=0, column=0, sticky=tk.W)
        self.lista_temas = tk.Listbox(main_frame, height=10, width=30)
        self.lista_temas.grid(row=1, column=0, rowspan=4, sticky=tk.NSEW, padx=5, pady=5)
        self.lista_temas.bind('<<ListboxSelect>>', self.selecionar_tema)

        ttk.Label(main_frame, text="Nome do tema:").grid(row=1, column=1, sticky=tk.W)
        self.entry_tema = ttk.Entry(main_frame, width=30)
        self.entry_tema.grid(row=1, column=2, padx=5, pady=5)

        ttk.Label(main_frame, text="Palavras-chave (separadas por vírgula):").grid(row=2, column=1, sticky=tk.W)
        self.entry_keywords = tk.Text(main_frame, width=30, height=8)
        self.entry_keywords.grid(row=2, column=2, padx=5, pady=5)

        btn_salvar = ttk.Button(main_frame, text="Salvar tema", command=self.salvar_tema)
        btn_salvar.grid(row=3, column=2, sticky=tk.W, padx=5, pady=5)

        btn_remover = ttk.Button(main_frame, text="Remover tema", command=self.remover_tema)
        btn_remover.grid(row=4, column=2, sticky=tk.W, padx=5, pady=5)

        btn_fechar = ttk.Button(main_frame, text="Fechar", command=self.janela.destroy)
        btn_fechar.grid(row=5, column=2, sticky=tk.W, padx=5, pady=5)

        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(2, weight=1)
        main_frame.rowconfigure(4, weight=1)

    def carregar_temas(self):
        self.lista_temas.delete(0, tk.END)
        temas = database.get_all_user_theme_names()
        for tema in temas:
            self.lista_temas.insert(tk.END, tema)

    def selecionar_tema(self, event):
        selecionado = self.lista_temas.curselection()
        if not selecionado:
            return
        tema = self.lista_temas.get(selecionado[0])
        self.entry_tema.delete(0, tk.END)
        self.entry_tema.insert(0, tema)
        keywords = database.get_keywords_for_theme(tema)
        self.entry_keywords.delete(1.0, tk.END)
        self.entry_keywords.insert(1.0, ', '.join(keywords))

    def salvar_tema(self):
        tema = self.entry_tema.get().strip()
        if not tema:
            messagebox.showwarning("Aviso", "Informe um nome para o tema.")
            return
        texto_keywords = self.entry_keywords.get(1.0, tk.END)
        keywords = [kw.strip() for kw in texto_keywords.split(',') if kw.strip()]
        if not keywords:
            messagebox.showwarning("Aviso", "Adicione pelo menos uma palavra-chave.")
            return
        database.save_user_theme(tema, keywords)
        self.carregar_temas()
        messagebox.showinfo("Sucesso", f"Tema '{tema}' salvo com {len(keywords)} palavra(s).")

    def remover_tema(self):
        selecionado = self.lista_temas.curselection()
        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione um tema na lista para remover.")
            return
        tema = self.lista_temas.get(selecionado[0])
        if messagebox.askyesno("Confirmar", f"Deseja remover o tema '{tema}'?"):
            database.delete_user_theme(tema)
            self.carregar_temas()
            self.entry_tema.delete(0, tk.END)
            self.entry_keywords.delete(1.0, tk.END)
            messagebox.showinfo("Removido", f"Tema '{tema}' removido.")


class LogHandler(logging.Handler):
    """Handler personalizado para exibir logs na interface."""
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record) + '\n'
        self.text_widget.insert(tk.END, msg)
        self.text_widget.see(tk.END)


if __name__ == '__main__':
    root = tk.Tk()
    app = DocOrganizerApp(root)
    root.mainloop()