# DocOrganizer

Organizador local de documentos para Windows.

O DocOrganizer analisa pastas, extrai texto e metadados de documentos (PDF, DOCX, TXT, MD) e os organiza automaticamente em pastas temáticas, com **segurança** e **transparência**.

---

## ✨ Funcionalidades

- Varredura recursiva de diretórios
- Suporte a:
  - PDFs textuais
  - PDFs escaneados (OCR local via Tesseract)
  - PDFs híbridos (texto + imagem)
  - Documentos Word (.docx)
  - Arquivos de texto (.txt) e Markdown (.md) — opcionais
- Extração de texto e metadados
- Classificação determinística por regras de palavras-chave e pontuação
- Níveis de confiança:
  - `SEGURA` — classificação confiável
  - `REVISAO` — ambiguidade, requer revisão manual
  - `TRIAGEM` — não foi possível classificar
- Geração de plano de organização com pré-visualização
- Execução segura:
  - Nunca sobrescreve arquivos
  - Renomeia automaticamente em conflitos
  - Ignora duplicados idênticos
- Histórico persistente em SQLite
- Desfazer última organização (Undo)
- Interface gráfica simples com Tkinter
- Botão Cancelar para interromper análise
- OCR local incluído (Tesseract)
- 100% offline — nenhum dado sai do computador

---

## 📦 Formatos suportados

| Tipo | Extensão | Processamento |
|------|----------|---------------|
| Documento prioritário | `.pdf`, `.docx` | Sempre processado |
| Texto simples (opcional) | `.txt`, `.md` | Desativado por padrão; pode ser habilitado na interface |

> Por padrão, o DocOrganizer processa **apenas PDF e DOCX** para evitar arquivos de configuração de jogos/programas. Você pode ativar a inclusão de `.txt` e `.md` marcando a opção na interface.

---

## 🖥️ Como usar (usuário final)

1. Execute o **DocOrganizer.exe** (se estiver usando o instalador).
2. Selecione a **pasta de origem** (onde estão os documentos).
3. Selecione a **pasta de destino** (onde as pastas temáticas serão criadas).
4. Escolha as opções:
   - **Incluir subpastas**: varre também os subdiretórios.
   - **Ativar OCR**: processa PDFs escaneados.
   - **Incluir arquivos de texto**: processa `.txt` e `.md`.
5. Clique em **Analisar**.
6. Clique em **Pré-visualizar** para ver o plano proposto.
7. Clique em **Organizar** para executar a organização (após confirmação).
8. Se necessário, use **Desfazer última** para reverter a operação.

---

## 🧰 Instalação (desenvolvedores)

### Pré-requisitos

- Python 3.12
- Pip
- Git

### Passos

```bash
# Clone o repositório
git clone https://github.com/Marcoferrera/DocOrganizer.git
cd DocOrganizer

# Crie e ative um ambiente virtual
python -m venv venv
venv\Scripts\activate  # Windows

# Instale as dependências
pip install PyMuPDF python-docx pytesseract Pillow
