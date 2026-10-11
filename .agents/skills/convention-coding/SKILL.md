---
name: convention-coding
description: Guides implementation, bug fixes, refactoring, and removal of code under the shared engineering convention. Use for changes to application logic, behavioral configuration, architecture, public or data contracts, retries, fallbacks, and exceptional execution paths.
---

# Написание и изменение кода

Работать в рамках [convention-workflow](../convention-workflow/SKILL.md).

1. До изменения прочитать [архитектуру, контракты и безопасность](references/architecture-and-contracts.md) и [прямолинейное исполнение](references/execution-paths.md). Проверить существующие границы, потребителей и условия отказа.
2. При добавлении ответственности, выделении компонентов или рефакторинге прочитать [модульность](references/modularity.md). Сохранять связность и незатронутое поведение; не вводить слои под гипотетическое будущее.
3. При замене или удалении реализации, выключенных веток, зависимостей и конфигурации прочитать [мёртвый код](references/dead-code.md). Не удалять механизм по одному отсутствующему статическому вызову.
4. При затрагивании retry/fallback/деградации, интеграций, SDK, очередей или настроек автоматических повторов прочитать [реестр исключительных путей](references/exceptional-execution-paths.md). Проверить код ↔ реестр, предварительное согласование оператора, лимиты и тесты. Предложения сохранять в `TODO/`; действующую несогласованную ветку не легализовать записью и не удалять вслепую.
5. Проверить изменённый контракт по [convention-testing](../convention-testing/SKILL.md), затем актуализировать затронутые документы по [convention-documentation](../convention-documentation/SKILL.md).

Пакет включает [начальный реестр](../../../docs/exceptional_execution_paths.md) со статусом `NOT ASSESSED`. При первом подключении использовать его только если реестра сервиса ещё нет. Существующий реестр сохранять и проверять по справочнику; обновление пакета не перезаписывает записи, согласования и статус проверки сервиса. Первоначальное состояние не доказывает отсутствия исключений.
