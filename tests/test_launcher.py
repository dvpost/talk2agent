import configparser
import json
import logging
import os
import re
import select
import shutil
import socket
import subprocess
import sys
from types import SimpleNamespace

import pytest

from talk2g import cli, launcher, runtime
from talk2g.config import Settings


@pytest.mark.skipif(sys.platform != "linux", reason="Linux application menu")
@pytest.mark.parametrize("frozen", [pytest.param(False, id="source"), pytest.param(True, id="standalone")])
def test_menu_launcher_opens_correct_profile_through_real_desktop_parser(monkeypatch, tmp_path, frozen):
    # GIVEN: программа и профиль с пробелами, кириллицей и специальными символами пути.
    if not shutil.which("gio") or not shutil.which("desktop-file-validate"):
        pytest.skip("GIO and desktop-file-validate are required")
    data_dir = tmp_path / 'Данные $HOME `tick` "quote" back\\slash %f'
    profile = tmp_path / 'Профиль $HOME `tick` "quote" back\\slash %f'
    profile.mkdir()
    applications = data_dir / "applications"
    applications.mkdir(parents=True)
    other = applications / "another.desktop"
    other.write_text("Чужое приложение", encoding="utf-8")
    executable = tmp_path / 'Программа $HOME `tick` "quote" back\\slash'
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        listener.settimeout(5)
        address = listener.getsockname()
        executable.write_text(
            f"#!{sys.executable}\n"
            "import json, socket, sys\n"
            f"with socket.create_connection({address!r}, timeout=5) as connection:\n"
            "    connection.sendall(json.dumps(sys.argv[1:]).encode())\n",
            encoding="utf-8",
        )
        executable.chmod(0o700)
        monkeypatch.setattr(sys, "executable", str(executable))
        monkeypatch.setattr(sys, "frozen", frozen, raising=False)
        monkeypatch.setenv("XDG_DATA_HOME", str(data_dir))
        # WHEN: ярлык устанавливают дважды и запускают системным launcher из другой папки.
        entry = launcher.install_launcher(home=profile)
        first = entry.read_bytes()
        launcher.install_launcher(home=profile)
        assert entry.read_bytes() == first
        subprocess.run(["desktop-file-validate", str(entry)], check=True)
        subprocess.run(["gio", "launch", str(entry)], cwd=tmp_path, check=True)
        connection, _ = listener.accept()
        with connection, connection.makefile() as stream:
            arguments = json.load(stream)
    # THEN: открывается правильный профиль без фонового режима; ярлык виден и имеет иконку.
    expected = ["app", "--home", str(profile)]
    if not frozen:
        expected = ["-m", "talk2g", *expected]
    assert arguments == expected
    assert entry == applications / "talk2g.desktop"
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(entry, encoding="utf-8")
    section = parser["Desktop Entry"]
    assert section["Name"] == "talk2g"
    assert section["Type"] == "Application"
    assert section["Terminal"] == "false"
    assert not section.getboolean("NoDisplay", fallback=False)
    assert not section.getboolean("Hidden", fallback=False)
    assert "диктовка" in section["Keywords[ru]"]
    assert "диктовка" in section["Keywords"]
    icon = data_dir / "icons/hicolor/scalable/apps/talk2g.svg"
    assert section["Icon"] == str(icon).replace("\\", "\\\\")
    assert "<svg" in icon.read_text(encoding="utf-8")
    assert other.read_text(encoding="utf-8") == "Чужое приложение"


@pytest.mark.skipif(sys.platform != "linux", reason="Linux application menu")
def test_default_menu_location_uses_current_user_data_directory(monkeypatch, tmp_path):
    # GIVEN: пользователь без XDG_DATA_HOME и без явного пути профиля.
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setattr(launcher.Path, "home", lambda: tmp_path)
    monkeypatch.setenv("TALK2G_HOME", str(tmp_path / "profile"))
    # WHEN: устанавливают ярлык с настройками по умолчанию.
    entry = launcher.install_launcher()
    # THEN: запись попадает в меню текущего пользователя и сохраняет его профиль.
    assert entry == tmp_path / ".local/share/applications/talk2g.desktop"
    assert entry.is_file()
    assert str(tmp_path / "profile") in entry.read_text(encoding="utf-8")


@pytest.mark.skipif(sys.platform != "linux", reason="Linux application menu")
def test_invalid_profile_does_not_install_partial_menu_entry(monkeypatch, tmp_path):
    # GIVEN: профиль содержит перевод строки, недопустимый в Desktop Entry.
    data_dir = tmp_path / "data"
    monkeypatch.setenv("XDG_DATA_HOME", str(data_dir))
    # WHEN: пытаются зарегистрировать такой профиль.
    with pytest.raises(ValueError, match="недопустимый символ"):
        launcher.install_launcher(home=tmp_path / "bad\nprofile")
    # THEN: ни ярлык, ни иконка не созданы.
    assert not data_dir.exists()


@pytest.mark.parametrize(
    "name",
    [pytest.param("talk%2g", id="percent"), pytest.param("talk=2g", id="equals")],
)
def test_unsupported_executable_path_does_not_install_an_unlaunchable_entry(monkeypatch, tmp_path, name):
    # GIVEN: путь программы содержит символ, который системный Desktop Entry launcher не поддерживает.
    data_dir = tmp_path / "data"
    monkeypatch.setenv("XDG_DATA_HOME", str(data_dir))
    monkeypatch.setattr(sys, "executable", str(tmp_path / name))
    # WHEN: регистрируют программу с таким путём.
    with pytest.raises(ValueError, match="Путь программы.*%.*="):
        launcher.install_launcher(home=tmp_path / "profile")
    # THEN: приложение сообщает причину, а не создаёт неработающий пункт меню.
    assert not data_dir.exists()


def test_cli_can_register_menu_without_opening_the_app(monkeypatch, tmp_path, capsys):
    # GIVEN: отдельный профиль и каталог меню текущего пользователя.
    data_dir = tmp_path / "data"
    profile = tmp_path / "profile"
    monkeypatch.setenv("XDG_DATA_HOME", str(data_dir))
    monkeypatch.setenv("TALK2G_HOME", str(profile))
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(sys, "argv", ["talk2g", "install-launcher", "--home", str(profile)])
    # WHEN: вызывают отдельную команду установки ярлыка.
    cli.main()
    # THEN: ярлык создан, команда сообщает его путь; журнал GUI не создаётся.
    entry = data_dir / "applications/talk2g.desktop"
    assert entry.is_file()
    assert str(entry) in capsys.readouterr().out
    assert not (profile / ".data/app.log").exists()


@pytest.fixture
def app_startup(monkeypatch, tmp_path):
    windows = []
    monkeypatch.setenv("TALK2G_HOME", str(tmp_path / "profile"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setattr(runtime, "desktop_runtime", lambda: None)
    monkeypatch.setitem(
        sys.modules,
        "talk2g.desktop",
        SimpleNamespace(run_app=lambda settings, *, background: windows.append(background)),
    )
    root = logging.getLogger()
    handlers = list(root.handlers)
    yield windows
    for handler in list(root.handlers):
        if handler not in handlers:
            root.removeHandler(handler)
            handler.close()


@pytest.mark.parametrize(
    ("platform", "arguments", "background", "installed"),
    [
        pytest.param("linux", [], False, True, id="linux-default-launch"),
        pytest.param("linux", ["app", "--background"], True, True, id="linux-background-launch"),
        pytest.param("win32", ["app"], False, False, id="windows-launch"),
    ],
)
def test_app_startup_registers_linux_menu(
    monkeypatch, tmp_path, app_startup, platform, arguments, background, installed
):
    # GIVEN: обычный или фоновый запуск приложения на указанной платформе.
    monkeypatch.setattr(sys, "platform", platform)
    monkeypatch.setattr(sys, "argv", ["talk2g", *arguments])
    # WHEN: CLI открывает приложение, подменяя только границу GUI.
    cli.main()
    # THEN: меню устанавливается на Linux; выбранный режим окна сохранён.
    assert (tmp_path / "data/applications/talk2g.desktop").is_file() is installed
    assert app_startup == [background]


def test_menu_installation_failure_stops_app_startup_and_logs_reason(
    monkeypatch, tmp_path, app_startup, caplog
):
    # GIVEN: целевой путь ярлыка занят каталогом; заменить его файлом невозможно.
    entry = tmp_path / "data/applications/talk2g.desktop"
    entry.mkdir(parents=True)
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(sys, "argv", ["talk2g", "app"])
    # WHEN: приложение запускают с недоступной регистрацией меню.
    with pytest.raises(SystemExit) as error:
        cli.main()
    # THEN: ошибка сохраняется в журнале, окно не открывается, временные файлы убраны.
    assert error.value.code == 1
    assert app_startup == []
    assert "talk2g.desktop" in caplog.text
    assert "talk2g.desktop" in (tmp_path / "profile/.data/app.log").read_text(encoding="utf-8")
    assert sorted(path.name for path in entry.parent.iterdir()) == ["talk2g.desktop"]


@pytest.mark.skipif(
    not os.environ.get("TALK2G_DESKTOP_TESTS") or sys.platform != "linux", reason="Isolated X11 desktop"
)
@pytest.mark.desktop
def test_menu_opens_existing_app_and_starts_it_again_after_exit(monkeypatch, tmp_path, qtbot):
    # GIVEN: отдельные X11, профиль, меню и TMPDIR для сокета single-instance.
    profile = tmp_path / "profile"
    Settings(load_on_demand=True).save(profile)
    data_dir = tmp_path / "data"
    ipc_dir = tmp_path / "ipc"
    ipc_dir.mkdir()
    environment = dict(
        os.environ,
        XDG_DATA_HOME=str(data_dir),
        XDG_CONFIG_HOME=str(tmp_path / "config"),
        TMPDIR=str(ipc_dir),
        TALK2G_HOME=str(tmp_path / "wrong-profile"),
        HF_HUB_OFFLINE="1",
    )
    monkeypatch.setenv("XDG_DATA_HOME", str(data_dir))
    entry = launcher.install_launcher(home=profile)
    journal = profile / ".data/app.log"
    pidfds = []

    def started():
        content = journal.read_text(encoding="utf-8") if journal.exists() else ""
        return [int(pid) for pid in re.findall(r"Интерфейс готов: pid=(\d+), фон=(?:True|False)", content)]

    def visible(pid):
        return subprocess.run(
            ["xdotool", "search", "--onlyvisible", "--all", "--pid", str(pid), "--name", "^talk2g$"],
            capture_output=True,
            text=True,
            timeout=3,
        )

    def launch():
        subprocess.run(["gtk-launch", "talk2g"], cwd=tmp_path, env=environment, check=True, timeout=5)

    def quit_app():
        return subprocess.run(
            [sys.executable, "-m", "talk2g", "quit"], env=environment, capture_output=True, timeout=5
        )

    try:
        # WHEN: программу открывают из меню, сворачивают и повторно выбирают тот же пункт.
        launch()
        qtbot.waitUntil(lambda: len(started()) == 1, timeout=8000)
        first_pid = started()[0]
        pidfds.append(os.pidfd_open(first_pid))
        qtbot.waitUntil(lambda: visible(first_pid).returncode == 0)
        window_id = visible(first_pid).stdout.strip().splitlines()[0]
        subprocess.run(["xdotool", "windowminimize", window_id], check=True, timeout=3)
        qtbot.waitUntil(lambda: visible(first_pid).returncode != 0)
        launch()
        qtbot.waitUntil(lambda: visible(first_pid).returncode == 0)
        # THEN: окно того же экземпляра открывается; после выхода меню запускает новый процесс.
        assert started() == [first_pid]
        assert quit_app().returncode == 0
        assert select.select([pidfds[0]], [], [], 5)[0] == [pidfds[0]]
        assert entry.is_file()
        launch()
        qtbot.waitUntil(lambda: len(started()) == 2, timeout=8000)
        second_pid = started()[1]
        pidfds.append(os.pidfd_open(second_pid))
        qtbot.waitUntil(lambda: visible(second_pid).returncode == 0)
        assert second_pid != first_pid
        assert not (tmp_path / "wrong-profile/.data").exists()
        assert quit_app().returncode == 0
        assert select.select([pidfds[1]], [], [], 5)[0] == [pidfds[1]]
    finally:
        quit_app()
        for pidfd in pidfds:
            select.select([pidfd], [], [], 5)
            os.close(pidfd)
