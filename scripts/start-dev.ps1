# Start backend + frontend (requires Ollama running separately)
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$project = Split-Path -Parent $root

Write-Host "Starting Resume Matcher..." -ForegroundColor Cyan

$backendCmd = "Set-Location '$project\backend'; .\.venv\Scripts\Activate.ps1; if (-not (Test-Path .env)) { Copy-Item .env.example .env }; python -m uvicorn app.main:app --reload --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

Start-Sleep -Seconds 2

$frontendCmd = "Set-Location '$project\frontend'; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

Write-Host ""
Write-Host "Backend:  http://localhost:8000" -ForegroundColor Green
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Green
Write-Host "API docs: http://localhost:8000/docs" -ForegroundColor Green
Write-Host ""
Write-Host "Ensure Ollama is running: ollama serve" -ForegroundColor Yellow
