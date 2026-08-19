# config.py
# Configurações centrais do DocOrganizer

import shutil
import sys
from pathlib import Path

# Extensões de documentos prioritários (sempre processadas)
EXTENSOES_DOCUMENTOS = ['.pdf', '.docx']

# Extensões de texto simples (opcionais, desativadas por padrão)
EXTENSOES_TEXTO_SIMPLES = ['.txt', '.md']

# Extensões suportadas no total (para referência)
EXTENSOES_SUPORTADAS = EXTENSOES_DOCUMENTOS + EXTENSOES_TEXTO_SIMPLES

# Por padrão, NÃO processar .txt e .md (evita lixo de jogos/sistemas)
INCLUIR_TEXTO_SIMPLES_PADRAO = False

# Limites de pontuação para classificação
LIMITE_CONFIANCA_ALTA = 50   # pontuação mínima para classificação segura
LIMITE_CONFIANCA_MEDIA = 20  # pontuação mínima para revisão
MARGEM_SEGURANCA = 15        # diferença mínima entre 1º e 2º colocados para ser SEGURA

# Configurações de OCR
TAMANHO_MAX_OCR_MB = 50      # arquivos PDF maiores que isso não passam por OCR
PAGINAS_MAX_OCR = 10         # número máximo de páginas processadas por OCR

# Configurações de histórico/undo
MAX_UNDO_ACTIONS = 1000      # limite de ações mantidas em memória para desfazer

# Pastas que devem ser ignoradas durante a varredura (nomes exatos ou partes)
PASTAS_IGNORADAS = [
    # Sistema e programas
    'Windows',
    'Program Files',
    'Program Files (x86)',
    'System32',
    '$Recycle.Bin',
    'AppData',
    'Temp',
    'node_modules',
    'Python',               # evita pastas de instalação do Python
    'Python312',
    'venv',

    # Jogos e plataformas de distribuição
    'Steam',
    'SteamLibrary',
    'Epic Games',
    'GOG Games',
    'Ubisoft',
    'Project-Zomboid',
    'media',                # muitas vezes contém assets de jogos
    'scripts',              # scripts de jogos e programas
    'generated',
    'Workshop',
    'Mods',
    'mods',
    'assets',

    # Pastas comuns de configuração e dados
    'Application Data',
    'Local Settings',
    'My Games',
    'Saved Games',

    # Outras
    'cache',
    'tmp',
    'logs',
    'log',
]

# Arquivos específicos que devem ser ignorados
ARQUIVOS_IGNORADOS = [
    'desktop.ini',
    'thumbs.db',
    '.gitignore',
    'LICENSE',
    'README.md',            # opcional: ignore READMEs (mude conforme preferir)
]

# Função para localizar o executável do Tesseract automaticamente
def _encontrar_tesseract():
    # 1. Verifica se está no PATH do sistema
    caminho_no_path = shutil.which('tesseract')
    if caminho_no_path:
        return caminho_no_path

    # 2. Verifica locais comuns de instalação no Windows
    locais_comuns = [
        Path(r'C:\Program Files\Tesseract-OCR\tesseract.exe'),
        Path(r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'),
        Path(r'C:\Users\Public\Tesseract-OCR\tesseract.exe'),
    ]
    for local in locais_comuns:
        if local.exists():
            return str(local)

    # 3. Verifica na pasta do executável (quando empacotado)
    if getattr(sys, 'frozen', False):
        # Executável PyInstaller
        base = Path(sys.executable).parent
    else:
        # Rodando como script
        base = Path(__file__).parent
    local_app = base / 'Tesseract-OCR' / 'tesseract.exe'
    if local_app.exists():
        return str(local_app)

    # 4. Fallback
    return 'tesseract'

# Caminho para o executável do Tesseract OCR
TESSERACT_CMD = _encontrar_tesseract()

# Idioma padrão para o OCR (português + inglês)
OCR_LANG = 'por+eng'

# Nome da pasta para onde irão os documentos sem classificação confiável
PASTA_TRIAGEM = 'Triagem'