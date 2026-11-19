"""Guard the approved split convention across source-of-truth documents."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MethodologyDocumentationTests(unittest.TestCase):
    def _read(self, relative_path: str) -> str:
        return (ROOT / relative_path).read_text(encoding="utf-8")

    def test_financial_specification_uses_act_365_for_residual_yields(self):
        specification = self._read("docs/financial_specification.md")

        self.assertIn(
            "D = actual calendar days from settlement_date to maturity_date",
            specification,
        )
        self.assertIn("TEA = (1 + HPR)^(365 / D) - 1", specification)
        self.assertIn("TEM = (1 + TEA)^(1 / 12) - 1", specification)
        self.assertIn("TNA = TEM * 12", specification)
        self.assertNotIn("TNA = HPR * 360 / D", specification)

    def test_market_conventions_separate_vpv_from_residual_yields(self):
        conventions = self._read("docs/market_conventions.md")

        self.assertIn("Treasury-adapted 30/360 convention", conventions)
        self.assertIn("ACT/365 compound annualization", conventions)
        self.assertIn("TNA is the nominal annual rate", conventions)
        self.assertIn("`TEM * 12`", conventions)

    def test_research_register_records_the_corrected_decision(self):
        register = self._read("docs/research/README.md")

        self.assertIn("ACT/365 compound", register)
        self.assertIn("`TNA = TEM x 12`", register)
        self.assertIn("former simple 30/360 annualization", register)


if __name__ == "__main__":
    unittest.main()
