import jedi
from prompt_toolkit.completion import Completer, Completion


class JediCompleter(Completer):
    """Native Jedi completer using the standalone `jedi` package."""

    def __init__(self, namespace: dict):
        self.namespace = namespace

    def get_completions(self, document, complete_event):
        try:
            interpreter = jedi.Interpreter(
                code=document.text,
                namespaces=[self.namespace],
            )
            for c in interpreter.complete(
                line=document.cursor_position_row + 1,
                column=document.cursor_position_col,
            ):
                yield Completion(
                    text=c.name,
                    start_position=-len(c.name_with_symbols) + len(c.complete or ""),
                    display=c.name,
                    display_meta=c.type,
                )
        except Exception:
            # Fall back quietly on syntax errors or incomplete expressions
            pass
