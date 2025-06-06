import sys
import io
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

# Set UTF-8 encoding for stdout to prevent encoding errors
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Load test results
try:
    results_df = pd.read_csv("locust_results.csv")
except FileNotFoundError:
    print("Error: 'locust_results.csv' not found. Run locustfile.py first.")
    sys.exit(1)

if results_df.empty:
    print("Error: 'locust_results.csv' is empty. Ensure Locust test generated valid data.")
    sys.exit(1)

required_columns = ["language", "latency_ms", "error", "timestamp"]
missing_columns = [col for col in required_columns if col not in results_df.columns]
if missing_columns:
    print(f"Error: 'locust_results.csv' missing columns: {missing_columns}")
    sys.exit(1)

# Calculate per-language metrics
language_metrics = results_df.groupby("language").agg({
    "latency_ms": [
        "mean",
        lambda x: x.quantile(0.95) if not x.dropna().empty else 0,
        lambda x: x.quantile(0.75) if not x.dropna().empty else 0,
        lambda x: x.quantile(0.50) if not x.dropna().empty else 0
    ],
    "error": "mean"
}).reset_index()
language_metrics.columns = [
    "Language", "Avg Latency (ms)", "p95 Latency (ms)",
    "p75 Latency (ms)", "p50 Latency (ms)", "Error Rate"
]
language_metrics["Error Rate"] *= 100
language_metrics = language_metrics.fillna(0)

# Aggregate metrics
try:
    time_diff = (
        pd.to_datetime(results_df["timestamp"], errors="coerce").max() -
        pd.to_datetime(results_df["timestamp"], errors="coerce").min()
    ).total_seconds()
    aggregate_metrics = {
        "p95 Latency (ms)": results_df["latency_ms"].quantile(0.95),
        "p75 Latency (ms)": results_df["latency_ms"].quantile(0.75),
        "p50 Latency (ms)": results_df["latency_ms"].quantile(0.50),
        "Avg Response Time (ms)": results_df["latency_ms"].mean(),
        "RPS": len(results_df) / time_diff if time_diff > 0 else 0,
        "Error Rate (%)": results_df["error"].mean() * 100
    }
except Exception as e:
    print(f"Error computing aggregate metrics: {e}")
    sys.exit(1)

# Plot 1: Latency by Language
plt.figure(figsize=(12, 6))
sns.barplot(data=language_metrics, x="Language", y="p95 Latency (ms)", color="red", label="p95", alpha=0.8)
sns.barplot(data=language_metrics, x="Language", y="p75 Latency (ms)", color="blue", label="p75", alpha=0.5)
sns.barplot(data=language_metrics, x="Language", y="p50 Latency (ms)", color="green", label="p50", alpha=0.3)
plt.title("Latency Metrics by Language")
plt.xlabel("Language")
plt.ylabel("Latency (ms)")
plt.legend()
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig("latency_by_language.png")
plt.close()

# Plot 2: Sweep Config Performance
sweep_configs = [
    {"concurrency": 1},
    {"concurrency": 5},
    {"concurrency": 10},
    {"concurrency": 25}
]
config_metrics = []
for i, config in enumerate(sweep_configs):
    try:
        config_df = pd.read_csv(f"locust_stats_config_{i}_stats.csv")
        if not config_df.empty and "Name" in config_df.columns and "Aggregated" in config_df["Name"].values:
            p95_value = config_df[config_df["Name"] == "Aggregated"]["95%"].iloc[0]
            if pd.notna(p95_value):  # Ensure p95 value is not NaN
                config_metrics.append({
                    "Concurrency": config["concurrency"],
                    "p95 Latency (ms)": p95_value
                })
            else:
                print(f"Warning: No valid p95 latency in locust_stats_config_{i}_stats.csv.")
        else:
            print(f"Warning: locust_stats_config_{i}_stats.csv invalid or missing 'Aggregated' row.")
    except FileNotFoundError:
        print(f"Warning: locust_stats_config_{i}_stats.csv not found. Skipping.")

# Generate p95_by_concurrency.png
if config_metrics:
    config_df = pd.DataFrame(config_metrics)
    plt.figure(figsize=(10, 5))
    plt.plot(config_df["Concurrency"], config_df["p95 Latency (ms)"], marker="o")
    plt.title("p95 Latency Across Concurrency Levels")
    plt.xlabel("Concurrency")
    plt.ylabel("p95 Latency (ms)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("p95_by_concurrency.png")
    plt.close()
else:
    # Fallback: Use single-run data from locust_results.csv
    print("Warning: No valid concurrency sweep data found. Generating p95_by_concurrency.png with single-run data.")
    plt.figure(figsize=(10, 5))
    plt.plot([1], [aggregate_metrics["p95 Latency (ms)"]], marker="o")
    plt.title("p95 Latency Across Concurrency Levels (Single Run)")
    plt.xlabel("Concurrency")
    plt.ylabel("p95 Latency (ms)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("p95_by_concurrency.png")
    plt.close()

# Save results
language_metrics.to_csv("language_metrics.csv", index=False)
pd.DataFrame([aggregate_metrics]).to_csv("aggregate_metrics.csv", index=False)
print("Metrics saved to language_metrics.csv and aggregate_metrics.csv")
print("Plots saved to latency_by_language.png and p95_by_concurrency.png")