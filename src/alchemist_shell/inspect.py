from typing import Any, List
from rich.console import Console
from rich.table import Table
from sqlalchemy import inspect
from sqlalchemy.engine import Row


def inspect_model(obj: Any, console: Console | None = None) -> None:
    console = console or Console()

    if not hasattr(obj, "__table__"):
        console.print("[bold red]Error:[/bold red] Object is not a SQLAlchemy model instance.")
        return

    table = Table(
        title=f"Inspecting {obj.__class__.__name__}",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Column", style="magenta")
    table.add_column("Value", style="white")

    state = inspect(obj)

    for column in obj.__table__.columns:
        name = column.name
        if name in state.unloaded:
            value = "[italic yellow]<Not Loaded>[/italic yellow]"
        else:
            value = str(getattr(obj, name))
        table.add_row(name, value)

    console.print(table)


def inspect_collection(collection: List[Any], console: Console | None = None) -> None:
    """
    Renders an array/list of SQLAlchemy models or Rows as a structured table matrix.
    """
    console = console or Console()

    if not collection:
        console.print("[italic yellow]⚡ Empty collection response.[/italic yellow]")
        return

    # Normalize Rows to straight model instances if applicable
    unpacked_items = []
    for item in collection:
        if isinstance(item, Row) and len(item) == 1 and hasattr(item[0], "__table__"):
            unpacked_items.append(item[0])
        else:
            unpacked_items.append(item)

    first_item = unpacked_items[0]
    if not hasattr(first_item, "__table__"):
        console.print(repr(collection))
        return

    model_cls = first_item.__class__
    table = Table(
        title=f"{model_cls.__name__} Dataset [dim]({len(unpacked_items)} entries)[/dim]",
        show_header=True,
        header_style="bold cyan",
    )

    # Use the model columns definitions to forge headers
    columns = [col.name for col in model_cls.__table__.columns]
    for col in columns:
        table.add_column(col, style="magenta" if col == "id" else "white")

    # Add records to the table rows
    for item in unpacked_items:
        if item.__class__ != model_cls:
            continue

        state = inspect(item)
        row_values = []
        for col in columns:
            if col in state.unloaded:
                row_values.append("[italic yellow]<Not Loaded>[/italic yellow]")
            else:
                row_values.append(str(getattr(item, col, "")))
        table.add_row(*row_values)

    console.print(table)
