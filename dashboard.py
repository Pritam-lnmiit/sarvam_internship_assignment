import streamlit as st
import subprocess
import pandas as pd
import os
import time
import re
from dotenv import load_dotenv

# Page configuration
st.set_page_config(page_title="Sarvam API Load Test Dashboard", layout="wide")
st.title("Sarvam Transliteration API Load Test Dashboard")

# Input fields
st.header("Test Configuration")
col1, col2, col3, col4 = st.columns(4)
with col1:
    concurrency = st.number_input("Concurrency", min_value=1, value=1, step=1)
with col2:
    spawn_rate = st.number_input("Spawn Rate", min_value=1, value=1, step=1)
with col3:
    run_time = st.text_input("Run Time (e.g., 30s, 1m)", value="30s")
with col4:
    api_key = st.text_input("Sarvam API Key", type="password", help="Enter your Sarvam API key. If not provided, the key from .env file will be used.")

def validate_run_time(run_time):
    return bool(re.match(r"^\d+[smh]$", run_time))

# Check for required files
required_files = ["locustfile.py", "analyze_results.py"]
for file in required_files:
    if not os.path.exists(file):
        st.error(f"{file} not found. Please ensure it exists in the same directory.")
        st.stop()

# Check Locust installation
try:
    result = subprocess.run(["locust", "--version"], capture_output=True, text=True, check=True)
    st.info(f"Locust version: {result.stdout.strip()}")
except subprocess.CalledProcessError:
    st.error("Locust is not installed or not found in PATH. Install it using 'pip install locust'.")
    st.stop()

# Check .env file as fallback if API key not provided
if not api_key and not os.path.exists(".env"):
    st.error("No API key provided and '.env' file not found. Please provide an API key or create a .env file with SARVAM_API_KEY.")
    st.stop()

# Load .env file as fallback if API key not provided
if not api_key:
    load_dotenv()
    api_key = os.getenv("SARVAM_API_KEY")
    if not api_key:
        st.error("No API key provided and SARVAM_API_KEY not found in .env file.")
        st.stop()

# Run Load Test button
if st.button("Run Load Test"):
    if not validate_run_time(run_time):
        st.error("Invalid Run Time format. Use '30s', '1m', or '1h'.")
        st.stop()

    # Set SARVAM_API_KEY environment variable for Locust
    os.environ["SARVAM_API_KEY"] = api_key

    csv_prefix = f"locust_stats_{int(time.time())}"
    cmd = [
        "locust", "-f", "locustfile.py", "--headless",
        "-u", str(concurrency), "-r", str(spawn_rate),
        "-t", run_time, "--host=https://api.sarvam.ai",
        f"--csv={csv_prefix}"
    ]

    with st.spinner("Running Locust test..."):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            st.subheader("Locust Output")
            st.code(result.stdout)
            if result.stderr:
                st.subheader("Locust Error Output")
                st.code(result.stderr)

            if result.returncode == 0:
                st.success("Locust test completed successfully.")
            elif "Type" in result.stdout and "# reqs" in result.stdout:
                st.warning(f"Locust ran but exited with code {result.returncode}. Some requests were sent. Check error output above.")
            else:
                st.error(f"Locust failed with exit code {result.returncode}. No requests were sent.")
                st.code(result.stderr)
                st.stop()
        except subprocess.TimeoutExpired:
            st.error("Locust test timed out after 10 minutes.")
            st.stop()

    with st.spinner("Running analysis..."):
        try:
            result = subprocess.run(["python", "analyze_results.py"], capture_output=True, text=True, check=True)
            st.success("Analysis completed. Metrics and charts generated.")
            st.code(result.stdout)
        except subprocess.CalledProcessError as e:
            st.error(f"Analysis failed:\n{e.stderr}")
            st.stop()

# Display Metrics
st.header("Test Results")
try:
    if os.path.exists("language_metrics.csv"):
        language_metrics = pd.read_csv("language_metrics.csv")
        if language_metrics.empty:
            st.warning("language_metrics.csv is empty.")
        else:
            st.subheader("Language-wise Metrics")
            st.dataframe(language_metrics)
    else:
        st.warning("language_metrics.csv not found.")

    if os.path.exists("aggregate_metrics.csv"):
        aggregate_metrics = pd.read_csv("aggregate_metrics.csv")
        if aggregate_metrics.empty:
            st.warning("aggregate_metrics.csv is empty.")
        else:
            st.subheader("Aggregate Metrics")
            st.dataframe(aggregate_metrics)
    else:
        st.warning("aggregate_metrics.csv not found.")

    st.subheader("Latency by Language")
    if os.path.exists("latency_by_language.png"):
        st.image("latency_by_language.png", caption="Latency (p95, p75, p50) by Language")
    else:
        st.warning("latency_by_language.png not found.")

    st.subheader("p95 Latency by Concurrency")
    if os.path.exists("p95_by_concurrency.png"):
        st.image("p95_by_concurrency.png", caption="p95 Latency Across Concurrency Levels")
    else:
        st.warning("p95_by_concurrency.png not found.")

except Exception as e:
    st.error(f"Error loading results: {e}")

# Upload to Google Sheets
st.header("Upload to Google Sheets")
if st.button("Upload Results to Google Sheets"):
    if not os.path.exists("upload_to_sheets.py"):
        st.error("upload_to_sheets.py not found.")
        st.stop()
    with st.spinner("Uploading to Google Sheets..."):
        try:
            result = subprocess.run(["python", "upload_to_sheets.py"], capture_output=True, text=True, check=True)
            st.success("Results uploaded to Google Sheets.")
            st.code(result.stdout)
        except subprocess.CalledProcessError as e:
            st.error(f"Upload failed: {e.stderr}")

# Instructions
st.header("Instructions")
st.markdown("""
1. Ensure Locust is installed (`pip install locust`) and `locustfile.py` is configured correctly.
2. Enter your Sarvam API key in the text field above, or create a `.env` file with `SARVAM_API_KEY=your_api_key_here`.
3. Enter concurrency, spawn rate, and run time (e.g., '30s', '1m', '1h').
4. Click 'Run Load Test' to test the Transliteration API.
5. Check the Locust output and error output for issues if no requests are sent.
6. View metrics and plots in the 'Test Results' section.
7. Click 'Upload Results to Google Sheets' to sync.
8. In the Google Sheet:
   - Create Bar Chart: Latency Metrics by Language (p95, p75, p50)
   - Create Line Chart: p95 Latency Across Concurrency Levels
9. Share Google Sheet with public viewer access.
""")