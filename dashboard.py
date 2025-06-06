import streamlit as st
import subprocess
import pandas as pd
import os
import time
import re

# Streamlit page configuration
st.set_page_config(page_title="Sarvam API Load Test Dashboard", layout="wide")
st.title("Sarvam Transliteration API Load Test Dashboard")

# Test Configuration
st.header("Test Configuration")
col1, col2, col3 = st.columns(3)
with col1:
    concurrency = st.number_input("Concurrency", min_value=1, value=1, step=1)
with col2:
    spawn_rate = st.number_input("Spawn Rate", min_value=1, value=1, step=1)
with col3:
    run_time = st.text_input("Run Time (e.g., 30s, 1m)", value="30s")

# Validate run_time format (e.g., 30s, 1m, 5m)
def validate_run_time(run_time):
    pattern = r"^\d+[sm]$"
    return bool(re.match(pattern, run_time))

# Button to Trigger Locust Test
if st.button("Run Load Test"):
    if not validate_run_time(run_time):
        st.error("Invalid Run Time format. Use format like '30s' or '1m'.")
        st.stop()

    with st.spinner("Running Locust test..."):
        # Run Locust test
        csv_prefix = f"locust_stats_{int(time.time())}"
        cmd = [
            "locust",
            "-f", "locustfile.py",
            "--headless",
            "-u", str(concurrency),
            "-r", str(spawn_rate),
            "-t", run_time,
            "--host=https://api.sarvam.ai",
            f"--csv={csv_prefix}"
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            st.success("Locust test completed successfully!")
        except subprocess.CalledProcessError as e:
            st.error(f"Locust test failed: {e.stderr}")
            st.stop()

        # Run analysis
        with st.spinner("Running analysis..."):
            try:
                result = subprocess.run(["python", "analyze_results.py"], capture_output=True, text=True, check=True)
                st.success("Analysis completed. Metrics and charts generated.")
            except subprocess.CalledProcessError as e:
                st.error(f"Analysis failed: {e.stderr}")
                st.stop()

    # Display Metrics
    st.header("Test Results")
    try:
        if os.path.exists("language_metrics.csv"):
            language_metrics = pd.read_csv("language_metrics.csv")
            st.subheader("Language-wise Metrics")
            st.dataframe(language_metrics)
        else:
            st.warning("language_metrics.csv not found. Ensure analysis ran successfully.")

        if os.path.exists("aggregate_metrics.csv"):
            aggregate_metrics = pd.read_csv("aggregate_metrics.csv")
            st.subheader("Aggregate Metrics")
            st.dataframe(aggregate_metrics)
        else:
            st.warning("aggregate_metrics.csv not found. Ensure analysis ran successfully.")

        # Display Latency by Language Plot
        st.subheader("Latency by Language")
        if os.path.exists("latency_by_language.png"):
            st.image("latency_by_language.png", caption="p95, p75, p50 Latency by Language")
        else:
            st.warning("Latency by Language plot not found.")

        # Display p95 Latency by Concurrency
        if os.path.exists("p95_by_concurrency.png"):
            st.subheader("p95 Latency by Concurrency")
            st.image("p95_by_concurrency.png", caption="p95 Latency Across Concurrency Levels")
        else:
            st.warning("p95 by Concurrency plot not found. Run sweep configurations to generate.")

    except Exception as e:
        st.error(f"Error loading results: {e}")
        st.stop()

# Button to Upload to Google Sheets
st.header("Upload to Google Sheets")
if st.button("Upload Results to Google Sheets"):
    with st.spinner("Uploading to Google Sheets..."):
        try:
            result = subprocess.run(["python", "upload_to_sheets.py"], capture_output=True, text=True, check=True)
            st.success("Results uploaded to Google Sheets.")
            st.markdown("**Note**: Share the Google Sheet with public viewer access and include the link in your submission.")
        except subprocess.CalledProcessError as e:
            st.error(f"Upload failed: {e.stderr}")
            st.stop()
        except FileNotFoundError:
            st.error("Error: 'upload_to_sheets.py' not found in the project directory.")
            st.stop()

# Instructions
st.header("Instructions")
st.write("""
1. Enter concurrency, spawn rate, and run time (e.g., '30s' or '1m').
2. Click 'Run Load Test' to execute the Locust test for the Transliteration API.
3. View results and charts below.
4. Click 'Upload to Google Sheets' to update the Google Sheet.
5. In Google Sheets, add:
   - Bar Chart: Latency Metrics by Language (p95, p75, p50).
   - Line Chart: p95 Latency Across Concurrency Levels.
6. Share the Google Sheet with public viewer access.
""")