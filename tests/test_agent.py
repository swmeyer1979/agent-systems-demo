from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_systems_proof.agent import ResearchAgent, SimulatedInterruption
from agent_systems_proof.evaluator import Evaluator
from agent_systems_proof.paths import DEFAULT_EVAL_FIXTURE, DEFAULT_SOURCE_DIR
from agent_systems_proof.storage import RunStore
from agent_systems_proof.tools import build_registry, read_source, write_report
from agent_systems_proof.tracing import JsonlTracer


class AgentProofTests(unittest.TestCase):
    def test_agent_runs_and_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = RunStore(root / "runs.db")
            agent = ResearchAgent(
                store=store,
                tools=build_registry(DEFAULT_SOURCE_DIR, root / "workspace"),
                tracer=JsonlTracer(root / "traces", "unit-demo"),
                workspace_dir=root / "workspace",
            )
            result = agent.run(
                run_id="unit-demo",
                question="What makes agent systems production-ready?",
                resume=False,
            )
            self.assertEqual(result.status, "completed")
            self.assertIsNotNone(result.output_path)
            report = Path(result.output_path or "").read_text(encoding="utf-8")
            self.assertIn("Durability", report)
            self.assertIn("[S1]", report)
            self.assertEqual(store.list_step_names("unit-demo")[-1], "write_report")

    def test_resume_after_interruption(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = RunStore(root / "runs.db")
            first_agent = ResearchAgent(
                store=store,
                tools=build_registry(DEFAULT_SOURCE_DIR, root / "workspace"),
                tracer=JsonlTracer(root / "traces", "unit-resume"),
                workspace_dir=root / "workspace",
            )
            with self.assertRaises(SimulatedInterruption):
                first_agent.run(
                    run_id="unit-resume",
                    question="How should a long-running agent resume after a process stop?",
                    stop_after_step=3,
                )
            interrupted = store.get_run("unit-resume")
            self.assertIsNotNone(interrupted)
            self.assertEqual(interrupted.status, "interrupted")

            second_agent = ResearchAgent(
                store=store,
                tools=build_registry(DEFAULT_SOURCE_DIR, root / "workspace"),
                tracer=JsonlTracer(root / "traces", "unit-resume"),
                workspace_dir=root / "workspace",
            )
            result = second_agent.run(run_id="unit-resume", question=None, resume=True)
            self.assertEqual(result.status, "completed")
            self.assertEqual(store.get_run("unit-resume").status, "completed")  # type: ignore[union-attr]

    def test_eval_suite_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = RunStore(root / "runs.db")
            summary = Evaluator(
                fixture_path=DEFAULT_EVAL_FIXTURE,
                source_dir=DEFAULT_SOURCE_DIR,
                workspace_dir=root / "workspace",
                trace_dir=root / "traces",
                store=store,
                results_dir=root / "eval_results",
            ).run()
            self.assertTrue(summary["passed"], summary)

    def test_file_outputs_reject_path_traversal_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                JsonlTracer(root / "traces", "../escaped")
            with self.assertRaises(ValueError):
                write_report(root / "workspace", "../escaped", "nope")

    def test_read_source_rejects_path_traversal_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_dir = root / "docs" / "sources"
            source_dir.mkdir(parents=True)
            outside = root / "docs" / "outside.md"
            outside.write_text("# Outside\n\n- secret\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                read_source(source_dir, "../outside")


if __name__ == "__main__":
    unittest.main()
