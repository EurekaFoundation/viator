#!/usr/bin/env bash
# Crea Viator in formato AppImage (un solo file: doppio clic e parte) per Linux.
# Uso: bash packaging/linux/build_linux.sh
set -euo pipefail
cd "$(dirname "$0")/../.."

python3 -m pip install --upgrade -r requirements.txt pyinstaller
VERSION=$(python3 -c "import viator; print(viator.APP_VERSION)")
ARCH=$(uname -m)
echo "Versione: $VERSION ($ARCH)"

python3 -m PyInstaller --noconfirm --clean --windowed --name viator main.py

# --- struttura AppDir
APPDIR=build/Viator.AppDir
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/lib" "$APPDIR/usr/share/applications" "$APPDIR/usr/share/icons/hicolor/256x256/apps"
cp -R dist/viator "$APPDIR/usr/lib/viator"
cp packaging/linux/viator.desktop "$APPDIR/viator.desktop"
cp packaging/linux/viator.desktop "$APPDIR/usr/share/applications/viator.desktop"
cp assets/viator.png "$APPDIR/viator.png"
cp assets/viator.png "$APPDIR/usr/share/icons/hicolor/256x256/apps/viator.png"
cat > "$APPDIR/AppRun" <<'RUN'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/lib/viator/viator" "$@"
RUN
chmod +x "$APPDIR/AppRun"

# --- appimagetool (scaricato da GitHub la prima volta)
TOOL=build/appimagetool-$ARCH.AppImage
if [ ! -x "$TOOL" ]; then
  curl -fL -o "$TOOL" "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-$ARCH.AppImage"
  chmod +x "$TOOL"
fi
mkdir -p dist/installer
OUT="dist/installer/Viator-$VERSION-Linux-$ARCH.AppImage"
ARCH=$ARCH "$TOOL" --appimage-extract-and-run "$APPDIR" "$OUT"

# --- in alternativa, archivio .tar.gz
tar -C dist -czf "dist/installer/Viator-$VERSION-Linux-$ARCH.tar.gz" viator
echo "Fatto! $OUT"
