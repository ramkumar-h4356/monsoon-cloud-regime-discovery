import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    ROOT
    / "src"
    / "06_feature_engineering"
    / "analyze_ceres_missingness.py"
)

spec = importlib.util.spec_from_file_location(
    "analyze_ceres_missingness",
    MODULE_PATH,
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TestMatchingAreaVariable(unittest.TestCase):

    def test_all_property_families_and_layers(self):
        layers = ("high", "mid_high", "mid_low", "low", "total")

        prefixes = (
            "cldpress_top_",
            "cldpress_",
            "cldhght_",
            "cldtemp_",
            "cldtau_",
            "lwp_",
            "iwp_",
        )

        available = {
            f"cldarea_{layer}_1h"
            for layer in layers
        }

        for prefix in prefixes:
            for layer in layers:
                variable = f"{prefix}{layer}_1h"

                with self.subTest(variable=variable):
                    result = module.matching_area_variable(
                        variable,
                        available,
                    )

                    self.assertEqual(
                        result,
                        f"cldarea_{layer}_1h",
                    )

    def test_cloud_area_variables_do_not_match_themselves(self):
        available = {
            f"cldarea_{layer}_1h"
            for layer in ("high", "mid_high", "mid_low", "low", "total")
        }

        for variable in available:
            with self.subTest(variable=variable):
                self.assertIsNone(
                    module.matching_area_variable(variable, available)
                )

    def test_invalid_or_unknown_variables_return_none(self):
        available = {
            "cldarea_high_1h",
            "cldarea_low_1h",
        }

        invalid_variables = (
            "cldpress_unknown_1h",
            "cldpress_top_unknown_1h",
            "cldpress_high",
            "unknown_high_1h",
        )

        for variable in invalid_variables:
            with self.subTest(variable=variable):
                self.assertIsNone(
                    module.matching_area_variable(variable, available)
                )

    def test_missing_area_partner_returns_none(self):
        available = {"cldarea_high_1h"}

        self.assertIsNone(
            module.matching_area_variable(
                "cldpress_low_1h",
                available,
            )
        )


if __name__ == "__main__":
    unittest.main()
