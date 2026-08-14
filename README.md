# TeamStorm API Examples

**Русский** | [English](README.en.md)

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Практические типизированные примеры и переиспользуемые Python-обёртки для **TeamStorm CWM Public API** (`/cwm/public/api/v1`). Репозиторий содержит клиент, pydantic-модели, 32 ресурсных интерфейса для 159 операций OpenAPI и готовые сценарии автоматизации.

Это **эталонная реализация и набор примеров**, а не отдельный официальный продукт. Приоритетный способ распространения — версионированный локальный архив, который можно передать без доступа к Git. Публикации в реестры пакетов и обещания поддержки нет.

## Возможности

- единый HTTP-клиент с тайм-аутами, повторами и безопасной авторизацией;
- типизированные модели запросов и ответов;
- рабочие пространства, папки, задачи, документы, спринты, портфели, пользователи, роли, атрибуты, вложения и другие ресурсы;
- полная [таблица соответствия API](docs/api-coverage.md);
- [технические заметки о совместимости поведения](docs/technical-behavior.md);
- импорт задач и спринтов из Excel/CSV;
- skill для AI-агентов в [`.agents/skills/teamstorm-api/`](.agents/skills/teamstorm-api/).

## Установка из локального архива — рекомендуемый способ

Требуется Python 3.11 или новее. Получите файл `teamstorm-api-examples-1.0.0.zip` у владельца репозитория или на странице [релиза 1.0.0](https://github.com/saktush/teamstorm-api-examples/releases/tag/v1.0.0), затем:

```bash
python3 -m zipfile -e teamstorm-api-examples-1.0.0.zip .
python3 -m venv .venv
.venv/bin/python -m pip install ./teamstorm-api-examples-1.0.0
```

Архив содержит исходный код и metadata проекта, но не сторонние зависимости. Если целевая машина полностью изолирована от сети, заранее передайте совместимые wheels для `requests`, `pydantic` и их зависимостей и установите их из локального каталога через `pip --no-index --find-links`.

После установки можно удалить распакованный каталог. Сам архив рекомендуется хранить вместе с опубликованным файлом `SHA256SUMS` и проверять командой:

```bash
sha256sum --check SHA256SUMS
```

## Установка из Git — дополнительный способ

Пользователи с доступом к приватному репозиторию могут установить зафиксированный commit:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install \
  "git+https://github.com/saktush/teamstorm-api-examples.git@<commit>"
```

Либо установить локальный checkout:

```bash
gh repo clone saktush/teamstorm-api-examples
cd teamstorm-api-examples
python3 -m venv .venv
.venv/bin/python -m pip install .
```

Имя импортируемого Python-пакета остаётся `teamstorm`.

## Быстрый старт

```python
import os

from teamstorm.client import TsClient
from teamstorm.api import TeamStormAPI

client = TsClient(
    base_url=os.environ["TEAMSTORM_BASE_URL"],
    token=os.environ["TEAMSTORM_API_TOKEN"],
)
api = TeamStormAPI(client)

workspace = api.workspaces.get("YOUR_WORKSPACE_KEY")
print(workspace.name)
```

Полный запускаемый вариант: [`examples/quickstart.py`](examples/quickstart.py). Он читает совместимые с [`.env.template`](.env.template) имена `BASE_URL`, `API_TOKEN` и `WORKSPACE_KEY`; имена `TEAMSTORM_*` выше используются только в автономном фрагменте.

## Аутентификация и безопасность

`TsClient` добавляет к запросам заголовок авторизации с префиксом `PrivateToken`. В переменной `TEAMSTORM_API_TOKEN` храните только значение токена без префикса. Не записывайте токены в код, логи, отчёты или историю Git.

По умолчанию клиент требует HTTPS. `allow_insecure=True` допустим только для локального имитационного сервера без настоящих учётных данных.

При работе через Hermes HTTP MCP действующий секрет может находиться в request-header конфигурации, а не в окружении процесса сервера. Для прямого Python-вызова используйте тот же источник, удалите ровно один префикс `PrivateToken ` и передайте оставшееся значение в `TsClient`.

## Модели и вызовы

Используйте точную модель тела запроса, а не произвольный `dict`:

```python
from uuid import UUID
from teamstorm.models.workitems import CreateWorkitemRequestBody

body = CreateWorkitemRequestBody(
    name="Проверить интеграцию",
    type="Задача",
    parent_id=UUID("00000000-0000-0000-0000-000000000001"),
)
item = api.workitems.create("SPACE", body)
```

Каждый workspace-метод принимает ключ пространства первым аргументом. Для сериализации пользовательских тел используйте `model_dump(mode="json", exclude_none=True)`. PATCH-методы различают отсутствующее поле и явно переданный `None`.

Большинство `list()`-методов собирает все страницы. Для больших наборов используйте `client.iter_all()` и валидируйте элементы соответствующей моделью.

## Области API

`TeamStormAPI` предоставляет 32 ленивых свойства: `workspaces`, `folders`, `agile`, `sprints`, `workitems`, `users`, `types`, `workflows`, `statuses`, `attributes`, комментарии, документы, вложения, права доступа, связи, портфели, роли, группы, интеграции, запросы и учёт времени. Полная карта 159 операций находится в [`docs/api-coverage.md`](docs/api-coverage.md).

## Известные особенности живого API

- Явное присоединение атрибута к типу задачи на проверенном экземпляре возвращало HTTP 500. Сначала проверяйте чтением и не повторяйте изменение вслепую.
- Создание задачи с неприсоединённым пользовательским атрибутом может вернуть `AttributeNotFound`/404, даже если определение атрибута существует.
- Связь элемента портфеля с задачей может сохраниться на сервере, а ответ иметь неожиданную форму и не пройти валидацию модели. Перед повтором обязательно прочитайте состояние сервера.

Подробные безопасные сценарии находятся в agent skill.

## Покрытие API

| Область | Операций | Свойства API |
|---|---|---|
| Рабочие пространства и папки | 10 | `workspaces`, `folders` |
| Agile и спринты | 9 | `agile`, `sprints` |
| Рабочие элементы | 10 | `workitems` |
| Комментарии | 9 | `workitem_comments`, `document_comments` |
| Связи | 8 | `links`, `document_workitem_links` |
| Общий доступ | 8 | `workitem_sharing`, `document_sharing` |
| Вложения | 18 | `workitem_attachments`, `document_attachments` |
| Настройки пространства | 24 | `attributes`, `types`, `workflows`, `statuses` |
| Роли | 5 | `roles` |
| Пользователи и группы | 18 | `users`, `groups`, `workspace_users`, `workspace_groups` |
| Документы | 12 | `documents`, `document_versions`, `document_statuses` |
| Портфели | 12 | `portfolios`, `portfolio_elements` |
| Учёт времени и запросы | 5 | `time_tracking`, `queries` |
| Интеграции | 11 | `git_integration_tokens`, `open_id`, `providers` |
| **Итого** | **159** | 32 свойства |

## Примеры

- [`examples/quickstart.py`](examples/quickstart.py) — минимальное чтение API;
- [`examples/import_toolkit/`](examples/import_toolkit/) — импорт Excel/CSV и синхронизация параметров пространства;
- [`examples/README.md`](examples/README.md) — настройка и команды.

## Разработка и проверки

```bash
uv venv .venv
uv pip install --python .venv/bin/python ".[dev,examples]"
.venv/bin/python scripts/check_repository_positioning.py
.venv/bin/flake8 teamstorm/ examples/ tests/ scripts/
.venv/bin/black --check teamstorm/ examples/ tests/ scripts/
.venv/bin/mypy teamstorm/
.venv/bin/python -m pytest -q
```

CI запускает эти проверки для pull request, изменений в `main` и вручную. Инструкции для участников: [`CONTRIBUTING.md`](CONTRIBUTING.md). Правила для агентов: [`AGENTS.md`](AGENTS.md).

## Лицензия

[MIT](LICENSE).
