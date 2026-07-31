import ast
import asyncio
from functools import wraps
from pathlib import Path
from typing import Any, Dict, Optional, Type

import nest_asyncio
import typer
from pygments.lexers.python import PythonLexer
from rich.console import Console
from rich.table import Table
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.styles import Style

nest_asyncio.apply()

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

from .discovery import discover_models
from .inspect import inspect_collection, inspect_model
from .session import get_session

console = Console()
app = typer.Typer(name="alchemist", help="The Modern SQLAlchemy Shell")

# Custom prompt_toolkit styling
ALCHEMIST_STYLE = Style.from_dict(
    {
        "prompt": "bold #98c379",
        "marker": "bold #61afef",
    }
)


def run_async(coro: Any) -> Any:
    """Executes a coroutine wrapped inside an explicit task to support Python 3.14+ timeouts."""
    loop = asyncio.get_event_loop()
    task = loop.create_task(coro)
    return loop.run_until_complete(task)


def make_sync_proxy(db: AsyncSession) -> Any:
    class AsyncProxy:
        def __init__(self, obj: AsyncSession):
            self._obj = obj

        def __getattr__(self, name: str) -> Any:
            attr = getattr(self._obj, name)
            if callable(attr):

                @wraps(attr)
                def wrapper(*args: Any, **kwargs: Any) -> Any:
                    result = attr(*args, **kwargs)
                    if asyncio.iscoroutine(result):
                        return run_async(result)
                    return result

                return wrapper
            return attr

    return AsyncProxy(db)


def display_result(result: Any) -> None:
    """Renders execution results using Alchemist rich inspectors or standard repr."""
    if result is None:
        return

    # 1. Collections of models or single-element rows (lists, tuples, ScalarResults, etc.)
    items = (
        list(result)
        if hasattr(result, "__iter__")
        and not isinstance(result, (str, bytes, dict, Row))
        and not hasattr(result, "__table__")
        else None
    )

    if items and len(items) > 0:
        first = items[0]
        is_model_row = isinstance(first, Row) and len(first) == 1 and hasattr(first[0], "__table__")
        if hasattr(first, "__table__") or is_model_row:
            inspect_collection(items)
            return

    # 2. SQLAlchemy Rows
    if isinstance(result, Row):
        if len(result) == 1 and hasattr(result[0], "__table__"):
            result = result[0]
        else:
            console.print(repr(result))
            return

    # 3. Single SQLAlchemy Model
    if hasattr(result, "__table__"):
        inspect_model(result)
        return

    # Default fallback
    console.print(result)


def execute_code(code_str: str, namespace: Dict[str, Any]) -> None:
    """Executes code strings with support for top-level await and expression evaluation."""
    code_str = code_str.strip()
    if not code_str:
        return

    try:
        # Try parsing as a single expression to print output automatically
        parsed = ast.parse(code_str, mode="eval")
        compiled = compile(parsed, "<alchemist>", "eval")
        result = eval(compiled, namespace)

        # If the result is a coroutine, resolve it inside a task
        if asyncio.iscoroutine(result):
            result = run_async(result)

        display_result(result)
        namespace["_"] = result

    except SyntaxError:
        # Fall back to executing multi-line statements / assignments
        try:
            if "await " in code_str:
                async_code = f"async def __alchemist_async_exec():\n" + "\n".join(
                    f"    {line}" for line in code_str.splitlines()
                )
                exec(async_code, namespace)
                run_async(namespace["__alchemist_async_exec"]())
                namespace.pop("__alchemist_async_exec", None)
            else:
                exec(code_str, namespace)
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")


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
    with console.status("[cyan]Scanning modules...[/cyan]"):
        models: Dict[str, Type[Any]] = discover_models(path)

    try:
        db, engine = get_session(db_url, env)
    except Exception as e:
        console.print(f"[bold red]Initialization Error:[/bold red] {e}")
        raise typer.Exit(1)

    is_async = isinstance(db, AsyncSession)
    mode_label = "ASYNC" if is_async else "SYNC"

    active_db = make_sync_proxy(db) if is_async else db

    namespace: Dict[str, Any] = {
        "db": active_db,
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

    # Print Header Table
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

    while True:
        try:
            user_input = session.prompt(prompt_message)
            execute_code(user_input, namespace)
        except KeyboardInterrupt, EOFError:
            console.print("\n[dim]Goodbye![/dim]")
            break


def main():
    app()


if __name__ == "__main__":
    main()
