import logging
from typing import Mapping, Optional
from uuid import UUID

from teamstorm.api import TeamStormAPI
from teamstorm.client import ApiError
from teamstorm.models.sprints import (
    CreateSprintRequestBody,
    PatchSprintRequestBody,
    SprintModel,
)

from import_toolkit.controllers.core.utils import _date_to_iso_datetime, calc_workdays
from import_toolkit.io.readers.contracts import SprintImportRow


def upsert_sprints(
    api: TeamStormAPI,
    *,
    workspace_key: str,
    folder_id: UUID,
    agile_id: Optional[UUID] = None,
    sprints_by_name: Mapping[str, SprintImportRow],
    counters,
    dry_run: bool,
    log: logging.Logger,
    errors: list[str],
) -> dict[str, UUID]:
    sprint_id_by_name: dict[str, UUID] = {}
    for sprint_name, s in sprints_by_name.items():
        try:
            start_iso = _date_to_iso_datetime(s["start_date"])
            end_iso = _date_to_iso_datetime(s["end_date"])

            found: list[SprintModel] = api.sprints.list(workspace_key, folder_id=folder_id, name=sprint_name)

            if len(found) == 0:
                if dry_run:
                    log.info("Sprint CREATE: %r %s..%s", sprint_name, start_iso, end_iso)
                    sprint_id_by_name[sprint_name] = UUID()
                else:
                    body_kwargs = {
                        "name": sprint_name,
                        "startDate": start_iso,
                        "endDate": end_iso,
                        "workdays": calc_workdays(start_iso, end_iso),
                    }
                    if agile_id is not None:
                        body_kwargs["agileId"] = agile_id

                    body = CreateSprintRequestBody(**body_kwargs)
                    log.debug("Sprint CREATE payload=%r", body.model_dump(mode="json"))

                    created = api.sprints.create(workspace_key, body)
                    sprint_id_by_name[sprint_name] = created.id
                    counters.sprints_created += 1
                    log.info("Sprint создан: %r id=%s", sprint_name, created.id)

            elif len(found) == 1:
                sprint = found[0]
                sprint_id_by_name[sprint_name] = sprint.id

                if dry_run:
                    log.info(
                        "Sprint PATCH: %r id=%s => %s..%s",
                        sprint_name,
                        sprint.id,
                        start_iso,
                        end_iso,
                    )
                else:
                    api.sprints.patch(
                        workspace_key,
                        sprint_id=sprint.id,
                        body=PatchSprintRequestBody(
                            name=sprint_name,
                            startDate=start_iso,
                            endDate=end_iso,
                        ),
                    )
                    counters.sprints_patched += 1
                    log.info("Sprint обновлён: %r id=%s", sprint_name, sprint.id)

            else:
                errors.append(f"Sprints: найдено >1 для name={sprint_name!r} (folderId={folder_id})")

        except Exception as e:
            errors.append(f"Sprint {sprint_name!r}: {e}")
    return sprint_id_by_name
