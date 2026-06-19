@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ============================================================
echo    清理旧文件 - 视频提示词反推工具
echo ============================================================
echo  会删除【旧版本的打包产物和缓存】，不会动源代码，
echo  更不会删除签名私钥 private_key.pem。
echo ------------------------------------------------------------
echo.

echo [1/4] 关闭可能在运行的旧程序（避免文件被占用）...
taskkill /F /T /IM VideoPromptTool.exe       >nul 2>nul
taskkill /F /T /IM VideoPromptTool_debug.exe >nul 2>nul
taskkill /F /T /IM Keygen.exe                >nul 2>nul
echo       完成。
echo.

echo [2/4] 删除旧的打包产物（dist / build，含旧的 exe）...
if exist "源代码版本\dist"  rd /s /q "源代码版本\dist"
if exist "源代码版本\build" rd /s /q "源代码版本\build"
if exist "用户版本\dist"    rd /s /q "用户版本\dist"
if exist "用户版本\build"   rd /s /q "用户版本\build"
echo       完成。
echo.

echo [3/4] 删除 Python 缓存（__pycache__ / *.pyc）...
for /d /r %%d in (__pycache__) do if exist "%%d" rd /s /q "%%d"
del /s /q *.pyc >nul 2>nul
echo       完成。
echo.

echo [4/4] 旧的用户分发压缩包（可选，约 100MB）
if not exist "用户版本.zip" goto skipzip
choice /C YN /M "是否删除 用户版本.zip （Y=删除  N=保留）"
if errorlevel 2 goto keepzip
del /q "用户版本.zip"
echo       已删除 用户版本.zip
goto afterzip
:keepzip
echo       已保留 用户版本.zip
goto afterzip
:skipzip
echo       未找到 用户版本.zip，跳过。
:afterzip
echo.

echo ============================================================
echo    清理完成！
echo.
echo    重新打包【新版】可执行文件：
echo      主程序   ：双击 源代码版本\build_exe.bat     -^> 生成新的 VideoPromptTool.exe
echo      激活码工具：双击 源代码版本\build_keygen.bat  -^> 生成新的 Keygen.exe（只给自己用）
echo ============================================================
echo.
pause
