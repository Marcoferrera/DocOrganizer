# planner.py
# Módulo responsável por montar o plano de organização

import logging
from pathlib import Path
import hashlib
import config  # <-- importação necessária


def calcular_hash(arquivo):
    """Calcula o hash SHA-256 de um arquivo."""
    h = hashlib.sha256()
    with open(arquivo, 'rb') as f:
        for bloco in iter(lambda: f.read(4096), b''):
            h.update(bloco)
    return h.hexdigest()


def criar_plano(documentos, classificacoes, destino_base):
    """
    Gera uma lista de dicionários com origem, destino, tema, ação, motivo e nível original.
    """
    plano = []
    for doc, classif in zip(documentos, classificacoes):
        if classif is None:
            # Classificação falhou, envia para Triagem como ação MOVE
            tema = config.PASTA_TRIAGEM
            nivel = 'TRIAGEM'
            destino_pasta = Path(destino_base) / tema
            destino_arquivo = destino_pasta / doc.name
            action = 'MOVE'
            reason = 'Falha na classificação, enviado para Triagem'
        else:
            tema = classif.theme
            nivel = classif.level
            if nivel == 'TRIAGEM':
                destino_pasta = Path(destino_base) / config.PASTA_TRIAGEM
                destino_arquivo = destino_pasta / doc.name
                action = 'MOVE'
                reason = 'Baixa confiança, enviado para Triagem'
            elif nivel == 'REVISAO':
                # Para itens de revisão, o destino será decidido pelo usuário.
                # Inicialmente, action = 'REVIEW' e destino vazio.
                destino_pasta = None
                destino_arquivo = None
                action = 'REVIEW'
                reason = 'Classificação incerta, requer revisão'
            else:  # SEGURA
                destino_pasta = Path(destino_base) / tema
                destino_arquivo = destino_pasta / doc.name

                # Verifica conflitos
                if destino_arquivo.exists():
                    hash_origem = calcular_hash(doc.path)
                    hash_destino = calcular_hash(destino_arquivo)
                    if hash_origem == hash_destino:
                        action = 'SKIP_DUPLICATE'
                        reason = 'Arquivo idêntico já existe no destino'
                    else:
                        action = 'RENAME_CONFLICT'
                        reason = 'Arquivo com mesmo nome, mas conteúdo diferente'
                        base = Path(doc.name).stem
                        ext = Path(doc.name).suffix
                        contador = 1
                        novo_nome = f"{base}_{contador}{ext}"
                        novo_destino = destino_pasta / novo_nome
                        while novo_destino.exists():
                            contador += 1
                            novo_nome = f"{base}_{contador}{ext}"
                            novo_destino = destino_pasta / novo_nome
                        destino_arquivo = novo_destino
                else:
                    action = 'MOVE'
                    reason = ''

        plano.append({
            'origem': doc.path,
            'destino': str(destino_arquivo) if destino_arquivo else '',
            'tema': tema,
            'action': action,
            'reason': reason,
            'original_name': doc.name,
            'nivel': nivel  # guarda o nível original para permitir revisões futuras
        })

    return plano