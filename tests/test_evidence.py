import copy
import tempfile
import unittest
from pathlib import Path

from dcc_harness.evidence import digest,evaluate,compare,write_json,read_json
from dcc_harness.project import Project


def observation():
    payload={"objects":{"bench":{"type":"MESH","asset_id":"bench","dimensions":[1.9,.5,.9],
             "material_ids":["wood"],"triangles":100}},"materials":{"wood":{"name":"Wood","roughness":.5}},
             "scene":{"units":{"system":"METRIC","scale_length":1}},
             "coverage":{"not_measured":["animation"]},"issues":[]}
    return {"schema":"dcc.observation.v1",**payload,"revision":digest(payload)}


def resign(obs):
    obs["revision"]=digest({k:obs[k] for k in ("objects","materials","scene","coverage","issues")})
    return obs


SPEC={"schema":"dcc.spec.v1","required":{"bench":{"dimensions":[1.9,.5,.9],"min_triangles":24}},"min_asset_definitions":1}


class EvidenceTests(unittest.TestCase):
    def test_placeholder_and_missing_target_fail(self):
        original=observation()
        self.assertTrue(evaluate(original,SPEC)["passed"])
        for mutation in (lambda o:o["objects"].clear(),lambda o:o["objects"]["bench"].update(triangles=12),
                         lambda o:o["objects"]["bench"].update(dimensions=[2,.5,.9])):
            bad=copy.deepcopy(original); mutation(bad)
            self.assertFalse(evaluate(resign(bad),SPEC)["passed"])

    def test_unknown_rule_and_empty_spec_are_errors(self):
        for spec in ({"schema":"dcc.spec.v1","required":{}},
                     {"schema":"dcc.spec.v1","required":{"bench":{"magic_quality":True}}}):
            with self.assertRaises(ValueError): evaluate(observation(),spec)

    def test_tampering_and_nonfinite_numbers_rejected(self):
        bad=observation(); bad["objects"]["bench"]["triangles"]=900
        with self.assertRaises(ValueError): evaluate(bad,SPEC)
        with self.assertRaises(ValueError): digest({"x":float("nan")})
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"bad.json"; path.write_text('{"x":NaN}')
            with self.assertRaises(ValueError): read_json(path)

    def test_desired_material_value_is_required(self):
        spec=copy.deepcopy(SPEC)
        spec["material_nodes"]={"wood":{"Tint":{"Color2":[.1,.2,.3,1]}}}
        self.assertFalse(evaluate(observation(),spec)["passed"])
        obs=observation()
        obs["materials"]["wood"]["graph"]={"nodes":[{"name":"Tint","inputs":{"Color2":[.1,.2,.3,1]}}]}
        self.assertTrue(evaluate(resign(obs),spec)["passed"])

    def test_allowed_revision_does_not_hide_material_regression(self):
        before=observation(); after=copy.deepcopy(before)
        after["objects"]["bench"]["dimensions"][0]=2.1; resign(after)
        allow={"objects":{"bench":["dimensions"]}}
        self.assertTrue(compare(before,after,allow)["passed"])
        after["materials"]["wood"]["roughness"]=.1; resign(after)
        self.assertFalse(compare(before,after,allow)["passed"])

    def test_coverage_change_and_duplicate_id_issue_fail(self):
        before=observation(); after=copy.deepcopy(before)
        after["coverage"]["not_measured"].append("materials"); resign(after)
        self.assertFalse(compare(before,after)["passed"])
        after=copy.deepcopy(before); after["issues"]=["Duplicate instance ID: bench"]; resign(after)
        self.assertFalse(evaluate(after,SPEC)["passed"])

    def test_evidence_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"receipt.json"; write_json(path,{"accepted":True})
            with self.assertRaises(FileExistsError): write_json(path,{"accepted":False})
            self.assertTrue(read_json(path)["accepted"])


class JournalTests(unittest.TestCase):
    def test_restart_blocks_ambiguous_write_until_reconciled(self):
        with tempfile.TemporaryDirectory() as folder:
            project=Project(folder); project.init("test")
            script=Path(folder)/"change.py"; script.write_text("# test intent")
            op=project.begin("create",script)
            resumed=Project(folder)
            with self.assertRaises(RuntimeError): resumed.begin("retry",script)
            receipt=Path(folder)/"inspection.json"; write_json(receipt,{"native_objects":1})
            resumed.finish(op,receipt,reconciled=True)
            self.assertFalse(resumed.pending())
            with self.assertRaises(ValueError): resumed.finish(op,receipt)
            self.assertNotEqual(op,resumed.begin("next",script))

    def test_torn_journal_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            project=Project(folder); project.init("test")
            (Path(folder)/"operations.jsonl").write_text('{"event":"beg')
            with self.assertRaises(RuntimeError): project.status()


if __name__ == "__main__": unittest.main()
