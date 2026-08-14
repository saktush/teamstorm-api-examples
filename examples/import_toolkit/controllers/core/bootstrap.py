import logging
from typing import List, Optional
from uuid import UUID

from teamstorm.api import TeamStormAPI
from teamstorm.client import ApiError
from teamstorm.models.agile import AgileModel, CreateAgileRequestBody
from teamstorm.models.folders import CreateFolderRequestBody, FolderModel

from import_toolkit.io.readers import ExcelReader, ValidatedImport
from import_toolkit.controllers.core.utils import pick_single


def validate_and_load_excel(excel_path: str, logger: logging.Logger) -> ValidatedImport:
    return ExcelReader().load(excel_path, logger)


def ensure_folder(
    api: TeamStormAPI,
    *,
    workspace_key: str,
    folder_name: str,
    workspace_id: UUID,
    log: logging.Logger,
) -> UUID:
    folders: List[FolderModel] = api.folders.list(
        workspace_key,
        name=folder_name,
        parent_id=workspace_id,
    )

    if len(folders) == 0:
        folder = api.folders.create(
            workspace_key,
            CreateFolderRequestBody(
                name=folder_name,
                parentId=workspace_id,
            ),
        )
        log.info("Folder %s не найдена, создана: id=%s", folder_name, folder.id)
        return folder.id

    folder = pick_single(
        folders,
        f"Folder name={folder_name!r} parentId={workspace_id}",
    )
    log.info("Folder %s найдена: id=%s", folder_name, folder.id)
    return folder.id


def ensure_agile_extension(
    api: TeamStormAPI,
    *,
    workspace_key: str,
    folder_id: UUID,
    dry_run: bool,
    log: logging.Logger,
) -> UUID:
    agiles: List[AgileModel] = api.agile.list(workspace_key, folder_id=folder_id)

    if len(agiles) == 0:
        if dry_run:
            log.info("Agile extension не найден: dry-run => было бы выполнено CreateAgile(folderId, EstimatesInTime)")
            return UUID(int=0)
        created = api.agile.create(
            workspace_key,
            body=CreateAgileRequestBody(
                folderId=folder_id,
                estimatesType="EstimatesInTime",
            ),
        )
        log.info("Agile extension создан: id=%s", created.id)
        return created.id

    if len(agiles) == 1:
        agile_id = agiles[0].id
        log.info("Agile extension найден: id=%s", agile_id)
        return agile_id

    raise ApiError(f"Agile extensions: найдено >1 для folderId={folder_id} (не поддерживается)")
