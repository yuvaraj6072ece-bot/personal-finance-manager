"""Personal Finance Manager: track income/expenses, set budgets, see charts and tips."""
import random
import sqlite3
from datetime import date, timedelta

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

DB = "finance.db"
EXPENSE_CATS = ["Food", "Rent", "Transport", "Shopping", "Bills", "Entertainment", "Health", "Education", "Other"]
INCOME_CATS = ["Salary", "Stipend", "Pocket Money", "Freelance", "Other"]


# ---------- Database ----------
def conn():
    return sqlite3.connect(DB)


def init_db():
    with conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, type TEXT, category TEXT, amount REAL, note TEXT)""")
        c.execute("CREATE TABLE IF NOT EXISTS budgets (category TEXT PRIMARY KEY, amount REAL)")


def add_transaction(d, t, cat, amt, note):
    with conn() as c:
        c.execute("INSERT INTO transactions (date, type, category, amount, note) VALUES (?,?,?,?,?)",
                  (d.isoformat(), t, cat, float(amt), note))


def delete_transaction(tid):
    with conn() as c:
        c.execute("DELETE FROM transactions WHERE id = ?", (int(tid),))


def load_transactions():
    with conn() as c:
        df = pd.read_sql("SELECT * FROM transactions ORDER BY date DESC, id DESC", c)
    df["date"] = pd.to_datetime(df["date"])
    return df


def load_budgets():
    with conn() as c:
        df = pd.read_sql("SELECT * FROM budgets", c)
    return dict(zip(df["category"], df["amount"]))


def save_budget(cat, amt):
    with conn() as c:
        c.execute("INSERT OR REPLACE INTO budgets (category, amount) VALUES (?, ?)", (cat, float(amt)))


def load_sample_data():
    random.seed(1)
    today = date.today()
    for m in range(3):
        base = (today.replace(day=1) - timedelta(days=30 * m)).replace(day=1)
        add_transaction(base, "Income", "Stipend", 15000, "Monthly stipend")
        add_transaction(base + timedelta(days=1), "Expense", "Rent", 4000, "Room share")
        for _ in range(12):
            cat = random.choice(["Food", "Transport", "Shopping", "Bills", "Entertainment"])
            add_transaction(base + timedelta(days=random.randint(2, 27)), "Expense", cat,
                            random.randint(100, 1200), "Sample")


# ---------- Analysis ----------
def month_summary(df):
    income = df.loc[df["type"] == "Income", "amount"].sum()
    expense = df.loc[df["type"] == "Expense", "amount"].sum()
    saved = income - expense
    rate = (saved / income * 100) if income > 0 else 0
    return income, expense, saved, rate


def recommendations(cur, prev, budgets):
    tips = []
    income, expense, saved, rate = month_summary(cur)
    if income == 0 and expense == 0:
        return ["No data for this month yet. Add some transactions."]
    if income > 0:
        if rate < 0:
            tips.append("You spent more than you earned this month. Cut non-essential spending first.")
        elif rate < 20:
            tips.append(f"Your savings rate is {rate:.0f}%. A common target is 20% or more.")
        else:
            tips.append(f"Great job. You saved {rate:.0f}% of your income.")
    exp = cur[cur["type"] == "Expense"].groupby("category")["amount"].sum().sort_values(ascending=False)
    if not exp.empty and expense > 0:
        top, share = exp.index[0], exp.iloc[0] / expense * 100
        if share > 40:
            tips.append(f"{top} is {share:.0f}% of your spending. Look for savings there.")
    for cat, limit in budgets.items():
        spent = exp.get(cat, 0)
        if limit > 0 and spent > limit:
            tips.append(f"Over budget on {cat} by {spent - limit:,.0f}.")
        elif limit > 0 and spent > 0.8 * limit:
            tips.append(f"{cat} has used {spent / limit * 100:.0f}% of its budget.")
    prev_exp = prev.loc[prev["type"] == "Expense", "amount"].sum()
    if prev_exp > 0 and expense > prev_exp * 1.15:
        tips.append(f"Spending is up {(expense / prev_exp - 1) * 100:.0f}% compared with last month.")
    return tips


# ---------- UI ----------
st.set_page_config(page_title="Personal Finance Manager", page_icon="💰", layout="wide")
init_db()
st.title("💰 Personal Finance Manager")

# Sidebar: add transaction
with st.sidebar:
    st.header("Add transaction")
    t_type = st.radio("Type", ["Expense", "Income"], horizontal=True)
    with st.form("add_form", clear_on_submit=True):
        t_date = st.date_input("Date", date.today())
        t_cat = st.selectbox("Category", EXPENSE_CATS if t_type == "Expense" else INCOME_CATS)
        t_amt = st.number_input("Amount", min_value=0.0, step=50.0)
        t_note = st.text_input("Note (optional)")
        if st.form_submit_button("Add") and t_amt > 0:
            add_transaction(t_date, t_type, t_cat, t_amt, t_note)
            st.rerun()
    if st.button("Load sample data"):
        load_sample_data()
        st.rerun()

df = load_transactions()
budgets = load_budgets()

if df.empty:
    st.info("No transactions yet. Add one from the sidebar, or click 'Load sample data'.")
    st.stop()

# Month selection
df["month"] = df["date"].dt.strftime("%Y-%m")
months = sorted(df["month"].unique(), reverse=True)
month = st.selectbox("Month", months)
cur = df[df["month"] == month]
idx = months.index(month)
prev = df[df["month"] == months[idx + 1]] if idx + 1 < len(months) else df.iloc[0:0]

# Metrics
income, expense, saved, rate = month_summary(cur)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Income", f"{income:,.0f}")
c2.metric("Expenses", f"{expense:,.0f}")
c3.metric("Saved", f"{saved:,.0f}")
c4.metric("Savings rate", f"{rate:.0f}%")

# Recommendations
st.subheader("Recommendations")
for tip in recommendations(cur, prev, budgets):
    st.write("• " + tip)

# Charts
left, right = st.columns(2)
with left:
    st.subheader("Spending by category")
    exp = cur[cur["type"] == "Expense"].groupby("category")["amount"].sum()
    if exp.empty:
        st.write("No expenses this month.")
    else:
        fig, ax = plt.subplots()
        ax.pie(exp, labels=exp.index, autopct="%1.0f%%", startangle=90)
        ax.axis("equal")
        st.pyplot(fig)
with right:
    st.subheader("Monthly income vs expenses")
    trend = df.pivot_table(index="month", columns="type", values="amount", aggfunc="sum", fill_value=0)
    st.bar_chart(trend.sort_index())

# Budgets
st.subheader("Budgets")
b1, b2, b3 = st.columns([2, 2, 1])
b_cat = b1.selectbox("Category", EXPENSE_CATS, key="b_cat")
b_amt = b2.number_input("Monthly limit", min_value=0.0, step=100.0, key="b_amt")
if b3.button("Save budget"):
    save_budget(b_cat, b_amt)
    st.rerun()
exp_all = cur[cur["type"] == "Expense"].groupby("category")["amount"].sum()
for cat, limit in budgets.items():
    spent = exp_all.get(cat, 0)
    pct = spent / limit if limit > 0 else 0
    st.write(f"**{cat}**: {spent:,.0f} / {limit:,.0f}")
    st.progress(min(pct, 1.0))

# Transactions
st.subheader("Transactions")
show = cur.drop(columns=["month"]).copy()
show["date"] = show["date"].dt.date
st.dataframe(show, use_container_width=True, hide_index=True)
d1, d2 = st.columns([1, 3])
del_id = d1.number_input("Delete by ID", min_value=0, step=1)
if d1.button("Delete") and del_id > 0:
    delete_transaction(del_id)
    st.rerun()
d2.download_button("Download all as CSV", df.drop(columns=["month"]).to_csv(index=False), "transactions.csv")
