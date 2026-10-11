"""Current-user application menu registration on Linux."""

import os
import sys
from pathlib import Path

from .config import project_home
from .desktop_entry import desktop_argument, desktop_string, write_desktop_file

ICON = """<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
<rect x="2" y="2" width="60" height="60" rx="16" fill="#4775f5"/>
<path fill="white" d="M28 17h8v9h10v7H36v11c0 4 2 5 5 5h5v7h-6c-9 0-12-4-12-12V33h-7v-7h7z"/>
</svg>
"""


def install_launcher(*, home: Path | None = None) -> Path:
    """Install the application menu entry and return its path."""
    data_dir = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
    if not data_dir.is_absolute():
        raise ValueError("XDG_DATA_HOME должен содержать абсолютный путь")
    if "%" in sys.executable or "=" in sys.executable:
        raise ValueError("Путь программы для меню не должен содержать % или =. Переместите папку программы")
    home = (home or project_home()).resolve()
    prefix = [sys.executable] if getattr(sys, "frozen", False) else [sys.executable, "-m", "talk2g"]
    command = prefix + ["app", "--home", str(home)]
    icon = data_dir / "icons/hicolor/scalable/apps/talk2g.svg"
    content = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=talk2g\n"
        "GenericName=Voice typing\n"
        "GenericName[ru]=Голосовой ввод\n"
        "Comment=Local Russian dictation\n"
        "Comment[ru]=Локальная русская диктовка\n"
        "Exec=" + " ".join(desktop_argument(part) for part in command) + "\n"
        "Icon=" + desktop_string(str(icon)) + "\n"
        "Terminal=false\n"
        "StartupNotify=false\n"
        "Categories=Utility;Accessibility;\n"
        "Keywords=dictation;speech;transcription;диктовка;голос;толк;толк тут;толк ту джи;\n"
        "Keywords[ru]=диктовка;голос;распознавание;толк;толк тут;толк ту джи;\n"
    )
    entry = data_dir / "applications/talk2g.desktop"
    write_desktop_file(icon, ICON)
    write_desktop_file(entry, content)
    return entry
