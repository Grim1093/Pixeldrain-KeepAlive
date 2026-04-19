import os
import json
import logging
import requests
import getpass
from datetime import datetime, timezone

# --- Setup Diagnostic System ---
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def main():
    logging.info("--- STARTING PIXELDRAIN DATA FETCH ---")
    
    # Step 1: Initialization
    logging.info("Step 1: Requesting API Key securely")
    api_key = getpass.getpass("Enter your Pixeldrain API Key (input will be hidden): ")
    
    if not api_key.strip():
        logging.error("CRITICAL FAILURE: API key cannot be empty. Point of failure: User Input.")
        return

    # Step 2: Fetching Account History
    logging.info("Step 2: Connecting to Pixeldrain API (/user/files)")
    url = "https://pixeldrain.com/api/user/files"
    
    try:
        # Pixeldrain requires basic auth with the key as the password
        resp = requests.get(url, auth=('', api_key))
        
        if resp.status_code == 401:
            logging.error("CRITICAL FAILURE: Unauthorized. Your API key is invalid. Point of failure HTTP Status: 401")
            return
        elif resp.status_code != 200:
            logging.error(f"FAILURE: API rejected request. Point of failure HTTP Status: {resp.status_code}. Response: {resp.text}")
            return
            
        logging.info("SUCCESS: Raw account data retrieved.")
        files_data = resp.json()
        
    except Exception as e:
        logging.error(f"CRITICAL FAILURE: Network error during API call. Point of failure: {e}")
        return

    # Step 3: Data Parsing & Formatting
    logging.info("Step 3: Parsing file IDs and formatting for tracker.json")
    
    # The API returns an array of files or an object containing a files array depending on the exact endpoint structure.
    # We will handle both safely.
    if isinstance(files_data, dict) and "files" in files_data:
        file_list = files_data["files"]
    elif isinstance(files_data, list):
        file_list = files_data
    else:
        logging.error("CRITICAL FAILURE: Unexpected JSON structure returned from Pixeldrain.")
        return
        
    if not file_list:
        logging.warning("No files found in your Pixeldrain account.")
        return

    formatted_files = []
    # Using an old date so the cloud script targets them immediately
    old_date = "2026-01-01T00:00:00Z"
    
    for item in file_list:
        file_id = item.get("id")
        if file_id:
            formatted_files.append({
                "id": file_id,
                "last_touched": old_date,
                "views": 0,
                "downloads": 0
            })
            
    logging.info(f"Successfully formatted {len(formatted_files)} files.")

    # Step 4: Overwriting the local tracker
    logging.info("Step 4: Saving to local tracker.json")
    tracker_payload = {
        "files": formatted_files
    }
    
    try:
        with open('tracker.json', 'w') as f:
            json.dump(tracker_payload, f, indent=2)
        logging.info("SUCCESS: tracker.json has been completely overwritten with your live account data.")
    except Exception as e:
        logging.error(f"CRITICAL FAILURE: Could not write to tracker.json. Point of failure: {e}")
        return
        
    logging.info("--- FETCH COMPLETE ---")

if __name__ == "__main__":
    main()