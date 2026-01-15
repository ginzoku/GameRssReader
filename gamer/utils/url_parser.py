"""Deprecated shim for gamespark parser.

このモジュールは名前変更の互換性のために残しています。
新しい実装は `gamer.utils.gamespark_url_parser.GameSparkUrlParser` を参照してください。
"""

from .gamespark_url_parser import GameSparkUrlParser as UrlParser

__all__ = ["UrlParser"]

