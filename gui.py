# gui.py
# Interface gráfica do DocOrganizer usando Tkinter (com botão Cancelar)

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
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


class DocOrganizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DocOrganizer")
        self.root.geometry("750x650")
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

        # Lista de botões de ação (exceto cancelar)
        self.botoes_acao = []

        # Cria a interface
        self.criar_widgets()

        # Configura o log para aparecer na interface
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.log_handler = LogHandler(self.txt_log)
        logging.getLogger().addHandler(self.log_handler)

    def criar_widgets(self):
        # Frame principal
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

        # Botões de ação e cancelar
        botoes_frame = ttk.Frame(main_frame)
        botoes_frame.grid(row=3, column=0, columnspan=3, pady=10)

        btn_analisar = ttk.Button(botoes_frame, text="1. Analisar", command=self.analisar)
        btn_analisar.pack(side=tk.LEFT, padx=5)
        self.botoes_acao.append(btn_analisar)

        btn_preview = ttk.Button(botoes_frame, text="2. Pré-visualizar", command=self.pre_visualizar)
        btn_preview.pack(side=tk.LEFT, padx=5)
        self.botoes_acao.append(btn_preview)

        btn_organizar = ttk.Button(botoes_frame, text="3. Organizar", command=self.organizar)
        btn_organizar.pack(side=tk.LEFT, padx=5)
        self.botoes_acao.append(btn_organizar)

        btn_desfazer = ttk.Button(botoes_frame, text="4. Desfazer última", command=self.desfazer)
        btn_desfazer.pack(side=tk.LEFT, padx=5)
        self.botoes_acao.append(btn_desfazer)

        self.btn_cancelar = ttk.Button(botoes_frame, text="Cancelar", command=self.cancelar_operacao, state='disabled')
        self.btn_cancelar.pack(side=tk.LEFT, padx=5)

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

        # Configuração de grid para redimensionamento
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(5, weight=1)

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
        if not origem or not Path(origem).exists():
            messagebox.showerror("Erro", "Selecione uma pasta de origem válida.")
            return
        self.limpar_log()
        self.progresso['value'] = 0
        self.cancelar = False
        self.set_estado_operacao(True)  # desabilita ações e habilita cancelar
        threading.Thread(target=self._analisar_thread, args=(origem,), daemon=True).start()

    def _analisar_thread(self, origem):
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

            if not self.cancelar:
                seguras = sum(1 for c in self.classificacoes if c and c.level == 'SEGURA')
                revisao = sum(1 for c in self.classificacoes if c and c.level == 'REVISAO')
                triagem = sum(1 for c in self.classificacoes if c and c.level == 'TRIAGEM')
                logging.info(f"Classificação concluída: {seguras} seguras, {revisao} revisão, {triagem} triagem.")

        finally:
            self.root.after(0, self._operacao_finalizada)

    def _atualizar_progresso(self, valor):
        self.progresso['value'] = valor

    def _operacao_finalizada(self):
        self.set_estado_operacao(False)  # reabilita ações e desabilita cancelar
        self.cancelar = False

    def pre_visualizar(self):
        if not self.documentos or not self.classificacoes:
            messagebox.showwarning("Aviso", "Execute a análise primeiro.")
            return
        destino = self.destino_var.get().strip()
        if not destino:
            messagebox.showerror("Erro", "Selecione uma pasta de destino.")
            return
        self.plano = planner.criar_plano(self.documentos, self.classificacoes, destino)
        self.mostrar_plano()

    def mostrar_plano(self):
        janela = tk.Toplevel(self.root)
        janela.title("Plano de organização")
        janela.geometry("850x400")
        texto = tk.Text(janela, wrap=tk.NONE)
        scroll_y = ttk.Scrollbar(janela, orient=tk.VERTICAL, command=texto.yview)
        scroll_x = ttk.Scrollbar(janela, orient=tk.HORIZONTAL, command=texto.xview)
        texto.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        texto.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        for item in self.plano:
            origem = Path(item['origem']).name
            destino = item['destino'] if item['destino'] else '—'
            linha = f"{origem:30} -> {destino:40} | Ação: {item['action']:15} | Tema: {item['tema']}\n"
            if item['reason']:
                linha += f"  Motivo: {item['reason']}\n"
            texto.insert(tk.END, linha)

        texto.config(state=tk.DISABLED)

    def organizar(self):
        if not self.plano:
            messagebox.showwarning("Aviso", "Gere o plano primeiro (pré-visualizar).")
            return
        if not messagebox.askyesno("Confirmar", "Deseja realmente mover os arquivos?"):
            return
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
                destino = Path(item['destino'])
                destino.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.move(item['origem'], destino)
                    logging.info(f"Movido: {item['origem']} -> {destino}")
                    hist.record_item(op_id, item['origem'], str(destino), '', 'SUCCESS')
                    success += 1
                except Exception as e:
                    logging.error(f"Erro ao mover {item['origem']}: {e}")
                    hist.record_item(op_id, item['origem'], str(destino), '', 'FAILED')
                    failed += 1
            elif item['action'] == 'SKIP_DUPLICATE':
                logging.info(f"Duplicado ignorado: {item['origem']}")
                hist.record_item(op_id, item['origem'], item['destino'], '', 'SKIPPED')
                skipped += 1
            elif item['action'] == 'REVIEW':
                logging.info(f"Requer revisão: {item['origem']}")

            progresso = (i + 1) / total * 100
            self.root.after(0, self._atualizar_progresso, progresso)

        hist.finish_operation(op_id, 'SUCCESS' if failed == 0 else 'PARTIAL', success, failed, skipped)
        logging.info(f"Execução concluída: sucesso={success}, falhas={failed}, ignorados={skipped}")

        self.root.after(0, self._operacao_finalizada)

    def desfazer(self):
        if not messagebox.askyesno("Desfazer", "Deseja desfazer a última organização?"):
            return
        hist = HistorySQLite()
        hist.undo_last_operation()
        messagebox.showinfo("Desfeito", "Operação desfeita com sucesso.")

    def cancelar_operacao(self):
        self.cancelar = True
        logging.info("Cancelamento solicitado...")
        self.btn_cancelar.config(state='disabled')  # evita cliques repetidos

    def set_estado_operacao(self, em_andamento):
        """
        Se em_andamento=True, desabilita botões de ação e habilita Cancelar.
        Caso contrário, reabilita botões e desabilita Cancelar.
        """
        estado_acao = 'disabled' if em_andamento else 'normal'
        estado_cancelar = 'normal' if em_andamento else 'disabled'
        for btn in self.botoes_acao:
            btn.config(state=estado_acao)
        self.btn_cancelar.config(state=estado_cancelar)

    def limpar_log(self):
        self.txt_log.delete(1.0, tk.END)


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