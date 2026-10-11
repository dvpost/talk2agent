"""Desktop Entry string encoding and atomic file replacement."""

import tempfile
from pathlib import Path


def desktop_string(value: str) -> str:
    if "\0" in value:
        raise ValueError("Путь запуска содержит недопустимый символ")
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")


def desktop_argument(value: str) -> str:
    if any(character in value for character in "\n\r\0"):
        raise ValueError("Путь запуска содержит недопустимый символ")
    # Desktop string escaping is undone before Exec argument unquoting.
    value = value.replace("%", "%%")
    value = "".join("\\" + character if character in '\\"`$' else character for character in value)
    return '"' + desktop_string(value) + '"'


def write_desktop_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, prefix=".talk2g-", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
        temporary.replace(path)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)
