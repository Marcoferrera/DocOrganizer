# organizar_sqlite.py
# Script de teste do fluxo completo com histórico persistente

import argparse
import logging
import shutil  # <-- FALTANTE
from pathlib import Path

import database
import scanner
import extractor
import classifier
import planner
from history import HistorySQLite


def main():
    parser = argparse.ArgumentParser(description='Organizar documentos (com SQLite)')
    parser.add_argument('--origem', required=True, help='Pasta de origem')
    parser.add_argument('--destino', required=True, help='Pasta de destino')
    parser.add_argument('--dry-run', action='store_true', help='Apenas mostrar o plano, sem mover')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    database.init_db()

    # 1. Escanear
    docs = scanner.encontrar_documentos(args.origem, incluir_subpastas=True)
    logging.info(f"Documentos encontrados: {len(docs)}")

    # 2. Extrair e classificar
    classificacoes = []
    for doc in docs:
        conteudo = extractor.extrair_metadados_e_texto(doc.path, usar_ocr=True)
        result = classifier.classificar(
            texto=conteudo['texto'],
            metadados=conteudo['metadados'],
            nome_arquivo=doc.name
        )
        classificacoes.append(result)

    # 3. Gerar plano
    plano = planner.criar_plano(docs, classificacoes, args.destino)

    # 4. Mostrar plano
    print("\n--- PLANO DE ORGANIZAÇÃO ---")
    for item in plano:
        origem = Path(item['origem']).name
        destino = item['destino'] if item['destino'] else '—'
        print(f"{origem:30} -> {destino:40} | Ação: {item['action']:15} | Tema: {item['tema']}")
        if item['reason']:
            print(f"  Motivo: {item['reason']}")

    # 5. Executar (se não dry-run)
    if args.dry_run:
        logging.info("Modo simulação: nenhum arquivo foi movido.")
    else:
        confirma = input("\nDeseja executar o plano? (s/n): ").lower()
        if confirma == 's':
            hist = HistorySQLite()
            op_id = hist.start_operation(total=len(plano))

            success = failed = skipped = 0
            for item in plano:
                if item['action'] == 'MOVE' or item['action'] == 'RENAME_CONFLICT':
                    destino = Path(item['destino'])
                    destino.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        shutil.move(item['origem'], destino)
                        logging.info(f"Movido: {item['origem']} -> {destino}")
                        hist.record_item(op_id, item['origem'], str(destino), '', 'SUCCESS')
                        success += 1
                    except Exception as e:
                        logging.error(f"Erro ao mover {item['origem']}: {e}")
                        hist.record_item(op_id, item['origem'], str(destino), '', 'FAILED')
                        failed += 1
                elif item['action'] == 'SKIP_DUPLICATE':
                    logging.info(f"Duplicado ignorado: {item['origem']}")
                    hist.record_item(op_id, item['origem'], item['destino'], '', 'SKIPPED')
                    skipped += 1
                elif item['action'] == 'REVIEW':
                    logging.info(f"Requer revisão: {item['origem']}")
                    # Não registra como item movido
                    pass

            hist.finish_operation(op_id, 'SUCCESS' if failed == 0 else 'PARTIAL', success, failed, skipped)
            logging.info(f"Execução concluída: sucesso={success}, falhas={failed}, ignorados={skipped}")

            # Pergunta se deseja desfazer
            desfazer = input("Deseja desfazer a última organização? (s/n): ").lower()
            if desfazer == 's':
                hist.undo_last_operation()
        else:
            logging.info("Operação cancelada.")

if __name__ == '__main__':
    main()