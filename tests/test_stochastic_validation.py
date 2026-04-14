import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

os.environ.setdefault("MPLBACKEND", "Agg")
mpl_config = Path(tempfile.gettempdir()) / "dice-mplconfig"
mpl_config.mkdir(exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(mpl_config))

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from directdiceengine import monte_carlo_validate


RUN_STOCHASTIC_VALIDATION = os.environ.get("RUN_STOCHASTIC_VALIDATION") == "1"


@unittest.skipUnless(
    RUN_STOCHASTIC_VALIDATION,
    "Set RUN_STOCHASTIC_VALIDATION=1 to run slow Monte Carlo validation after major semantic changes.",
)
class StochasticValidationTest(unittest.TestCase):
    def assertValidationPasses(self, expression, tolerance, min_samples=4000, max_samples=20000):
        report = monte_carlo_validate(
            expression,
            min_samples=min_samples,
            max_samples=max_samples,
            batch_size=2000,
            timeout_seconds=10,
            tolerance=tolerance,
            seed=123,
        )
        if not report["passed"]:
            self.fail(
                "Monte Carlo validation failed for {!r}: metrics={}, improving={}, samples={}".format(
                    expression,
                    report["metrics"],
                    report.get("improving"),
                    report["samples"],
                )
            )

    def test_convolution_matches_direct_sampling(self):
        self.assertValidationPasses("d2 + d2", tolerance=0.03)

    def test_boolean_comparison_matches_direct_sampling(self):
        self.assertValidationPasses("d20 >= 11", tolerance=0.03)

    def test_filtered_comparison_matches_direct_sampling(self):
        self.assertValidationPasses("d20[20] >= 14", tolerance=0.02, min_samples=6000, max_samples=30000)

    def test_rollhigh_matches_direct_sampling(self):
        self.assertValidationPasses("4d6h3", tolerance=0.05, min_samples=6000, max_samples=30000)


if __name__ == "__main__":
    unittest.main()
