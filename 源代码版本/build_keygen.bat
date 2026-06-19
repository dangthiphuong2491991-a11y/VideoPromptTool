@echo off
REM ============================================================
REM  Build the keygen (author's tool) into Keygen.exe
REM  Pure tkinter -> easy to pack. Do NOT share Keygen.exe!
REM  Put this file next to keygen.py and double-click.
REM ============================================================

python --version >nul 2>nul
if %errorlevel%==0 (set PYCMD=python& goto build)
py --version >nul 2>nul
if %errorlevel%==0 (set PYCMD=py& goto build)
echo [ERROR] Python not found. Install from python.org (check "Add to PATH").
pause
exit /b 1

:build
echo Installing PyInstaller + cryptography ...
%PYCMD% -m pip install pyinstaller cryptography
if errorlevel 1 ( echo [ERROR] install failed. & pause & exit /b 1 )

echo.
echo Building Keygen.exe ...
%PYCMD% -m PyInstaller --noconfirm --onefile --windowed --collect-all cryptography --name Keygen keygen.py
if errorlevel 1 ( echo [ERROR] build failed. & pause & exit /b 1 )

echo.
echo ============================================================
echo  SUCCESS!  Your keygen is here:  dist\Keygen.exe
echo  Keep it private - do NOT give it to users.
echo ============================================================
echo.
pause
