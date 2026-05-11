#!/bin/bash

echo "Building macOS executable..."

rm -rf build/
rm -rf dist/

pyinstaller hiddenote.spec

if [ $? -eq 0 ]; then
    echo "Build completed successfully!"
    echo "Updating Info.plist..."
    echo "Application available at: dist/hiddenote.app"
    # Remove the non-bundle executable
    rm -rf dist/hiddenote

    echo "Signing and cleaning app bundle..."
    xattr -cr dist/hiddenote.app
    codesign --force --sign - dist/hiddenote.app/Contents/Frameworks/Python.framework
    codesign --force --deep --sign - dist/hiddenote.app
else
    echo "Build failed!"
    exit 1
fi
