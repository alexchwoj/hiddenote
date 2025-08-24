@echo off

echo Building Windows executable...

rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul

pyinstaller --onefile --windowed --add-data "assets;assets" --add-data "src;src" --icon=assets/icon.ico main.py --name hiddenote

if %errorlevel% equ 0 (
    echo Build completed successfully!
    echo Executable available at: dist\hiddenote.exe
) else (
    echo Build failed!
    exit /b 1
)

pause
