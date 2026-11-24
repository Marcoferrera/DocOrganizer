$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    python -m venv .venv
}
& '.venv\Scripts\python.exe' -m pip install -r requirements-v2.txt
& '.venv\Scripts\python.exe' -m unittest -v test_v2.py
if ($LASTEXITCODE -ne 0) { throw 'Os testes falharam.' }

& '.venv\Scripts\python.exe' -m PyInstaller --noconfirm --clean --windowed --onedir --name DocOrganizer2 --icon assets\docorganizer.ico --add-data 'assets\docorganizer.ico;assets' app_v2.py
if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar o executável.' }

$ocrSource = 'C:\Program Files\Tesseract-OCR'
if (-not (Test-Path -LiteralPath (Join-Path $ocrSource 'tesseract.exe'))) {
    throw 'Tesseract OCR com português precisa estar instalado em C:\Program Files\Tesseract-OCR.'
}
$ocrTarget = Join-Path $PSScriptRoot 'dist\DocOrganizer2\Tesseract-OCR'
New-Item -ItemType Directory -Force -Path $ocrTarget | Out-Null
Get-ChildItem -LiteralPath $ocrSource -File | Where-Object { $_.Extension -eq '.dll' -or $_.Name -eq 'tesseract.exe' } | Copy-Item -Destination $ocrTarget -Force
$dataTarget = Join-Path $ocrTarget 'tessdata'
New-Item -ItemType Directory -Force -Path $dataTarget | Out-Null
foreach ($language in @('eng.traineddata', 'por.traineddata')) {
    $source = Join-Path $ocrSource "tessdata\$language"
    if (-not (Test-Path -LiteralPath $source)) { throw "Idioma de OCR ausente: $language" }
    Copy-Item -LiteralPath $source -Destination $dataTarget -Force
}
$docTarget = Join-Path $ocrTarget 'doc'
New-Item -ItemType Directory -Force -Path $docTarget | Out-Null
Get-ChildItem -LiteralPath (Join-Path $ocrSource 'doc') -File | Where-Object { $_.Name -in @('LICENSE', 'AUTHORS', 'README.md') } | Copy-Item -Destination $docTarget -Force

$runtimeLicenses = Join-Path $PSScriptRoot 'dist\DocOrganizer2\licenses'
New-Item -ItemType Directory -Force -Path $runtimeLicenses | Out-Null
$sitePackages = Join-Path $PSScriptRoot '.venv\Lib\site-packages'
Get-ChildItem -LiteralPath $sitePackages -Directory |
    Where-Object { $_.Name -match '^(pypdfium2|Pillow|pytesseract)-.*\.dist-info$' } |
    ForEach-Object {
        $licenseSource = Join-Path $_.FullName 'licenses'
        if (Test-Path -LiteralPath $licenseSource) {
            Copy-Item -LiteralPath $licenseSource -Destination (Join-Path $runtimeLicenses $_.Name) -Recurse -Force
        }
    }

$compiler = 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe'
if (-not (Test-Path -LiteralPath $compiler)) { throw 'Inno Setup 6 precisa estar instalado.' }
& $compiler installer.iss
if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar o instalador.' }
