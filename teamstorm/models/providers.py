from __future__ import annotations

from uuid import UUID

from pydantic import Field

from .base import TsBaseModel
from .enums import ProviderType


class ProviderModel(TsBaseModel):
    """
    A configured identity provider.

    Swagger: ProviderModel
    required: id, providerType
    """

    id: UUID
    name: str | None = None
    provider_type: ProviderType = Field(alias="providerType")


class ProviderModelList(TsBaseModel):
    """
    Response envelope for GET /providers.

    Swagger: ProviderModelList
    required: providers
    NOTE: the wrapping key is "providers", not the usual "items"/pagination
    envelope used elsewhere in this API — this endpoint is not paginated.
    """

    providers: list[ProviderModel]
