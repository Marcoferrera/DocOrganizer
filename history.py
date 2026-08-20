# history.py
# Módulo de histórico persistente usando SQLite

import logging
import os
import shutil
from datetime import datetime
from pathlib import Path

import database


class HistorySQLite:
    """Gerencia o histórico de operações e permite desfazer a última válida."""

    def __init__(self):
        database.init_db()
        self.current_operation_id = None

    def start_operation(self, total=0):
        """Inicia uma nova operação no banco e retorna seu ID."""
        conn = database.get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO operations (timestamp, status, total)
            VALUES (?, ?, ?)
        ''', (now, 'PENDING', total))
        conn.commit()
        self.current_operation_id = cursor.lastrowid
        conn.close()
        logging.info(f"Operação #{self.current_operation_id} iniciada.")
        return self.current_operation_id

    def record_item(self, operation_id, origin, destination, file_hash, result):
        """Registra uma movimentação individual dentro de uma operação."""
        conn = database.get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO operation_items (operation_id, origin, destination, file_hash, result, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (operation_id, origin, destination, file_hash, result, now))
        conn.commit()
        conn.close()

    def finish_operation(self, operation_id, status, success, failed, skipped):
        """Atualiza o status e contadores finais de uma operação."""
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE operations
            SET status = ?, success = ?, failed = ?, skipped = ?
            WHERE id = ?
        ''', (status, success, failed, skipped, operation_id))
        conn.commit()
        conn.close()
        logging.info(f"Operação #{operation_id} finalizada com status {status}.")

    def get_last_operation(self):
        """
        Retorna a operação mais recente (qualquer status) e seus itens.
        """
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM operations ORDER BY id DESC LIMIT 1')
        op = cursor.fetchone()
        if not op:
            return None
        op_dict = dict(op)
        cursor.execute('SELECT * FROM operation_items WHERE operation_id = ? ORDER BY id DESC', (op_dict['id'],))
        items = [dict(item) for item in cursor.fetchall()]
        op_dict['items'] = items
        conn.close()
        return op_dict

    def get_undoable_operation(self):
        """
        Retorna a operação mais recente que ainda pode ser desfeita.
        Considera apenas operações com status diferente de UNDONE e que possuem itens SUCCESS.
        """
        conn = database.get_connection()
        cursor = conn.cursor()
        # Seleciona a última operação, independente do status
        cursor.execute('SELECT * FROM operations ORDER BY id DESC LIMIT 1')
        op = cursor.fetchone()
        if not op:
            conn.close()
            return None
        op_dict = dict(op)

        # Verifica se a operação já foi desfeita
        if op_dict['status'] == 'UNDONE':
            conn.close()
            return None

        # Verifica se há itens de sucesso para desfazer
        cursor.execute('SELECT COUNT(*) as cnt FROM operation_items WHERE operation_id = ? AND result = ?',
                       (op_dict['id'], 'SUCCESS'))
        row = cursor.fetchone()
        conn.close()

        if row['cnt'] == 0:
            return None

        # Carrega os itens
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM operation_items WHERE operation_id = ? ORDER BY id DESC', (op_dict['id'],))
        items = [dict(item) for item in cursor.fetchall()]
        op_dict['items'] = items
        conn.close()
        return op_dict

    def undo_last_operation(self):
        """
        Desfaz a última operação que pode ser desfeita.
        Se a última já estiver desfeita ou não houver itens de sucesso, não faz nada.
        """
        op = self.get_undoable_operation()
        if not op:
            logging.info("Nenhuma operação válida para desfazer.")
            return False

        logging.info(f"Desfazendo operação #{op['id']}...")
        success = 0
        pastas_criadas = set()

        for item in op['items']:
            origem = item['destination']
            destino = item['origin']
            if Path(origem).exists():
                Path(destino).parent.mkdir(parents=True, exist_ok=True)
                shutil.move(origem, destino)
                logging.info(f"Desfeito: {origem} -> {destino}")
                success += 1
                pastas_criadas.add(str(Path(origem).parent))
            else:
                logging.warning(f"Arquivo não encontrado para desfazer: {origem}")

        # Tenta remover pastas criadas que ficaram vazias
        for pasta in sorted(pastas_criadas, key=lambda p: p.count(os.sep), reverse=True):
            try:
                if Path(pasta).exists() and not any(Path(pasta).iterdir()):
                    Path(pasta).rmdir()
                    logging.info(f"Pasta vazia removida: {pasta}")
            except OSError as e:
                logging.warning(f"Não foi possível remover a pasta {pasta}: {e}")

        # Marca a operação como desfeita
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE operations SET status = ? WHERE id = ?', ('UNDONE', op['id']))
        conn.commit()
        conn.close()
        logging.info(f"Operação #{op['id']} desfeita. {success} arquivos restaurados.")
        return True

    def has_undoable_operation(self):
        """
        Retorna True se existe uma operação que pode ser desfeita.
        """
        return self.get_undoable_operation() is not None