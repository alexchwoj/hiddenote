#!/bin/bash

CREATE_DMG=false
VERSION="0.2.0"

for arg in "$@"; do
    case $arg in
        --dmg) CREATE_DMG=true; shift ;;
    esac
done

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

    if [ "$CREATE_DMG" = true ]; then
        DMG_NAME="hiddenote-${VERSION}.dmg"
        echo "Creating DMG: $DMG_NAME"

        rm -f "$DMG_NAME"
        mkdir -p dmg_temp
        cp -r "dist/hiddenote.app" dmg_temp/
        ln -s /Applications dmg_temp/Applications

        hdiutil create -volname "hiddenote" \
            -srcfolder dmg_temp \
            -ov -format UDZO \
            "$DMG_NAME"

        rm -rf dmg_temp
        echo "✅ DMG created: $DMG_NAME"
    fi

else
    echo "Build failed!"
    exit 1
fi