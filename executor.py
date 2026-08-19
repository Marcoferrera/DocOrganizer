# executor.py
# Módulo responsável por executar o plano aprovado

import logging
import shutil
from pathlib import Path


class History:
    """Histórico simples em memória para desfazer."""
    def __init__(self):
        self.items = []

    def add(self, acao):
        self.items.append(acao)

    def desfazer(self):
        """Desfaz as ações na ordem inversa."""
        if not self.items:
            logging.info("Nada para desfazer.")
            return
        for item in reversed(self.items):
            origem = item['destino']
            destino = item['origem']
            if Path(origem).exists():
                Path(destino).parent.mkdir(parents=True, exist_ok=True)
                shutil.move(origem, destino)
                logging.info(f"Desfeito: {origem} -> {destino}")
            else:
                logging.warning(f"Arquivo não encontrado para desfazer: {origem}")
        self.items.clear()


def executar_plano(plano, history):
    """Executa cada item do plano. Retorna estatísticas."""
    stats = {'movidos': 0, 'ignorados': 0, 'erros': 0}

    for item in plano:
        if item['action'] == 'MOVE' or item['action'] == 'RENAME_CONFLICT':
            destino = Path(item['destino'])
            destino.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(item['origem'], destino)
                logging.info(f"Movido: {item['origem']} -> {destino}")
                history.add({
                    'origem': item['origem'],
                    'destino': str(destino),
                    'hash': '',  # pode ser preenchido se necessário
                    'timestamp': None
                })
                stats['movidos'] += 1
            except Exception as e:
                logging.error(f"Erro ao mover {item['origem']}: {e}")
                stats['erros'] += 1
        elif item['action'] == 'SKIP_DUPLICATE':
            logging.info(f"Duplicado ignorado: {item['origem']}")
            stats['ignorados'] += 1
        elif item['action'] == 'REVIEW':
            logging.info(f"Requer revisão: {item['origem']}")
            # não conta como movido, apenas registra
        else:
            logging.warning(f"Ação desconhecida {item['action']} para {item['origem']}")

    return stats