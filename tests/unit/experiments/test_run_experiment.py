"""
Unit tests for ``dev-tools/experiments/runners/run_experiment.py``.

``conftest.py`` puts ``dev-tools/experiments/`` on ``sys.path`` so
``runners`` imports as a normal package.
"""

import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from runners import run_experiment

pytestmark = pytest.mark.unit


class TestCreateExperimentStructureShutilShadowing:
    """``create_experiment_structure`` must not shadow module-level shutil.

    Python's scoping rule treats any name assigned in a function
    (including via ``import``) as local for the entire function. A
    previous version of the runner had ``import shutil`` inside a
    conditional block, which made the earlier ``shutil.copy`` call at
    the top of the same function raise ``UnboundLocalError`` whenever
    the function executed at all — fully breaking ``--init`` mode.

    Regression: when a stale ``.git`` exists at the experiment root,
    the function must clean it up using the module-level ``shutil`` and
    keep going, not crash before getting there.
    """

    def test_init_succeeds_when_stale_git_present(
        self,
        tmp_path: Path,
    ) -> None:
        """A pre-existing ``.git`` at the experiment root does not crash --init.

        Builds an experiment directory containing a stale ``.git`` so
        the function's cleanup branch fires, supplies a templates dir
        with the bundled config, and stubs the ``git`` / ``claude``
        subprocess calls because they would otherwise reach out to
        external binaries the CI runner may not have.
        """
        # Arrange — stale .git that must be removed by shutil.rmtree.
        experiment_dir = tmp_path / "experiment"
        experiment_dir.mkdir()
        stale_git = experiment_dir / ".git"
        stale_git.mkdir()
        (stale_git / "HEAD").write_text("ref: refs/heads/main\n")

        # Templates dir with a minimal config.yaml.template the function
        # copies in.
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "config.yaml.template").write_text(
            "project_name: 'test'\nagents: []\n"
        )

        # Stub subprocess.run so ``git init`` / ``claude mcp list`` are
        # no-ops on hosts that lack those binaries.
        with patch.object(
            (
                run_experiment.subprocess
                if hasattr(run_experiment, "subprocess")
                else subprocess
            ),
            "run",
            return_value=type("R", (), {"returncode": 0, "stdout": "marcus"})(),
        ):
            # Act — must not raise UnboundLocalError on shutil.
            run_experiment.create_experiment_structure(experiment_dir, templates_dir)

        # Assert — stale .git was actually removed and the templated
        # config.yaml landed in place.
        assert not stale_git.exists(), "Stale .git should have been rmtree'd"
        assert (
            experiment_dir / "config.yaml"
        ).exists(), "config.yaml should have been copied from the template"
