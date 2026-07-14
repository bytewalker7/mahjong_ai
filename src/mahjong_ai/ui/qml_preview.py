"""Launch the standalone Qt Quick 2.5D Mahjong table art preview."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine


def create_engine() -> QQmlApplicationEngine:
    engine = QQmlApplicationEngine()
    qml_path = Path(__file__).with_name("qml") / "MahjongTablePreview.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        raise RuntimeError(f"无法加载 QML 预览：{qml_path}")
    return engine


def main() -> int:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    engine = create_engine()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
