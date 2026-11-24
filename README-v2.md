# DocOrganizer 2

Aplicativo Windows para organizar PDFs locais por matéria ou categoria, sem enviar documentos para a internet.

## Uso

1. Instale e abra o DocOrganizer 2.
2. Selecione a pasta que contém os PDFs. O aplicativo também lê as subpastas e pode sugerir correções para arquivos já organizados.
3. Clique em **Analisar**. O texto nativo é lido; páginas sem texto podem passar pelo OCR local em português.
4. Confira a tabela. Itens **PENDENTE** ficam no lugar até você escolher o destino. Dê um clique duplo para abrir a revisão e, se necessário, abra o PDF original.
5. Crie novas pastas pelo botão **Criar pasta** ou digite o nome de uma nova categoria na revisão.
6. Ajuste o nome proposto de cada arquivo, se quiser. Uma mudança de nome sugerida pelo aplicativo sempre exige revisão.
7. Clique em **Organizar plano aprovado** e confirme a quantidade de arquivos. Nenhum item pendente é movido.
8. Para reverter, clique em **Desfazer última sessão**. Um PDF alterado depois da organização é preservado e sinalizado como bloqueado.

O aplicativo evita sobrescrever arquivos. Quando existe um arquivo idêntico no destino, ele mantém a origem. Se há outro arquivo com o mesmo nome e conteúdo diferente, acrescenta um número ao nome. O histórico fica em `%APPDATA%\DocOrganizer\history_v2.db`.

## Classificação

As pastas existentes fornecem os nomes das categorias. Matemática e Método para Produção de Trabalhos Científicos também estão disponíveis inicialmente. O aplicativo usa pistas do nome e do texto e aprende semelhanças com PDFs já colocados nas pastas. Sugestões fracas, falhas de leitura e mudanças de nome propostas aparecem como pendentes. A leitura é limitada às primeiras 10 páginas; no máximo duas páginas sem texto recebem OCR para manter a análise viável em lotes grandes.

## Desenvolvimento e instalador

No Windows, com Python 3 e Tesseract OCR com os idiomas `por` e `eng` instalados em `C:\Program Files\Tesseract-OCR`, execute `build_windows.ps1`. Ele instala as dependências locais, executa os testes, gera o executável e compila o instalador com Inno Setup 6. O instalador é salvo em `dist\installer`. Para usar diretamente durante o desenvolvimento, execute `python app_v2.py` no ambiente virtual.

O instalador inclui o OCR local. Ele não modifica seus PDFs durante a instalação. A organização só ocorre após confirmação explícita na interface.

## Licença

O código do DocOrganizer é distribuído sob a licença [MIT](LICENSE). O instalador contém componentes com licenças próprias; veja [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
