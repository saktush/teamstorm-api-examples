# Live E2E-сценарий — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** opt-in pytest-прогон, который против живого стенда вызывает все 163 разрешённые операции API в двух временных
пространствах, удаляет всё за собой, убирает забытые пространства прошлых прогонов и пишет отчёт по 170 операциям.

**Architecture:** `tests/e2e/runner.py` — каталог операций из манифеста, `RecordingClient` (перехват
`TsClient._request`), движок шагов с `needs`/реестром, отчёт md/json, предикат уборки. `tests/e2e/scenario.py` —
упорядоченный список шагов. `tests/e2e/test_e2e_offline.py` — тесты без сети. `tests/e2e/test_live_e2e.py` — вход под
`RUN_LIVE_E2E=1`.

**Tech Stack:** Python 3.11, unittest-стиль как в `tests/api`, `teamstorm` (requests + pydantic v2).

**Spec:** `docs/superpowers/specs/2026-10-28-live-e2e-scenario-design.md`

## Global Constraints

- Запуск только при `RUN_LIVE_E2E=1`; креды из `.env` (`BASE_URL`, `API_TOKEN`), загрузка как в `tests/api/test_live_time_metrics.py`.
- Исключены (EXCLUDED): `BlockUser`, `UnblockUser`, `GetConnections`, `CreateConnection`, `DeleteConnection`, `CreateUser`, `UpdateQueryVisibilitySettings`.
- Демо-пользователи `demo.user1..4`; их учётные записи не меняются.
- Ключи `E2E<UTC yyyymmddHHMMSS>A|B`; маркер в описании `teamstorm-api-examples live e2e run <префикс>`.
- Уборка забытых: ключ `^E2E\d{14}[AB]$` + маркер с тем же префиксом + тот же автор + старше 6 ч + не текущий прогон.
- Неидемпотентные записи не повторяются; токен не попадает в лог/отчёт.
- Отчёт: `build/e2e/<префикс>.md` и `.json`.
- black 120, flake8, mypy только для `teamstorm/` (тесты не обязаны, но аннотации ставим).

## Review Focus

- Путь `/workspaces/{workspace}/workitems/count` против `/workspaces/{workspace}/workitems/{workitem}` (и
  `/workspaces/time-tracking-entries` против `/workspaces/{workspace}`): сопоставление выбирает шаблон с меньшим числом
  плейсхолдеров — тест `test_match_prefers_literal_segments`.
- Ответ 2xx, который упал на валидации модели: операция FAIL, а не PASS — тест `test_validation_error_marks_last_call_failed`.
- Одна из нескольких однотипных операций упала (например, `update_attribute` по 7 типам): FAIL — тест `test_any_failed_call_fails_op`.
- Упавший шаг пропускает зависимых, но не шаги удаления — тест `test_failed_step_skips_dependents_not_cleanup`.
- Уборка не трогает свежие/чужие/без маркера/текущие пространства — `test_stale_predicate_*`.

---

### Task 1: Каталог операций и запись вызовов (`runner.py`)

**Interfaces — Produces:**
- `OPERATIONS: dict[str, OpMapping]` — ключ `op_key(row) = row.operation_id or f"{method} {path}"`.
- `EXCLUDED: dict[str, str]` — ключ операции → причина.
- `match_operation(method: str, path: str) -> str | None`.
- `class Call` (dataclass: `op`, `method`, `path`, `step`, `status: int | None`, `seconds`, `error: str | None`, `counts: bool`).
- `class RecordingClient(TsClient)`: `calls: list[Call]`, `current_step: str`, `counts: bool`; переопределяет `_request`.

- [ ] Тесты `test_match_prefers_literal_segments`, `test_match_all_manifest_templates_roundtrip` (каждый шаблон с
  подставленными значениями матчится в свою операцию), `test_recording_client_records_success_and_api_error` (подмена
  `requests.Session.request`).
- [ ] Реализация, тесты зелёные.

### Task 2: Движок шагов и статусы операций

**Interfaces — Produces:**
- `@dataclass Step(name: str, ops: tuple[str, ...], fn: Callable[[Ctx], None], needs: tuple[str, ...] = (), cleanup: bool = False)`.
- `class Ctx`: `api: TeamStormAPI`, `client: RecordingClient`, `reg: dict[str, Any]`, `prefix: str`, `started: datetime`, `env: Mapping[str, str]`; `skip(reason)` бросает `StepSkipped`.
- `run_steps(ctx, steps) -> list[StepResult]` (`StepResult`: `name`, `status` PASS/FAIL/SKIP, `reason`, `seconds`).
- `op_statuses(steps, results, calls) -> dict[str, OpStatus]` — правила: EXCLUDED по списку; есть засчитанные вызовы:
  FAIL, если хоть один упал, иначе PASS; вызовов нет: SKIP с причиной шага, если шаг пропущен, иначе FAIL «не вызвана».
- Нестандартное исключение шага (не `ApiError`) помечает последний вызов этого шага упавшим.

- [ ] Тесты `test_failed_step_skips_dependents_not_cleanup`, `test_validation_error_marks_last_call_failed`, `test_any_failed_call_fails_op`.
- [ ] Реализация, тесты зелёные.

### Task 3: Отчёт и уборка

**Interfaces — Produces:**
- `write_report(path_stem: Path, meta: dict[str, Any], results, statuses, sweep: list[dict]) -> str` — пишет `.md`/`.json`, возвращает краткую сводку для консоли.
- `is_stale_e2e_workspace(ws: WorkspaceModel, *, owner_id: UUID, now: datetime, current_prefix: str, min_age: timedelta = timedelta(hours=6)) -> bool`.

- [ ] Тесты `test_stale_predicate_accepts_old_marked_own`, `test_stale_predicate_rejects_{fresh,foreign_author,no_marker,marker_mismatch,current_run,bad_key}`, `test_report_counts`.
- [ ] Реализация, тесты зелёные.

### Task 4: Сценарий (`scenario.py`) и офлайн-тест полноты

**Interfaces — Produces:** `build_steps() -> list[Step]` в порядке спеки (0–14) + `sweep` после создания A.

- [ ] Тест `test_declared_ops_plus_excluded_equal_manifest` (объединение = 170, без пересечений и лишних ключей).
- [ ] Шаги по спеке; кнопки данных стенда: `E2E_QUERY_ID`, `E2E_QUERY_WORKSPACE`, `E2E_GROUP`.

### Task 5: Live-вход, документация, quality gate

- [ ] `test_live_e2e.py`: skip без `RUN_LIVE_E2E=1`; режим `E2E_CLEANUP_ONLY=1` (+`E2E_OWNER`); `finally` — удаление
  пространств из реестра; печать сводки; `assert` нет FAIL.
- [ ] Краткий раздел в `README.md`/`README.en.md`.
- [ ] Полный quality gate из CLAUDE.md.
