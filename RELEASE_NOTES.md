# DocOrganizer 2.0.0

Nova implementação focada na organização offline de PDFs por matéria ou categoria.

- Lê texto nativo de PDFs e aplica OCR local em português e inglês a páginas escaneadas.
- Usa nomes de pastas existentes e exemplos já organizados para sugerir destinos, com alternativa e evidências.
- Permite revisar sugestões, corrigir pastas, criar novas categorias e ajustar nomes antes de mover.
- Exige confirmação final para executar o plano; itens pendentes permanecem no local original.
- Evita sobrescrita, identifica duplicados idênticos e guarda histórico para desfazer a última sessão.
- Inclui instalador Windows com OCR local.

O instalador não é assinado digitalmente. A versão 2 não importa o histórico de desfazer da versão 1.3. Sugestões incertas precisam de revisão humana.
# DocOrganizer 2.2.0

- Leitura adaptativa de PDFs: até 16 páginas, incluindo início, capítulos do sumário navegável e amostras posteriores.
- OCR local seletivo em até três páginas com pouco texto por documento.
- Sugestões explicáveis por página e diagnóstico CSV somente de leitura com `adaptive_analysis.py`.
- Metadados de título genéricos ou suspeitos deixam de propor nomes automaticamente.
- Classificação adaptativa permanece pendente quando o classificador anterior não encontra evidência forte; não há movimentação automática baseada apenas na nova pontuação.
- O diagnóstico ainda exige conferência humana para calibrar as regras antes de considerar suas classificações seguras para movimentação.
