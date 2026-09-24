```bat
@echo off
setlocal

echo ============================================================
echo       Advanced Agentic AI - Environment Setup
echo ============================================================
echo.

REM ============================================================
REM Clear potentially conflicting Python environment variables
REM ============================================================
set PYTHONHOME=
set PYTHONPATH=

REM ============================================================
REM 1. Check for Python 3.12
REM ============================================================
echo Checking for Python 3.12...

set "PYTHON312="

REM Try Python Launcher first
py -3.12 --version >nul 2>&1

if not errorlevel 1 (
    set "PYTHON312=py -3.12"
    echo Python 3.12 found using Python Launcher.
    goto PYTHON_FOUND
)

REM Check common Python 3.12 installation locations
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
    set "PYTHON312=%LocalAppData%\Programs\Python\Python312\python.exe"
    echo Python 3.12 found:
    echo %LocalAppData%\Programs\Python\Python312\python.exe
    goto PYTHON_FOUND
)

if exist "C:\Program Files\Python312\python.exe" (
    set "PYTHON312=C:\Program Files\Python312\python.exe"
    echo Python 3.12 found:
    echo C:\Program Files\Python312\python.exe
    goto PYTHON_FOUND
)

if exist "C:\Program Files (x86)\Python312\python.exe" (
    set "PYTHON312=C:\Program Files (x86)\Python312\python.exe"
    echo Python 3.12 found:
    echo C:\Program Files (x86)\Python312\python.exe
    goto PYTHON_FOUND
)

REM ============================================================
REM Python 3.12 NOT FOUND
REM ============================================================
echo.
echo ============================================================
echo ERROR: Python 3.12 was NOT found.
echo ============================================================
echo.
echo This training environment requires Python 3.12.
echo.
echo Python 3.13 will NOT be used.
echo.
echo Please install Python 3.12 on this machine.
echo.
pause
exit /b 1


:PYTHON_FOUND

echo.
echo Using Python:
%PYTHON312% --version

echo.
echo Testing Python standard library...

%PYTHON312% -c "import encodings; print('Python standard library OK')"

if errorlevel 1 (
    echo.
    echo ============================================================
    echo ERROR: Python 3.12 installation appears to be damaged.
    echo ============================================================
    echo.
    pause
    exit /b 1
)

REM ============================================================
REM 2. Go to Desktop
REM ============================================================
cd /d "%USERPROFILE%\Desktop"

REM ============================================================
REM 3. Create Advanced Agentic AI folder
REM ============================================================
if not exist "Advanced Agentic AI" (
    echo.
    echo Creating Advanced Agentic AI folder...
    mkdir "Advanced Agentic AI"
)

cd /d "%USERPROFILE%\Desktop\Advanced Agentic AI"

echo.
echo Project folder:
echo %CD%

REM ============================================================
REM 4. Create requirements.txt
REM ============================================================
echo.
echo Creating requirements.txt...

(
echo # ============================================================
echo # Advanced Agentic AI: Production Engineering
echo # Walmart Global Tech Academy ^| requirements.txt
echo #
echo # Covers: Days 1-5 ^(Notebooks IN01-IN17 + ARB Capstone^)
echo # Python: 3.10, 3.11, or 3.12
echo # ============================================================
echo.
echo # Core OpenAI SDK
echo openai^>=1.30.0
echo tiktoken^>=0.7.0
echo.
echo # Environment variables
echo python-dotenv^>=1.0.0
echo.
echo # LangChain ecosystem
echo langchain^>=0.2.16
echo langchain-core^>=0.2.38
echo langchain-openai^>=0.1.22
echo langchain-community^>=0.2.16
echo.
echo # LangGraph
echo langgraph^>=0.2.0
echo.
echo # Vector stores
echo chromadb^>=0.5.0
echo faiss-cpu^>=1.7.4
echo pinecone-client^>=3.2.0
echo.
echo # Fine-tuning frameworks
echo transformers^>=4.40.0
echo peft^>=0.11.0
echo accelerate^>=0.30.0
echo datasets^>=2.20.0
echo.
echo # Evaluation metrics
echo rouge-score^>=0.1.2
echo nltk^>=3.8.1
echo scikit-learn^>=1.4.0
echo.
echo # Observability
echo langfuse^>=2.0.0
echo.
echo # Utilities
echo pydantic^>=2.7.0
echo numpy^>=1.26.0
echo rich^>=13.7.0
echo requests^>=2.31.0
echo.
echo # Network ^& Infrastructure Engineering
echo mcp^>=1.0.0
echo pandas^>=2.2.0
echo PyYAML^>=6.0.1
echo.
echo # Jupyter environment
echo jupyter^>=1.0.0
echo ipykernel^>=6.29.0
echo notebook^>=7.2.0
) > requirements.txt

echo requirements.txt created.

REM ============================================================
REM 5. Create venv using Python 3.12
REM ============================================================
echo.
echo ============================================================
echo Creating Python 3.12 virtual environment...
echo ============================================================

if not exist "venv\Scripts\python.exe" (
    %PYTHON312% -m venv venv

    if errorlevel 1 (
        echo.
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo venv already exists.
)

REM ============================================================
REM 6. Activate venv
REM ============================================================
echo.
echo Activating virtual environment...

call "venv\Scripts\activate.bat"

REM ============================================================
REM 7. Verify Python version inside venv
REM ============================================================
echo.
echo ============================================================
echo Python inside virtual environment:
echo ============================================================

python --version

python -c "import sys; print(sys.executable)"

REM ============================================================
REM 8. Upgrade pip
REM ============================================================
echo.
echo Upgrading pip...

python -m pip install --upgrade pip

REM ============================================================
REM 9. Install requirements
REM ============================================================
echo.
echo ============================================================
echo Installing packages...
echo ============================================================
echo.

python -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ============================================================
    echo WARNING: Package installation failed.
    echo ============================================================
    echo.
    pause
    exit /b 1
)

REM ============================================================
REM 10. Verify installation
REM ============================================================
echo.
echo ============================================================
echo Verifying installation...
echo ============================================================

python -c "import openai; print('OpenAI       : OK')"
python -c "import langchain; print('LangChain    : OK')"
python -c "import langgraph; print('LangGraph    : OK')"
python -c "import chromadb; print('ChromaDB     : OK')"
python -c "import faiss; print('FAISS        : OK')"
python -c "import transformers; print('Transformers : OK')"
python -c "import pandas; print('Pandas       : OK')"
python -c "import numpy; print('NumPy        : OK')"
python -c "import jupyter; print('Jupyter      : OK')"

echo.
echo ============================================================
echo       SETUP COMPLETED SUCCESSFULLY
echo ============================================================
echo.
echo Project folder:
echo %CD%
echo.
echo Virtual environment:
echo %CD%\venv
echo.
echo Requirements:
echo %CD%\requirements.txt
echo.
echo Python version:
python --version
echo.
echo To activate later:
echo.
echo cd "%USERPROFILE%\Desktop\Advanced Agentic AI"
echo venv\Scripts\activate
echo.
echo ============================================================

pause
endlocal
```
