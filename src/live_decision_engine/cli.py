from pathlib import Path

import typer

from live_decision_engine.ingestion.adapter import validate_session
from live_decision_engine.pipeline import run_pipeline

app = typer.Typer(add_completion=False)


@app.command()
def validate(session_dir: Path):
    """校验 session 目录的四件套输入。"""
    errors = validate_session(session_dir)
    if errors:
        for e in errors:
            typer.echo(f"[FAIL] {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"[OK] {session_dir} 输入合法")


@app.command()
def run(
    session_dir: Path,
    from_stage: str | None = typer.Option(None, "--from", help="从某层开始重跑：01/02/03/04"),
    llm: bool = typer.Option(False, "--llm", help="启用 LLM 增强（需配置 LDE_LLM_* 环境变量）"),
):
    """跑完一场直播的完整决策管线。"""
    try:
        result = run_pipeline(session_dir, from_stage=from_stage, llm=llm)
    except Exception as e:
        typer.echo(f"[ERROR] {e}", err=True)
        raise typer.Exit(1)

    typer.echo(result["summary"])
    typer.echo(
        f"总计: {result['counts']['cards']} 张卡片, "
        f"平均分 {result['counts']['score_avg']}"
    )
