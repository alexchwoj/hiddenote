#!/bin/bash

echo "Building macOS executable..."

rm -rf build/
rm -rf dist/

pyinstaller --onefile --windowed --add-data "assets:assets" --add-data "src:src" main.py --name hiddenote

if [ $? -eq 0 ]; then
    echo "Build completed successfully!"
    echo "Executable available at: dist/hiddenote"
    chmod +x dist/hiddenote
else
    echo "Build failed!"
    exit 1
fi
