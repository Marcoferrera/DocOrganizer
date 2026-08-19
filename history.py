# history.py
# Módulo de histórico persistente usando SQLite

import logging
from datetime import datetime
import shutil
from pathlib import Path

import database


class HistorySQLite:
    """Gerencia o histórico de operações e permite desfazer a última."""

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
        """Retorna a operação mais recente e seus itens."""
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

    def undo_last_operation(self):
        """Desfaz a última operação, movendo os arquivos de volta."""
        last = self.get_last_operation()
        if not last:
            logging.info("Nenhuma operação para desfazer.")
            return

        logging.info(f"Desfazendo operação #{last['id']}...")
        success = 0
        for item in last['items']:
            origem = item['destination']
            destino = item['origin']
            if Path(origem).exists():
                Path(destino).parent.mkdir(parents=True, exist_ok=True)
                shutil.move(origem, destino)
                logging.info(f"Desfeito: {origem} -> {destino}")
                success += 1
            else:
                logging.warning(f"Arquivo não encontrado para desfazer: {origem}")

        # Marca a operação como desfeita (opcional: alterar status)
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE operations SET status = ? WHERE id = ?', ('UNDONE', last['id']))
        conn.commit()
        conn.close()
        logging.info(f"Operação #{last['id']} desfeita. {success} arquivos restaurados.")