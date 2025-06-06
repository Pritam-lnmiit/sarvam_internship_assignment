from locust import HttpUser, task, between, events
import json
from sarvamai import SarvamAI
import pandas as pd
import time
import os


import os
from dotenv import load_dotenv
load_dotenv()
os.environ["SARVAM_API_KEY"]=os.getenv("SARVAM_API_KEY")

client = SarvamAI(api_subscription_key=os.environ["SARVAM_API_KEY"])

# Supported languages for testing
LANGUAGES = {
    "hi-IN": "Hindi",
    "ta-IN": "Tamil",
    "bn-IN": "Bengali",
    "kn-IN": "Kannada",
    "ml-IN": "Malayalam",
    "mr-IN": "Marathi",
    "od-IN": "Odia",
    "pa-IN": "Punjabi",
    "te-IN": "Telugu"
}

# Sample text for transliteration
SAMPLE_TEXT = "Hello, how are you today?"

# Store results for Google Sheets
results = []

class SarvamTransliterationUser(HttpUser):
    wait_time = between(1, 3)  # Random wait time between requests

    @task
    def transliterate(self):
        for lang_code, lang_name in LANGUAGES.items():
            payload = {
                "input": SAMPLE_TEXT,
                "source_language_code": lang_code,
                "target_language_code": "en-IN",
                "numerals_format": "international",
                "spoken_form": False
            }
            headers = {"Content-Type": "application/json"}
            
            # Measure request time
            start_time = time.time()
            response = self.client.post(
                "/transliterate",
                json=payload,
                headers=headers
            )
            elapsed_time = (time.time() - start_time) * 1000  # Convert to ms

            # log results
            result = {
                "language": lang_name,
                "status_code": response.status_code,
                "latency_ms": elapsed_time,
                "error": response.status_code != 200,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            results.append(result)

# Save results to CSV on test stop
@events.test_stop.add_listener
def on_test_stop(**kwargs):
    df = pd.DataFrame(results)
    df.to_csv("locust_results.csv", index=False)
    print("Results saved to locust_results.csv")

# Function to run Locust 
def run_locust(concurrency, spawn_rate, run_time):
    os.system(f"locust -f locustfile.py --headless -u {concurrency} -r {spawn_rate} -t {run_time} --host=https://api.sarvam.ai")