from typing import Any
from rich.console import Console
from rich.table import Table
from sqlalchemy import inspect

console = Console()

def inspect_model(obj: Any) -> None:
    """
    Pretty-prints the attributes and values of a SQLAlchemy model instance.
    """
    if not hasattr(obj, "__table__"):
        console.print("[bold red]Error:[/bold red] Object is not a SQLAlchemy model instance.")
        return

    table = Table(title=f"Inspecting {obj.__class__.__name__}", show_header=True, header_style="bold cyan")
    table.add_column("Column", style="magenta")
    table.add_column("Value", style="white")

    # Get state to check for unloaded attributes (to avoid lazy-load crashes)
    state = inspect(obj)
    
    for column in obj.__table__.columns:
        name = column.name
        # Check if the attribute is actually loaded in the current session
        if name in state.unloaded:
            value = "[italic yellow]<Not Loaded>[/italic yellow]"
        else:
            value = str(getattr(obj, name))
        table.add_row(name, value)

    console.print(table)