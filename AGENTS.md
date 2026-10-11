# talk2g

> Локальная русская диктовка: после паузы распознанный текст вводится в выбранное приложение.

## Правила работы

- Перед работой применяй [convention-workflow](.agents/skills/convention-workflow/SKILL.md),
  затем тематические навыки по задаче. Источник и версия — в
  [локальном индексе конвенции](docs/conventions/README.md).
- Сохраняй WebSocket v1, формат настроек и пользовательские данные.
  При несовпадении кода и требований исследуй причину до изменения поведения.
- Распознавание выполняется только целыми блоками после `recognition_pause`
  или Stop; клиент требует `ready.recognize_on_pause=true` перед передачей PCM.
  Ответы WebSocket проверяй в `protocol.py` до передачи потребителям Qt/CLI.
- Открывай серверный HTTP/WebSocket listener после подготовки модели;
  контракт запуска и готовности хранится в `docs/PROTOCOL.md`.
- Держи сервер и обработку текста независимыми от Qt; вкладки UI передают
  намерения контроллеру, который управляет записью и системными службами.
- Перед удалением реализации проверяй регистрации Qt, команды CLI и сборку.
- Проверяй запись и ввод на временных профилях и в отдельных тестовых окнах.
  Сохраняй работающий пользовательский экземпляр; для native X11 используй
  `benchmarks/check_x11.sh`, а не текущий рабочий стол.
- На X11 сохраняй блок clipboard до запроса текста целевым клиентом;
  граница доставки и отказ описаны в `docs/ARCHITECTURE.md`. Не восстанавливай
  прежний буфер при неподтверждённой доставке уже отправленной вставки.
- Сохраняй причину ошибки диктовки в основном и плавающем окнах и в
  `.data/app.log`; расположение и хранение журналов описаны в `docs/OPERATIONS.md`.
- Используй синтетические токены в тестах, временные файлы в фикстурах;
  `.data`, `models`, `recordings` и отчёты запусков оставляй вне Git.
- Для новых и содержательно изменённых тестов пиши GIVEN/WHEN/THEN по-русски;
  контракты файлов/SQLite/WebSocket проверяй с реальной интеграцией.
- Выполняй отдельные простые shell-команды без цепочек; исследуй локальные
  файлы через `rg` и существующие утилиты.
- При изменении команд, границ или контрактов обновляй `AGENTS.md` и
  затронутые документы.
- На Linux установка и запуск GUI регистрируют ярлык меню текущего пользователя;
  команда `install-launcher --home` обновляет его без запуска GUI.
  Контракт путей, профиля и отказа — [docs/USAGE.md](docs/USAGE.md#запуск-из-меню-приложений-linux).

## Команды

Из корня репозитория:

```bash
uv sync --frozen --extra desktop --extra dev
./check.sh
./check.sh tests/test_protocol.py tests/test_server.py
uv run python scripts/check_docs.py
uv run ruff check src tests benchmarks packaging scripts
uv run ruff format --check src tests benchmarks packaging scripts
./run-linux.sh app --background
./run-linux.sh install-launcher --home /absolute/profile
```

Для Windows и проверок с дополнительными системными зависимостями,
реальной моделью или сборкой используй команды и условия из `docs/VALIDATION.md`.

## Навигация

| Контекст | Источник |
| --- | --- |
| Конвенция разработки и навыки агентов | [docs/conventions/README.md](docs/conventions/README.md) |
| Быстрый старт | [README.md](README.md) |
| Установка, настройки диктовки и архив аудио | [docs/USAGE.md](docs/USAGE.md) |
| Сервер, профили, журналы и диагностика остановки | [docs/OPERATIONS.md](docs/OPERATIONS.md) |
| Границы, критичные потоки, карта кода | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Handshake, PCM, события, Stop/Cancel | [docs/PROTOCOL.md](docs/PROTOCOL.md) |
| Команды проверок, gates и ограничения платформ | [docs/VALIDATION.md](docs/VALIDATION.md) |
| Действующие разрешённые исключительные пути | [docs/exceptional_execution_paths.md](docs/exceptional_execution_paths.md) |
| Зависимости и закреплённое окружение | [pyproject.toml](pyproject.toml), [uv.lock](uv.lock) |
| Сторонние компоненты и лицензии поставки | [docs/THIRD_PARTY.md](docs/THIRD_PARTY.md) |
| CI | [.github/workflows/check.yml](.github/workflows/check.yml) |
