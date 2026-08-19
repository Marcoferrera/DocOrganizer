# default_evidence.py
# Vocabulário de evidências padrão para o classificador

# Cada chave é uma categoria (não necessariamente uma pasta final)
# As palavras associadas servem como pistas para identificar o assunto do documento.

EVIDENCIAS_PADRAO = {
    "Financeiro": [
        "fatura", "boleto", "imposto", "receita federal", "nota fiscal",
        "nf-e", "irpf", "comprovante", "extrato", "investimento",
        "declaracao", "cobranca", "pagamento", "salario", "holerite",
        "contracheque", "tributo", "taxa", "orcamento", "despesa"
    ],
    "Jurídico": [
        "contrato", "clausula", "contratante", "contratado", "advogado",
        "peticao", "sentenca", "lei", "decreto", "tribunal", "processo",
        "juridico", "procuracao", "acordo", "termo", "aditivo", "testemunha"
    ],
    "Acadêmico": [
        "universidade", "faculdade", "tcc", "dissertacao", "tese",
        "artigo", "monografia", "prova", "trabalho", "escola",
        "aluno", "professor", "disciplina", "curso", "certificado",
        "historico escolar", "diploma"
    ],
    "Tecnologia": [
        "python", "codigo", "programacao", "manual", "api",
        "software", "algoritmo", "tutorial", "desenvolvimento",
        "sistema", "aplicativo", "banco de dados", "sql", "linux"
    ],
    "Saúde": [
        "exame", "receita medica", "laudo", "consulta", "vacina",
        "plano de saude", "hemograma", "raio-x", "medico", "paciente",
        "hospital", "diagnostico", "tratamento"
    ],
    "Trabalho": [
        "relatorio", "projeto", "reuniao", "cliente", "proposta",
        "curriculo", "entrevista", "cargo", "salario", "empresa",
        "funcionario", "chefe", "demissao", "admissao"
    ],
    "Pessoal": [
        "rg", "cpf", "cnh", "passaporte", "certidao",
        "titulo de eleitor", "identidade", "casamento", "nascimento",
        "foto", "familia", "viagem", "receita"
    ],
    "Imóveis": [
        "aluguel", "escritura", "imovel", "iptu", "condominio",
        "financiamento", "compra", "venda", "locacao", "terreno",
        "casa", "apartamento"
    ],
    "Veículos": [
        "carro", "veiculo", "ipva", "licenciamento", "multa",
        "seguro", "moto", "caminhao", "placa", "renavam"
    ],
    "Seguros": [
        "apolice", "seguro", "cobertura", "sinistro", "premio",
        "vida", "auto", "residencial", "beneficiario"
    ],
    "Educação": [
        "apostila", "livro", "ebook", "resumo", "material",
        "aula", "ead", "univesp", "ensino", "aprendizado"
    ],
    "Manuais": [
        "manual", "guia", "instrucoes", "tutorial", "como usar",
        "especificacoes", "datasheet"
    ],
}

# Lista combinada de todas as palavras-chave (para consulta rápida)
TODAS_PALAVRAS = list(set(
    palavra
    for palavras in EVIDENCIAS_PADRAO.values()
    for palavra in palavras
))