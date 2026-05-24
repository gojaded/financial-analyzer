from datetime import datetime
from . import storage

EXPENSE_CATEGORIES = [
    "Housing", "Food", "Transport", "Utilities", "Healthcare",
    "Entertainment", "Clothing", "Education", "Savings", "Other"
]
INCOME_CATEGORIES = ["Salary", "Freelance", "Investment", "Gift", "Other"]


def add_transaction(tx_type: str, amount: float, category: str,
                    description: str, date: str | None = None) -> dict:
    transactions = storage.load_transactions()
    tx = {
        "id": _next_id(transactions),
        "type": tx_type,          # "income" or "expense"
        "amount": round(amount, 2),
        "category": category,
        "description": description,
        "date": date or datetime.today().strftime("%Y-%m-%d"),
    }
    transactions.append(tx)
    storage.save_transactions(transactions)
    return tx


def get_transactions(tx_type: str | None = None,
                     month: str | None = None) -> list[dict]:
    """Return transactions, optionally filtered by type and/or YYYY-MM month."""
    txs = storage.load_transactions()
    if tx_type:
        txs = [t for t in txs if t["type"] == tx_type]
    if month:
        txs = [t for t in txs if t["date"].startswith(month)]
    return txs


def delete_transaction(tx_id: int) -> bool:
    transactions = storage.load_transactions()
    new = [t for t in transactions if t["id"] != tx_id]
    if len(new) == len(transactions):
        return False
    storage.save_transactions(new)
    return True


def _next_id(transactions: list[dict]) -> int:
    return max((t["id"] for t in transactions), default=0) + 1
