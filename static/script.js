/**
 * static/scripts.js
 * Handles dashboard interactivity including:
 * - Fetching historical logs and displaying charts with theme colors & categorization.
 * - Applying filters to historical data.
 * - Displaying real-time logs via Server-Sent Events with theme styling.
 * - Tab navigation between content sections.
 * - User logout.
 * - Snort Alerts (Enhanced Display)
 * - System Health
 * - Log Refresh
 * - Report Generation Triggers
 * - IP Block Pop-up Modal Control
 */

// --- Helper to get CSS Variable values ---
function getCssVariable(variableName) {
    try {
        return getComputedStyle(document.documentElement).getPropertyValue(variableName).trim();
    } catch (e) {
        console.warn(`Could not get CSS variable ${variableName}`, e);
        return null;
    }
}

// --- Chart.js Theme Configuration ---
function configureChartJsDefaults() {
    try {
        const textColor = getCssVariable('--text-primary') || '#e5e7eb';
        const gridColor = getCssVariable('--border-color') || '#374151';
        const tooltipBg = getCssVariable('--bg-panel') || '#111827';

        Chart.defaults.color = textColor;
        Chart.defaults.borderColor = gridColor;
        Chart.defaults.scale.grid.color = gridColor;
        Chart.defaults.scale.ticks.color = textColor;
        Chart.defaults.plugins.legend.labels.color = textColor;
        Chart.defaults.plugins.tooltip.backgroundColor = tooltipBg;
        Chart.defaults.plugins.tooltip.titleColor = textColor;
        Chart.defaults.plugins.tooltip.bodyColor = textColor;
        Chart.defaults.plugins.tooltip.borderColor = gridColor;
        Chart.defaults.plugins.tooltip.borderWidth = 1;

        console.log("Chart.js defaults configured with theme colors.");

    } catch (error) {
        console.error("Error configuring Chart.js defaults:", error);
    }
}

configureChartJsDefaults();

// =====================================================
// == START: Pop-up Modal Logic (IP Block Notification) ==
// =====================================================

// --- References to the modal elements ---
// Note: We get these *after* the DOM is loaded, usually inside DOMContentLoaded listener,
// but declaring placeholders here is fine. The actual assignment might be better later.
let ipBlockedPopup = null;
let blockedIpSpan = null;
// The close button reference is fetched within the functions or DOMContentLoaded

/**
 * Shows the IP Blocked pop-up modal.
 * @param {string} ipAddress - The IP address that was blocked.
 */
function showIpBlockedPopup(ipAddress) {
    if (!ipBlockedPopup) ipBlockedPopup = document.getElementById('ipBlockedPopup'); // Get element if not already cached
    if (!blockedIpSpan) blockedIpSpan = document.getElementById('blockedIpAddress'); // Get element if not already cached

    if (!ipBlockedPopup || !blockedIpSpan) {
        console.error("Popup elements not found!");
        return;
    }
    // Set the blocked IP address in the modal
    blockedIpSpan.textContent = ipAddress || 'Unknown IP'; // Display IP or a default

    // Show the modal
    ipBlockedPopup.style.display = 'flex'; // Use 'flex' because of the centering styles in CSS
    console.log(`Showing IP Block popup for: ${ipAddress}`);
}

/**
 * Hides the IP Blocked pop-up modal.
 */
function hideIpBlockedPopup() {
    if (!ipBlockedPopup) ipBlockedPopup = document.getElementById('ipBlockedPopup'); // Get element if not already cached

    if (!ipBlockedPopup) {
        console.error("Popup element not found!");
        return;
    }
    ipBlockedPopup.style.display = 'none';
    console.log("Hiding IP Block popup.");
}

// Note: Event listeners for the modal (close button, overlay click)
// are added within the DOMContentLoaded listener at the end of this file.

// --- HOW TO TRIGGER IT (EXAMPLE) ---
// In your actual implementation, this function call would come from
// the part of your code that receives notifications from the backend
// (e.g., via WebSockets, Server-Sent Events, or polling results)
// when Snort blocks an IP.
// Example: webSocket.onmessage = (event) => {
//     const data = JSON.parse(event.data);
//     if (data.type === 'ip_blocked') {
//         showIpBlockedPopup(data.ip);
//     }
// };

// For testing purposes, you can call this from the browser console:
// showIpBlockedPopup('192.168.1.105');
// Or uncomment this line in DOMContentLoaded for a timed test:
// setTimeout(() => { showIpBlockedPopup('192.168.1.105'); }, 5000); // Shows popup after 5 seconds

// =====================================================
// == END: Pop-up Modal Logic                         ==
// =====================================================


// --- Palette for Charts ---
const chartColorPalette = [
    getCssVariable('--accent-primary') || '#22d3ee',   // Cyan
    getCssVariable('--accent-secondary') || '#0ea5e9', // Sky Blue
    getCssVariable('--success-color') || '#34d399',    // Green
    getCssVariable('--warning-color') || '#facc15',    // Yellow
    getCssVariable('--debug-color') || '#a855f7',      // Purple
    getCssVariable('--text-secondary') || '#9ca3af'    // Grey
];
function colorToRgba(color, alpha = 0.3) {
    if (!color) return `rgba(156, 163, 175, ${alpha})`;
    if (color.startsWith('#')) {
        const r = parseInt(color.slice(1, 3), 16) || 0;
        const g = parseInt(color.slice(3, 5), 16) || 0;
        const b = parseInt(color.slice(5, 7), 16) || 0;
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    } else if (color.startsWith('rgb')) {
        const parts = color.match(/[\d.]+/g);
        if (parts && parts.length === 3) return `rgba(${parts[0]}, ${parts[1]}, ${parts[2]}, ${alpha})`;
    }
    return `rgba(156, 163, 175, ${alpha})`;
}
const chartColorPaletteRGBA = chartColorPalette.map(color => colorToRgba(color, 0.3));

// --- Global variables ---
let startDate = '';
let endDate = '';
let logLevel = 'all';

// --- Function to fetch HISTORICAL log data ---
async function fetchLogData() {
    try {
        const url = new URL('/logs', window.location.origin);
        const currentStartDate = document.getElementById('startDate')?.value;
        const currentEndDate = document.getElementById('endDate')?.value;
        const currentLogLevel = document.getElementById('logLevel')?.value || 'all';

        if (currentStartDate) url.searchParams.append('startDate', currentStartDate);
        if (currentEndDate) url.searchParams.append('endDate', currentEndDate);
        if (currentLogLevel && currentLogLevel.toLowerCase() !== 'all') url.searchParams.append('logLevel', currentLogLevel);

        console.log("Fetching historical logs from:", url.toString());
        const response = await fetch(url);

        if (!response.ok) { console.error(`Error fetching logs: ${response.status} ${response.statusText}`); return []; }
        const data = await response.json();
        console.log("Historical log data received:", data?.length || 0);
        return Array.isArray(data) ? data : [];
    } catch (error) { console.error('Network or processing error fetching log data:', error); return []; }
}

// --- Function to create/update CATEGORIZED charts ---
async function createCharts() {
    console.log("Attempting to create/update charts with categorized log data...");
    const logData = await fetchLogData();

    Object.values(Chart.instances).forEach(instance => { try { instance.destroy(); } catch (e) {} });
    console.log("Existing charts destroyed.");

    const chartPanelIds = ['barChart1', 'pieChart', 'lineChart', 'barChart3', 'barChart2', 'radarChart'];
    chartPanelIds.forEach(id => { const p = document.getElementById(id)?.closest('.panel'); if(p) p.style.display = 'flex'; });

    const totalLogElement = document.getElementById('total-log-count');
    const totalLogs = logData.length;
    if (totalLogElement) totalLogElement.textContent = totalLogs.toLocaleString();

    if (totalLogs === 0) {
        console.log('No historical logs found or fetch failed. Hiding chart panels.');
         chartPanelIds.forEach(id => { const p = document.getElementById(id)?.closest('.panel'); if (p) p.style.display = 'none'; });
         return;
    }
    console.log(`Processing ${totalLogs} log entries...`);

    // --- Data Processing ---
    let logCountsBySeverity = { Critical: 0, Warning: 0, Info: 0, Success: 0, Debug: 0 };
    let logCountsByCategory = {};
    let logCountsByHour = {};

    logData.forEach(log => {
        if (!log || typeof log.message !== 'string' || typeof log.timestamp !== 'string') return;
        const message = log.message, timestamp = log.timestamp, hourKey = timestamp.length >= 13 ? timestamp.substring(0, 13) : 'unknown', upperMessage = message.toUpperCase();
        let severity = 'Info', category = 'Unknown';

        // Severity Mapping (REFINE!)
        if (upperMessage.includes('ERROR')||upperMessage.includes('FAILED')||upperMessage.includes('INVALID')||upperMessage.includes('CRITICAL')) severity='Critical';
        else if (upperMessage.includes('WARN')||upperMessage.includes('WARNING')) severity='Warning';
        else if (upperMessage.includes('SUCCESS')||upperMessage.includes('ACCEPTED')||upperMessage.includes('OPENED SESSION')||upperMessage.includes('CONNECTION CLOSED')) severity='Success';
        else if (upperMessage.includes('DEBUG')) severity='Debug';
        else severity='Info';

        // Category Mapping (REFINE!)
        if (upperMessage.includes('SSHD')) category='SSH Daemon';
        else if (upperMessage.includes('PAM')) category='PAM Auth';
        else if (upperMessage.includes('CRON')) category='Cron Jobs';
        else if (upperMessage.includes('SYSTEMD')) category='Systemd';
        else if (message.match(/\[\s*\*\*\s*\]\s*\[\s*\d+:\d+:\d+\s*\]/)) { category='IDS/IPS Alert'; const pm=message.match(/\[\s*Priority\s*:\s*(\d+)\s*\]/i); if(pm){ const p=parseInt(pm[1],10); if(p===1)severity='Critical'; else if(p===2)severity='Warning'; }}
        else category='System/Other';

        // Increment
        if (logCountsBySeverity.hasOwnProperty(severity)) logCountsBySeverity[severity]++;
        logCountsByCategory[category]=(logCountsByCategory[category]||0)+1;
        if (hourKey!=='unknown') { if(!logCountsByHour[hourKey])logCountsByHour[hourKey]={Critical:0,Warning:0,Info:0}; if(severity==='Critical')logCountsByHour[hourKey]['Critical']++; else if(severity==='Warning')logCountsByHour[hourKey]['Warning']++; else logCountsByHour[hourKey]['Info']++; }
    });
    // --- End Processing ---

    try {
        // Chart 1: Severity (Doughnut)
        const severityLabels = Object.keys(logCountsBySeverity).filter(s => logCountsBySeverity[s] > 0);
        if (severityLabels.length > 0) {
             const severityData = severityLabels.map(s => logCountsBySeverity[s]);
             const severityColors = severityLabels.map(s => { switch(s){ case 'Critical': return getCssVariable('--error-border')||'#dc2626'; case 'Warning': return getCssVariable('--warning-color')||'#facc15'; case 'Success': return getCssVariable('--success-color')||'#34d399'; case 'Debug': return getCssVariable('--debug-color')||'#a855f7'; default: return getCssVariable('--info-color')||'#0ea5e9'; } });
             const severityCtx = document.getElementById('barChart1')?.getContext('2d');
             if (severityCtx) new Chart(severityCtx, { type:'doughnut', data:{labels:severityLabels, datasets:[{data:severityData, backgroundColor:severityColors, borderColor:getCssVariable('--bg-panel')||'#111827', borderWidth:2}]}, options:{responsive:true, maintainAspectRatio:false, plugins:{legend:{position:'right', labels:{padding:10}}, title:{display:true, text:'Log Severity Distribution'}}} });
             else { const p=document.getElementById('barChart1')?.closest('.panel'); if(p)p.style.display='none'; console.warn("Canvas 'barChart1' not found."); }
        } else { const p=document.getElementById('barChart1')?.closest('.panel'); if(p)p.style.display='none'; console.warn("No severity data for chart."); }

        // Chart 2: Category (Pie)
        const categoryLabels = Object.keys(logCountsByCategory).filter(c => logCountsByCategory[c] > 0);
         if (categoryLabels.length > 0) {
             const categoryData = categoryLabels.map(c => logCountsByCategory[c]);
             const categoryColors = categoryLabels.map((_, i) => chartColorPalette[i % chartColorPalette.length]);
             const categoryCtx = document.getElementById('pieChart')?.getContext('2d');
             if (categoryCtx) new Chart(categoryCtx, { type:'pie', data:{labels:categoryLabels, datasets:[{data:categoryData, backgroundColor:categoryColors, borderColor:getCssVariable('--bg-panel')||'#111827', borderWidth:2}]}, options:{responsive:true, maintainAspectRatio:false, plugins:{legend:{position:'right', labels:{padding:10}}, title:{display:true, text:'Log Category Breakdown'}}} });
             else { const p=document.getElementById('pieChart')?.closest('.panel'); if(p)p.style.display='none'; console.warn("Canvas 'pieChart' not found."); }
        } else { const p=document.getElementById('pieChart')?.closest('.panel'); if(p)p.style.display='none'; console.warn("No category data for chart."); }

        // Chart 3: Timeline (Line)
        const sortedHours = Object.keys(logCountsByHour).sort();
         if (sortedHours.length > 0) {
             const timeLabels = sortedHours.map(h => { try { const d=new Date(h+':00:00Z'); return d.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'}); } catch(e){ console.warn(`Date format error: ${h}`); return h; } });
             const criticalData = sortedHours.map(h => logCountsByHour[h]?.Critical||0);
             const warningData = sortedHours.map(h => logCountsByHour[h]?.Warning||0);
             const infoData = sortedHours.map(h => logCountsByHour[h]?.Info||0);
             const timeCtx = document.getElementById('lineChart')?.getContext('2d');
             if (timeCtx) new Chart(timeCtx, { type:'line', data:{labels:timeLabels, datasets:[ {label:'Critical', data:criticalData, borderColor:getCssVariable('--error-border')||'#dc2626', backgroundColor:colorToRgba(getCssVariable('--error-border'),0.1), fill:true, tension:0.3}, {label:'Warning', data:warningData, borderColor:getCssVariable('--warning-color')||'#facc15', backgroundColor:colorToRgba(getCssVariable('--warning-color'),0.1), fill:true, tension:0.3}, {label:'Info/Other', data:infoData, borderColor:getCssVariable('--info-color')||'#0ea5e9', backgroundColor:colorToRgba(getCssVariable('--info-color'),0.1), fill:true, tension:0.3} ]}, options:{responsive:true, maintainAspectRatio:false, plugins:{legend:{position:'bottom'}, title:{display:true, text:'Events Over Time by Severity'}}, scales:{y:{beginAtZero:true, stacked:true}, x:{}}} });
             else { const p=document.getElementById('lineChart')?.closest('.panel'); if(p)p.style.display='none'; console.warn("Canvas 'lineChart' not found."); }
        } else { const p=document.getElementById('lineChart')?.closest('.panel'); if(p)p.style.display='none'; console.warn("No time-series data for chart."); }

        // Chart 4: Top Issues (Bar)
        const criticalCategories = {};
        logData.forEach(log => { if (!log||typeof log.message!=='string') return; const m=log.message, um=m.toUpperCase(); let issue=um.includes('ERROR')||um.includes('FAILED')||um.includes('INVALID')||um.includes('CRITICAL')||um.includes('WARN')||um.includes('WARNING'); if(!issue){ const pm=m.match(/\[\s*Priority\s*:\s*(\d+)\s*\]/i); if(pm&&(pm[1]==='1'||pm[1]==='2')) issue=true; } if(issue){ let cat='Unknown'; if(um.includes('SSHD'))cat='SSH Daemon'; else if(um.includes('PAM'))cat='PAM Auth'; else if(m.match(/\[\s*\*\*\s*\]\s*\[\s*\d+:\d+:\d+\s*\]/))cat='IDS/IPS Alert'; else cat='System/Other'; criticalCategories[cat]=(criticalCategories[cat]||0)+1; } });
        const sortedCriticalCats = Object.entries(criticalCategories).sort(([,a],[,b])=>b-a).slice(0,7);
        if (sortedCriticalCats.length > 0) {
             const topIssueLabels = sortedCriticalCats.map(([c])=>c);
             const topIssueData = sortedCriticalCats.map(([,n])=>n);
             const topIssueCtx = document.getElementById('barChart3')?.getContext('2d');
             if (topIssueCtx) new Chart(topIssueCtx, { type:'bar', data:{labels:topIssueLabels, datasets:[{label:'Count', data:topIssueData, backgroundColor:chartColorPalette.slice().reverse(), borderWidth:1}]}, options:{indexAxis:'y', responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false}, title:{display:true, text:'Top Issue Categories (Crit/Warn/P1/P2)'}}, scales:{x:{beginAtZero:true}}} });
             else { const p=document.getElementById('barChart3')?.closest('.panel'); if(p)p.style.display='none'; console.warn("Canvas 'barChart3' not found."); }
        } else { const p=document.getElementById('barChart3')?.closest('.panel'); if(p)p.style.display='none'; console.warn("No critical/warning category data for chart."); }

        // Hide Unused Placeholders
        const panelBar2 = document.getElementById('barChart2')?.closest('.panel'); if(panelBar2) panelBar2.style.display = 'none';
        const panelRadar = document.getElementById('radarChart')?.closest('.panel'); if(panelRadar) panelRadar.style.display = 'none';

        console.log("Charts created/updated.");
    } catch (error) { console.error("Error during chart creation:", error); }
}


// --- Function to apply filters ---
async function applyFilters() {
    startDate = document.getElementById('startDate')?.value;
    endDate = document.getElementById('endDate')?.value;
    logLevel = document.getElementById('logLevel')?.value || 'all';
    console.log(`Applying filters - Start: ${startDate}, End: ${endDate}, Level: ${logLevel}`);
    await createCharts();
}

// --- Function to append log line ---
function appendLogLine(logLine, logOutputElement) {
    if (typeof logLine !== 'string' || !logOutputElement) return; // Added check for logOutputElement
    const logNode = document.createElement('span');
    logNode.classList.add('log-line');
    const ul = logLine.toUpperCase();
    // Use more specific class names based on CSS
    if (ul.includes('ERROR')||ul.includes('FAILED')||ul.includes('INVALID')||ul.includes('CRITICAL')||logLine.match(/\[\s*Priority\s*:\s*1\s*\]/i)) logNode.classList.add('error');
    else if (ul.includes('WARN')||ul.includes('WARNING')||logLine.match(/\[\s*Priority\s*:\s*2\s*\]/i)) logNode.classList.add('warning');
    else if (ul.includes('ACCEPTED')) logNode.classList.add('accepted'); // Match CSS
    else if (ul.includes('DISCONNECTED')) logNode.classList.add('disconnected'); // Match CSS
    else if (ul.includes('INVALID')) logNode.classList.add('invalid'); // Match CSS
    else if (ul.includes('FAILED')) logNode.classList.add('failed'); // Match CSS
    else if (ul.includes('INFO')) logNode.classList.add('info');
    else if (ul.includes('SUCCESS')||ul.includes('OPENED SESSION')) logNode.classList.add('success');
    else if (ul.includes('DEBUG')) logNode.classList.add('debug');
    // Add more rules as needed...
    logNode.textContent = logLine;
    logOutputElement.appendChild(logNode);
    // Optionally add newline character if needed visually (CSS `white-space: pre` handles it though)
    // logOutputElement.appendChild(document.createTextNode('\n'));
}

// --- Function to initialize REAL-TIME Logs (SSE) ---
function initializeRealtimeLogs() {
    const logOutputElement = document.getElementById('realtime-log-output');
    const logStatusElement = document.getElementById('log-status');
    if (!logOutputElement || !logStatusElement) {
        console.warn("Real-time log elements not found, skipping SSE init.");
        return;
    }
    console.log("Initializing real-time log viewer...");
    let eventSource = null, retryTimeout = null;
    function connectSSE() {
        if (retryTimeout) clearTimeout(retryTimeout);
        if (eventSource && eventSource.readyState !== EventSource.CLOSED) eventSource.close();
        eventSource = new EventSource('/stream-realtime-logs');
        logStatusElement.textContent = 'Connecting...';
        eventSource.onopen = () => { logStatusElement.textContent = 'Connected'; console.log("SSE opened."); };
        eventSource.onmessage = ev => { logStatusElement.textContent = 'Connected'; appendLogLine(ev.data, logOutputElement); if (logOutputElement.scrollHeight-logOutputElement.clientHeight<=logOutputElement.scrollTop+50) logOutputElement.scrollTop=logOutputElement.scrollHeight; }; // Auto-scroll if near bottom
        eventSource.onerror = err => { logStatusElement.textContent = 'Connection error. Retrying...'; console.error("SSE failed:", err); eventSource.close(); retryTimeout = setTimeout(connectSSE, 5000); }; // Retry after 5s
    }
    connectSSE();
    // Clean up on page leave
    window.addEventListener('beforeunload', () => { if(retryTimeout)clearTimeout(retryTimeout); if(eventSource&&eventSource.readyState!==EventSource.CLOSED){eventSource.close();console.log("SSE closed on unload.");} });
}

// --- Function to fetch Snort Alerts ---
async function fetchSnortAlerts() {
    const listEl = document.getElementById('snort-alerts-list'), statusEl = document.getElementById('snort-status');
    if (!listEl || !statusEl) return;
    statusEl.textContent = 'Loading alerts...'; listEl.innerHTML = '';
    try {
        const response = await fetch('/snort-alerts'); if (!response.ok) throw new Error(`HTTP ${response.status}`); const alerts = await response.json();
        if (alerts && alerts.length > 0) {
             alerts.forEach(alert => { try { const li=document.createElement('li'); li.classList.add('snort-alert-item'); let msg=alert.message||'', ts=alert.timestamp?new Date(alert.timestamp).toLocaleString():'', pri=3, cls='N/A', pro='N/A', sip='N/A', dip='N/A', txt=msg; if(!ts){const tsm=msg.match(/^(\d{2}\/\d{2}-\d{2}:\d{2}:\d{2}\.\d+)\s+/); if(tsm){ts=tsm[1];msg=msg.substring(tsm[0].length);}} const pm=msg.match(/\[\s*Priority\s*:\s*(\d+)\s*\]/i); if(pm)pri=parseInt(pm[1],10); li.classList.add(`priority-${pri}`); const clm=msg.match(/\[\s*Classification\s*:\s*([^\]]+)\s*\]/i); if(clm)cls=clm[1].trim(); const prm=msg.match(/\{\s*(\w+)\s*\}/i); if(prm)pro=prm[1]; const ipm=msg.match(/(\d{1,3}(\.\d{1,3}){3}(?::\d+)?)\s*->\s*(\d{1,3}(\.\d{1,3}){3}(?::\d+)?)/); if(ipm){sip=ipm[1];dip=ipm[2];} let tmp=msg; if(pm)tmp=tmp.replace(pm[0],''); if(clm)tmp=tmp.replace(clm[0],''); if(prm)tmp=tmp.replace(prm[0],''); if(ipm)tmp=tmp.replace(ipm[0],''); const txtm=tmp.match(/\[\s*\*\*\s*\]\s*\[\s*\d+:\d+:\d+\s*\]\s*([^\[\{]+)/); if(txtm)txt=txtm[1].trim(); else txt=msg.split('[ Class')[0].split('[ Prio')[0].split('{')[0].trim(); li.innerHTML=`<div class="alert-header"><span class="alert-timestamp">${ts||'No Timestamp'}</span> <span class="alert-priority priority-${pri}">P${pri}</span></div><div class="alert-message">${txt||'No Message Text'}</div><div class="alert-details">${cls!=='N/A'?`<span class="alert-classification">Cls: ${cls}</span>`:''} ${pro!=='N/A'?`<span class="alert-protocol">Pro: ${pro}</span>`:''}</div> ${sip!=='N/A'?`<div class="alert-network"><span class="alert-ip source">${sip}</span> <span class="alert-arrow">➔</span> <span class="alert-ip dest">${dip}</span></div>`:''}`; listEl.appendChild(li); } catch(pE){ console.error("Snort parse error:",alert,pE); const eli=document.createElement('li'); eli.classList.add('snort-alert-item','error-message'); eli.textContent=`Error displaying alert: ${alert?.message?.substring(0,100)||'Unknown format'}`; listEl.appendChild(eli); } }); statusEl.textContent = ''; // Clear status if successful
        } else { statusEl.textContent = 'No alerts found.'; }
    } catch (error) { console.error('Fetch Snort failed:',error); statusEl.textContent='Failed to load alerts.'; listEl.innerHTML='<li class="snort-alert-item error-message">Failed to load alerts. Check console.</li>'; }
}

// --- Function to fetch System Health ---
async function fetchSystemHealth() {
    const cpuEl=document.getElementById('cpu-usage'), memEl=document.getElementById('memory-usage'), statEl=document.getElementById('system-health-status');
    if (!cpuEl||!memEl||!statEl) return; statEl.textContent='Loading...';
    try {
        const response = await fetch('/system-health'); if(!response.ok) throw new Error(`HTTP ${response.status}`); const d=await response.json();
        if (d&&typeof d.cpu_usage==='number'&&typeof d.memory_usage==='number') { cpuEl.innerHTML=`CPU Usage: <span class="health-value">${d.cpu_usage.toFixed(1)}%</span>`; memEl.innerHTML=`Memory Usage: <span class="health-value">${d.memory_usage.toFixed(1)}%</span>`; statEl.textContent=''; } // Clear status if successful
        else { throw new Error("Invalid health data received"); }
    } catch (error) { console.error('Fetch Health failed:',error); statEl.textContent='Failed to load health.'; cpuEl.innerHTML='CPU Usage: <span class="health-value error">Error</span>'; memEl.innerHTML='Memory Usage: <span class="health-value error">Error</span>'; }
}

// --- Function to handle tab switching ---
function initializeTabs() {
    const navLinks=document.querySelectorAll('nav a.nav-link'), contentSections=document.querySelectorAll('.content-section');
    if (navLinks.length===0||contentSections.length===0) return;
    navLinks.forEach(link => { link.addEventListener('click', function(e){ e.preventDefault(); if(this.classList.contains('active')) return; const targetId=this.getAttribute('data-target'), targetSection=document.getElementById(targetId); navLinks.forEach(n=>n.classList.remove('active')); contentSections.forEach(s=>s.classList.remove('active')); this.classList.add('active'); if(targetSection){ targetSection.classList.add('active'); console.log(`Tab switched to: ${targetId}`); if(targetId==='dashboard-content'){ if(Object.keys(Chart.instances).length>0) Object.values(Chart.instances).forEach(i=>{try{i.resize();}catch(e){}}); else createCharts(); } else if(targetId==='environment-content'){ fetchSnortAlerts(); fetchSystemHealth(); } else if (targetId === 'analysis-content') { /* Maybe re-focus log window? */ } } else console.warn(`Target section missing: ${targetId}`); }); });
    // Ensure initial active tab is set correctly
    let activeFound=false, initialTargetId='dashboard-content'; navLinks.forEach(l=>{if(l.classList.contains('active')){if(activeFound)l.classList.remove('active'); else{activeFound=true; initialTargetId=l.getAttribute('data-target');}}}); if(!activeFound)document.getElementById('nav-dashboard')?.classList.add('active'); contentSections.forEach(s=>s.classList.remove('active')); const initialSection=document.getElementById(initialTargetId); if(initialSection){ initialSection.classList.add('active'); console.log(`Initial tab set to: ${initialTargetId}`); if(initialTargetId==='dashboard-content')createCharts(); else if(initialTargetId==='environment-content'){fetchSnortAlerts();fetchSystemHealth();} } else { console.warn("Initial target section not found, defaulting to dashboard."); document.getElementById('dashboard-content')?.classList.add('active'); createCharts(); } console.log("Tabs initialized.");
}

// --- Function to handle logout ---
async function handleLogout() {
    console.log("Attempting logout...");
    try { const r=await fetch('/logout',{method:'POST'}); if(r.ok||r.redirected) window.location.href='/'; else { const d=await r.json().catch(()=>({error:`HTTP ${r.status}`})); alert(`Logout failed: ${d.error||'Unknown error'}`); } }
    catch(e){ console.error('Logout network error:',e); alert('Logout failed due to a network error.'); }
}

// --- Function to refresh logs ---
async function refreshLogs() {
    const logOut=document.getElementById('realtime-log-output'), logStat=document.getElementById('log-status'); if(!logOut||!logStat) return;
    logStat.textContent='Refreshing...'; logOut.innerHTML='<span class="log-status" style="color:var(--text-secondary);padding:20px;">Loading historical logs...</span>'; // Indicate loading
    try { const r=await fetch('/refresh-logs'); // Assuming this endpoint gets recent historical logs
         if(!r.ok)throw new Error(`HTTP ${r.status}`); const logs=await r.json(); logOut.innerHTML=''; // Clear loading message
        if(logs&&Array.isArray(logs)){ if(logs.length===0)logStat.textContent='No historical logs found.'; else {logs.forEach(l=>{appendLogLine(l.message||l,logOut);}); logStat.textContent=`Refreshed (${logs.length} lines shown). Real-time stream active.`; logOut.scrollTop=logOut.scrollHeight;} }
        else logStat.textContent='Invalid data received from refresh.';
    } catch(e){ console.error('Log refresh failed:',e); logOut.innerHTML=`<span class="log-line error">Failed to refresh logs: ${e.message}</span>`; logStat.textContent='Refresh failed.'; }
}

// --- Report Generation Functions ---

function getReportFilters() {
    const params = new URLSearchParams();
    const startDate = document.getElementById('reportStartDate')?.value;
    const endDate = document.getElementById('reportEndDate')?.value;
    const priority = document.getElementById('reportPriority')?.value;
    if (startDate) params.append('startDate', startDate);
    if (endDate) params.append('endDate', endDate);
    if (priority) params.append('priority', priority);
    console.log("Report filters:", params.toString());
    return params;
}

function setReportStatus(message, type = 'info') {
    const statusEl = document.getElementById('report-status');
    if (statusEl) {
        statusEl.textContent = message;
        statusEl.className = 'report-status-message'; // Reset classes
        if (type === 'success') statusEl.classList.add('success');
        else if (type === 'error') statusEl.classList.add('error');
        else if (type === 'loading') statusEl.classList.add('loading'); // Use loading class if available
    }
}

function setReportButtonsDisabled(disabled) {
     document.getElementById('generateHtmlReportBtn')?.toggleAttribute('disabled', disabled);
     document.getElementById('generatePdfReportBtn')?.toggleAttribute('disabled', disabled);
}

async function generateSnortHtmlReport() {
    setReportStatus('Generating HTML report...', 'loading'); // Use loading type
    setReportButtonsDisabled(true);
    const filters = getReportFilters();
    const reportUrl = `/generate-report/snort/html?${filters.toString()}`; // ** ADJUST URL IF NEEDED **
    try {
        const response = await fetch(reportUrl);
        if (!response.ok) { const errD=await response.json().catch(()=>({error:`HTTP ${response.status}`})); throw new Error(errD.error||response.statusText); }
        const htmlContent = await response.text(); // Assuming backend sends HTML text
        setReportStatus('HTML report generated successfully. Opening in new tab...', 'success');
        const reportWindow = window.open("", "_blank");
        if(reportWindow) { reportWindow.document.write(htmlContent); reportWindow.document.close(); }
        else { setReportStatus('Could not open new tab. Please check your popup blocker settings.', 'error'); } // More specific error
    } catch (error) { console.error('HTML Report generation failed:', error); setReportStatus(`HTML Report Error: ${error.message}`, 'error');
    } finally { setReportButtonsDisabled(false); }
}

function generateSnortPdfReport() {
    setReportStatus('Initiating PDF report generation... Your download should start automatically.', 'loading'); // Use loading type
    setReportButtonsDisabled(true);
    const filters = getReportFilters();
    const reportUrl = `/generate-report/snort/pdf?${filters.toString()}`; // ** ADJUST URL IF NEEDED **

    // Use a hidden iframe or direct window location to trigger download
    // Using window.location.href is simpler for direct downloads triggered by server headers
    window.location.href = reportUrl;

    // Provide feedback, but acknowledge download start might take time or fail silently client-side
    setTimeout(() => {
        // Check if the status is still 'loading', implying no error was caught immediately
        const statusEl = document.getElementById('report-status');
        if (statusEl && statusEl.classList.contains('loading')) {
             setReportStatus('PDF generation requested. If download does not start, check server logs or network issues.', 'success');
        }
        setReportButtonsDisabled(false);
    }, 4000); // Wait a bit longer
}


// --- Main Initialization ---
document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM fully loaded and parsed. Initializing dashboard components...");
    try {
        // Get references for the modal *after* DOM is ready
        ipBlockedPopup = document.getElementById('ipBlockedPopup');
        blockedIpSpan = document.getElementById('blockedIpAddress');

        // Add event listeners for the modal
        if (ipBlockedPopup) {
            const closeButton = ipBlockedPopup.querySelector('.close-button');
            if (closeButton) {
                closeButton.addEventListener('click', hideIpBlockedPopup);
            }
            const okButton = ipBlockedPopup.querySelector('button'); // Assuming only one button is the OK button
            if (okButton) {
                okButton.addEventListener('click', hideIpBlockedPopup);
            }
            // Optional: Close the modal if the user clicks outside the content area
            ipBlockedPopup.addEventListener('click', function(event) {
                if (event.target === ipBlockedPopup) { // Check if the click was directly on the overlay
                    hideIpBlockedPopup();
                }
            });
        } else {
            console.warn("IP Blocked Popup element not found in the DOM.");
        }

        // Initialize other components
        initializeTabs();
        const btnFilters = document.getElementById('applyFilters'); if(btnFilters)btnFilters.addEventListener('click', applyFilters); else console.warn("Filter button ('applyFilters') not found.");
        initializeRealtimeLogs();
        const lnkLogout = document.getElementById('logout-link'); if(lnkLogout)lnkLogout.addEventListener('click', e=>{e.preventDefault();handleLogout();}); else console.warn("Logout link ('logout-link') not found.");
        const btnRefresh = document.getElementById('refresh-logs-button'); if(btnRefresh)btnRefresh.addEventListener('click', refreshLogs); else console.warn("Refresh logs button ('refresh-logs-button') not found.");
        const btnHtmlRpt = document.getElementById('generateHtmlReportBtn'); if(btnHtmlRpt)btnHtmlRpt.addEventListener('click', generateSnortHtmlReport); else console.warn("HTML Report button ('generateHtmlReportBtn') not found.");
        const btnPdfRpt = document.getElementById('generatePdfReportBtn'); if(btnPdfRpt)btnPdfRpt.addEventListener('click', generateSnortPdfReport); else console.warn("PDF Report button ('generatePdfReportBtn') not found.");

        // --- Test for IP Block Popup ---
        // Uncomment the line below to test the popup 5 seconds after the page loads
        // setTimeout(() => { showIpBlockedPopup('198.51.100.123'); }, 5000);

        console.log("Dashboard initialization complete.");

    } catch (error) {
         console.error("!!! FATAL INITIALIZATION ERROR !!!", error);
         // Attempt to display a user-friendly error message on the page
         try{document.body.innerHTML=`<div style="padding:30px;color:#fdd;background:#300;border:1px solid red;font-family:sans-serif;"><h2>Initialization Error</h2><p>The dashboard failed to load correctly. Please check the browser console (F12) for details.</p><pre style="white-space:pre-wrap; color:#fcc; margin-top:15px;">${error.message}\n${error.stack}</pre></div>`;}catch(displayError){}
    }
});
