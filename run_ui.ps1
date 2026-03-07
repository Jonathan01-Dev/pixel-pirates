# Lance l'interface web Archipel avec encodage UTF-8 (evite l'erreur charmap)
chcp 65001 | Out-Null
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
if (-not $env:GEMINI_API_KEY) {
    Write-Host "INFO: GEMINI_API_KEY non defini. Exemple:"
    Write-Host '  $env:GEMINI_API_KEY = "VOTRE_CLE"'
}
Set-Location $PSScriptRoot
python src/web_ui.py @args
