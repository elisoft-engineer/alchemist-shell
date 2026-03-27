import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

def find_and_load_env(env_file: Optional[str] = None) -> None:
    """Searches for and loads the appropriate .env file."""
    if env_file and Path(env_file).exists():
        load_dotenv(env_file)
        return

    # Priority: .env.dev -> .env.local -> .env
    targets: list[str] = [".env.dev", ".env.local", ".env"]
    for target in targets:
        if Path(target).exists():
            load_dotenv(target)
            break