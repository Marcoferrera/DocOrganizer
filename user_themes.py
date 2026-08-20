# user_themes.py
# Módulo para combinar temas padrão e personalizados

import default_evidence
import database

def get_combined_themes():
    """
    Retorna um dicionário contendo os temas padrão (default_evidence.EVIDENCIAS_PADRAO)
    e os temas personalizados salvos no banco.
    """
    combined = dict(default_evidence.EVIDENCIAS_PADRAO)  # copia do padrão
    user_themes = database.load_user_themes()

    for tema, palavras in user_themes.items():
        if tema in combined:
            # Se o tema já existir no padrão, adiciona palavras sem duplicar
            conjunto = set(combined[tema])
            conjunto.update(palavras)
            combined[tema] = list(conjunto)
        else:
            combined[tema] = palavras

    return combined