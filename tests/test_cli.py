import shutil
from pathlib import Path

from typer.testing import CliRunner

from live_decision_engine.cli import app

FIXTURE = Path(__file__).parent / "fixtures" / "session_mini"

runner = CliRunner()


def test_validate_valid_fixture_exits_zero():
    result = runner.invoke(app, ["validate", str(FIXTURE)])
    assert result.exit_code == 0


def test_run_valid_fixture_exits_zero(tmp_path):
    # 拷到 tmp 目录，避免污染 fixture 的 output/
    session = tmp_path / "session_mini"
    shutil.copytree(FIXTURE, session)
    result = runner.invoke(app, ["run", str(session)])
    assert result.exit_code == 0
    assert (session / "output" / "summary.txt").exists()
