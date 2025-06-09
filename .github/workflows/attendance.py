name: HROne Attendance Cron

on:
  schedule:
    - cron: '25 3 * * *'   # 9:00 AM IST
    - cron: '25 12 * * *'  # 6:00 PM IST
  workflow_dispatch:       # Optional: run manually from GitHub UI

jobs:
  mark-attendance:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.x'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run attendance script
        env:
          HRONE_USERNAME: ${{ secrets.HRONE_USERNAME }}
          HRONE_PASSWORD: ${{ secrets.HRONE_PASSWORD }}
          EMPLOYEE_ID: ${{ secrets.EMPLOYEE_ID }}
        run: python main.py
