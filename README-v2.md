# DocOrganizer 2

Aplicativo Windows para organizar PDFs locais por matéria ou categoria, sem enviar documentos para a internet.

## Uso

1. Instale e abra o DocOrganizer 2.
2. Selecione a pasta que contém os PDFs. Escolha **PDFs soltos** para organizar novos arquivos ou **Auditar subpastas** para revisar os que já estão organizados.
3. Clique em **Analisar**. O texto nativo é lido; páginas sem texto podem passar pelo OCR local em português.
4. Confira a tabela. Itens **PENDENTE** ficam no lugar até você escolher o destino. Dê um clique duplo para abrir a revisão e, se necessário, abra o PDF original.
5. O aplicativo pode propor uma nova pasta, como `DEV/Prompts e IA`, sem criá-la durante a análise. Na revisão, aprove a proposta, escolha uma pasta existente dentro da pasta PDF ou digite outro destino. A nova pasta só é criada ao confirmar a organização.
6. Ajuste o nome proposto de cada arquivo, se quiser. Uma mudança de nome sugerida pelo aplicativo sempre exige revisão.
7. Clique em **Organizar plano aprovado** e confirme a quantidade de arquivos. Nenhum item pendente é movido.
8. Para reverter, clique em **Desfazer última sessão**. Um PDF alterado depois da organização é preservado e sinalizado como bloqueado.

O aplicativo evita sobrescrever arquivos. Quando existe um arquivo idêntico no destino, ele mantém a origem. Se há outro arquivo com o mesmo nome e conteúdo diferente, acrescenta um número ao nome. O histórico fica em `%APPDATA%\DocOrganizer\history_v2.db`.

## Classificação

O aplicativo identifica primeiro o contexto geral: faculdade, desenvolvimento, pessoal, música ou indefinido. Depois sugere uma pasta entre as existentes ou propõe uma nova, com base no nome e no texto extraído. Termos como “prompt” não bastam para classificar um arquivo como material de uma disciplina. Pastas existentes e PDFs já organizados ajudam a sugerir destinos, mas propostas de nova pasta e sugestões incertas exigem revisão. A busca de pastas é limitada à pasta PDF selecionada e suas subpastas. A leitura é limitada às primeiras 10 páginas; no máximo duas páginas sem texto recebem OCR para manter a análise viável em lotes grandes.

O desfazer restaura os arquivos da última sessão e remove apenas pastas criadas por essa sessão que estejam vazias. Pastas que já existiam e pastas com arquivos são preservadas.

## Desenvolvimento e instalador

No Windows, com Python 3 e Tesseract OCR com os idiomas `por` e `eng` instalados em `C:\Program Files\Tesseract-OCR`, execute `build_windows.ps1`. Ele instala as dependências locais, executa os testes, gera o executável e compila o instalador com Inno Setup 6. O instalador é salvo em `dist\installer`. Para usar diretamente durante o desenvolvimento, execute `python app_v2.py` no ambiente virtual.

O instalador inclui o OCR local. Ele não modifica seus PDFs durante a instalação. A organização só ocorre após confirmação explícita na interface.

## Licença

O código do DocOrganizer é distribuído sob a licença [MIT](LICENSE). O instalador contém componentes com licenças próprias; veja [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
