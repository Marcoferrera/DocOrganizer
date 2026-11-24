"""DocOrganizer 2: offline review-first Windows desktop interface."""

from __future__ import annotations

import os
import sys
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from engine_v2 import Proposal, analyze, available_ocr, execute, last_undoable, safe_name, undo_last
from subject_classifier import subject_names


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("DocOrganizer 2 — Organização de PDFs")
        root.geometry("1320x800")
        icon = (Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "assets" / "docorganizer.ico")
        if icon.exists():
            root.iconbitmap(str(icon))
        self.folder = tk.StringVar(value=str(Path.home() / "Desktop" / "PDF") if (Path.home() / "Desktop" / "PDF").is_dir() else "")
        self.ocr = tk.BooleanVar(value=True)
        self.scope = tk.StringVar(value="inbox")
        self.search = tk.StringVar()
        self.filter = tk.StringVar(value="Todos")
        self.status = tk.StringVar(value="Selecione a pasta e clique em Analisar.")
        self.events = queue.Queue()
        self.proposals: list[Proposal] = []
        self.cancelled = False
        self.running = False
        self._build()
        self.root.after(100, self._poll)

    def _build(self):
        frame = ttk.Frame(self.root, padding=12)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(4, weight=1)
        ttk.Label(frame, text="Pasta dos PDFs").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.folder).grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Button(frame, text="Escolher...", command=self._choose).grid(row=0, column=2)
        options = ttk.Frame(frame)
        options.grid(row=1, column=0, columnspan=3, sticky="ew", pady=8)
        ttk.Checkbutton(options, text="Usar OCR para páginas escaneadas", variable=self.ocr).pack(side="left")
        self.ocr_label = ttk.Label(options, text="")
        self.ocr_label.pack(side="left", padx=12)
        ttk.Radiobutton(options, text="PDFs soltos", variable=self.scope, value="inbox", command=self._change_scope).pack(side="left", padx=(20, 4))
        ttk.Radiobutton(options, text="Auditar subpastas", variable=self.scope, value="audit", command=self._change_scope).pack(side="left")
        ok, _ = available_ocr()
        self.ocr_label.config(text="OCR em português disponível" if ok else "OCR indisponível: instale Tesseract com idioma português")
        toolbar = ttk.Frame(frame)
        toolbar.grid(row=2, column=0, columnspan=3, sticky="ew", pady=4)
        self.analyze_button = ttk.Button(toolbar, text="Analisar", command=self._analyze)
        self.analyze_button.pack(side="left", padx=3)
        self.review_button = ttk.Button(toolbar, text="Revisar selecionado", command=self._review)
        self.review_button.pack(side="left", padx=3)
        self.open_button = ttk.Button(toolbar, text="Abrir PDF", command=self._open_selected)
        self.open_button.pack(side="left", padx=3)
        self.new_folder_button = ttk.Button(toolbar, text="Criar pasta", command=self._new_folder)
        self.new_folder_button.pack(side="left", padx=3)
        self.execute_button = ttk.Button(toolbar, text="Organizar plano aprovado", command=self._execute)
        self.execute_button.pack(side="left", padx=3)
        self.undo_button = ttk.Button(toolbar, text="Desfazer última sessão", command=self._undo)
        self.undo_button.pack(side="left", padx=3)
        self.cancel_button = ttk.Button(toolbar, text="Cancelar", command=self._cancel, state="disabled")
        self.cancel_button.pack(side="left", padx=3)
        filters = ttk.Frame(frame)
        filters.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(3, 5))
        ttk.Label(filters, text="Buscar").pack(side="left")
        ttk.Entry(filters, textvariable=self.search, width=42).pack(side="left", padx=(8, 16))
        ttk.Label(filters, text="Mostrar").pack(side="left")
        ttk.Combobox(filters, textvariable=self.filter, values=("Todos", "Pendentes", "Sugeridos", "Manter"), state="readonly", width=15).pack(side="left", padx=8)
        self.search.trace_add("write", lambda *_: self._refresh())
        self.filter.trace_add("write", lambda *_: self._refresh())
        columns = ("file", "current", "suggested", "alternative", "name", "action", "warning")
        self.table = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")
        for key, title, width in [
            ("file", "PDF", 230), ("current", "Pasta atual", 125), ("suggested", "Sugestão", 180),
            ("alternative", "Alternativa", 140), ("name", "Novo nome", 200),
            ("action", "Decisão", 90), ("warning", "Aviso", 200),
        ]:
            self.table.heading(key, text=title)
            self.table.column(key, width=width, minwidth=75)
        self.table.grid(row=4, column=0, columnspan=3, sticky="nsew")
        self.table.bind("<Double-1>", lambda _: self._review())
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.table.yview)
        scrollbar.grid(row=4, column=3, sticky="ns")
        hscroll = ttk.Scrollbar(frame, orient="horizontal", command=self.table.xview)
        hscroll.grid(row=5, column=0, columnspan=3, sticky="ew")
        self.table.configure(yscrollcommand=scrollbar.set, xscrollcommand=hscroll.set)
        ttk.Label(frame, text="Revise os itens marcados como PENDENTE. Nenhum arquivo será movido sem a confirmação final.").grid(row=6, column=0, columnspan=3, sticky="w", pady=(8, 0))
        self.progress = ttk.Progressbar(frame, mode="determinate")
        self.progress.grid(row=7, column=0, columnspan=3, sticky="ew", pady=8)
        ttk.Label(frame, textvariable=self.status).grid(row=8, column=0, columnspan=3, sticky="w")

    def _change_scope(self):
        self.proposals.clear()
        self._refresh()
        self.status.set("Modo alterado. Clique em Analisar para gerar um novo plano.")

    def _open_selected(self):
        selected = self.table.selection()
        if not selected:
            messagebox.showinfo("Seleção", "Selecione um PDF na lista.")
            return
        source = self.proposals[int(selected[0])].source
        try:
            os.startfile(source)
        except OSError as error:
            messagebox.showerror("Não foi possível abrir o PDF", str(error))

    def _root_path(self) -> Path | None:
        path = Path(self.folder.get().strip())
        if not path.is_dir():
            messagebox.showerror("Pasta inválida", "Selecione uma pasta existente.")
            return None
        return path.resolve()

    def _choose(self):
        chosen = filedialog.askdirectory(title="Escolha a pasta de PDFs")
        if chosen:
            self.folder.set(chosen)
            self.proposals.clear()
            self._refresh()

    def _busy(self, value: bool):
        self.running = value
        for button in (self.analyze_button, self.review_button, self.open_button, self.new_folder_button, self.execute_button, self.undo_button):
            button.config(state="disabled" if value else "normal")
        self.cancel_button.config(state="normal" if value else "disabled")

    def _cancel(self):
        self.cancelled = True
        self.status.set("Cancelando após o arquivo atual...")

    def _worker(self, task, *args):
        try:
            self.events.put(("result", task(*args)))
        except Exception as error:
            self.events.put(("error", str(error)))

    def _poll(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "progress":
                    done, total = value
                    self.progress.config(maximum=max(total, 1), value=done)
                    self.status.set(f"Processados {done} de {total} PDFs...")
                elif kind == "result":
                    self._busy(False)
                    if isinstance(value, list):
                        self.proposals = value
                        self._refresh()
                        pending = sum(p.needs_review for p in value)
                        self.status.set(f"Análise concluída: {len(value)} PDFs; {pending} pedem revisão. Revise o plano antes de organizar.")
                    elif isinstance(value, dict) and "restored" in value:
                        self.status.set(f"Desfazer: {value['restored']} restaurados; {value['blocked']} bloqueados.")
                        self.proposals.clear()
                        self._refresh()
                        detail = "\n".join(value.get("errors", [])[:8])
                        (messagebox.showwarning if detail else messagebox.showinfo)("Desfazer concluído", self.status.get() + ("\n\n" + detail if detail else ""))
                    else:
                        self.status.set(f"Sessão {value['status']}: {value['moved']} movidos, {value['skipped']} ignorados, {value['failed']} erros.")
                        self.proposals.clear()
                        self._refresh()
                        detail = "\n".join(value.get("errors", [])[:8])
                        (messagebox.showwarning if detail else messagebox.showinfo)("Organização concluída", self.status.get() + ("\n\n" + detail if detail else ""))
                elif kind == "error":
                    self._busy(False)
                    self.status.set("Operação interrompida por erro.")
                    messagebox.showerror("Erro", value)
        except queue.Empty:
            pass
        self.root.after(100, self._poll)

    def _analyze(self):
        path = self._root_path()
        if not path:
            return
        self.cancelled = False
        self.proposals.clear()
        self._refresh()
        self._busy(True)
        self.status.set("Lendo PDFs...")
        def work():
            return analyze(path, self.ocr.get(), lambda i, n: self.events.put(("progress", (i, n))), lambda: self.cancelled, self.scope.get())
        threading.Thread(target=self._worker, args=(work,), daemon=True).start()

    def _refresh(self):
        self.table.delete(*self.table.get_children())
        query = self.search.get().strip().casefold()
        selected_filter = self.filter.get()
        for index, proposal in enumerate(self.proposals):
            decision = "PENDENTE" if proposal.needs_review and proposal.action == "KEEP" else "MOVER" if proposal.action == "MOVE" else "MANTER"
            if query and query not in " ".join((proposal.source.name, proposal.current_folder, proposal.subject, proposal.alternative, proposal.proposed_name, proposal.warning)).casefold():
                continue
            if selected_filter == "Pendentes" and decision != "PENDENTE":
                continue
            if selected_filter == "Sugeridos" and decision != "MOVER":
                continue
            if selected_filter == "Manter" and decision != "MANTER":
                continue
            self.table.insert("", "end", iid=str(index), values=(proposal.source.name, proposal.current_folder or "PDF", proposal.subject or "Sem sugestão",
                                                                  proposal.alternative, proposal.proposed_name, decision, proposal.warning))

    def _new_folder(self):
        root = self._root_path()
        if not root:
            return
        name = simpledialog.askstring("Nova pasta", "Nome da matéria ou categoria:", parent=self.root)
        if not name:
            return
        if name in {".", ".."} or Path(name).name != name or any(c in name for c in '<>:"/\\|?*'):
            messagebox.showerror("Nome inválido", "Use apenas um nome de pasta, sem barras ou caracteres especiais.")
            return
        (root / name).mkdir(exist_ok=True)
        self.status.set(f"Pasta {name} criada. Analise novamente para incluir a nova matéria nas sugestões.")

    def _review(self):
        selected = self.table.selection()
        if not selected:
            messagebox.showinfo("Seleção", "Selecione um PDF na lista.")
            return
        proposal = self.proposals[int(selected[0])]
        root = self._root_path()
        if not root:
            return
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Revisar {proposal.source.name}")
        dialog.geometry("800x630")
        dialog.transient(self.root)
        dialog.grab_set()
        body = ttk.Frame(dialog, padding=14)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=proposal.source.name, wraplength=750, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        ttk.Label(body, text=f"Pasta atual: {proposal.current_folder or 'PDF'}").pack(anchor="w", pady=5)
        ttk.Label(body, text=f"Sugestão: {proposal.subject or 'nenhuma'}; alternativa: {proposal.alternative or 'nenhuma'}").pack(anchor="w")
        ttk.Label(body, text=f"Motivos: {proposal.evidence or 'nenhuma pista suficiente'}", wraplength=750).pack(anchor="w", pady=6)
        if proposal.warning:
            ttk.Label(body, text=f"Aviso: {proposal.warning}", wraplength=750).pack(anchor="w")
        ttk.Button(body, text="Abrir PDF para conferir", command=self._open_selected).pack(anchor="w", pady=8)
        ttk.Label(body, text="Trecho do conteúdo extraído:").pack(anchor="w")
        excerpt = tk.Text(body, height=8, wrap="word")
        excerpt.insert("1.0", proposal.excerpt or "Nenhum texto extraído. Abra o PDF para conferir.")
        excerpt.config(state="disabled")
        excerpt.pack(fill="both", expand=True, pady=(3, 8))
        ttk.Label(body, text="Pasta de destino (você pode digitar uma nova):").pack(anchor="w")
        subject = tk.StringVar(value=proposal.subject or proposal.current_folder)
        selector = ttk.Combobox(body, textvariable=subject, values=subject_names(root))
        selector.pack(fill="x")
        ttk.Label(body, text="Nome do arquivo:").pack(anchor="w", pady=(8, 0))
        filename = tk.StringVar(value=proposal.proposed_name)
        ttk.Entry(body, textvariable=filename).pack(fill="x")
        def approve():
            name = subject.get().strip()
            if not name:
                messagebox.showerror("Pasta necessária", "Escolha ou digite uma pasta.", parent=dialog)
                return
            try:
                clean = safe_name(Path(filename.get().strip()).stem)
                if clean != filename.get().strip():
                    raise ValueError("Nome de PDF inválido")
                if name in {".", ".."} or Path(name).name != name or any(c in name for c in '<>:"/\\|?*'):
                    raise ValueError("Pasta inválida")
            except ValueError as error:
                messagebox.showerror("Destino inválido", str(error), parent=dialog)
                return
            proposal.subject = name
            proposal.proposed_name = clean
            proposal.needs_review = False
            proposal.action = "MOVE" if proposal.source != root / name / clean else "KEEP"
            self._refresh()
            dialog.destroy()
        buttons = ttk.Frame(body)
        buttons.pack(anchor="w", pady=15)
        ttk.Button(buttons, text="Aprovar destino", command=approve).pack(side="left", padx=3)
        ttk.Button(buttons, text="Manter onde está", command=lambda: self._keep(proposal, dialog)).pack(side="left", padx=3)

    def _keep(self, proposal: Proposal, dialog: tk.Toplevel):
        proposal.action = "KEEP"
        proposal.needs_review = False
        self._refresh()
        dialog.destroy()

    def _execute(self):
        root = self._root_path()
        if not root:
            return
        approved = [p for p in self.proposals if p.action == "MOVE"]
        if not approved:
            messagebox.showinfo("Nada a organizar", "Analise os PDFs e aprove ao menos uma movimentação.")
            return
        pending = sum(p.needs_review for p in self.proposals)
        message = f"Mover {len(approved)} PDFs?\n\n{pending} itens pendentes permanecerão onde estão. Você poderá desfazer esta sessão."
        if not messagebox.askyesno("Confirmar organização", message):
            return
        self.cancelled = False
        self._busy(True)
        def work():
            return execute(root, approved, progress=lambda i, n: self.events.put(("progress", (i, n))), cancel=lambda: self.cancelled)
        threading.Thread(target=self._worker, args=(work,), daemon=True).start()

    def _undo(self):
        if not last_undoable():
            messagebox.showinfo("Nada para desfazer", "Não há sessão com arquivos movidos para restaurar.")
            return
        if not messagebox.askyesno("Desfazer sessão", "Restaurar os arquivos da última sessão aos locais originais? Arquivos alterados serão preservados e sinalizados."):
            return
        self._busy(True)
        threading.Thread(target=self._worker, args=(undo_last,), daemon=True).start()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
