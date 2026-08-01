import ast
import asyncio
from pathlib import Path
from typing import Any, Dict, Optional, Type

import typer
from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.styles import Style
from pygments.lexers.python import PythonLexer
from rich.console import Console
from rich.table import Table
from sqlalchemy import (
    and_,
    asc,
    delete,
    desc,
    func,
    insert,
    not_,
    or_,
    select,
    text,
    update,
)
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from .discovery import discover_models
from .inspect import inspect_collection, inspect_model
from .session import get_session

console = Console()
app = typer.Typer(name="alchemist", help="The Modern SQLAlchemy Shell")

ALCHEMIST_STYLE = Style.from_dict(
    {
        "prompt": "bold #98c379",
        "marker": "bold #61afef",
    }
)


class ExitShellException(Exception):
    """Custom exception to trigger clean shell shutdown."""

    pass


def display_result(result: Any) -> None:
    """Renders execution results using Alchemist rich inspectors or standard repr."""
    if result is None:
        return

    items = (
        list(result)
        if hasattr(result, "__iter__")
        and not isinstance(result, (str, bytes, dict, Row))
        and not hasattr(result, "__table__")
        else None
    )
    if items and len(items) > 0:
        first = items[0]
        is_model_row = (
            isinstance(first, Row)
            and len(first) == 1
            and hasattr(first[0], "__table__")
        )
        if hasattr(first, "__table__") or is_model_row:
            inspect_collection(items)
            return

    if isinstance(result, Row):
        if len(result) == 1 and hasattr(result[0], "__table__"):
            result = result[0]
        else:
            console.print(repr(result))
            return

    if hasattr(result, "__table__"):
        inspect_model(result)
        return

    console.print(result)


async def execute_code_async(code_str: str, namespace: Dict[str, Any]) -> None:
    """Executes code strings inside an active asyncio Task context with proper namespace persistence."""
    code_str = code_str.strip()
    if not code_str:
        return

    # Direct exit shortcuts
    if code_str in ("exit", "exit()", "quit", "quit()"):
        raise ExitShellException()

    try:
        tree = ast.parse(code_str, mode="exec")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        return

    # Collect variable names target of assignment statements
    assigned_names = [
        target.id
        for stmt in tree.body
        if isinstance(stmt, ast.Assign)
        for target in stmt.targets
        if isinstance(target, ast.Name)
    ]

    has_expr = False
    if tree.body and isinstance(tree.body[-1], ast.Expr):
        last_expr = tree.body[-1]
        tree.body[-1] = ast.Assign(
            targets=[ast.Name(id="_alchemist_out", ctx=ast.Store())],
            value=last_expr.value,
        )
        ast.fix_missing_locations(tree)
        has_expr = True

    try:
        compiled = compile(
            tree, "<alchemist>", "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT
        )
        res = eval(compiled, namespace)

        if asyncio.iscoroutine(res):
            await res

        # Auto-await any coroutines assigned to variables
        for name in assigned_names:
            val = namespace.get(name)
            if asyncio.iscoroutine(val):
                namespace[name] = await val

        if has_expr and "_alchemist_out" in namespace:
            out = namespace.pop("_alchemist_out")
            if asyncio.iscoroutine(out):
                out = await out
            display_result(out)
            namespace["_"] = out
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")


async def run_shell_async(db_url: Optional[str], path: str, env: Optional[str]) -> None:
    with console.status("[cyan]Scanning modules...[/cyan]"):
        models: Dict[str, Type[Any]] = discover_models(path)

    try:
        db, engine = get_session(db_url, env)
    except Exception as e:
        console.print(f"[bold red]Initialization Error:[/bold red] {e}")
        raise typer.Exit(1)

    is_async = isinstance(db, AsyncSession)
    mode_label = "ASYNC" if is_async else "SYNC"

    namespace: Dict[str, Any] = {
        "db": db,
        "engine": engine,
        "inspect": inspect_model,
        "inspect_all": inspect_collection,
        "sql_on": lambda: engine.__setattr__("echo", True),
        "sql_off": lambda: engine.__setattr__("echo", False),
        "select": select,
        "insert": insert,
        "update": update,
        "delete": delete,
        "func": func,
        "and_": and_,
        "or_": or_,
        "not_": not_,
        "desc": desc,
        "asc": asc,
        "text": text,
        **models,
    }

    table = Table(show_header=True, header_style="bold blue", box=None)
    table.add_column("Model", style="magenta")
    table.add_column("Table", style="dim")
    for name, cls in models.items():
        table.add_row(name, str(getattr(cls, "__tablename__", "N/A")))

    console.print("\n[bold magenta]🔮 Alchemist Shell[/bold magenta]")
    console.print(table)

    db_name = engine.url.database or "memory"
    console.print(
        f"[bold cyan]Connected:[/bold cyan] [white]{db_name}[/white] [dim]({mode_label})[/dim]"
    )
    console.print(
        "[dim]Common imports pre-loaded. Type a model instance or list to view it.[/dim]\n"
    )

    history_file = Path.home() / ".alchemist_history"
    session = PromptSession(
        history=FileHistory(str(history_file)),
        auto_suggest=AutoSuggestFromHistory(),
        lexer=PygmentsLexer(PythonLexer),
        style=ALCHEMIST_STYLE,
    )
    prompt_message = HTML("<prompt>alchemist</prompt> <marker>❯</marker> ")

    try:
        while True:
            try:
                user_input = await session.prompt_async(prompt_message)
                await execute_code_async(user_input, namespace)
            except ExitShellException:
                console.print("[dim]Goodbye![/dim]")
                break
            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim]Goodbye![/dim]")
                break
    finally:
        if is_async:
            await db.close()
            if isinstance(engine, AsyncEngine):
                await engine.dispose()
        else:
            db.close()
            engine.dispose()

        current_task = asyncio.current_task()
        pending = [t for t in asyncio.all_tasks() if t is not current_task]
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)


def version_callback(value: bool):
    if value:
        from . import __version__

        console.print(f"Alchemist Shell v{__version__}")
        raise typer.Exit()


@app.callback()
def common(
    version: Optional[bool] = typer.Option(
        None, "--version", "-v", callback=version_callback, is_eager=True
    ),
):
    """The Modern SQLAlchemy Shell."""
    pass


@app.command()
def shell(
    db_url: Optional[str] = typer.Option(None, "--db-url", "-u"),
    path: str = typer.Option(".", "--path", "-p"),
    env: Optional[str] = typer.Option(None, "--env", "-e"),
) -> None:
    asyncio.run(run_shell_async(db_url, path, env))


def main():
    app()


if __name__ == "__main__":
    main()
