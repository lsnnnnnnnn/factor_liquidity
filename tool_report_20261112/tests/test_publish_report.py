import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


spec = importlib.util.spec_from_file_location("publish_report", Path(__file__).resolve().parents[1]/"publish_report.py")
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


class PublicReportTests(unittest.TestCase):
    def source(self, root):
        source = root/"source"/"report"
        (source/"data").mkdir(parents=True)
        for name in ("main.pdf", "main.tex", "README.md"):
            (source/name).write_text("test fixture, not a report")
        metadata = dict(data_kind="company_historical_replay", pdf_status="compiled",
            private_security_data_included=False, criterion="all-plan-same-day-exact-100pct-20261109-v1",
            reference_price_rule="max_age", rule_version="historical-test-rule", observed_trials=1)
        (source/"data/report_metadata.json").write_text(json.dumps(metadata))
        (source/"data/trial_summary.csv").write_text("factor,scenario,capital,verdict\nN20,regular,10000000,fail\n")
        (source/"data/capacity_summary.csv").write_text("factor,scenario,tested_count\nN20,regular,1\n")
        (source/"data/fills.csv").write_text("private ledger must not be copied")
        (source/"private").mkdir()
        (source/"private/input.csv").write_text("private source must not be copied")
        return source

    def test_only_public_files_are_copied_and_existing_report_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = self.source(root); destination = root/"public"
            preview = publisher.publish(source, destination, "historical_baseline", dry_run=True)
            self.assertFalse(destination.exists())
            self.assertNotIn("data/fills.csv", preview["files"])
            publisher.publish(source, destination, "historical_baseline")
            self.assertEqual({str(p.relative_to(destination)) for p in destination.rglob("*") if p.is_file()},
                             set(preview["files"])|{"publication.json"})
            self.assertFalse(json.loads((destination/"publication.json").read_text())["historical_results_are_new_capacity"])
            self.assertTrue((root/"public_tex_bundle.zip").is_file())
            with self.assertRaises(FileExistsError):
                publisher.publish(source, destination, "historical_baseline")

    def test_private_columns_and_private_metadata_cannot_enter_public_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = self.source(root)
            path = source/"data/trial_summary.csv"
            path.write_text("factor,account\nN20,/private/account\n")
            with self.assertRaisesRegex(ValueError, "non-public columns"):
                publisher.publish(source, root/"public", "representative")
            path.write_text("factor\nN20\n")
            meta = source/"data/report_metadata.json"
            data = json.loads(meta.read_text()); data["source"]={"broker_socket":"private"};meta.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "private fields"):
                publisher.publish(source, root/"public", "representative")
            self.assertFalse((root/"public").exists())

    def test_real_report_metadata_shape_and_both_strict_criterion_names(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = self.source(root)
            path = source/"data/report_metadata.json"
            metadata = json.loads(path.read_text())
            metadata.update(rule_version="g1-0935-event-updates-20261027-v1", reference_max_age_seconds=30,
                start="2024-01-02", end="2024-08-30", factor_variants=["N20", "N61", "N121", "N241", "N481"],
                scenarios={"regular":{"participation_rate":.1,"daily_turnover_cap":.1},
                           "sweep":{"sweep_limit_gap_pp":1.,"post_trigger_participation":1.,"pricing":"official_directional_limit"}},
                progress_scope="saved_account_status_not_live_process_verification",
                progress=[{"factor":"N20","scenario":"sweep","capital":1e9,"saved_status":"running",
                           "completed_day":"2024-08-30","completed_trading_days":162,"total_trading_days":162,
                           "recorded_at_utc":"2026-11-11T07:48:16.335017+00:00"}],
                market_impact=None, financial_accounts_recomputed=False, source_results_generated_at_utc=None)
            for criterion in publisher.STRICT_CRITERIA:
                with self.subTest(criterion=criterion):
                    metadata["criterion"]=criterion;path.write_text(json.dumps(metadata))
                    receipt=publisher.publish(source,root/"public","historical_baseline",dry_run=True)
                    self.assertEqual(receipt["reference_price_rule"],"max_age")
                    self.assertEqual(receipt["rule_version"],metadata["rule_version"])
            metadata["criterion"]="ordinary-plan-99pct";path.write_text(json.dumps(metadata))
            with self.assertRaisesRegex(ValueError,"exact 100%"):
                publisher.publish(source,root/"public","historical_baseline",dry_run=True)

    def test_legal_plan_publication_requires_distinct_scope_and_deviation_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source=self.source(root)
            meta=source/"data/report_metadata.json"
            data=json.loads(meta.read_text())
            data.update(criterion=publisher.LEGAL_PLAN_CRITERION,
                research_plan_policy="legal_net_demand_floor_v1",
                rule_version="g1-0935-legal-plan-impact-20261116-v5")
            meta.write_text(json.dumps(data))
            with self.assertRaisesRegex(FileNotFoundError,"target-deviation"):
                publisher.publish(source,root/"public","representative",dry_run=True)
            summary=source/"data/plan_rounding_summary.csv"
            summary.write_text("factor,scenario,capital,legal_zero_plan_count,plan_rounding_reference_cny\nN20,sweep,10000000,27,281414.12\n")
            receipt=publisher.publish(source,root/"public","representative",dry_run=True)
            self.assertIn("data/plan_rounding_summary.csv",receipt["files"])
            summary.write_text("factor,instrument\nN20,private-security\n")
            with self.assertRaisesRegex(ValueError,"non-public columns"):
                publisher.publish(source,root/"public","representative",dry_run=True)
            data['criterion']="all-plan-same-day-exact-100pct-20261109-v1"
            meta.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,"historical original-plan"):
                publisher.publish(source,root/"public","representative",dry_run=True)

    def test_legal_plan_publication_rejects_legacy_version(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source=self.source(root)
            meta=source/"data/report_metadata.json";data=json.loads(meta.read_text())
            data.update(criterion=publisher.LEGAL_PLAN_CRITERION,
                research_plan_policy="legal_net_demand_floor_v1")
            meta.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,"v5 financial rule"):
                publisher.publish(source,root/"public","representative",dry_run=True)

    def test_v6_sweep_publication_requires_explicit_matching_policy_and_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source=self.source(root)
            path=source/"data/report_metadata.json"
            metadata=json.loads(path.read_text())
            metadata.update(criterion=publisher.LEGAL_PLAN_CRITERION,
                research_plan_policy="legal_net_demand_floor_v1",
                research_execution_policy="lot_preserving_quote_cash_v1",
                rule_version=publisher.EXTENDED_SWEEP_RULE,
                sweep_band_policy=publisher.EXTENDED_SWEEP_BAND_POLICY,
                sweep_limit_bands_pct=[5,10,20], scenarios={scene:dict(
                    sweep_band_policy=publisher.EXTENDED_SWEEP_BAND_POLICY,
                    sweep_limit_bands_pct=[5,10,20]) for scene in ("sweep", "sweep_impact")})
            (source/"data/plan_rounding_summary.csv").write_text("factor,scenario,capital,legal_zero_plan_count\nN20,sweep,10000000,27\n")
            path.write_text(json.dumps(metadata))
            receipt=publisher.publish(source,root/"public","representative",dry_run=True)
            self.assertEqual(receipt["sweep_band_policy"],publisher.EXTENDED_SWEEP_BAND_POLICY)
            self.assertEqual(receipt["sweep_limit_bands_pct"],[5,10,20])
            self.assertNotIn("data/fills.csv",receipt["files"])
            for changed in ({"sweep_band_policy":None}, {"sweep_limit_bands_pct":[10,20]},
                    {"rule_version":publisher.LEGAL_PLAN_RULE}, {"research_execution_policy":None},
                    {"criterion":"all-plan-same-day-exact-quantity"},
                    {"scenarios":{"sweep":{"sweep_limit_bands_pct":[10,20]}}}):
                with self.subTest(changed=changed):
                    path.write_text(json.dumps(metadata|changed))
                    with self.assertRaises(ValueError):
                        publisher.publish(source,root/"public","representative",dry_run=True)
            self.assertFalse((root/"public").exists())


    def test_v7_policy_and_public_exception_summary_are_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source=self.source(root)
            path=source/'data/report_metadata.json'
            meta=json.loads(path.read_text())
            meta.update(criterion=publisher.LEGAL_PLAN_CRITERION, rule_version=publisher.EXCEPTION_RIGHTS_RULE,
                research_plan_policy='legal_net_demand_floor_v1', research_execution_policy='lot_preserving_quote_cash_v1',
                sweep_band_policy=publisher.EXTENDED_SWEEP_BAND_POLICY, sweep_limit_bands_pct=[5,10,20],
                research_expiry_policy='ordinary_day_end_exception_resume_v1',
                corporate_action_policy='record_holdings_integer_or_unknown_v1')
            path.write_text(json.dumps(meta))
            (source/'data/plan_rounding_summary.csv').write_text('factor,legal_zero_plan_count\nN20,1\n')
            (source/'data/exception_summary.csv').write_text('factor,scenario,capital,event,event_cn,timing,plan_count,event_record_count\nN20,sweep,10000000,exception_completed,延期完成,after_original_day,1,1\n')
            result=publisher.publish(source,root/'new','representative',dry_run=True)
            self.assertIn('data/exception_summary.csv',result['files'])
            for change in ({'corporate_action_policy':None}, {'rule_version':publisher.EXTENDED_SWEEP_RULE}):
                path.write_text(json.dumps(meta|change))
                with self.assertRaises(ValueError):
                    publisher.publish(source,root/'new','representative',dry_run=True)


if __name__ == "__main__":
    unittest.main()
