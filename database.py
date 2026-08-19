# database.py
# Módulo de conexão e inicialização do banco SQLite

import os
import sqlite3
from pathlib import Path

# Define a pasta de dados do usuário (AppData\Roaming\DocOrganizer)
def _get_data_dir():
    if os.name == 'nt':  # Windows
        base = Path(os.environ.get('APPDATA', Path.home()))
    else:
        base = Path.home() / '.docorganizer'
    data_dir = base / 'DocOrganizer'
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir

DATA_DIR = _get_data_dir()
DB_PATH = DATA_DIR / 'docorganizer.db'

def get_connection():
    """Retorna uma conexão com o banco de dados local."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row  # permite acessar colunas por nome
    return conn

def init_db():
    """Cria as tabelas necessárias no banco, se não existirem."""
    conn = get_connection()
    cursor = conn.cursor()

    # Tabela de operações (sessões de organização)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            status TEXT NOT NULL,
            total INTEGER DEFAULT 0,
            success INTEGER DEFAULT 0,
            failed INTEGER DEFAULT 0,
            skipped INTEGER DEFAULT 0
        )
    ''')

    # Tabela de itens de operação (movimentações individuais)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS operation_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation_id INTEGER NOT NULL,
            origin TEXT NOT NULL,
            destination TEXT NOT NULL,
            file_hash TEXT,
            result TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (operation_id) REFERENCES operations (id)
        )
    ''')

    conn.commit()
    conn.close()

if __name__ == '__main__':
    # Teste simples: inicializa o banco e mostra o caminho
    init_db()
    print(f"Banco de dados criado em: {DB_PATH}")