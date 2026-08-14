from __future__ import annotations

from uuid import UUID

from pydantic import Field

from .base import TsBaseModel
from .enums import TreeNodeType


class IdNameModel(TsBaseModel):
    """
    Hand-written base for the "thumbnail" models below: a lightweight id/name
    reference to a related entity, as embedded in a parent response (e.g.
    `WorkitemModel.folder`), as opposed to the entity's own full model.
    There is no matching swagger schema for this base itself -- each swagger
    schema it's built from (`FolderThumbModel`, `WorkflowThumbModel`, ...)
    happens to share this exact id/name shape.
    """

    id: UUID
    name: str


class FolderThumbModel(IdNameModel):
    """
    Lightweight folder reference, e.g. `WorkitemModel.folder` /
    `PortfolioModel.folder`.

    Swagger: FolderThumbModel
    required: id, name
    """


class WorkflowThumbModel(IdNameModel):
    """
    Lightweight workflow reference, e.g. `WorkitemModel.workflow` /
    `TypeModel.workflow`.

    Swagger: WorkflowThumbModel
    required: id, name
    """


class TypeThumbModel(IdNameModel):
    """
    Lightweight workitem-type reference, e.g. `WorkitemModel.type` /
    `AttributeModel.workitem_types`.

    Swagger: TypeThumbModel
    required: id, name
    """


class SprintThumbModel(IdNameModel):
    """
    Lightweight sprint reference, e.g. `WorkitemModel.sprint`.

    Swagger: SprintThumbModel
    required: id, name
    """


class PortfolioElementThumbModel(IdNameModel):
    """
    Lightweight portfolio-element reference, e.g. `PortfolioModel.elements`.

    Swagger: PortfolioElementThumbModel
    required: id, name
    """


class TreeNodeThumbModel(TsBaseModel):
    """
    A lightweight reference to a node in a workspace's folder tree (folder,
    document, workitem, or the workspace root itself), identifying it by id
    and node type. Used as `DocumentModel.parent`.

    Swagger: TreeNodeThumbModel
    required: id, nodeType
    """

    id: UUID
    node_type: TreeNodeType = Field(alias="nodeType")


class WorkitemPortfolioModel(TsBaseModel):
    """
    Swagger: WorkitemPortfolioModel
    required: elements, id, name
    """

    id: UUID
    name: str
    elements: list[PortfolioElementThumbModel]
