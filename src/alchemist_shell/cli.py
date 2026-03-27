import asyncio
import nest_asyncio
from pathlib import Path
import typer
from functools import wraps
from typing import Optional, Dict, Any, Type
from IPython.terminal.embed import InteractiveShellEmbed
from IPython.terminal.prompts import Prompts
from pygments.token import Token 
from traitlets.config import Config
from rich.console import Console
from rich.table import Table
from sqlalchemy.ext.asyncio import AsyncSession

nest_asyncio.apply()

from sqlalchemy import (
    select, insert, update, delete, 
    func, and_, or_, not_, desc, asc, text
)

from .discovery import discover_models
from .inspect import inspect_model
from .session import get_session

console = Console()
app = typer.Typer(name="alchemist", help="The Modern SQLAlchemy Shell")

class AlchemistPrompts(Prompts):
    def in_prompt_tokens(self):
        return [(Token.Prompt, "alchemist "), (Token.PromptMarker, "❯ ")]
    def out_prompt_tokens(self):
        return []
    def continuation_prompt_tokens(self, width=None):
        return [(Token.Prompt, "          ❯ ")]

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
                        try:
                            asyncio.get_running_loop()
                            return result
                        except RuntimeError:
                            return asyncio.get_event_loop().run_until_complete(result)
                    return result
                return wrapper
            return attr
    return AsyncProxy(db)

def version_callback(value: bool):
    if value:
        from . import __version__
        console.print(f"Alchemist Shell v{__version__}")
        raise typer.Exit()

@app.callback()
def common(
    version: Optional[bool] = typer.Option(None, "--version", "-v", callback=version_callback, is_eager=True)
):
    """The Modern SQLAlchemy Shell."""
    pass

@app.command()
def shell(
    db_url: Optional[str] = typer.Option(None, "--db-url", "-u"),
    path: str = typer.Option(".", "--path", "-p"),
    env: Optional[str] = typer.Option(None, "--env", "-e")
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
    
    cfg = Config()
    cfg.InteractiveShell.autoawait = True
    cfg.InteractiveShell.display_banner = False
    cfg.InteractiveShell.quiet = True
    cfg.TerminalInteractiveShell.display_completions_help = False
    cfg.TerminalInteractiveShell.prompts_class = AlchemistPrompts
    cfg.TerminalInteractiveShell.term_title = False
    cfg.IPCompleter.greedy = True
    cfg.TerminalInteractiveShell.autosuggestions_provider = 'NavigableAutoSuggestFromHistory'
    cfg.IPCompleter.use_jedi = True

    active_db = make_sync_proxy(db) if is_async else db

    namespace: Dict[str, Any] = {
        "db": active_db, 
        "engine": engine, 
        "inspect": inspect_model,
        "sql_on": lambda: engine.__setattr__('echo', True),
        "sql_off": lambda: engine.__setattr__('echo', False),
        "select": select, "insert": insert, "update": update,
        "delete": delete, "func": func, "and_": and_,
        "or_": or_, "not_": not_, "desc": desc,
        "asc": asc, "text": text,
        **models
    }

    ipshell = InteractiveShellEmbed(config=cfg, user_ns=namespace, colors="neutral", banner1="")
    
    # Auto-inspection formatter
    def alchemist_display_formatter(obj, p, cycle):
        if cycle: return p.text(repr(obj))
        if hasattr(obj, "__table__"):
            inspect_model(obj)
        else:
            p.text(repr(obj))

    ipshell.display_formatter.formatters['text/plain'].for_type(object, alchemist_display_formatter)

    table = Table(show_header=True, header_style="bold blue", box=None)
    table.add_column("Model", style="magenta")
    table.add_column("Table", style="dim")
    for name, cls in models.items():
        table.add_row(name, str(getattr(cls, "__tablename__", "N/A")))

    console.print("\n[bold magenta]🔮 Alchemist Shell[/bold magenta]")
    console.print(table)
    db_name = engine.url.database or "memory"
    console.print(f"[bold cyan]Connected:[/bold cyan] [white]{db_name}[/white] [dim]({mode_label})[/dim]")
    console.print("[dim]Common imports pre-loaded. Type a model instance to view it.[/dim]\n")

    history_file = Path.home() / ".alchemist_history"
    if not history_file.exists(): history_file.touch()
    ipshell.init_history(str(history_file))

    ipshell()

def main():
    app()

if __name__ == "__main__":
    main()