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
python cli.py --job fixtures\sample_job.txt --resumes fixtures\sample_resume_strong.txt fixtures\sample_resume_weak.txt --no-explain
endlocal
