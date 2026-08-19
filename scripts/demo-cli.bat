@echo off
setlocal
cd /d "%~dp0\..\backend"
if not exist .venv (
  python -m venv .venv
  call .venv\Scripts\activate.bat
  pip install -r requirements.txt
) else (
  call .venv\Scripts\activate.bat
)
if not exist .env copy .env.example .env
python cli.py --resume fixtures\sample_resume_strong.txt --jobs fixtures\sample_job.txt --no-explain
endlocal
