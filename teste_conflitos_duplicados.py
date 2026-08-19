# teste_conflitos_duplicados.py
# Script de teste automatizado para conflitos e duplicados no Planner

import os
import shutil
import tempfile
from pathlib import Path

# Importa módulos necessários
from models import DocumentInfo, ClassificationResult
import planner


def criar_arquivo(caminho, conteudo):
    """Cria um arquivo de texto com o conteúdo especificado."""
    with open(caminho, 'w', encoding='utf-8') as f:
        f.write(conteudo)


def main():
    # Cria diretórios temporários
    with tempfile.TemporaryDirectory() as tmpdir:
        origem = Path(tmpdir) / "origem"
        destino = Path(tmpdir) / "destino"
        origem.mkdir()
        destino.mkdir()

        # ========== CENÁRIO 1: CONFLITO (mesmo nome, conteúdo diferente) ==========
        print("=" * 60)
        print("CENÁRIO 1: CONFLITO (mesmo nome, conteúdo diferente)")
        print("=" * 60)

        # Arquivo na origem
        arquivo_origem = origem / "fatura.pdf"
        criar_arquivo(arquivo_origem, "Conteudo da fatura original")

        # Arquivo no destino com mesmo nome, conteúdo diferente
        arquivo_destino = destino / "Financeiro" / "fatura.pdf"
        arquivo_destino.parent.mkdir(parents=True, exist_ok=True)
        criar_arquivo(arquivo_destino, "Conteudo antigo diferente")

        # Cria DocumentInfo para o arquivo da origem
        doc_info = DocumentInfo(
            path=str(arquivo_origem),
            name="fatura.pdf",
            extension=".pdf",
            size=arquivo_origem.stat().st_size,
            modified=arquivo_origem.stat().st_mtime,
            is_hidden=False,
            is_symlink=False
        )

        # Cria ClassificationResult (tema Financeiro, nível SEGURA)
        classif = ClassificationResult(
            theme="Financeiro",
            score=100,
            level="SEGURA",
            evidences=[],
            second_theme=None,
            second_score=0,
            margin=100
        )

        # Gera plano
        plano = planner.criar_plano([doc_info], [classif], str(destino))

        for item in plano:
            print(f"Origem: {Path(item['origem']).name}")
            print(f"Destino proposto: {item['destino']}")
            print(f"Ação: {item['action']}")
            print(f"Motivo: {item['reason']}")
            print("-" * 40)

        # ========== CENÁRIO 2: DUPLICADO (mesmo nome, mesmo conteúdo) ==========
        print("\n" + "=" * 60)
        print("CENÁRIO 2: DUPLICADO (mesmo nome, mesmo conteúdo)")
        print("=" * 60)

        # Reutiliza o mesmo arquivo de origem, mas agora o destino tem conteúdo idêntico
        # Para simplificar, recriamos o destino com mesmo conteúdo
        if arquivo_destino.exists():
            arquivo_destino.unlink()  # remove o antigo
        criar_arquivo(arquivo_destino, "Conteudo da fatura original")

        # Atualiza o hash? O planner calcula na hora, então não precisa
        # Gera plano novamente
        plano = planner.criar_plano([doc_info], [classif], str(destino))

        for item in plano:
            print(f"Origem: {Path(item['origem']).name}")
            print(f"Destino proposto: {item['destino']}")
            print(f"Ação: {item['action']}")
            print(f"Motivo: {item['reason']}")
            print("-" * 40)


if __name__ == '__main__':
    main()