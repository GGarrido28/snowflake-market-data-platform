import importlib
import sys
import unittest


class KalshiPackageImportTests(unittest.TestCase):
    def test_package_import_does_not_eager_import_snowflake_scrapers(self):
        module_names = [
            "market_data_platform.pipelines.kalshi",
            "market_data_platform.pipelines.kalshi.events",
            "market_data_platform.pipelines.kalshi.markets",
            "market_data_platform.pipelines.kalshi.series",
            "market_data_platform.warehouse.snowflake",
        ]
        original_modules = {module_name: sys.modules.get(module_name) for module_name in module_names}
        try:
            for module_name in module_names:
                sys.modules.pop(module_name, None)

            importlib.import_module("market_data_platform.pipelines.kalshi")

            self.assertNotIn("market_data_platform.pipelines.kalshi.events", sys.modules)
            self.assertNotIn("market_data_platform.pipelines.kalshi.markets", sys.modules)
            self.assertNotIn("market_data_platform.pipelines.kalshi.series", sys.modules)
            self.assertNotIn("market_data_platform.warehouse.snowflake", sys.modules)
        finally:
            for module_name in module_names:
                sys.modules.pop(module_name, None)
                if original_modules[module_name] is not None:
                    sys.modules[module_name] = original_modules[module_name]


if __name__ == "__main__":
    unittest.main()
