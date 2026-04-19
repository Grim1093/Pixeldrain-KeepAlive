// --- Setup Diagnostic System ---
const terminal = document.getElementById('terminal-output');
const tableBody = document.getElementById('table-body');

function logToTerminal(message, level = "INFO") {
    // Generate ISO timestamp to perfectly match the backend log format
    const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 19);
    const logLine = `[${timestamp}] ${level} - ${message}`;
    
    // Log to hidden browser console
    console.log(logLine); 
    
    // Log to visible HTML terminal
    const p = document.createElement('div');
    p.textContent = logLine;
    
    if (level === "ERROR" || level === "CRITICAL FAILURE") {
        p.style.color = "var(--error-color)"; 
    }
    
    terminal.appendChild(p);
    terminal.scrollTop = terminal.scrollHeight; // Auto-scroll to latest log
}

async function initDashboard() {
    logToTerminal("--- STARTING DASHBOARD INITIALIZATION ---");
    
    // Step 1: Data Retrieval
    logToTerminal("Step 1: Fetching tracker.json from repository database...");
    let trackerData;
    try {
        const response = await fetch('tracker.json');
        if (!response.ok) {
            logToTerminal(`CRITICAL FAILURE: Network rejected request. Point of failure HTTP Status: ${response.status}`, "ERROR");
            return;
        }
        trackerData = await response.json();
        logToTerminal("SUCCESS: tracker.json loaded into memory.");
    } catch (error) {
        logToTerminal(`CRITICAL FAILURE: Failed to parse tracker.json. Point of failure: ${error.message}`, "ERROR");
        return;
    }

    // Step 2: Data Validation
    logToTerminal("Step 2: Validating array structure...");
    const files = trackerData.files;
    if (!files || !Array.isArray(files) || files.length === 0) {
        logToTerminal("WARNING: No files found in tracker.json.", "ERROR");
        return;
    }
    logToTerminal(`SUCCESS: Detected ${files.length} active files in vault.`);

    // Step 3: DOM Rendering
    logToTerminal("Step 3: Rendering UI Table...");
    try {
        // Sort files so the oldest 'last_touched' dates (the danger zone) appear at the top
        files.sort((a, b) => new Date(a.last_touched) - new Date(b.last_touched));

        files.forEach(file => {
            const tr = document.createElement('tr');
            
            const tdId = document.createElement('td');
            tdId.textContent = file.id;
            
            const tdTouched = document.createElement('td');
            tdTouched.textContent = file.last_touched;
            
            const tdViews = document.createElement('td');
            tdViews.textContent = file.views;
            
            const tdDownloads = document.createElement('td');
            tdDownloads.textContent = file.downloads;
            
            tr.appendChild(tdId);
            tr.appendChild(tdTouched);
            tr.appendChild(tdViews);
            tr.appendChild(tdDownloads);
            
            tableBody.appendChild(tr);
        });
        logToTerminal("SUCCESS: Grid rendering complete.");
    } catch (error) {
        logToTerminal(`CRITICAL FAILURE: Error generating DOM elements. Point of failure: ${error.message}`, "ERROR");
        return;
    }

    logToTerminal("--- DASHBOARD FULLY OPERATIONAL ---");
}

// Trigger the initialization sequence as soon as the HTML finishes loading
window.onload = initDashboard;
