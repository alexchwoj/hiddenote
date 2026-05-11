#!/bin/bash

echo "Building macOS executable..."

rm -rf build/
rm -rf dist/

pyinstaller hiddenote-macos.spec

if [ $? -eq 0 ]; then
    echo "Build completed successfully!"
    rm -rf dist/hiddenote

    echo "Signing and cleaning app bundle..."

    xattr -cr dist/hiddenote.app

    codesign --remove-signature dist/hiddenote.app 2>/dev/null || true
    codesign --force --deep --options runtime \
        --entitlements entitlements.plist \
        --sign - dist/hiddenote.app

    echo "Done."
else
    echo "Build failed!"
    exit 1
fi
