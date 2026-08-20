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
    conn.row_factory = sqlite3.Row
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

    # Tabela de temas personalizados
    # Cada linha: tema, palavra_chave
    # Tema pode se repetir para múltiplas palavras
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_themes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            theme TEXT NOT NULL,
            keyword TEXT NOT NULL,
            UNIQUE(theme, keyword)
        )
    ''')

    conn.commit()
    conn.close()

# ============ Funções para gerenciar temas personalizados ============

def load_user_themes():
    """
    Carrega os temas personalizados do banco e retorna um dicionário
    no formato {tema: [palavra1, palavra2, ...]}.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT theme, keyword FROM user_themes ORDER BY theme, keyword')
    rows = cursor.fetchall()
    conn.close()

    temas = {}
    for row in rows:
        tema = row['theme']
        keyword = row['keyword'].lower()
        if tema not in temas:
            temas[tema] = []
        temas[tema].append(keyword)
    return temas

def save_user_theme(theme, keywords):
    """
    Adiciona ou atualiza um tema personalizado.
    :param theme: nome do tema
    :param keywords: lista de palavras-chave (strings)
    """
    theme = theme.strip()
    if not theme:
        return False

    conn = get_connection()
    cursor = conn.cursor()

    # Remove palavras existentes do tema
    cursor.execute('DELETE FROM user_themes WHERE theme = ?', (theme,))

    # Insere as novas palavras
    for keyword in keywords:
        kw = keyword.strip().lower()
        if kw:
            cursor.execute(
                'INSERT OR IGNORE INTO user_themes (theme, keyword) VALUES (?, ?)',
                (theme, kw)
            )

    conn.commit()
    conn.close()
    return True

def delete_user_theme(theme):
    """Remove um tema personalizado inteiro."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM user_themes WHERE theme = ?', (theme,))
    conn.commit()
    conn.close()

def get_all_user_theme_names():
    """Retorna lista de nomes de temas personalizados distintos."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT theme FROM user_themes ORDER BY theme')
    rows = cursor.fetchall()
    conn.close()
    return [row['theme'] for row in rows]

def get_keywords_for_theme(theme):
    """Retorna a lista de palavras-chave de um tema."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT keyword FROM user_themes WHERE theme = ? ORDER BY keyword', (theme,))
    rows = cursor.fetchall()
    conn.close()
    return [row['keyword'] for row in rows]