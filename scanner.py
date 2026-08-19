# scanner.py
# Módulo responsável por varrer diretórios e coletar informações básicas dos documentos

import logging
from pathlib import Path

from models import DocumentInfo
import config


def deve_ignorar_pasta(caminho: Path) -> bool:
    """
    Verifica se alguma parte do caminho corresponde a uma pasta ignorada.
    """
    for ignorada in config.PASTAS_IGNORADAS:
        if ignorada.lower() in [part.lower() for part in caminho.parts]:
            return True
    return False


def deve_ignorar_arquivo(nome: str) -> bool:
    """
    Verifica se o nome do arquivo está na lista de arquivos ignorados.
    """
    return nome.lower() in config.ARQUIVOS_IGNORADOS


def encontrar_documentos(diretorio: str, incluir_subpastas: bool = True, incluir_texto_simples: bool = False) -> list[DocumentInfo]:
    """
    Varre o diretório (e subpastas, se permitido) e retorna uma lista de DocumentInfo.

    - Sempre processa extensões em config.EXTENSOES_DOCUMENTOS.
    - Só processa .txt/.md se incluir_texto_simples for True.
    - Ignora pastas de sistema e arquivos indesejados.
    """
    diretorio = Path(diretorio)
    if not diretorio.exists():
        logging.error(f"Diretório não existe: {diretorio}")
        return []

    # Define as extensões permitidas
    extensoes_permitidas = set(config.EXTENSOES_DOCUMENTOS)
    if incluir_texto_simples:
        extensoes_permitidas.update(config.EXTENSOES_TEXTO_SIMPLES)

    documentos = []

    if incluir_subpastas:
        iterator = diretorio.rglob('*')
    else:
        iterator = diretorio.glob('*')

    for caminho in iterator:
        try:
            if not caminho.is_file():
                continue
            if caminho.is_symlink():
                logging.info(f"Ignorando link simbólico: {caminho}")
                continue
            if caminho.name.startswith('.'):
                continue
            if deve_ignorar_arquivo(caminho.name):
                continue

            extensao = caminho.suffix.lower()
            if extensao not in extensoes_permitidas:
                continue

            if deve_ignorar_pasta(caminho):
                continue

            stat = caminho.stat()
            doc_info = DocumentInfo(
                path=str(caminho),
                name=caminho.name,
                extension=extensao,
                size=stat.st_size,
                modified=stat.st_mtime,
                is_hidden=caminho.name.startswith('.'),
                is_symlink=False,
            )
            documentos.append(doc_info)

        except PermissionError:
            logging.warning(f"Sem permissão para acessar: {caminho}")
            continue
        except OSError as e:
            logging.error(f"Erro ao acessar {caminho}: {e}")
            continue
        except Exception as e:
            logging.error(f"Erro inesperado ao processar {caminho}: {e}")
            continue

    return documentos


# Bloco para testar o scanner diretamente
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    pasta = input("Digite o caminho da pasta para testar o scanner: ").strip()
    incluir = input("Incluir subpastas? (s/n): ").lower() == 's'
    incluir_txt = input("Incluir arquivos .txt e .md? (s/n): ").lower() == 's'

    docs = encontrar_documentos(pasta, incluir, incluir_txt)
    print(f"\nDocumentos encontrados: {len(docs)}")
    for doc in docs[:10]:  # mostra até 10 para não poluir
        print(f"  - {doc.name} ({doc.size} bytes) - {doc.path}")