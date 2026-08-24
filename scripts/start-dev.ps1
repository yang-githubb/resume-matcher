# Start backend + frontend (requires Ollama running separately)
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$project = Split-Path -Parent $root

Write-Host "Starting Resume Matcher..." -ForegroundColor Cyan

$backendCmd = "Set-Location '$project\backend'; .\.venv\Scripts\Activate.ps1; if (-not (Test-Path .env)) { Copy-Item .env.example .env }; python -m uvicorn app.main:app --reload --port 8010"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

Start-Sleep -Seconds 2

$frontendCmd = "Set-Location '$project\frontend'; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

Write-Host ""
Write-Host "Backend:  http://localhost:8010" -ForegroundColor Green
Write-Host "Frontend: http://localhost:5273" -ForegroundColor Green
Write-Host "API docs: http://localhost:8010/docs" -ForegroundColor Green
Write-Host ""
Write-Host "Ensure Ollama is running: ollama serve" -ForegroundColor Yellow
