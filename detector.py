# detector.py
# Módulo responsável por identificar o tipo de documento (especialmente PDFs)

import logging
from pathlib import Path

import pymupdf  # PyMuPDF (nova forma de importar)


def detectar_tipo_documento(caminho: str) -> str:
    """
    Retorna o tipo genérico do documento conforme a extensão.
    Valores possíveis: 'pdf', 'docx', 'txt_md', 'desconhecido'.
    """
    extensao = Path(caminho).suffix.lower()
    if extensao == '.pdf':
        return 'pdf'
    elif extensao == '.docx':
        return 'docx'
    elif extensao in ['.txt', '.md']:
        return 'txt_md'
    else:
        return 'desconhecido'


def detectar_tipo_pdf(caminho: str) -> str:
    """
    Analisa um PDF e retorna seu tipo:
    'textual', 'escaneado', 'hibrido', 'protegido', 'corrompido'.
    """
    try:
        # Tenta abrir o PDF com PyMuPDF
        doc = pymupdf.open(caminho)

        total_paginas = len(doc)
        if total_paginas == 0:
            doc.close()
            return 'corrompido'

        paginas_com_texto = 0
        paginas_sem_texto = 0

        for pagina in doc:
            texto = pagina.get_text().strip()
            if texto:
                paginas_com_texto += 1
            else:
                paginas_sem_texto += 1

        doc.close()

        if paginas_sem_texto == 0 and paginas_com_texto > 0:
            return 'textual'
        elif paginas_com_texto == 0 and paginas_sem_texto > 0:
            return 'escaneado'
        elif paginas_com_texto > 0 and paginas_sem_texto > 0:
            return 'hibrido'
        else:
            # Caso improvável: todas as páginas sem texto e sem imagem
            return 'escaneado'

    except pymupdf.FileDataError:
        logging.error(f"PDF corrompido: {caminho}")
        return 'corrompido'
    except pymupdf.PasswordError:
        logging.warning(f"PDF protegido por senha: {caminho}")
        return 'protegido'
    except Exception as e:
        logging.error(f"Erro inesperado ao abrir PDF {caminho}: {e}")
        return 'corrompido'


# Bloco de teste
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    import scanner as sc

    pasta = input("Digite o caminho da pasta para testar o detector: ").strip()
    docs = sc.encontrar_documentos(pasta, incluir_subpastas=True)

    for doc in docs:
        tipo_doc = detectar_tipo_documento(doc.path)
        if tipo_doc == 'pdf':
            tipo_pdf = detectar_tipo_pdf(doc.path)
            print(f"{doc.name}: PDF do tipo {tipo_pdf}")
        else:
            print(f"{doc.name}: {tipo_doc}")