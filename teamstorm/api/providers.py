from __future__ import annotations

from teamstorm.api._base import BaseAPI
from teamstorm.models.providers import ProviderModel, ProviderModelList


class ProvidersAPI(BaseAPI):
    """
    Identity providers (e.g. SSO/OpenID connections) configured on this CWM
    instance, used to disambiguate users/groups whose username/name is not
    unique tenant-wide.

    1 op (Providers tag): list. Global (non-workspace-scoped) resource.
    """

    def list(self) -> list[ProviderModel]:
        """
        List every identity provider configured on this CWM instance.

        This is a global (non-workspace-scoped) resource with no filters and
        no pagination. The response wraps its items under a "providers" key
        rather than the usual "items"/pagination envelope, so this method
        calls ``client.get`` directly instead of ``client.get_all``.

        Returns:
            list[ProviderModel]: every configured identity provider.

        HTTP: GET /providers
        """
        data = self.client.get("/providers")
        return ProviderModelList.model_validate(data).providers
