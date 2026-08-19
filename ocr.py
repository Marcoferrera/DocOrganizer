# ocr.py
# Módulo de OCR local usando PyMuPDF + pytesseract + Pillow

import logging
from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image

import config

# Define o caminho do executável do Tesseract
pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD


def aplicar_ocr_pdf(caminho, paginas_max=None, tamanho_max_mb=None):
    """
    Converte páginas de um PDF em imagens e aplica OCR usando Tesseract.

    Retorna o texto extraído concatenado.
    """
    if paginas_max is None:
        paginas_max = config.PAGINAS_MAX_OCR
    if tamanho_max_mb is None:
        tamanho_max_mb = config.TAMANHO_MAX_OCR_MB

    caminho = Path(caminho)

    # Verifica o tamanho do arquivo
    tamanho_mb = caminho.stat().st_size / (1024 * 1024)
    if tamanho_mb > tamanho_max_mb:
        logging.warning(f"Arquivo {caminho.name} excede o limite de {tamanho_max_mb} MB para OCR.")
        return ''

    logging.info(f"Iniciando OCR para: {caminho.name}")

    try:
        # Abre o PDF
        doc = pymupdf.open(caminho)
        total_paginas = len(doc)
        paginas_processadas = min(total_paginas, paginas_max)

        texto_total = []
        for num_pagina in range(paginas_processadas):
            pagina = doc.load_page(num_pagina)
            # Renderiza a página como imagem (300 DPI)
            pix = pagina.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Aplica OCR com Tesseract (idioma configurável)
            texto = pytesseract.image_to_string(img, lang=config.OCR_LANG)
            texto_total.append(texto)

            # Log de progresso (opcional, pode ser removido se ficar verboso)
            logging.info(f"  Página {num_pagina + 1}/{paginas_processadas} processada.")

        doc.close()

        texto_final = '\n'.join(texto_total)
        logging.info(f"OCR concluído para: {caminho.name} ({len(texto_final)} caracteres extraídos)")
        return texto_final

    except Exception as e:
        logging.error(f"Erro ao aplicar OCR no arquivo {caminho}: {e}")
        return ''