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
    
    # Pull the API key securely from the cloud environment
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
        logging.warning("Warning: No files currently found in tracker.json. Relying on Auto-Sync to populate.")

    # Step 1.5: The Auto-Sync Engine (Additive and Subtractive)
    logging.info("Step 1.5: Auto-Syncing with Live Pixeldrain Account")
    live_files_url = "https://pixeldrain.com/api/user/files"
    try:
        sync_resp = requests.get(live_files_url, auth=('', api_key))
        if sync_resp.status_code == 200:
            live_data = sync_resp.json()
            live_files = []
            
            if isinstance(live_data, dict) and "files" in live_data:
                live_files = live_data["files"]
            elif isinstance(live_data, list):
                live_files = live_data
            
            # Create a set of live IDs for ultra-fast comparison
            live_ids = {lf.get("id") for lf in live_files if lf.get("id")}
            
            # --- PHASE A: Garbage Collection (Subtractive Sync) ---
            initial_count = len(files)
            files = [f for f in files if f['id'] in live_ids]
            removed_count = initial_count - len(files)
            if removed_count > 0:
                logging.info(f"SUCCESS: Garbage Collection complete. Removed {removed_count} ghost file(s) from memory.")
            else:
                logging.info("SUCCESS: Garbage Collection complete. No ghost files detected.")

            # --- PHASE B: Injection (Additive Sync) ---
            tracked_ids = {f['id'] for f in files}
            new_additions = 0
            
            for lf in live_files:
                lf_id = lf.get("id")
                if lf_id and lf_id not in tracked_ids:
                    files.append({
                        "id": lf_id,
                        "last_touched": "2026-01-01T00:00:00Z", # Old date ensures immediate targeting
                        "views": 0,
                        "downloads": 0
                    })
                    tracked_ids.add(lf_id)
                    new_additions += 1
            
            if new_additions > 0:
                logging.info(f"SUCCESS: Auto-Sync Additions complete. Added {new_additions} new files to the tracker.")
            else:
                logging.info("SUCCESS: Auto-Sync Additions complete. No new files found.")
            
            # Commit the fully synced list back to the main memory structure
            tracker_data['files'] = files 
                
        elif sync_resp.status_code == 401:
             logging.error("CRITICAL FAILURE: Auto-Sync Unauthorized. Your API key is invalid. Point of failure HTTP Status: 401")
             return
        else:
            logging.warning(f"FAILURE: Auto-Sync API rejected request. Point of failure HTTP Status: {sync_resp.status_code}")
    except Exception as e:
        logging.error(f"FAILURE: Auto-Sync failed due to network error. Point of failure: {e}")

    # Safety check in case the account is totally empty
    if not files:
        logging.error("CRITICAL FAILURE: No files available to process even after Auto-Sync. Exiting.")
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
