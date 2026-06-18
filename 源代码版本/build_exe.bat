@echo off
REM ============================================================
REM  Build script - Video Prompt Tool (enhanced version)
REM  Pure ASCII. Put this file in the SAME folder as
REM  video_prompt_tool.py , then double-click it.
REM  NOTE: keygen.py is for YOU only - do NOT pack/share it.
REM ============================================================

python --version >nul 2>nul
if %errorlevel%==0 goto haspython

py --version >nul 2>nul
if %errorlevel%==0 (
    set PYCMD=py
    goto build
)

echo.
echo [ERROR] Python was not found on this computer.
echo Please install Python from https://www.python.org/downloads/
echo During installation, CHECK the box "Add Python to PATH".
echo Then run this file again.
echo.
pause
exit /b 1

:haspython
set PYCMD=python

:build
echo.
echo [1/2] Installing dependencies (pyinstaller + dashscope + ttkbootstrap + cryptography) ...
%PYCMD% -m pip install pyinstaller dashscope ttkbootstrap cryptography
if errorlevel 1 goto failinstall

echo.
echo [2/2] Building the EXE, please wait ...
%PYCMD% -m PyInstaller --noconfirm --onefile --windowed --collect-all dashscope --collect-all ttkbootstrap --collect-all cryptography --name VideoPromptTool video_prompt_tool.py
if errorlevel 1 goto failbuild

echo.
echo ============================================================
echo  SUCCESS!  Your program is here:
echo     dist\VideoPromptTool.exe
echo ============================================================
echo.
pause
exit /b 0

:failinstall
echo.
echo [ERROR] Failed to install dependencies. Check your internet.
echo.
pause
exit /b 1

:failbuild
echo.
echo [ERROR] Build failed. Screenshot the messages and send to me.
echo.
pause
exit /b 1
