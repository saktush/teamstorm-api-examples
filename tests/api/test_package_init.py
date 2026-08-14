import tomllib
import unittest
from pathlib import Path

import teamstorm

PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


class PackageInitTestCase(unittest.TestCase):
    """teamstorm/__init__.py: version string and top-level public surface."""

    def test_version_is_a_non_empty_string(self) -> None:
        self.assertIsInstance(teamstorm.__version__, str)
        self.assertTrue(teamstorm.__version__)

    def test_version_matches_pyproject(self) -> None:
        """
        `__version__` reads installed distribution metadata by *distribution*
        name, which is not the import name -- the distribution is
        `teamstorm-api-examples`, the package is `teamstorm`. When running
        from an uninstalled source checkout, `version()` raises
        PackageNotFoundError and `__init__` substitutes the same release
        version declared by pyproject.toml, so both paths agree here by
        construction. If pyproject.toml's declared version and the
        distribution name passed to `importlib.metadata.version()` ever
        drift apart, this still fails loudly.
        """
        with open(PYPROJECT, "rb") as fh:
            declared = tomllib.load(fh)["project"]["version"]

        self.assertEqual(declared, teamstorm.__version__)

    def test_all_is_accurate(self) -> None:
        """Every name listed in __all__ must actually resolve on the module."""
        for name in teamstorm.__all__:
            with self.subTest(name=name):
                self.assertTrue(
                    hasattr(teamstorm, name),
                    f"teamstorm.__all__ lists {name!r} but teamstorm has no such attribute",
                )

    def test_all_contains_expected_public_names(self) -> None:
        self.assertEqual(
            set(teamstorm.__all__),
            {
                "__version__",
                "ApiError",
                "RetryConfig",
                "TimeoutConfig",
                "TsClient",
                "TeamStormAPI",
            },
        )

    def test_retry_and_timeout_config_importable_from_top_level(self) -> None:
        from teamstorm import ApiError, RetryConfig, TimeoutConfig

        self.assertTrue(issubclass(ApiError, RuntimeError))
        self.assertEqual(RetryConfig().max_attempts, 5)
        self.assertEqual(TimeoutConfig().as_requests_timeout, (10.0, 60.0))


if __name__ == "__main__":
    unittest.main()
