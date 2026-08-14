# teamstorm/api/agile.py
from __future__ import annotations

from uuid import UUID

from pydantic import TypeAdapter

from ._base import BaseAPI
from ..models.agile import AgileModel, CreateAgileRequestBody, EstimatesType


class AgileAPI(BaseAPI):
    """
    Agile board configuration ("agile extensions") attached to a folder --
    estimation type, board metadata -- distinct from workitems themselves.

    5 ops (Agile tag): list, get, create, create_simple (a friendly wrapper
    around create), delete.
    """

    def list(self, workspace_key: str, *, folder_id: UUID) -> list[AgileModel]:
        """
        List the agile board(s) configured for a folder.

        :param workspace_key: workspace key or id.
        :param folder_id: UUID of the folder whose agile board(s) to list.
        :return: every AgileModel for that folder.
        HTTP: GET /workspaces/{workspace}/agile/list
        NOTE: this endpoint does not paginate -- it uses get_all() only
        because that is the client's generic list-fetch helper, not because
        the response carries a nextToken; a bare array is returned.
        """
        data = self.client.get_all(
            f"/workspaces/{workspace_key}/agile/list",
            params={"folderId": str(folder_id)},  # query params должны быть строками
        )
        return TypeAdapter(list[AgileModel]).validate_python(data)

    def get(self, workspace_key: str, *, agile_id: UUID) -> AgileModel:
        """
        Fetch a single agile board by id.

        :param workspace_key: workspace key or id the agile board belongs to.
        :param agile_id: UUID of the agile board to fetch.
        :return: the matching AgileModel.
        HTTP: GET /workspaces/{workspace}/agile/{agileId}
        """
        data = self.client.get(f"/workspaces/{workspace_key}/agile/{agile_id}")
        return AgileModel.model_validate(data)

    def create(
        self,
        workspace_key: str,
        *,
        body: CreateAgileRequestBody,
    ) -> AgileModel:
        """
        Turn a folder into an agile board by creating its CreateAgileRequestBody
        (folder id + estimates type).

        :param workspace_key: workspace key or id.
        :param body: CreateAgileRequestBody -- folder_id and estimates_type.
        :return: the created AgileModel.
        HTTP: POST /workspaces/{workspace}/agile
        """
        # Важно: mode="json" чтобы UUID стал str и ушёл в JSON без ошибок
        payload = body.model_dump(mode="json", exclude_none=True)

        data = self.client.post(
            f"/workspaces/{workspace_key}/agile",
            body=payload,
        )
        return AgileModel.model_validate(data)

    # (опционально) удобный overload как раньше, но строго типизированный
    def create_simple(
        self,
        workspace_key: str,
        *,
        folder_id: UUID,
        estimates_type: EstimatesType = "EstimatesInTime",
    ) -> AgileModel:
        """
        Convenience wrapper around :meth:`create` that builds the
        CreateAgileRequestBody for you from a folder id and estimates type.

        :param workspace_key: workspace key or id.
        :param folder_id: UUID of the folder to turn into an agile board.
        :param estimates_type: ``"EstimatesInTime"`` or
            ``"EstimatesInStoryPoints"``; defaults to ``"EstimatesInTime"``.
        :return: the created AgileModel.
        HTTP: POST /workspaces/{workspace}/agile (delegates to create()).
        """
        return self.create(
            workspace_key,
            body=CreateAgileRequestBody(folderId=folder_id, estimatesType=estimates_type),
        )

    def delete(self, workspace_key: str, *, agile_id: UUID) -> None:
        """
        Delete an agile board.

        :param workspace_key: workspace key or id the agile board belongs to.
        :param agile_id: UUID of the agile board to delete.
        :return: None.
        HTTP: DELETE /workspaces/{workspace}/agile/{agileId}
        """
        self.client.delete(f"/workspaces/{workspace_key}/agile/{agile_id}")
        return None
