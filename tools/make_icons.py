"""Genera le icone dell'applicazione (assets/) a partire dal logo vettoriale.

Uso: python tools/make_icons.py   (richiede PySide6 e Pillow)
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PIL import Image  # noqa: E402
from PySide6.QtCore import QByteArray, Qt  # noqa: E402
from PySide6.QtGui import QGuiApplication, QImage, QPainter  # noqa: E402
from PySide6.QtSvg import QSvgRenderer  # noqa: E402

from viator.theme import LIGHT, logo_svg  # noqa: E402

ASSETS = os.path.join(ROOT, "assets")


def render(size, path):
    renderer = QSvgRenderer(QByteArray(logo_svg(LIGHT["accent"], "#FFFFFF").encode()))
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    margin = round(size * 0.04)  # piccolo margine come le icone di sistema
    renderer.render(painter, image.rect().adjusted(margin, margin, -margin, -margin))
    painter.end()
    image.save(path)


def main():
    QGuiApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    app = QGuiApplication.instance() or QGuiApplication(["make_icons", "-platform", "offscreen"])  # noqa: F841
    os.makedirs(ASSETS, exist_ok=True)
    big = os.path.join(ASSETS, "viator-1024.png")
    render(1024, big)
    render(256, os.path.join(ASSETS, "viator.png"))
    image = Image.open(big)
    image.save(os.path.join(ASSETS, "viator.ico"),
               sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    image.save(os.path.join(ASSETS, "viator.icns"))
    with open(os.path.join(ASSETS, "viator.svg"), "w", encoding="utf-8") as f:
        f.write(logo_svg(LIGHT["accent"], "#FFFFFF"))
    os.remove(big)
    print("Icone create in", ASSETS)


if __name__ == "__main__":
    main()
