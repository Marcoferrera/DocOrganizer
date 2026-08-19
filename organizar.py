# organizar.py
# Script de teste do fluxo completo (CLI)

import argparse
import logging
from pathlib import Path

import config
import scanner
import extractor
import classifier
import planner
import executor

def main():
    parser = argparse.ArgumentParser(description='Organizar documentos (versão CLI)')
    parser.add_argument('--origem', required=True, help='Pasta de origem')
    parser.add_argument('--destino', required=True, help='Pasta de destino')
    parser.add_argument('--dry-run', action='store_true', help='Apenas mostrar o plano, sem mover')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
            hist = executor.History()
            stats = executor.executar_plano(plano, hist)
            logging.info(f"Execução concluída: {stats}")
            # Pergunta se deseja desfazer
            desfazer = input("Deseja desfazer a última organização? (s/n): ").lower()
            if desfazer == 's':
                hist.desfazer()
        else:
            logging.info("Operação cancelada.")

if __name__ == '__main__':
    main()