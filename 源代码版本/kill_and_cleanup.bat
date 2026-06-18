@echo off
REM ============================================================
REM  Stop the test programs so their files can be deleted.
REM  RIGHT-CLICK this file -> "Run as administrator".
REM ============================================================

echo Stopping the tool's EXE processes ...
taskkill /F /T /IM VideoPromptTool.exe        >nul 2>nul
taskkill /F /T /IM VideoPromptTool_debug.exe  >nul 2>nul
taskkill /F /T /IM Keygen.exe                 >nul 2>nul
echo   done.
echo.

echo The next step stops ALL Python processes (python.exe / pythonw.exe).
echo It only matters if you launched the script with "python ..." in a
echo command window. If you have OTHER Python programs running that you
echo do NOT want to close, press Ctrl+C now to abort.
echo.
pause

taskkill /F /T /IM python.exe   >nul 2>nul
taskkill /F /T /IM pythonw.exe  >nul 2>nul

echo.
echo ============================================================
echo  All target processes have been stopped.
echo  You can now delete the files / folders.
echo ============================================================
echo.
echo Tip: if a file STILL refuses to delete, restart the computer
echo once and try again - that releases any remaining lock.
echo.
pause
