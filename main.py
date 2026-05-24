"""Personal Finance Tracker — interactive CLI."""
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import box
from rich.panel import Panel
from rich.text import Text

from finance import tracker, budget as budget_mod, goals as goals_mod, reports
from finance import pdf_import

console = Console()
TODAY = datetime.today().strftime("%Y-%m")


# ─── helpers ──────────────────────────────────────────────────────────────────

def fmt_money(amount: float) -> str:
    return f"${amount:,.2f}"


def pick(prompt: str, options: list[str]) -> str:
    console.print(f"\n[bold]{prompt}[/bold]")
    for i, opt in enumerate(options, 1):
        console.print(f"  [cyan]{i}[/cyan]. {opt}")
    while True:
        raw = Prompt.ask("Choice")
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        console.print("[red]Invalid choice.[/red]")


def ask_amount(prompt: str = "Amount") -> float:
    while True:
        raw = Prompt.ask(prompt)
        try:
            val = float(raw.replace("$", "").replace(",", ""))
            if val > 0:
                return val
        except ValueError:
            pass
        console.print("[red]Enter a positive number.[/red]")


def ask_date(prompt: str = "Date (YYYY-MM-DD, blank = today)") -> str:
    raw = Prompt.ask(prompt, default="")
    if not raw:
        return datetime.today().strftime("%Y-%m-%d")
    try:
        datetime.strptime(raw, "%Y-%m-%d")
        return raw
    except ValueError:
        console.print("[yellow]Invalid date, using today.[/yellow]")
        return datetime.today().strftime("%Y-%m-%d")


# ─── transactions ──────────────────────────────────────────────────────────────

def add_income():
    console.print(Panel("[bold green]Add Income[/bold green]"))
    amount = ask_amount("Amount ($)")
    category = pick("Category", tracker.INCOME_CATEGORIES)
    description = Prompt.ask("Description")
    date = ask_date()
    tx = tracker.add_transaction("income", amount, category, description, date)
    console.print(f"\n[green]✓ Income #{tx['id']} added: {fmt_money(tx['amount'])} ({category})[/green]")


def add_expense():
    console.print(Panel("[bold red]Add Expense[/bold red]"))
    amount = ask_amount("Amount ($)")
    category = pick("Category", tracker.EXPENSE_CATEGORIES)
    description = Prompt.ask("Description")
    date = ask_date()
    tx = tracker.add_transaction("expense", amount, category, description, date)
    console.print(f"\n[red]✓ Expense #{tx['id']} added: {fmt_money(tx['amount'])} ({category})[/red]")
    _warn_budget(category)


def _warn_budget(category: str):
    status = budget_mod.get_budget_status(TODAY)
    for row in status:
        if row["category"] == category and row["over"]:
            console.print(
                f"[bold yellow]⚠  You are over budget for {category}! "
                f"Spent {fmt_money(row['spent'])} / limit {fmt_money(row['limit'])}[/bold yellow]"
            )


def list_transactions():
    tx_type = pick("Show", ["All", "Income only", "Expenses only"])
    month_filter = Prompt.ask("Filter by month (YYYY-MM, blank = all)", default="")

    type_map = {"All": None, "Income only": "income", "Expenses only": "expense"}
    txs = tracker.get_transactions(
        tx_type=type_map[tx_type],
        month=month_filter or None,
    )

    if not txs:
        console.print("[yellow]No transactions found.[/yellow]")
        return

    table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold")
    table.add_column("ID", justify="right", style="dim")
    table.add_column("Date")
    table.add_column("Type")
    table.add_column("Category")
    table.add_column("Description")
    table.add_column("Amount", justify="right")

    for t in sorted(txs, key=lambda x: x["date"], reverse=True):
        color = "green" if t["type"] == "income" else "red"
        table.add_row(
            str(t["id"]),
            t["date"],
            f"[{color}]{t['type']}[/{color}]",
            t["category"],
            t["description"],
            f"[{color}]{fmt_money(t['amount'])}[/{color}]",
        )
    console.print(table)


def delete_transaction():
    tx_id = Prompt.ask("Transaction ID to delete")
    if not tx_id.isdigit():
        console.print("[red]Invalid ID.[/red]")
        return
    if Confirm.ask(f"Delete transaction #{tx_id}?"):
        ok = tracker.delete_transaction(int(tx_id))
        console.print("[green]Deleted.[/green]" if ok else "[red]Not found.[/red]")


# ─── budgets ──────────────────────────────────────────────────────────────────

def manage_budgets():
    action = pick("Budgets", ["View status", "Set budget", "Remove budget"])
    if action == "View status":
        month = Prompt.ask("Month (YYYY-MM)", default=TODAY)
        rows = budget_mod.get_budget_status(month)
        if not rows:
            console.print("[yellow]No budget data.[/yellow]")
            return
        table = Table(box=box.SIMPLE_HEAD, header_style="bold", title=f"Budget Status — {month}")
        table.add_column("Category")
        table.add_column("Spent", justify="right")
        table.add_column("Limit", justify="right")
        table.add_column("Remaining", justify="right")
        table.add_column("Status")
        for row in rows:
            remaining = fmt_money(row["remaining"]) if row["remaining"] is not None else "—"
            limit = fmt_money(row["limit"]) if row["limit"] is not None else "—"
            status = "[red]OVER[/red]" if row["over"] else ("[green]OK[/green]" if row["limit"] else "[dim]no limit[/dim]")
            table.add_row(row["category"], fmt_money(row["spent"]), limit, remaining, status)
        console.print(table)

    elif action == "Set budget":
        category = pick("Category", tracker.EXPENSE_CATEGORIES)
        limit = ask_amount("Monthly limit ($)")
        budget_mod.set_budget(category, limit)
        console.print(f"[green]✓ Budget set: {category} → {fmt_money(limit)}/month[/green]")

    elif action == "Remove budget":
        budgets = budget_mod.get_budgets()
        if not budgets:
            console.print("[yellow]No budgets set.[/yellow]")
            return
        category = pick("Remove which?", list(budgets.keys()))
        if Confirm.ask(f"Remove budget for {category}?"):
            budget_mod.delete_budget(category)
            console.print("[green]Removed.[/green]")


# ─── goals ────────────────────────────────────────────────────────────────────

def manage_goals():
    action = pick("Goals", ["View goals", "Add goal", "Contribute to goal", "Delete goal"])

    if action == "View goals":
        goal_list = goals_mod.get_goals()
        if not goal_list:
            console.print("[yellow]No goals yet.[/yellow]")
            return
        table = Table(box=box.SIMPLE_HEAD, header_style="bold", title="Savings Goals")
        table.add_column("ID", justify="right", style="dim")
        table.add_column("Name")
        table.add_column("Saved", justify="right")
        table.add_column("Target", justify="right")
        table.add_column("Progress")
        table.add_column("Deadline")
        table.add_column("Days left", justify="right")
        for g in goal_list:
            pct = goals_mod.goal_progress(g)
            bar = _progress_bar(pct)
            days = goals_mod.days_remaining(g)
            table.add_row(
                str(g["id"]),
                g["name"],
                fmt_money(g["saved"]),
                fmt_money(g["target"]),
                f"{bar} {pct}%",
                g["deadline"] or "—",
                str(days) if days is not None else "—",
            )
        console.print(table)

    elif action == "Add goal":
        name = Prompt.ask("Goal name")
        target = ask_amount("Target amount ($)")
        saved = ask_amount("Already saved ($) (0 if starting fresh)") if Confirm.ask("Add initial savings?") else 0.0
        deadline = Prompt.ask("Deadline (YYYY-MM-DD, blank = none)", default="") or None
        g = goals_mod.add_goal(name, target, deadline, saved)
        console.print(f"[green]✓ Goal '{g['name']}' created (target {fmt_money(g['target'])})[/green]")

    elif action == "Contribute to goal":
        goal_list = goals_mod.get_goals()
        if not goal_list:
            console.print("[yellow]No goals yet.[/yellow]")
            return
        options = [f"#{g['id']} {g['name']}" for g in goal_list]
        choice = pick("Contribute to", options)
        goal_id = int(choice.split()[0].lstrip("#"))
        amount = ask_amount("Amount to add ($)")
        updated = goals_mod.contribute(goal_id, amount)
        if updated:
            pct = goals_mod.goal_progress(updated)
            console.print(
                f"[green]✓ Added {fmt_money(amount)} → '{updated['name']}' "
                f"({fmt_money(updated['saved'])} / {fmt_money(updated['target'])}, {pct}%)[/green]"
            )

    elif action == "Delete goal":
        goal_list = goals_mod.get_goals()
        if not goal_list:
            console.print("[yellow]No goals.[/yellow]")
            return
        options = [f"#{g['id']} {g['name']}" for g in goal_list]
        choice = pick("Delete which?", options)
        goal_id = int(choice.split()[0].lstrip("#"))
        if Confirm.ask(f"Delete goal?"):
            goals_mod.delete_goal(goal_id)
            console.print("[green]Deleted.[/green]")


def _progress_bar(pct: float, width: int = 10) -> str:
    filled = int(pct / 100 * width)
    bar = "█" * filled + "░" * (width - filled)
    color = "green" if pct >= 100 else ("yellow" if pct >= 50 else "red")
    return f"[{color}]{bar}[/{color}]"


# ─── reports ──────────────────────────────────────────────────────────────────

def show_reports():
    action = pick("Reports", [
        "Monthly summary",
        "Spending pie chart",
        "Income vs Expenses (6-month bar chart)",
    ])

    if action == "Monthly summary":
        month = Prompt.ask("Month (YYYY-MM)", default=TODAY)
        s = reports.monthly_summary(month)
        console.print(Panel(
            f"[bold]Month:[/bold]         {s['month']}\n"
            f"[bold green]Income:[/bold green]        {fmt_money(s['income'])}\n"
            f"[bold red]Expenses:[/bold red]       {fmt_money(s['expenses'])}\n"
            f"[bold]Net:[/bold]           {fmt_money(s['net'])}\n"
            f"[bold]Savings rate:[/bold]  {s['savings_rate']}%",
            title="Monthly Summary", border_style="blue"
        ))
        if s["expense_by_category"]:
            table = Table(box=box.SIMPLE, title="Expenses by Category")
            table.add_column("Category")
            table.add_column("Amount", justify="right")
            for cat, amt in s["expense_by_category"].items():
                table.add_row(cat, fmt_money(amt))
            console.print(table)

    elif action == "Spending pie chart":
        month = Prompt.ask("Month (YYYY-MM)", default=TODAY)
        if not reports.show_spending_chart(month):
            console.print("[yellow]No expense data for that month (or matplotlib not installed).[/yellow]")

    elif action == "Income vs Expenses (6-month bar chart)":
        if not reports.show_income_vs_expense_chart(6):
            console.print("[yellow]Could not generate chart (matplotlib not installed or no data).[/yellow]")


# ─── pdf import ───────────────────────────────────────────────────────────────

def import_pdf_statement():
    if not pdf_import.PDF_AVAILABLE:
        console.print("[red]pdfplumber is not installed.[/red]")
        console.print("[dim]Run:  pip install pdfplumber[/dim]")
        return

    path = Prompt.ask("Path to PDF statement")
    if not Path(path).exists():
        console.print("[red]File not found.[/red]")
        return

    with console.status("[cyan]Extracting transactions from PDF…[/cyan]"):
        raw_txs = pdf_import.extract_transactions(path)

    if not raw_txs:
        console.print("[yellow]No transactions detected in that PDF.[/yellow]")
        return

    table = Table(box=box.SIMPLE_HEAD, title=f"Found {len(raw_txs)} potential transactions")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Raw date")
    table.add_column("Description")
    table.add_column("Amount", justify="right")
    for i, tx in enumerate(raw_txs, 1):
        table.add_row(str(i), tx["raw_date"], tx["description"][:55], fmt_money(tx["amount"]))
    console.print(table)

    if not Confirm.ask(f"Categorize these {len(raw_txs)} transaction(s) now?"):
        return

    saved = 0
    for i, tx in enumerate(raw_txs, 1):
        console.print(
            f"\n[bold]Transaction {i}/{len(raw_txs)}[/bold]  "
            f"[cyan]{tx['raw_date']}[/cyan]  "
            f"{tx['description'][:60]}  [bold]{fmt_money(tx['amount'])}[/bold]"
        )

        action = pick("How to record this?", ["Expense", "Income", "Skip"])
        if action == "Skip":
            continue

        tx_type = action.lower()
        categories = tracker.EXPENSE_CATEGORIES if tx_type == "expense" else tracker.INCOME_CATEGORIES
        category = pick("Category", categories)

        description = Prompt.ask("Description", default=tx["description"][:80])
        suggested_date = pdf_import.normalize_date(tx["raw_date"])
        date = Prompt.ask("Date (YYYY-MM-DD)", default=suggested_date)
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            console.print("[yellow]Invalid date format, using suggested date.[/yellow]")
            date = suggested_date

        amount_str = Prompt.ask("Amount ($)", default=f"{tx['amount']:.2f}")
        try:
            amount = float(amount_str.replace("$", "").replace(",", ""))
            if amount <= 0:
                raise ValueError
        except ValueError:
            console.print("[yellow]Invalid amount, using extracted value.[/yellow]")
            amount = tx["amount"]

        tracker.add_transaction(tx_type, amount, category, description, date)
        saved += 1
        color = "red" if tx_type == "expense" else "green"
        console.print(f"[{color}]✓ Saved as {tx_type}: {category}[/{color}]")
        if tx_type == "expense":
            _warn_budget(category)

    console.print(f"\n[bold green]✓ Imported {saved} transaction(s) from PDF.[/bold green]")


# ─── main menu ────────────────────────────────────────────────────────────────

MENU = [
    ("Add income",           add_income),
    ("Add expense",          add_expense),
    ("Import PDF statement", import_pdf_statement),
    ("View transactions",    list_transactions),
    ("Delete transaction",   delete_transaction),
    ("Budgets",              manage_budgets),
    ("Savings goals",        manage_goals),
    ("Reports & charts",     show_reports),
    ("Quit",                 None),
]


def main():
    console.print(Panel(
        Text("Personal Finance Tracker", justify="center", style="bold cyan"),
        subtitle="Powered by Python + Rich",
    ))

    while True:
        console.print()
        table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
        table.add_column(justify="right", style="bold cyan")
        table.add_column()
        for i, (label, _) in enumerate(MENU, 1):
            table.add_row(str(i), label)
        console.print(table)

        raw = Prompt.ask("\n[bold]Choose[/bold]")
        if not raw.isdigit() or not (1 <= int(raw) <= len(MENU)):
            console.print("[red]Invalid.[/red]")
            continue

        label, fn = MENU[int(raw) - 1]
        if fn is None:
            console.print("[dim]Goodbye.[/dim]")
            break
        try:
            fn()
        except KeyboardInterrupt:
            console.print("\n[dim](cancelled)[/dim]")


if __name__ == "__main__":
    main()
