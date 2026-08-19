# extractor.py
# Módulo responsável por extrair texto e metadados dos documentos

import hashlib
import logging
import unicodedata
from pathlib import Path

import pymupdf  # PyMuPDF
import docx  # python-docx

# Importa o módulo OCR (será criado depois)
try:
    import ocr
    OCR_DISPONIVEL = True
except ImportError:
    OCR_DISPONIVEL = False
    logging.warning("Módulo OCR não encontrado. PDFs escaneados não serão processados por OCR.")


def normalizar(texto):
    """Remove acentos e converte para minúsculas."""
    if not texto:
        return ''
    texto = unicodedata.normalize('NFKD', texto)
    texto = texto.encode('ASCII', 'ignore').decode('ASCII')
    return texto.lower()


def calcular_hash(caminho):
    """Calcula o hash SHA-256 de um arquivo."""
    h = hashlib.sha256()
    with open(caminho, 'rb') as f:
        for bloco in iter(lambda: f.read(4096), b''):
            h.update(bloco)
    return h.hexdigest()


def extrair_texto_pdf(caminho):
    """
    Extrai texto nativo de PDF e seus metadados.
    Retorna (texto_normalizado, dict_metadados).
    """
    doc = pymupdf.open(caminho)
    texto = ''
    for pagina in doc:
        texto += pagina.get_text() or ''

    metadados = {}
    info = doc.metadata
    if info:
        metadados['titulo'] = info.get('title')
        metadados['autor'] = info.get('author')
        metadados['assunto'] = info.get('subject')

    doc.close()
    return normalizar(texto), metadados


def extrair_texto_docx(caminho):
    """
    Extrai texto de um arquivo DOCX.
    Retorna (texto_normalizado, dict_metadados).
    """
    d = docx.Document(caminho)
    texto = '\n'.join(p.text for p in d.paragraphs)
    metadados = {}
    # Propriedades básicas
    try:
        metadados['titulo'] = d.core_properties.title
        metadados['autor'] = d.core_properties.author
    except:
        pass
    return normalizar(texto), metadados


def extrair_texto_txt_md(caminho):
    """
    Lê arquivo TXT/MD como texto puro.
    Retorna (texto_normalizado, dict_metadados vazio).
    """
    with open(caminho, 'r', encoding='utf-8', errors='ignore') as f:
        texto = f.read()
    return normalizar(texto), {}


def extrair_metadados_e_texto(caminho, usar_ocr=True):
    """
    Função principal chamada pelos outros módulos.
    Recebe um caminho de arquivo e retorna um dicionário com:
    - texto normalizado
    - metadados
    - hash SHA-256
    - tipo do PDF (se for PDF)
    - método de extração
    - se OCR foi utilizado
    """
    extensao = Path(caminho).suffix.lower()
    hash_arquivo = calcular_hash(caminho)
    texto = ''
    metadados = {}
    pdf_type = None
    extraction_method = ''
    ocr_used = False

    if extensao == '.pdf':
        # Detecta o tipo do PDF
        from detector import detectar_tipo_pdf
        pdf_type = detectar_tipo_pdf(caminho)

        if pdf_type == 'textual' or pdf_type == 'hibrido':
            # Extrai texto nativo das páginas que possuem texto
            texto, metadados = extrair_texto_pdf(caminho)
            extraction_method = 'PDF'
            # Se for híbrido, poderia chamar OCR para páginas sem texto,
            # mas por ora extraímos o que é nativo.
        elif pdf_type in ['escaneado', 'hibrido'] and usar_ocr and OCR_DISPONIVEL:
            # Aciona OCR para o PDF escaneado/híbrido
            logging.info(f"Aplicando OCR em: {caminho}")
            texto_ocr = ocr.aplicar_ocr_pdf(caminho)
            if texto_ocr:
                texto = normalizar(texto_ocr)
                extraction_method = 'OCR'
                ocr_used = True
            else:
                extraction_method = 'OCR (falhou)'
        else:
            # PDF escaneado sem OCR ou protegido/corrompido
            extraction_method = f'PDF {pdf_type} (sem extração)'

    elif extensao == '.docx':
        texto, metadados = extrair_texto_docx(caminho)
        extraction_method = 'DOCX'

    elif extensao in ['.txt', '.md']:
        texto, metadados = extrair_texto_txt_md(caminho)
        extraction_method = 'TXT/MD'

    return {
        'texto': texto,
        'metadados': metadados,
        'hash': hash_arquivo,
        'pdf_type': pdf_type,
        'extraction_method': extraction_method,
        'ocr_used': ocr_used,
    }


# Bloco de teste
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    import scanner as sc

    pasta = input("Digite o caminho da pasta para testar o extrator: ").strip()
    docs = sc.encontrar_documentos(pasta, incluir_subpastas=True)

    for doc in docs:
        print(f"\nProcessando: {doc.name}")
        resultado = extrair_metadados_e_texto(doc.path, usar_ocr=False)  # sem OCR por enquanto
        print(f"  Método: {resultado['extraction_method']}")
        print(f"  Tamanho do texto extraído: {len(resultado['texto'])} caracteres")
        print(f"  Primeiros 200 caracteres: {resultado['texto'][:200]}")
        print(f"  Hash: {resultado['hash'][:16]}...")