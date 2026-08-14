from __future__ import annotations

from uuid import UUID

from .base import TsBaseModel


class StatusCategoryModel(TsBaseModel):
    """
    A fixed, system-defined status category (e.g. "To Do" / "In Progress" /
    "Done") that every workspace `StatusModel` belongs to.

    Swagger: StatusCategoryModel
    required: id, name
    """

    id: UUID
    name: str


class StatusModel(TsBaseModel):
    """
    A workspace-configurable named workitem status (e.g. "In Review"),
    grouped under a fixed `StatusCategoryModel`.

    Swagger: StatusModel
    required: category, id, name
    """

    id: UUID
    name: str
    category: StatusCategoryModel


class StatusCategoryModelList(TsBaseModel):
    """
    Response envelope for GET /status-categories -- the fixed, system-wide
    list of status categories.

    Swagger: StatusCategoryModelList
    required: items
    """

    items: list[StatusCategoryModel]


class StatusModelList(TsBaseModel):
    """
    Response envelope for GET /workspaces/{workspace}/statuses.

    Swagger: StatusModelList
    required: items
    """

    items: list[StatusModel]


class CreateStatusRequestBody(TsBaseModel):
    """
    Request body for POST /workspaces/{workspace}/statuses -- `category` is
    the target `StatusCategoryModel`'s id/name (a plain string per swagger,
    not a nested object).

    Swagger: CreateStatusRequestBody
    required: category, name
    """

    name: str
    category: str
