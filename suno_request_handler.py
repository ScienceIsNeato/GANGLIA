import os
import time
import requests
from logger import Logger

class SunoRequestHandler:
    def __init__(self):
        self.api_key = os.getenv('FOXAI_SUNO_API_KEY')
        if not self.api_key:
            raise EnvironmentError("Environment variable 'FOXAI_SUNO_API_KEY' is not set.")

        self.base_url = "https://api.sunoaiapi.com/api/v1"
        self.headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json"
        }

    def query_job_status(self, job_id, retries=5, wait_time=60):
        endpoint = f"{self.base_url}/gateway/query?ids={job_id}"
        for attempt in range(retries):
            try:
                Logger.print_debug(f"Querying job status for job ID: {job_id}")
                response = requests.get(endpoint, headers=self.headers)
                if response.status_code == 200:
                    status_response = response.json()
                    if status_response and isinstance(status_response, list):
                        job_data = status_response[0]  # Assuming the response is a list with one item
                        Logger.print_debug(f"Job status response: {job_data}")
                        return job_data
                Logger.print_error(f"Error in status response: {response.text}")
            except Exception as e:
                Logger.print_error(f"Exception during status query: {e}")
                if 'Rate limit exceeded' in str(e):
                    Logger.print_warning(f"Rate limit exceeded. Retrying in {wait_time} seconds... (Attempt {attempt + 1} of {retries})")
                    time.sleep(wait_time)
                else:
                    return {"status": "error", "message": str(e)}
        return {"status": "error", "message": "Failed to query job status after retries."}


    def build_request_data(self, prompt, model, duration, with_lyrics):
        data = {
            "gpt_description_prompt": prompt if not with_lyrics else None,
            "prompt": prompt if with_lyrics else None,
            "make_instrumental": not with_lyrics,
            "mv": model,
            "duration": duration,
        }

        data["title"] = "Generated Song" #TODO: generate
        data["tags"] = "general" #TODO: generate


        endpoint = f"{self.base_url}/gateway/generate/music"
        data = {k: v for k, v in data.items() if v is not None}

        return endpoint, data

    def send_request(self, endpoint, data, retries, wait_time):
        attempt = 0
        while attempt < retries:
            try:
                Logger.print_debug(f"Sending request to {endpoint} with data: {data} and headers: {self.headers}")
                response = requests.post(endpoint, headers=self.headers, json=data)
                Logger.print_debug(f"Request to {endpoint} completed with status code {response.status_code}")

                if response.status_code == 200:
                    return response.json()
                else:
                    Logger.print_error(f"Error in response: {response.text}")
                    if response.status_code == 429:
                        Logger.print_warning(f"Rate limit exceeded. Retrying in {wait_time} seconds... (Attempt {attempt + 1} of {retries})")
                        time.sleep(wait_time)
                        attempt += 1
                    else:
                        return {"error": response.status_code, "message": response.text}
            except Exception as e:
                Logger.print_error(f"Exception during request to {endpoint}: {e}")
                if 'Rate limit exceeded' in str(e):
                    Logger.print_warning(f"Rate limit exceeded. Retrying in {wait_time} seconds... (Attempt {attempt + 1} of {retries})")
                    time.sleep(wait_time)
                    attempt += 1
                else:
                    return {"error": "exception", "message": str(e)}
            if attempt > 1:
                print("Retrying... (Attempt {attempt + 1} of {retries})")

        Logger.print_error(f"Failed to generate audio after {retries} attempts due to rate limiting.")
        return {"error": "rate_limit_exceeded", "message": "Failed to generate audio after multiple attempts due to rate limiting."}
