"""Backward-compatible alias for the completed QML game window."""

from .qml_game import main


if __name__ == "__main__":
    raise SystemExit(main())
