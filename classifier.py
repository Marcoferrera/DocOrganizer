# classifier.py
# Módulo responsável por classificar documentos com base em regras de palavras-chave

import logging
from default_evidence import EVIDENCIAS_PADRAO
from models import ClassificationResult, ClassificationEvidence
import config
import user_themes  # novo import


def classificar(texto: str, metadados: dict, nome_arquivo: str, temas: dict = None) -> ClassificationResult:
    """
    Analisa o texto, metadados e nome do arquivo para definir o tema mais provável.

    Retorna um objeto ClassificationResult com tema, pontuação, nível e evidências.
    """
    if temas is None:
        # Usa combinação de temas padrão e personalizados
        temas = user_themes.get_combined_themes()

    nome_normalizado = nome_arquivo.lower()
    titulo_meta = (metadados.get('titulo') or '').lower()
    autor_meta = (metadados.get('autor') or '').lower()

    pontuacoes = {tema: 0 for tema in temas}
    evidencias = {tema: [] for tema in temas}

    for tema, palavras in temas.items():
        for palavra in palavras:
            palavra = palavra.lower()

            if palavra in nome_normalizado:
                pontuacoes[tema] += 40
                evidencias[tema].append(ClassificationEvidence(palavra, 'nome', 40))

            if palavra in texto:
                pontuacoes[tema] += 20
                evidencias[tema].append(ClassificationEvidence(palavra, 'texto', 20))

            if palavra in titulo_meta or palavra in autor_meta:
                pontuacoes[tema] += 10
                evidencias[tema].append(ClassificationEvidence(palavra, 'metadado', 10))

    temas_ordenados = sorted(pontuacoes.items(), key=lambda x: x[1], reverse=True)

    tema_principal, score_principal = temas_ordenados[0]
    tema_secundario, score_secundario = temas_ordenados[1] if len(temas_ordenados) > 1 else (None, 0)

    margem = score_principal - score_secundario

    if score_principal >= config.LIMITE_CONFIANCA_ALTA and margem >= config.MARGEM_SEGURANCA:
        nivel = 'SEGURA'
    elif score_principal >= config.LIMITE_CONFIANCA_MEDIA:
        nivel = 'REVISAO'
    else:
        nivel = 'TRIAGEM'
        tema_principal = config.PASTA_TRIAGEM

    return ClassificationResult(
        theme=tema_principal,
        score=score_principal,
        level=nivel,
        evidences=evidencias.get(tema_principal, []),
        second_theme=tema_secundario,
        second_score=score_secundario,
        margin=margem
    )