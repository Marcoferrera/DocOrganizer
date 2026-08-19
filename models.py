# models.py
# Contratos de dados do DocOrganizer

from dataclasses import dataclass, field
from typing import List, Optional
import datetime


@dataclass
class DocumentInfo:
    """
    Informações básicas de um arquivo coletadas pelo Scanner.
    """
    path: str                       # caminho completo do arquivo
    name: str                       # nome do arquivo (com extensão)
    extension: str                  # extensão em minúsculas (ex: '.pdf')
    size: int                       # tamanho em bytes
    modified: float                 # timestamp da última modificação
    is_hidden: bool = False         # se é arquivo oculto
    is_symlink: bool = False        # se é um link simbólico


@dataclass
class ExtractedContent:
    """
    Resultado da extração de texto e metadados de um documento.
    """
    text: str                       # texto normalizado (minúsculas, sem acentos)
    metadata: dict = field(default_factory=dict)  # metadados extraídos (título, autor, etc.)
    hash: Optional[str] = None      # hash SHA-256 do arquivo (calculado posteriormente)
    pdf_type: Optional[str] = None  # tipo do PDF: 'textual', 'escaneado', 'hibrido', 'protegido', 'corrompido'
    extraction_method: str = ''     # descrição de como o texto foi obtido (ex: 'PDF', 'DOCX', 'OCR')
    ocr_used: bool = False          # se OCR foi utilizado


@dataclass
class ClassificationEvidence:
    """
    Registro de cada evidência encontrada que contribuiu para a classificação.
    """
    term: str                       # palavra-chave encontrada (ex: 'contrato')
    location: str                   # onde foi encontrada: 'nome', 'texto', 'metadado'
    points: int                     # pontos atribuídos


@dataclass
class ClassificationResult:
    """
    Resultado da classificação de um documento.
    """
    theme: str                      # tema escolhido (ou 'Triagem')
    score: int                      # pontuação do tema principal
    level: str                      # nível de confiança: 'SEGURA', 'REVISAO', 'TRIAGEM'
    evidences: List[ClassificationEvidence] = field(default_factory=list)  # evidências coletadas
    second_theme: Optional[str] = None   # segundo tema mais pontuado
    second_score: int = 0           # pontuação do segundo tema
    margin: int = 0                 # diferença entre primeiro e segundo


@dataclass
class PlanItem:
    """
    Item individual do plano de organização.
    Indica o que o sistema pretende fazer com um arquivo.
    """
    origin: str                     # caminho atual do arquivo
    destination: str                # caminho proposto (pode ser vazio se ação for SKIP/REVIEW)
    theme: str                      # tema atribuído
    action: str                     # ação a executar: 'MOVE', 'SKIP_DUPLICATE', 'RENAME_CONFLICT', 'REVIEW', 'SKIP', 'ERROR'
    reason: str = ''                # motivo da ação (ex: 'arquivo duplicado', 'baixa confiança')
    original_name: str = ''         # nome original (útil em caso de renomeação)


@dataclass
class OperationItem:
    """
    Ação individual que foi executada dentro de uma Operation.
    """
    origin: str                     # origem real
    destination: str                # destino real (após renomeação, se houver)
    hash: str                       # hash do arquivo movido
    result: str                     # 'SUCCESS', 'FAILED', 'SKIPPED'
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)


@dataclass
class Operation:
    """
    Representa uma sessão completa de organização (várias movimentações).
    O usuário pode desfazer uma operação inteira.
    """
    id: int                         # ID único (pode ser o timestamp ou sequencial)
    timestamp: datetime.datetime    # data/hora da operação
    status: str = 'PENDING'         # 'SUCCESS', 'PARTIAL', 'FAILED', 'PENDING'
    items: List[OperationItem] = field(default_factory=list)  # itens executados
    total: int = 0                  # total de arquivos planejados
    success: int = 0                # quantos tiveram sucesso
    failed: int = 0                 # quantos falharam
    skipped: int = 0                # quantos foram ignorados