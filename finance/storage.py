import json
import os
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

TRANSACTIONS_FILE = DATA_DIR / "transactions.json"
BUDGETS_FILE = DATA_DIR / "budgets.json"
GOALS_FILE = DATA_DIR / "goals.json"


def _load(path: Path) -> list | dict:
    if not path.exists():
        return [] if path in (TRANSACTIONS_FILE, GOALS_FILE) else {}
    with open(path) as f:
        return json.load(f)


def _save(path: Path, data) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def load_transactions() -> list[dict]:
    return _load(TRANSACTIONS_FILE)


def save_transactions(transactions: list[dict]) -> None:
    _save(TRANSACTIONS_FILE, transactions)


def load_budgets() -> dict:
    return _load(BUDGETS_FILE)


def save_budgets(budgets: dict) -> None:
    _save(BUDGETS_FILE, budgets)


def load_goals() -> list[dict]:
    return _load(GOALS_FILE)


def save_goals(goals: list[dict]) -> None:
    _save(GOALS_FILE, goals)
