import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import numpy as np

# Define sweep configurations (same as in locustfile.py)
sweep_configs = [
    {"concurrency": 1, "spawn_rate": 1, "run_time": "1m"},
    {"concurrency": 5, "spawn_rate": 2, "run_time": "1m"},
    {"concurrency": 10, "spawn_rate": 2, "run_time": "3m"},
    {"concurrency": 25, "spawn_rate": 4, "run_time": "5m"}
]

# Authenticate with Google Sheets API
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
try:
    creds = ServiceAccountCredentials.from_json_keyfile_name("sarvam-api-load-test-97edf974c22f.json", scope)
    client = gspread.authorize(creds)
except FileNotFoundError:
    print("Error: 'credentials.json' not found. Ensure it is in the project directory.")
    exit(1)

# Open Google Sheet
try:
    sheet = client.open("Sarvam_API_Load_Test")
except gspread.exceptions.SpreadsheetNotFound:
    print("Error: Sheet 'Sarvam_API_Load_Test' not found. Check sheet name or sharing permissions.")
    exit(1)

# Load and clean data
print("Loading and cleaning data...")
try:
    aggregate_metrics = pd.read_csv("aggregate_metrics.csv").fillna(0)
    language_metrics = pd.read_csv("language_metrics.csv").fillna(0)
except FileNotFoundError as e:
    print(f"Error: {e}. Ensure 'aggregate_metrics.csv' and 'language_metrics.csv' exist.")
    exit(1)

# Combine aggregate and language-wise metrics
summary_data = pd.concat([
    aggregate_metrics,
    language_metrics[["Language", "p95 Latency (ms)", "p75 Latency (ms)", "p50 Latency (ms)", "Error Rate"]]
], axis=0, ignore_index=True)
summary_data = summary_data.fillna(0)  # Ensure no NaN values

# Convert float columns to string to handle any remaining NaN/infinity
for col in summary_data.columns:
    if summary_data[col].dtype in [float, int]:
        summary_data[col] = summary_data[col].apply(lambda x: str(round(x, 2)) if not np.isnan(x) else "0")

# Tab 1: Summary Dashboard
print("Updating Summary Dashboard...")
try:
    worksheet = sheet.worksheet("Summary Dashboard")
except gspread.exceptions.WorksheetNotFound:
    worksheet = sheet.add_worksheet(title="Summary Dashboard", rows=100, cols=20)
worksheet.clear()
worksheet.update(range_name="A1", values=[summary_data.columns.tolist()] + summary_data.values.tolist())

# Tab 2: Raw Data
print("Updating Raw Data...")
try:
    raw_data = pd.read_csv("locust_results.csv").fillna(0)
except FileNotFoundError:
    print("Error: 'locust_results.csv' not found. Ensure Locust test has run.")
    exit(1)
try:
    worksheet = sheet.worksheet("Raw Data")
except gspread.exceptions.WorksheetNotFound:
    worksheet = sheet.add_worksheet(title="Raw Data", rows=len(raw_data) + 10, cols=20)
worksheet.clear()
worksheet.update(range_name="A1", values=[raw_data.columns.tolist()] + raw_data.values.tolist())

# Tab 3: Sweep Configurations
print("Updating Configurations...")
config_data = pd.DataFrame(sweep_configs) if sweep_configs else pd.DataFrame([{"concurrency": 1, "spawn_rate": 1, "run_time": "1m"}])
try:
    worksheet = sheet.worksheet("Configurations")
except gspread.exceptions.WorksheetNotFound:
    worksheet = sheet.add_worksheet(title="Configurations", rows=len(config_data) + 10, cols=20)
worksheet.clear()
worksheet.update(range_name="A1", values=[config_data.columns.tolist()] + config_data.values.tolist())

print("Google Sheet updated successfully.")
print("Manually add charts in the 'Summary Dashboard' tab for p95/p75/p50 latency and p95 by concurrency.")
print("Share the sheet publicly with Viewer access for submission.")