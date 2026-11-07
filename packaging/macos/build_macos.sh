#!/usr/bin/env bash
# Crea Viator.app e l'immagine disco .dmg per macOS.
# Uso: bash packaging/macos/build_macos.sh
set -euo pipefail
cd "$(dirname "$0")/../.."

python3 -m pip install --upgrade -r requirements.txt pyinstaller
VERSION=$(python3 -c "import viator; print(viator.APP_VERSION)")
echo "Versione: $VERSION"

python3 -m PyInstaller --noconfirm --clean --windowed --name Viator \
  --icon assets/viator.icns \
  --osx-bundle-identifier org.eurekafoundation.viator \
  main.py

PLIST="dist/Viator.app/Contents/Info.plist"
pb() { /usr/libexec/PlistBuddy -c "$1" "$PLIST" 2>/dev/null || /usr/libexec/PlistBuddy -c "${1/Add/Set}" "$PLIST"; }
# macOS chiede queste spiegazioni prima di dare accesso a fotocamera, microfono e posizione
pb "Add :NSCameraUsageDescription string Viator usa la fotocamera solo per i siti a cui la consenti."
pb "Add :NSMicrophoneUsageDescription string Viator usa il microfono solo per i siti a cui lo consenti."
pb "Add :NSLocationUsageDescription string Viator condivide la posizione solo con i siti a cui la consenti."
pb "Add :NSLocationWhenInUseUsageDescription string Viator condivide la posizione solo con i siti a cui la consenti."
pb "Add :CFBundleShortVersionString string $VERSION"
pb "Add :CFBundleVersion string $VERSION"
pb "Add :NSHighResolutionCapable bool true"

# firma "ad hoc" (senza certificato Apple): necessaria perché l'app parta su Mac con chip Apple
codesign --force --deep --sign - dist/Viator.app

mkdir -p dist/installer
rm -f "dist/installer/Viator-$VERSION-macOS.dmg"
STAGE=$(mktemp -d)
cp -R dist/Viator.app "$STAGE/"
ln -s /Applications "$STAGE/Applicazioni"
hdiutil create -volname "Viator" -srcfolder "$STAGE" -ov -format UDZO "dist/installer/Viator-$VERSION-macOS.dmg"
rm -rf "$STAGE"
echo "Fatto! dist/installer/Viator-$VERSION-macOS.dmg"
