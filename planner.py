# planner.py
# Módulo responsável por montar o plano de organização

import logging
from pathlib import Path
import hashlib


def calcular_hash(arquivo):
    """Calcula o hash SHA-256 de um arquivo."""
    h = hashlib.sha256()
    with open(arquivo, 'rb') as f:
        for bloco in iter(lambda: f.read(4096), b''):
            h.update(bloco)
    return h.hexdigest()


def criar_plano(documentos, classificacoes, destino_base):
    """
    Gera uma lista de PlanItem (dicts) com origem, destino, tema e ação.
    """
    plano = []
    for doc, classif in zip(documentos, classificacoes):
        tema = classif.theme
        nivel = classif.level

        if nivel == 'TRIAGEM':
            # Vai para a pasta de triagem automaticamente
            destino_pasta = Path(destino_base) / tema  # tema já é 'Triagem'
            destino_arquivo = destino_pasta / doc.name
            action = 'MOVE'
            reason = 'Baixa confiança, enviado para Triagem'
        elif nivel == 'REVISAO':
            # Requer revisão manual, não definimos destino
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
                    # Gera novo nome com sufixo
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
            'original_name': doc.name
        })

    return plano