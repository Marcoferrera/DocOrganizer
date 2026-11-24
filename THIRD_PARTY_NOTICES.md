# Componentes de terceiros

O código do DocOrganizer é distribuído sob a licença MIT, disponível em [LICENSE](LICENSE).

O instalador inclui Tesseract OCR e os modelos de idioma português e inglês. Eles são distribuídos sob a licença Apache 2.0. Os textos de licença e atribuição do Tesseract estão incluídos na instalação em `Tesseract-OCR/doc/`. Fontes oficiais: [Tesseract](https://github.com/tesseract-ocr/tesseract) e [tessdata](https://github.com/tesseract-ocr/tessdata).

O aplicativo usa pypdfium2/PDFium para ler e renderizar PDFs. O pypdfium2 está disponível sob Apache 2.0 ou BSD 3-Clause; PDFium tem licença do tipo BSD e dependências com avisos adicionais. Os avisos que acompanham a distribuição do PDFium devem permanecer no instalador. O aplicativo também usa Pillow e pytesseract. Suas licenças continuam pertencendo aos respectivos projetos; a licença MIT do DocOrganizer não substitui as licenças desses componentes.

O código legado da versão 1.3 permanece no repositório para referência e usa PyMuPDF, licenciado sob AGPLv3 ou licença comercial. Ele não faz parte do executável ou instalador da versão 2.
