import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load language-specific results
try:
    results_df = pd.read_csv("locust_results.csv")
except FileNotFoundError:
    print("Error: 'locust_results.csv' not found. Run locustfile.py first.")
    exit(1)

# Validate results_df
if results_df.empty:
    print("Error: 'locust_results.csv' is empty. Ensure Locust test generated valid data.")
    exit(1)
required_columns = ["language", "latency_ms", "error", "timestamp"]
missing_columns = [col for col in required_columns if col not in results_df.columns]
if missing_columns:
    print(f"Error: 'locust_results.csv' missing columns: {missing_columns}")
    exit(1)

# Calculate language-wise metrics, replacing NaN with 0
language_metrics = results_df.groupby("language").agg({
    "latency_ms": [
        "mean",
        lambda x: x.quantile(0.95) if not x.dropna().empty else 0,
        lambda x: x.quantile(0.75) if not x.dropna().empty else 0,
        lambda x: x.quantile(0.50) if not x.dropna().empty else 0
    ],
    "error": "mean"
}).reset_index()
language_metrics.columns = ["Language", "Avg Latency (ms)", "p95 Latency (ms)", "p75 Latency (ms)", "p50 Latency (ms)", "Error Rate"]
language_metrics["Error Rate"] = language_metrics["Error Rate"] * 100
language_metrics = language_metrics.fillna(0)

# Load aggregate metrics from Locust stats or compute from results
try:
    stats_df = pd.read_csv("locust_stats_stats.csv")
    if stats_df.empty or "Name" not in stats_df.columns or "Aggregated" not in stats_df["Name"].values:
        print("Warning: 'locust_stats_stats.csv' is empty or missing 'Aggregated' row. Computing from locust_results.csv.")
        raise FileNotFoundError
    aggregate_metrics = {
        "p95 Latency (ms)": stats_df[stats_df["Name"] == "Aggregated"]["95%"].iloc[0] if not stats_df.empty else 0,
        "p75 Latency (ms)": stats_df[stats_df["Name"] == "Aggregated"]["75%"].iloc[0] if not stats_df.empty else 0,
        "p50 Latency (ms)": stats_df[stats_df["Name"] == "Aggregated"]["50%"].iloc[0] if not stats_df.empty else 0,
        "Avg Response Time (ms)": stats_df[stats_df["Name"] == "Aggregated"]["Average Response Time"].iloc[0] if not stats_df.empty else 0,
        "RPS": stats_df[stats_df["Name"] == "Aggregated"]["Requests/s"].iloc[0] if not stats_df.empty else 0,
        "Error Rate (%)": stats_df[stats_df["Name"] == "Aggregated"]["Failure %"].iloc[0] if not stats_df.empty else 0
    }
except FileNotFoundError:
    print("locust_stats_stats.csv not found or invalid. Computing aggregate metrics from locust_results.csv.")
    try:
        time_diff = (
            pd.to_datetime(results_df["timestamp"], errors="coerce").max() - 
            pd.to_datetime(results_df["timestamp"], errors="coerce").min()
        ).total_seconds()
        aggregate_metrics = {
            "p95 Latency (ms)": results_df["latency_ms"].quantile(0.95) if not results_df["latency_ms"].dropna().empty else 0,
            "p75 Latency (ms)": results_df["latency_ms"].quantile(0.75) if not results_df["latency_ms"].dropna().empty else 0,
            "p50 Latency (ms)": results_df["latency_ms"].quantile(0.50) if not results_df["latency_ms"].dropna().empty else 0,
            "Avg Response Time (ms)": results_df["latency_ms"].mean() if not results_df["latency_ms"].dropna().empty else 0,
            "RPS": len(results_df) / time_diff if time_diff > 0 else 0,
            "Error Rate (%)": results_df["error"].mean() * 100 if not results_df.empty else 0
        }
    except Exception as e:
        print(f"Error computing aggregate metrics: {e}")
        exit(1)

# Plot 1: Latency by Language
plt.figure(figsize=(12, 6))
for metric in ["p95 Latency (ms)", "p75 Latency (ms)", "p50 Latency (ms)"]:
    plt.plot(language_metrics["Language"], language_metrics[metric], marker="o", label=metric)
plt.title("Latency Metrics by Language")
plt.xlabel("Language")
plt.ylabel("Latency (ms)")
plt.legend()
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig("latency_by_language.png")
plt.close()

# Plot 2: p95 Latency Across Configurations (for sweep)
sweep_configs = [
    {"concurrency": 1, "spawn_rate": 1, "run_time": "1m"},
    {"concurrency": 5, "spawn_rate": 2, "run_time": "1m"},
    {"concurrency": 10, "spawn_rate": 2, "run_time": "3m"},
    {"concurrency": 25, "spawn_rate": 4, "run_time": "5m"}
]
config_metrics = []
for i, config in enumerate(sweep_configs):
    try:
        config_df = pd.read_csv(f"locust_stats_config_{i}_stats.csv")
        if not config_df.empty and "Name" in config_df.columns and "Aggregated" in config_df["Name"].values:
            config_metrics.append({
                "Concurrency": config["concurrency"],
                "p95 Latency (ms)": config_df[config_df["Name"] == "Aggregated"]["95%"].iloc[0]
            })
        else:
            print(f"Warning: locust_stats_config_{i}_stats.csv is empty or invalid. Skipping.")
    except FileNotFoundError:
        print(f"locust_stats_config_{i}_stats.csv not found. Skipping configuration {i}.")
if config_metrics:
    config_df = pd.DataFrame(config_metrics)
    plt.figure(figsize=(10, 5))
    plt.plot(config_df["Concurrency"], config_df["p95 Latency (ms)"], marker="o")
    plt.title("p95 Latency Across Concurrency Levels")
    plt.xlabel("Concurrency")
    plt.ylabel("p95 Latency (ms)")
    plt.tight_layout()
    plt.savefig("p95_by_concurrency.png")
    plt.close()

# Save metrics for Google Sheets
language_metrics.to_csv("language_metrics.csv", index=False)
pd.DataFrame([aggregate_metrics]).to_csv("aggregate_metrics.csv", index=False)
print("Metrics saved to language_metrics.csv and aggregate_metrics.csv")