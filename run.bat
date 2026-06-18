set project_dir=%~dp0
set venv_dir="%project_dir%\venv\Scripts\activate.bat"
cd /d "%project_dir%"
if exist "%venv_dir%" (
    call "%venv_dir%"
) else (
    @echo off
    echo Virtual environment not found. Please set up the virtual environment first.
    exit /b 1
)

python ai.py