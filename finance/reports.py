from datetime import datetime
from . import tracker, budget as budget_mod, goals as goals_mod

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


def monthly_summary(month: str | None = None) -> dict:
    """Return income, expenses, net, savings rate for a YYYY-MM month."""
    month = month or datetime.today().strftime("%Y-%m")
    income_txs = tracker.get_transactions(tx_type="income", month=month)
    expense_txs = tracker.get_transactions(tx_type="expense", month=month)

    total_income = sum(t["amount"] for t in income_txs)
    total_expenses = sum(t["amount"] for t in expense_txs)
    net = total_income - total_expenses
    savings_rate = (net / total_income * 100) if total_income > 0 else 0.0

    expense_by_cat: dict[str, float] = {}
    for t in expense_txs:
        cat = t["category"]
        expense_by_cat[cat] = expense_by_cat.get(cat, 0) + t["amount"]

    return {
        "month": month,
        "income": round(total_income, 2),
        "expenses": round(total_expenses, 2),
        "net": round(net, 2),
        "savings_rate": round(savings_rate, 1),
        "expense_by_category": {k: round(v, 2) for k, v in sorted(
            expense_by_cat.items(), key=lambda x: -x[1])},
    }


def show_spending_chart(month: str | None = None) -> bool:
    """Pie chart of expenses by category. Returns False if matplotlib missing."""
    if not HAS_MPL:
        return False
    month = month or datetime.today().strftime("%Y-%m")
    summary = monthly_summary(month)
    data = summary["expense_by_category"]
    if not data:
        return False

    labels = list(data.keys())
    values = list(data.values())

    fig, ax = plt.subplots(figsize=(7, 5))
    wedges, texts, autotexts = ax.pie(
        values, labels=labels, autopct="%1.1f%%", startangle=140
    )
    ax.set_title(f"Spending by Category — {month}")
    plt.tight_layout()
    plt.show()
    return True


def show_income_vs_expense_chart(months: int = 6) -> bool:
    """Bar chart comparing income vs expenses over the last N months."""
    if not HAS_MPL:
        return False

    from datetime import date
    import calendar

    today = date.today()
    month_labels, incomes, expenses = [], [], []
    for i in range(months - 1, -1, -1):
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        label = f"{year}-{month:02d}"
        s = monthly_summary(label)
        month_labels.append(label)
        incomes.append(s["income"])
        expenses.append(s["expenses"])

    x = range(len(month_labels))
    width = 0.35

    fig, ax = plt.subplots(figsize=(9, 5))
    bars_i = ax.bar([v - width / 2 for v in x], incomes, width, label="Income", color="#4CAF50")
    bars_e = ax.bar([v + width / 2 for v in x], expenses, width, label="Expenses", color="#F44336")
    ax.set_xticks(list(x))
    ax.set_xticklabels(month_labels, rotation=30, ha="right")
    ax.set_ylabel("Amount ($)")
    ax.set_title(f"Income vs Expenses — Last {months} Months")
    ax.legend()
    plt.tight_layout()
    plt.show()
    return True
