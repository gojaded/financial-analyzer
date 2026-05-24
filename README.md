# Personal Finance Tracker

A terminal-based personal finance tracker built with Python and Rich.

## Features

- **Income & expense tracking** — log transactions with categories and dates
- **PDF statement import** — upload a bank statement PDF and categorize each transaction interactively
- **Budgets** — set monthly spending limits per category with over-budget warnings
- **Savings goals** — track progress toward financial goals with deadlines
- **Reports & charts** — monthly summaries, spending breakdowns, and 6-month income vs. expense bar charts

## Requirements

- Python 3.10+
- [pandas](https://pandas.pydata.org/) — data manipulation for reports
- [matplotlib](https://matplotlib.org/) — spending and income/expense charts
- [rich](https://github.com/Textualize/rich) — terminal UI, tables, and prompts
- [pdfplumber](https://github.com/jsvine/pdfplumber) — PDF text extraction for statement import

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

> **Windows users:** if you see Unicode errors in the terminal, run with UTF-8 mode:
> ```bash
> python -X utf8 main.py
> ```

## PDF Import

Choose **Import PDF statement** from the main menu and provide the path to your bank statement PDF. The app will detect transactions and walk you through categorizing each one as income or expense before saving them.

PDF parsing uses regex to find lines containing a date and a dollar amount. Results vary by bank format — all fields (date, description, amount) are editable before saving.
