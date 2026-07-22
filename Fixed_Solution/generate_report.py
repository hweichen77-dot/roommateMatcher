import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font

errors_df = pd.read_csv("errors_raw.csv")

wb = Workbook()
ws = wb.active
ws.title = "Error Report"

default_font = Font(name="Arial", size=10)
bold_font = Font(name="Arial", size=10, bold=True)

headers = ["Student Name", "CSV Row", "Request #", "Error Type", "Details", "Suggested Fix"]
for col, h in enumerate(headers, 1):
    cell = ws.cell(row=1, column=col, value=h)
    cell.font = bold_font

for i, (_, row) in enumerate(errors_df.iterrows()):
    r = i + 2
    values = [row["Student"], row["Row"], row["Request Number"], row["Error Type"], row["Details"], row["Suggested Fix"]]
    for col, val in enumerate(values, 1):
        cell = ws.cell(row=r, column=col, value=val if pd.notna(val) else "")
        cell.font = default_font

widths = [22, 10, 12, 22, 50, 25]
for i, w in enumerate(widths):
    ws.column_dimensions[chr(65 + i)].width = w

wb.save("error_report.xlsx")
total = len(errors_df)
by_type = errors_df["Error Type"].nunique()
print(f"Report generated: {total} errors across {by_type} categories")
