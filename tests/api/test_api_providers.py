import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from teamstorm.api.providers import ProvidersAPI


def _providers_payload() -> dict:
    return {
        "providers": [
            {"id": str(uuid4()), "name": "Local", "providerType": "Local"},
            {"id": str(uuid4()), "name": None, "providerType": "ActiveDirectory"},
        ]
    }


class ProvidersAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = ProvidersAPI(self.client)

    def test_list_uses_plain_get_not_get_all_and_unwraps_providers_key(self) -> None:
        # GetProviders is not paginated and its response wraps items under a
        # "providers" key, not "items" — get_all()/extract_items_and_token()
        # only understands "items", so it must NOT be used here.
        self.client.get.return_value = _providers_payload()

        result = self.api.list()

        self.client.get.assert_called_once_with("/providers")
        self.client.get_all.assert_not_called()
        self.assertEqual(2, len(result))
        self.assertEqual("Local", result[0].name)
        self.assertEqual("Local", result[0].provider_type)
        self.assertIsNone(result[1].name)
        self.assertEqual("ActiveDirectory", result[1].provider_type)


if __name__ == "__main__":
    unittest.main()
