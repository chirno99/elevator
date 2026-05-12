@echo off
echo [1/3] Creating Virtual Environment (venv)...
python -m venv venv

echo [2/3] Activating Environment and Updating pip...
call venv\Scripts\activate
python -m pip install --upgrade pip

echo [3/3] Installing Libraries from requirements.txt...
pip install -r requirements.txt

echo Done! Virtual environment is ready.
pause