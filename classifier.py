# classifier.py
# Módulo responsável por classificar documentos com base em regras de palavras-chave

import logging
from default_evidence import EVIDENCIAS_PADRAO
from models import ClassificationResult, ClassificationEvidence
import config


def classificar(texto: str, metadados: dict, nome_arquivo: str, temas: dict = None) -> ClassificationResult:
    """
    Analisa o texto, metadados e nome do arquivo para definir o tema mais provável.

    Retorna um objeto ClassificationResult com tema, pontuação, nível e evidências.
    """
    if temas is None:
        temas = EVIDENCIAS_PADRAO

    # Normaliza o nome do arquivo e os metadados
    nome_normalizado = nome_arquivo.lower()
    titulo_meta = (metadados.get('titulo') or '').lower()
    autor_meta = (metadados.get('autor') or '').lower()

    # Estrutura para acumular pontuação por tema
    pontuacoes = {tema: 0 for tema in temas}
    evidencias = {tema: [] for tema in temas}

    # Para cada tema e suas palavras-chave
    for tema, palavras in temas.items():
        for palavra in palavras:
            palavra = palavra.lower()

            # Verifica no nome do arquivo
            if palavra in nome_normalizado:
                pontuacoes[tema] += 40
                evidencias[tema].append(ClassificationEvidence(palavra, 'nome', 40))

            # Verifica no texto extraído
            if palavra in texto:
                pontuacoes[tema] += 20
                evidencias[tema].append(ClassificationEvidence(palavra, 'texto', 20))

            # Verifica nos metadados (título/author)
            if palavra in titulo_meta or palavra in autor_meta:
                pontuacoes[tema] += 10
                evidencias[tema].append(ClassificationEvidence(palavra, 'metadado', 10))

    # Ordena temas por pontuação decrescente
    temas_ordenados = sorted(pontuacoes.items(), key=lambda x: x[1], reverse=True)

    tema_principal, score_principal = temas_ordenados[0]
    tema_secundario, score_secundario = temas_ordenados[1] if len(temas_ordenados) > 1 else (None, 0)

    # Calcula margem
    margem = score_principal - score_secundario

    # Determina o nível de confiança
    if score_principal >= config.LIMITE_CONFIANCA_ALTA and margem >= config.MARGEM_SEGURANCA:
        nivel = 'SEGURA'
    elif score_principal >= config.LIMITE_CONFIANCA_MEDIA:
        nivel = 'REVISAO'
    else:
        nivel = 'TRIAGEM'
        # Se for TRIAGEM, o tema será a pasta de triagem definida em config
        tema_principal = config.PASTA_TRIAGEM

    # Monta o resultado
    result = ClassificationResult(
        theme=tema_principal,
        score=score_principal,
        level=nivel,
        evidences=evidencias.get(tema_principal, []),
        second_theme=tema_secundario,
        second_score=score_secundario,
        margin=margem
    )

    return result


# Bloco de teste
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    import scanner as sc
    import extractor as ex

    pasta = input("Digite o caminho da pasta para testar o classificador: ").strip()
    docs = sc.encontrar_documentos(pasta, incluir_subpastas=True)

    for doc in docs:
        # Extrai conteúdo
        conteudo = ex.extrair_metadados_e_texto(doc.path, usar_ocr=True)
        resultado = classificar(
            texto=conteudo['texto'],
            metadados=conteudo['metadados'],
            nome_arquivo=doc.name
        )
        print(f"\nDocumento: {doc.name}")
        print(f"  Tema: {resultado.theme}")
        print(f"  Pontuação: {resultado.score}")
        print(f"  Nível: {resultado.level}")
        print(f"  Segundo tema: {resultado.second_theme} ({resultado.second_score})")
        print(f"  Margem: {resultado.margin}")
        print(f"  Evidências: {[e.term for e in resultado.evidences]}")