# Personal Finance Manager

A Streamlit app to track income and expenses, set category budgets, view charts,
and get simple spending recommendations. Data is stored locally in SQLite.

## Features
- Add income and expense transactions
- Monthly summary: income, expenses, savings, savings rate
- Pie chart of spending by category and monthly income vs expense chart
- Category budgets with progress bars
- Rule-based recommendations (low savings, over budget, spending spikes)
- CSV export

## Setup
```
python -m venv venv
venv\Scripts\activate        # Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Tech
Python, Streamlit, pandas, matplotlib, SQLite
