#!/usr/bin/env python3
"""Unit tests for evidence_collector.py"""

import unittest
from evidence_collector import (
    validate_record,
    compute_retention_rates,
    generate_markdown_table,
    generate_csv,
    run_gap_and_feasibility_assessment
)


class TestEvidenceCollector(unittest.TestCase):

    def setUp(self):
        self.sample_data = {
            "study_title": "PLA Recycling Evaluation",
            "baseline": {
                "material_name": "PLA (Ingeo 4043D)",
                "tensile_strength_mpa": 60.0,
                "elongation_at_break_pct": 5.0
            },
            "records": [
                {
                    "record_id": "REC-001",
                    "process_type": "FDM/FFF",
                    "material_name": "PLA (Ingeo 4043D)",
                    "recycled_content_pct": 100.0,
                    "cycle_generation": "G1",
                    "tensile_strength_mpa": 54.0,
                    "elongation_at_break_pct": 4.0,
                    "evidence_level": "EMPIRICAL",
                    "testing_standard": "ASTM D638",
                    "source_reference": "DOI: 10.1016/sample.2021",
                    "environmental_lca_impact": "-50% carbon",
                    "safety_ehs_notes": "Well ventilated"
                },
                {
                    "record_id": "REC-002",
                    "process_type": "FDM/FFF",
                    "material_name": "PLA (Ingeo 4043D)",
                    "recycled_content_pct": 100.0,
                    "cycle_generation": "G2",
                    "tensile_strength_mpa": 48.0,
                    "elongation_at_break_pct": 2.5,
                    "evidence_level": "EMPIRICAL",
                    "testing_standard": "ASTM D638",
                    "source_reference": "DOI: 10.1016/sample.2021",
                    "environmental_lca_impact": "-55% carbon",
                    "safety_ehs_notes": "Wear mask"
                },
                {
                    "record_id": "REC-003",
                    "process_type": "FDM/FFF",
                    "material_name": "PLA (Ingeo 4043D)",
                    "recycled_content_pct": 50.0,
                    "cycle_generation": "G1-Blend",
                    "tensile_strength_mpa": 57.0,
                    "elongation_at_break_pct": 4.5,
                    "evidence_level": "EMPIRICAL",
                    "testing_standard": "ASTM D638",
                    "source_reference": "DOI: 10.1016/sample.2022",
                    "environmental_lca_impact": "-30% carbon",
                    "safety_ehs_notes": "Low VOC"
                }
            ]
        }

    def test_validate_record_valid(self):
        errs = validate_record(self.sample_data["records"][0], 1)
        self.assertEqual(errs, [])

    def test_validate_record_invalid(self):
        bad_rec = {
            "record_id": "BAD-01",
            "process_type": "INVALID_TYPE",
            "evidence_level": "UNKNOWN"
        }
        errs = validate_record(bad_rec, 1)
        self.assertTrue(any("Invalid 'process_type'" in e for e in errs))
        self.assertTrue(any("Missing required field: 'material_name'" in e for e in errs))
        self.assertTrue(any("Invalid 'evidence_level'" in e for e in errs))

    def test_compute_retention_rates(self):
        updated_data, count = compute_retention_rates(self.sample_data)
        # REC-001: 54 / 60 = 90.0%, 4 / 5 = 80.0%
        rec1 = updated_data["records"][0]
        self.assertEqual(rec1["tensile_retention_pct"], 90.0)
        self.assertEqual(rec1["elongation_retention_pct"], 80.0)
        # REC-002: 48 / 60 = 80.0%, 2.5 / 5 = 50.0%
        rec2 = updated_data["records"][1]
        self.assertEqual(rec2["tensile_retention_pct"], 80.0)
        self.assertEqual(rec2["elongation_retention_pct"], 50.0)

    def test_generate_markdown_table(self):
        md = generate_markdown_table(self.sample_data)
        self.assertIn("| REC-001 | FDM/FFF | PLA (Ingeo 4043D) |", md)
        self.assertIn("`EMPIRICAL`", md)

    def test_generate_csv(self):
        csv_text = generate_csv(self.sample_data)
        self.assertIn("record_id,process_type,material_name", csv_text)
        self.assertIn("REC-001,FDM/FFF,PLA (Ingeo 4043D)", csv_text)

    def test_gap_and_feasibility_assessment(self):
        report = run_gap_and_feasibility_assessment(self.sample_data)
        self.assertEqual(report["total_records"], 3)
        self.assertEqual(report["empirical_ratio_pct"], 100.0)
        self.assertEqual(report["evaluated_trl"], 5)
        self.assertEqual(report["identified_gaps"], [])


if __name__ == "__main__":
    unittest.main()
