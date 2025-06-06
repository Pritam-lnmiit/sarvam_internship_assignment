import sys
import io
from locust import HttpUser, task, between, events
import json
import pandas as pd
import time
import os
from dotenv import load_dotenv
import random
import logging

# Set UTF-8 encoding for stdout to prevent encoding errors
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

API_KEY = os.getenv("SARVAM_API_KEY")
if not API_KEY:
    logger.error("SARVAM_API_KEY not found in environment variables")
    raise ValueError("SARVAM_API_KEY not found in environment variables")

SAMPLE_TEXT = "Hello, how are you today?"
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

results = []
VERBOSE = False

class SarvamTransliterationUser(HttpUser):
    wait_time = between(3, 8)

    @task
    def transliterate_single_language_randomly(self):
        lang_code, lang_name = random.choice(list(LANGUAGES.items()))
        self.transliterate_single_language(lang_code, lang_name)
        time.sleep(1)

    def transliterate_single_language(self, lang_code, lang_name):
        payload = {
            "input": SAMPLE_TEXT,
            "source_language_code": "en-IN",
            "target_language_code": lang_code,
            "numerals_format": "international",
            "spoken_form": False
        }
        headers = {
            "Content-Type": "application/json",
            "api-subscription-key": API_KEY
        }

        start_time = time.time()
        try:
            with self.client.post("/transliterate", json=payload, headers=headers, catch_response=True) as response:
                elapsed_time = (time.time() - start_time) * 1000
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                if response.status_code == 200:
                    data = response.json()
                    transliterated_text = data.get('transliterated_text', 'N/A')
                    if VERBOSE:
                        logger.info(f"{lang_name}: '{SAMPLE_TEXT}' -> '{transliterated_text}'")
                    response.success()
                    result = {
                        "language": lang_name,
                        "status_code": response.status_code,
                        "latency_ms": round(elapsed_time, 2),
                        "output_text": transliterated_text,
                        "error": False,
                        "timestamp": timestamp
                    }
                else:
                    response.failure(f"HTTP {response.status_code}")
                    result = {
                        "language": lang_name,
                        "status_code": response.status_code,
                        "latency_ms": round(elapsed_time, 2),
                        "output_text": None,
                        "error": True,
                        "timestamp": timestamp
                    }
                results.append(result)
        except Exception as e:
            elapsed_time = (time.time() - start_time) * 1000
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            logger.error(f"Error in transliterate task for {lang_name}: {str(e)}")
            results.append({
                "language": lang_name,
                "status_code": 0,
                "latency_ms": round(elapsed_time, 2),
                "output_text": None,
                "error": True,
                "timestamp": timestamp
            })

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    logger.info(f"Starting Transliteration Load Test")
    logger.info(f"Testing {len(LANGUAGES)} languages with text: '{SAMPLE_TEXT}'")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    if not results:
        logger.warning("No results collected.")
        return

    df = pd.DataFrame(results)
    filename = "locust_results.csv"
    df.to_csv(filename, index=False)

    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    total = len(results)
    successes = sum(1 for r in results if not r['error'])
    failures = total - successes
    avg_latency = sum(r['latency_ms'] for r in results if not r['error']) / successes if successes else 0
    logger.info(f"Successful requests: {successes}")
    logger.info(f"Failed requests: {failures}")
    logger.info(f"Avg latency: {avg_latency:.2f} ms")
    logger.info(f"Results saved to: {filename}")

    logger.info("PERFORMANCE STATS PER LANGUAGE")
    for lang in LANGUAGES.values():
        lang_results = [r for r in results if r['language'] == lang]
        if not lang_results:
            continue
        success = [r for r in lang_results if not r['error']]
        fail = len(lang_results) - len(success)
        avg = sum(r['latency_ms'] for r in success) / len(success) if success else 0
        logger.info(f"{lang}: {len(lang_results)} reqs | Success: {len(success)} | Fail: {fail} | Avg: {avg:.2f} ms")