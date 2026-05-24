from . import storage, tracker


def set_budget(category: str, monthly_limit: float) -> None:
    budgets = storage.load_budgets()
    budgets[category] = round(monthly_limit, 2)
    storage.save_budgets(budgets)


def get_budgets() -> dict:
    return storage.load_budgets()


def get_budget_status(month: str) -> list[dict]:
    """
    Returns per-category spend vs budget for the given YYYY-MM month.
    Categories with no budget are still included if they have spending.
    """
    budgets = storage.load_budgets()
    expenses = tracker.get_transactions(tx_type="expense", month=month)

    spent_by_category: dict[str, float] = {}
    for tx in expenses:
        cat = tx["category"]
        spent_by_category[cat] = spent_by_category.get(cat, 0) + tx["amount"]

    all_categories = set(budgets) | set(spent_by_category)
    rows = []
    for cat in sorted(all_categories):
        spent = spent_by_category.get(cat, 0.0)
        limit = budgets.get(cat)
        rows.append({
            "category": cat,
            "spent": round(spent, 2),
            "limit": limit,
            "over": limit is not None and spent > limit,
            "remaining": round(limit - spent, 2) if limit is not None else None,
        })
    return rows


def delete_budget(category: str) -> bool:
    budgets = storage.load_budgets()
    if category not in budgets:
        return False
    del budgets[category]
    storage.save_budgets(budgets)
    return True
