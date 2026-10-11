---
name: convention-audit
description: Audits a repository against the shared engineering convention and performs safe alignment within the assigned scope. Use when adopting or updating the convention, assessing project compliance, or conducting a requested audit of code structure, test quality, documentation, and exceptional execution paths.
---

# Внедрение и аудит конвенции

Работать в рамках [convention-workflow](../convention-workflow/SKILL.md). Подключение и обновление описаны в [README локального пакета](../../../docs/conventions/README.md). Копирование файлов не подтверждает соответствие проекта.

1. Прочитать [аудит и безопасное выравнивание](references/alignment.md) и [критерии и статусы](references/compliance.md). Установить, поручен полный аудит или конкретная область; не расширять полномочия из-за внедрения стандарта.
2. Использовать [convention-coding](../convention-coding/SKILL.md), [convention-testing](../convention-testing/SKILL.md) и [convention-documentation](../convention-documentation/SKILL.md) для их областей. Проверить скрытые зависимости, модульность, мёртвый код, качество тестов, актуальность документов и код ↔ реестр исключений.
3. При проверке планов прочитать [границу TODO/ и правила поиска](../convention-workflow/references/planning.md). Открытые находки сохранять только в `TODO/` с фактами, доказательствами, риском, действием и блокером.
4. Исправлять безопасные подтверждённые несоответствия в рамках поручения. Не менять продуктовые контракты, данные, права, production-инфраструктуру или действующие механизмы вслепую ради формального соответствия.
5. Повторно проверить затронутые области и выполнить доступные безопасные проверки. В отчёте различить VERIFIED / INFERRED / UNKNOWN и указать статус полноценно проверенной области. Статус всего сервиса давать только после полного аудита; не записывать его в постоянную документацию.
