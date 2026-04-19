import os
import json
import logging
import requests
from datetime import datetime, timezone

# --- Setup Diagnostic System ---
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def main():
    logging.info("--- STARTING CLOUD EXECUTION CYCLE ---")
    
    # Step 1: Initialization & Environment Variables
    logging.info("Step 1: Initialization and Data Loading")
    
    # We pull the API key securely from the cloud environment, not a local file
    api_key = os.environ.get("PIXELDRAIN_API_KEY")
    if not api_key:
        logging.error("CRITICAL FAILURE: PIXELDRAIN_API_KEY environment variable not found. Point of failure: Missing Cloud Secrets.")
        return

    try:
        with open('tracker.json', 'r') as f:
            tracker_data = json.load(f)
        logging.info("Successfully loaded tracker.json")
    except Exception as e:
        logging.error(f"CRITICAL FAILURE: Failed to load tracker.json. Point of failure: {e}")
        return

    files = tracker_data.get('files', [])
    if not files:
        logging.error("CRITICAL FAILURE: No files found in tracker.json.")
        return

    # Step 2: Target Selection
    logging.info("Step 2: Target Selection (Scanning for oldest 'last_touched' dates)")
    files.sort(key=lambda x: x.get('last_touched', '9999-12-31T23:59:59Z'))
    
    targets = files[:2]
    logging.info(f"Selected targets for today's cycle: {[t['id'] for t in targets]}")

    for target in targets:
        file_id = target['id']
        logging.info(f"--- Processing File ID: {file_id} ---")
        
        # Step 3: Info Check
        logging.info(f"Step 3: Fetching metadata for {file_id}")
        info_url = f"https://pixeldrain.com/api/file/{file_id}/info"
        try:
            # Pixeldrain requires the API key in the password field of Basic Auth
            info_resp = requests.get(info_url, auth=('', api_key))
            if info_resp.status_code != 200:
                logging.error(f"FAILURE: Info API rejected request for {file_id}. Point of failure HTTP Status: {info_resp.status_code}. API Response: {info_resp.text}")
                continue
            
            info_json = info_resp.json()
            file_size = info_json.get("size", 0)
            target['views'] = info_json.get("views", 0)
            target['downloads'] = info_json.get("downloads", 0)
            
            logging.info(f"Status check passed - Size: {file_size} bytes, Views: {target['views']}, Downloads: {target['downloads']}")

            # Step 4: The 15% Range Request
            logging.info(f"Step 4: Initiating 15% partial download for {file_id}")
            if file_size == 0:
                logging.warning(f"SKIPPED: File {file_id} has size 0. Nothing to download.")
                continue
            
            bytes_to_fetch = int(file_size * 0.15)
            headers = {"Range": f"bytes=0-{bytes_to_fetch}"}

            download_url = f"https://pixeldrain.com/api/file/{file_id}"
            dl_resp = requests.get(download_url, headers=headers, auth=('', api_key))
            
            # Step 5: Error Handling
            if dl_resp.status_code in (200, 206):
                logging.info(f"SUCCESS: Partial chunk fetched for {file_id}. HTTP Status: {dl_resp.status_code}")
                # Step 6: State Update
                target['last_touched'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            else:
                logging.error(f"FAILURE: Download rejected for {file_id}. Point of failure HTTP Status: {dl_resp.status_code}. API Response: {dl_resp.text}")

        except Exception as e:
            logging.error(f"FAILURE: Unhandled exception processing {file_id}. Point of failure: {e}")

    # Final Save
    logging.info("Step 6: Committing new state to tracker.json")
    try:
        with open('tracker.json', 'w') as f:
            json.dump(tracker_data, f, indent=2)
        logging.info("Successfully updated memory tracker.")
    except Exception as e:
        logging.error(f"CRITICAL FAILURE: Failed to save tracker.json. Point of failure: {e}")

    logging.info("--- CYCLE COMPLETE ---")

if __name__ == "__main__":
    main()