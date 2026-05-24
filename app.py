"""Streamlit GUI for the Personal Finance Tracker."""
import os
import tempfile
from datetime import datetime, date

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from finance import tracker, budget as budget_mod, goals as goals_mod, reports
from finance import pdf_import

st.set_page_config(
    page_title="Personal Finance Tracker",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

TODAY = datetime.today().strftime("%Y-%m")
ALL_CATEGORIES = list(dict.fromkeys(tracker.INCOME_CATEGORIES + tracker.EXPENSE_CATEGORIES))


def fmt(amount: float) -> str:
    return f"${amount:,.2f}"


def _spending_fig(month: str):
    data = reports.monthly_summary(month)["expense_by_category"]
    if not data:
        return None
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.pie(list(data.values()), labels=list(data.keys()), autopct="%1.1f%%", startangle=140)
    ax.set_title(f"Spending by Category — {month}")
    plt.tight_layout()
    return fig


def _trend_fig(months: int = 6):
    today = date.today()
    labels, incomes, expenses = [], [], []
    for i in range(months - 1, -1, -1):
        year, month = today.year, today.month - i
        while month <= 0:
            month += 12
            year -= 1
        label = f"{year}-{month:02d}"
        s = reports.monthly_summary(label)
        labels.append(label)
        incomes.append(s["income"])
        expenses.append(s["expenses"])

    x = list(range(len(labels)))
    width = 0.35
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar([v - width / 2 for v in x], incomes, width, label="Income", color="#4CAF50")
    ax.bar([v + width / 2 for v in x], expenses, width, label="Expenses", color="#F44336")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_ylabel("Amount ($)")
    ax.set_title(f"Income vs Expenses — Last {months} Months")
    ax.legend()
    plt.tight_layout()
    return fig


# ── Sidebar navigation ─────────────────────────────────────────────────────────

st.sidebar.title("💰 Finance Tracker")
page = st.sidebar.radio(
    "Navigate to",
    ["Dashboard", "Transactions", "Budgets", "Goals", "Import PDF"],
    label_visibility="collapsed",
)


# ── Dashboard ──────────────────────────────────────────────────────────────────

if page == "Dashboard":
    st.title("📊 Dashboard")

    month_options = [f"{date.today().year}-{m:02d}" for m in range(1, 13)]
    month = st.selectbox("Month", month_options, index=date.today().month - 1)

    s = reports.monthly_summary(month)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Income", fmt(s["income"]))
    c2.metric("Expenses", fmt(s["expenses"]))
    c3.metric("Net", fmt(s["net"]))
    c4.metric("Savings Rate", f"{s['savings_rate']}%")

    st.divider()
    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("Spending by Category")
        fig = _spending_fig(month)
        if fig:
            st.pyplot(fig)
            plt.close(fig)
        else:
            st.info("No expense data for this month.")

    with col_r:
        st.subheader("6-Month Trend")
        fig2 = _trend_fig(6)
        st.pyplot(fig2)
        plt.close(fig2)


# ── Transactions ───────────────────────────────────────────────────────────────

elif page == "Transactions":
    st.title("💳 Transactions")
    tab_view, tab_add, tab_delete = st.tabs(["View", "Add", "Delete"])

    with tab_add:
        tx_type = st.radio("Type", ["Expense", "Income"], horizontal=True)
        categories = tracker.EXPENSE_CATEGORIES if tx_type == "Expense" else tracker.INCOME_CATEGORIES

        with st.form("add_tx", clear_on_submit=True):
            c1, c2 = st.columns(2)
            amount = c1.number_input("Amount ($)", min_value=0.01, step=0.01, format="%.2f")
            category = c2.selectbox("Category", categories)
            description = st.text_input("Description")
            tx_date = st.date_input("Date", value=date.today())
            submitted = st.form_submit_button("Add Transaction", type="primary")

        if submitted:
            if not description.strip():
                st.error("Description is required.")
            else:
                tracker.add_transaction(
                    tx_type.lower(), amount, category,
                    description.strip(), tx_date.strftime("%Y-%m-%d"),
                )
                st.success(f"✓ {tx_type} of {fmt(amount)} ({category}) added.")
                if tx_type == "Expense":
                    for row in budget_mod.get_budget_status(tx_date.strftime("%Y-%m")):
                        if row["category"] == category and row["over"]:
                            st.warning(
                                f"⚠ Over budget for {category}! "
                                f"Spent {fmt(row['spent'])} / limit {fmt(row['limit'])}"
                            )

    with tab_view:
        c1, c2 = st.columns(2)
        filter_type = c1.selectbox("Type filter", ["All", "Income", "Expenses"])
        filter_month = c2.text_input("Month (YYYY-MM, blank = all)", value="")

        type_map = {"All": None, "Income": "income", "Expenses": "expense"}
        txs = tracker.get_transactions(
            tx_type=type_map[filter_type],
            month=filter_month.strip() or None,
        )

        if not txs:
            st.info("No transactions found.")
        else:
            df = pd.DataFrame(sorted(txs, key=lambda x: x["date"], reverse=True))
            df = df[["id", "date", "type", "category", "description", "amount"]]
            df["amount"] = df["amount"].apply(fmt)
            st.dataframe(df, use_container_width=True, hide_index=True)

    with tab_delete:
        st.write("Enter the ID shown in the View tab to remove a transaction.")
        with st.form("delete_tx"):
            tx_id = st.number_input("Transaction ID", min_value=1, step=1, format="%d")
            if st.form_submit_button("Delete", type="secondary"):
                ok = tracker.delete_transaction(int(tx_id))
                if ok:
                    st.success(f"Transaction #{int(tx_id)} deleted.")
                else:
                    st.error("Transaction not found.")


# ── Budgets ────────────────────────────────────────────────────────────────────

elif page == "Budgets":
    st.title("📋 Budgets")

    month = st.text_input("Month (YYYY-MM)", value=TODAY)
    rows = budget_mod.get_budget_status(month)

    if rows:
        st.subheader(f"Status for {month}")
        for row in rows:
            col1, col2 = st.columns([5, 1])
            spent, limit = row["spent"], row["limit"]
            if limit:
                pct = min(spent / limit, 1.0)
                col1.write(f"**{row['category']}** — {fmt(spent)} / {fmt(limit)}")
                col1.progress(pct)
                col2.write("🔴 OVER" if row["over"] else "🟢 OK")
            else:
                col1.write(f"**{row['category']}** — {fmt(spent)} *(no limit)*")
                col2.write("—")
    else:
        st.info("No data for this month.")

    st.divider()
    tab_set, tab_remove = st.tabs(["Set Budget", "Remove Budget"])

    with tab_set:
        with st.form("set_budget", clear_on_submit=True):
            category = st.selectbox("Category", tracker.EXPENSE_CATEGORIES)
            limit_val = st.number_input("Monthly limit ($)", min_value=0.01, step=10.0, format="%.2f")
            if st.form_submit_button("Set Budget", type="primary"):
                budget_mod.set_budget(category, limit_val)
                st.success(f"✓ {category} → {fmt(limit_val)}/month")
                st.rerun()

    with tab_remove:
        budgets = budget_mod.get_budgets()
        if budgets:
            with st.form("remove_budget"):
                category = st.selectbox("Category", list(budgets.keys()))
                if st.form_submit_button("Remove Budget", type="secondary"):
                    budget_mod.delete_budget(category)
                    st.success(f"Removed budget for {category}.")
                    st.rerun()
        else:
            st.info("No budgets set yet.")


# ── Goals ──────────────────────────────────────────────────────────────────────

elif page == "Goals":
    st.title("🎯 Savings Goals")

    goal_list = goals_mod.get_goals()

    if goal_list:
        for g in goal_list:
            pct = goals_mod.goal_progress(g)
            days = goals_mod.days_remaining(g)
            icon = "✅" if pct >= 100 else "🎯"

            with st.expander(f"{icon} {g['name']} — {fmt(g['saved'])} / {fmt(g['target'])} ({pct}%)"):
                st.progress(min(pct / 100, 1.0))
                c1, c2, c3 = st.columns(3)
                c1.metric("Saved", fmt(g["saved"]))
                c2.metric("Target", fmt(g["target"]))
                c3.metric("Days Left", str(days) if days is not None else "No deadline")

                col_contrib, col_del = st.columns([3, 1])
                with col_contrib:
                    with st.form(f"contrib_{g['id']}"):
                        contrib_amt = st.number_input(
                            "Contribute ($)", min_value=0.01, step=10.0,
                            format="%.2f", key=f"ci_{g['id']}",
                        )
                        if st.form_submit_button("Add Funds"):
                            goals_mod.contribute(g["id"], contrib_amt)
                            st.success(f"Added {fmt(contrib_amt)} to '{g['name']}'")
                            st.rerun()
                with col_del:
                    st.write("")
                    st.write("")
                    if st.button("🗑 Delete", key=f"dg_{g['id']}"):
                        goals_mod.delete_goal(g["id"])
                        st.rerun()
    else:
        st.info("No goals yet.")

    st.divider()
    st.subheader("Add New Goal")

    with st.form("add_goal", clear_on_submit=True):
        name = st.text_input("Goal name")
        c1, c2 = st.columns(2)
        target = c1.number_input("Target ($)", min_value=0.01, step=100.0, format="%.2f")
        saved_init = c2.number_input("Already saved ($)", min_value=0.0, step=10.0, format="%.2f", value=0.0)
        use_deadline = st.checkbox("Set a deadline")
        deadline_date = st.date_input("Deadline", value=date.today())

        if st.form_submit_button("Create Goal", type="primary"):
            if not name.strip():
                st.error("Goal name is required.")
            else:
                goals_mod.add_goal(
                    name.strip(), target,
                    deadline_date.strftime("%Y-%m-%d") if use_deadline else None,
                    saved_init,
                )
                st.success(f"✓ Goal '{name}' created!")
                st.rerun()


# ── Import PDF ─────────────────────────────────────────────────────────────────

elif page == "Import PDF":
    st.title("📄 Import PDF Statement")

    if not pdf_import.PDF_AVAILABLE:
        st.error("pdfplumber is not installed.")
        st.code("pip install pdfplumber")
        st.stop()

    uploaded = st.file_uploader("Upload a PDF bank or credit card statement", type=["pdf"])

    if uploaded:
        cache_key = uploaded.name + str(uploaded.size)
        if st.session_state.get("pdf_cache_key") != cache_key:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded.read())
                tmp_path = tmp.name
            with st.spinner("Extracting transactions…"):
                raw_txs = pdf_import.extract_transactions(tmp_path)
            os.unlink(tmp_path)
            st.session_state.pdf_txs = raw_txs
            st.session_state.pdf_cache_key = cache_key

        raw_txs = st.session_state.pdf_txs

        if not raw_txs:
            st.warning("No transactions detected in this PDF.")
            st.stop()

        st.success(f"Found **{len(raw_txs)}** potential transactions. Review below, then import.")

        with st.form("import_pdf"):
            rows_cfg = []
            for i, tx in enumerate(raw_txs):
                st.markdown(
                    f"**{i + 1}.** `{tx['raw_date']}` — "
                    f"{tx['description'][:70]} — **{fmt(tx['amount'])}**"
                )
                c1, c2, c3, c4 = st.columns([2, 2, 4, 2])
                action = c1.selectbox("Action", ["Expense", "Income", "Skip"], key=f"a{i}")
                category = c2.selectbox("Category", ALL_CATEGORIES, key=f"c{i}")
                desc = c3.text_input("Description", value=tx["description"][:80], key=f"d{i}")
                try:
                    default_date = datetime.strptime(
                        pdf_import.normalize_date(tx["raw_date"]), "%Y-%m-%d"
                    ).date()
                except (ValueError, TypeError):
                    default_date = date.today()
                tx_date = c4.date_input("Date", value=default_date, key=f"dt{i}")
                rows_cfg.append({
                    "action": action, "category": category,
                    "desc": desc, "date": tx_date, "amount": tx["amount"],
                })
                st.divider()

            if st.form_submit_button("Import Selected Transactions", type="primary"):
                saved = 0
                for row in rows_cfg:
                    if row["action"] == "Skip":
                        continue
                    tracker.add_transaction(
                        row["action"].lower(), row["amount"],
                        row["category"], row["desc"],
                        row["date"].strftime("%Y-%m-%d"),
                    )
                    saved += 1
                st.success(f"✓ Imported {saved} transaction(s).")
                del st.session_state["pdf_txs"]
                del st.session_state["pdf_cache_key"]
                st.rerun()
