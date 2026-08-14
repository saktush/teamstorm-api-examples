# teamstorm/models/portfolios.py
from __future__ import annotations

from uuid import UUID

from pydantic import Field

from .base import TsBaseModel
from .common import DateTimeLike, UserModel
from .statuses import StatusModel
from .workitems_thumbs import FolderThumbModel, PortfolioElementThumbModel, WorkflowThumbModel


class PortfolioThumbModel(TsBaseModel):
    """
    Swagger: PortfolioThumbModel
    required: id, name

    Minimal id/name reference to a portfolio; embedded in
    PortfolioElementModel.portfolio.
    """

    id: UUID
    name: str


class PortfolioModel(TsBaseModel):
    """
    Swagger: PortfolioModel
    required: elements, folder, id, name
    """

    id: UUID
    name: str
    folder: FolderThumbModel
    elements: list[PortfolioElementThumbModel]
    description: str | None = None
    workflow: WorkflowThumbModel | None = None


class PortfolioModelList(TsBaseModel):
    """
    Swagger: PortfolioModelList
    required: items

    NOTE: no fromToken/maxItemsCount/nextToken fields on this schema --
    ListPortfolios returns the full, unpaginated result set for the given
    filter in a single response (see PortfoliosAPI.list, which uses a plain
    get() instead of get_all()).
    """

    items: list[PortfolioModel]


class CreatePortfolioRequestBody(TsBaseModel):
    """
    Swagger: CreatePortfolioRequestBody
    required: folderId, name

    A portfolio must live inside an existing folder.
    """

    name: str
    folder_id: UUID = Field(alias="folderId")


class PatchPortfolioRequestBody(TsBaseModel):
    """
    Swagger: PatchPortfolioRequestBody
    required: name

    NOT a general partial-update body. The server's PatchPortfolioRequestBody
    is just a required `name` string with no per-field presence tracking --
    see docs/api-analysis/upstream-semantics.md, Section 7, item 2. `PATCH
    /portfolios/{id}` only renames the portfolio;
    there is nothing else patchable through this endpoint, and `name` is
    mandatory here, unlike a genuine partial-update body such as
    PatchPortfolioElementRequestBody below.
    """

    name: str


class PortfolioElementModel(TsBaseModel):
    """
    Swagger: PortfolioElementModel
    required: id, name, portfolio, responsibles, status
    """

    id: UUID
    name: str
    status: StatusModel
    responsibles: list[UserModel]
    portfolio: PortfolioThumbModel
    description: str | None = None
    start_date: DateTimeLike | None = Field(default=None, alias="startDate")
    end_date: DateTimeLike | None = Field(default=None, alias="endDate")


class PortfolioElementModelList(TsBaseModel):
    """
    Swagger: PortfolioElementModelList
    required: items

    NOTE: same as PortfolioModelList -- no pagination token fields; the
    server returns everything in one response (see PortfolioElementsAPI.list).
    """

    items: list[PortfolioElementModel]


class CreatePortfolioElementRequestBody(TsBaseModel):
    """
    Swagger: CreatePortfolioElementRequestBody
    required: name, portfolioId

    `responsibles` is an array of plain strings per swagger (no uuid format) --
    docs/api-analysis/upstream-semantics.md notes this is inferred to be
    usernames, not independently re-verified.
    """

    portfolio_id: UUID = Field(alias="portfolioId")
    name: str
    description: str | None = None
    start_date: DateTimeLike | None = Field(default=None, alias="startDate")
    end_date: DateTimeLike | None = Field(default=None, alias="endDate")
    responsibles: list[str] | None = None


class PatchPortfolioElementRequestBody(TsBaseModel):
    """
    Swagger: PatchPortfolioElementRequestBody
    required: (none)

    Unlike PatchPortfolioRequestBody above, this IS a genuine partial-update
    body: every field is optional and nullable. Serialized by
    PortfolioElementsAPI.patch with exclude_unset=True, exclude_none=False:
    a field never assigned here is omitted from the request (server: leave
    unchanged), while a field explicitly assigned None is sent as JSON null
    (server: clear this field).
    """

    name: str | None = None
    description: str | None = None
    start_date: DateTimeLike | None = Field(default=None, alias="startDate")
    end_date: DateTimeLike | None = Field(default=None, alias="endDate")
    status: str | None = None
    responsibles: list[str] | None = None
