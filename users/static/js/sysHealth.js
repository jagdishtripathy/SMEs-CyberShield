// app/static/js/dashboard.js
function initSysHealth() {
  // Chart instances
  let scoreGaugeChart = null;
  let cpuChartInstance = null;

  // Helper: Show toast notifications
  function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) return;

    const toastId = 'toast-' + Date.now();
    const bgClass = type === 'success' ? 'bg-success' : (type === 'error' ? 'bg-danger' : 'bg-info');
    const icon = type === 'success' ? 'fa-check-circle' : (type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle');

    const toastHTML = `
      <div id="${toastId}" class="toast show" role="alert">
        <div class="toast-header ${bgClass} text-white">
          <i class="fas ${icon} me-2"></i>
          <strong class="me-auto">${type === 'success' ? 'Success' : (type === 'error' ? 'Error' : 'Info')}</strong>
          <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
        </div>
        <div class="toast-body">
          ${message}
        </div>
      </div>
    `;

    toastContainer.insertAdjacentHTML('beforeend', toastHTML);
    const toastEl = document.getElementById(toastId);

    // Auto-hide after 4 seconds
    setTimeout(() => {
      if (toastEl) {
        toastEl.classList.remove('show');
        setTimeout(() => toastEl.remove(), 300);
      }
    }, 4000);
  }

  // Helper: render score gauge
  function renderScoreGauge(score) {
    const ctx = document.getElementById("scoreGauge");
    if (!ctx) return;

    if (scoreGaugeChart) scoreGaugeChart.destroy();

    scoreGaugeChart = new Chart(ctx.getContext("2d"), {
      type: "doughnut",
      data: {
        labels: ["Score", "Remaining"],
        datasets: [{ data: [score, 100 - score], borderWidth: 0 }]
      },
      options: {
        cutout: "70%",
        plugins: { legend: { display: false }, tooltip: { enabled: false } }
      }
    });

    // Add hover effect with percentage tooltip
    const canvasContainer = ctx.parentElement;
    let tooltipEl = document.getElementById('scoreTooltip');
    
    if (!tooltipEl) {
      tooltipEl = document.createElement('div');
      tooltipEl.id = 'scoreTooltip';
      tooltipEl.className = 'score-tooltip';
      canvasContainer.appendChild(tooltipEl);
    }

    ctx.addEventListener('mouseover', function(e) {
      tooltipEl.textContent = score + '%';
      tooltipEl.style.opacity = '1';
      tooltipEl.style.visibility = 'visible';
    });

    ctx.addEventListener('mousemove', function(e) {
      const rect = ctx.getBoundingClientRect();
      tooltipEl.style.left = (e.clientX - rect.left - 20) + 'px';
      tooltipEl.style.top = (e.clientY - rect.top - 30) + 'px';
    });

    ctx.addEventListener('mouseout', function(e) {
      tooltipEl.style.opacity = '0';
      tooltipEl.style.visibility = 'hidden';
    });

    const label = document.querySelector(".gauge-label");
    if (label) label.textContent = score;
  }

  // Helper: render CPU/Memory chart
  function renderCPUChart(cpu, mem) {
    const cpuChartEl = document.getElementById("cpuChart");
    if (!cpuChartEl) return;

    if (cpuChartInstance) cpuChartInstance.destroy();

    cpuChartInstance = new Chart(cpuChartEl.getContext("2d"), {
      type: "bar",
      data: {
        labels: ["CPU %", "Memory %"],
        datasets: [{ data: [cpu, mem], label: "Utilization", backgroundColor: ["#2196F3", "#FFC107"] }]
      },
      options: { scales: { y: { beginAtZero: true, max: 100 } } }
    });
  }

  // Helper: render security badges (OS-aware)
  function renderBadges(firewall, defender, platform) {
    // Show/hide OS-specific components
    const windowsComponents = document.getElementById("windowsSecurityComponents");
    const linuxComponents = document.getElementById("linuxSecurityComponents");
    const macComponents = document.getElementById("macosSecurityComponents");
    const platformBadge = document.getElementById("platformBadge");
    
    if (windowsComponents) windowsComponents.style.display = "none";
    if (linuxComponents) linuxComponents.style.display = "none";
    if (macComponents) macComponents.style.display = "none";

    function badgeEl(text, bgClass) {
      return `<span class="badge ${bgClass} fw-bold">${text}</span>`;
    }

    // Display platform badge
    if (platformBadge) {
      const platformBgClass = platform === "Windows" ? "bg-primary" : 
                             platform === "Linux" ? "bg-danger" : "bg-secondary";
      platformBadge.innerHTML = platform || "Unknown";
      platformBadge.className = `badge ${platformBgClass}`;
    }

    // WINDOWS: Firewall and Defender
    if (platform === "Windows") {
      if (windowsComponents) windowsComponents.style.display = "block";
      
      const fwStatusEl = document.getElementById("fwStatus");
      const avStatusEl = document.getElementById("avStatus");

      // Windows Firewall
      if (firewall && Array.isArray(firewall)) {
        let enabled = firewall.filter(p => p.Enabled == 1 || p.Enabled === true).length;
        let total = firewall.length;
        let bgClass;
        if (enabled === total) {
          bgClass = "bg-success";  // Green
        } else if (enabled > 0) {
          bgClass = "bg-warning text-dark";  // Yellow
        } else {
          bgClass = "bg-danger";  // Red
        }
        if (fwStatusEl) {
          fwStatusEl.className = "badge " + bgClass + " fw-bold";
          fwStatusEl.innerHTML = enabled + "/" + total + " profiles";
        }
      } else if (fwStatusEl) {
        fwStatusEl.className = "badge bg-secondary fw-bold";
        fwStatusEl.innerHTML = "Unknown";
      }

      // Windows Defender
      if (defender && defender.RealTimeProtectionEnabled) {
        if (avStatusEl) {
          avStatusEl.className = "badge bg-success fw-bold";
          avStatusEl.innerHTML = "Protection ON";
        }
      } else if (defender && defender.AntivirusEnabled && !defender.RealTimeProtectionEnabled) {
        if (avStatusEl) {
          avStatusEl.className = "badge bg-warning text-dark fw-bold";
          avStatusEl.innerHTML = "Limited";
        }
      } else if (defender && defender.error || !defender) {
        if (avStatusEl) {
          avStatusEl.className = "badge bg-danger fw-bold";
          avStatusEl.innerHTML = "DISABLED";
        }
      } else if (avStatusEl) {
        avStatusEl.className = "badge bg-secondary fw-bold";
        avStatusEl.innerHTML = "Unknown";
      }
    }
    
    // LINUX: Firewall, Antivirus, AIDE, fail2ban
    else if (platform === "Linux") {
      if (linuxComponents) linuxComponents.style.display = "block";
      
      const linuxFwEl = document.getElementById("linuxFwStatus");
      const linuxAvEl = document.getElementById("linuxAvStatus");
      const linuxAideEl = document.getElementById("linuxAideStatus");
      const linuxFail2banEl = document.getElementById("linuxFail2banStatus");

      // Check firewall status
      if (firewall && (firewall.ufw || firewall.firewalld || firewall.iptables)) {
        let enabled = false;
        let info = "";
        
        if (firewall.ufw && firewall.ufw.enabled) {
          enabled = true;
          info = "UFW Active";
        } else if (firewall.firewalld && firewall.firewalld.enabled) {
          enabled = true;
          info = "firewalld Active";
        } else if (firewall.iptables && firewall.iptables.installed) {
          enabled = true;
          info = `iptables (${firewall.iptables.rules_count} rules)`;
        }
        
        if (linuxFwEl) {
          linuxFwEl.className = enabled ? "badge bg-success fw-bold" : "badge bg-warning text-dark fw-bold";
          linuxFwEl.innerHTML = enabled ? info : "Not Active";
        }
      } else if (linuxFwEl) {
        linuxFwEl.className = "badge bg-secondary fw-bold";
        linuxFwEl.innerHTML = "Not Found";
      }

      // Check antivirus
      if (firewall && firewall.antivirus) {
        let hasAv = false;
        let avInfo = [];
        
        if (firewall.antivirus.clamav && firewall.antivirus.clamav.enabled) {
          hasAv = true;
          avInfo.push("ClamAV");
        }
        if (firewall.antivirus.sophos && !firewall.antivirus.sophos.error) {
          hasAv = true;
          avInfo.push("Sophos");
        }
        
        if (linuxAvEl) {
          linuxAvEl.className = hasAv ? "badge bg-success fw-bold" : "badge bg-warning text-dark fw-bold";
          linuxAvEl.innerHTML = hasAv ? avInfo.join("+") : "Not Installed";
        }
      } else if (linuxAvEl) {
        linuxAvEl.className = "badge bg-secondary fw-bold";
        linuxAvEl.innerHTML = "Info Unavailable";
      }

      // Check AIDE (File Integrity Monitor)
      if (firewall && firewall.antivirus && firewall.antivirus.aide && firewall.antivirus.aide.installed) {
        if (linuxAideEl) {
          linuxAideEl.className = firewall.antivirus.aide.enabled ? "badge bg-success fw-bold" : "badge bg-warning text-dark fw-bold";
          linuxAideEl.innerHTML = firewall.antivirus.aide.enabled ? "Installed & Active" : "Installed";
        }
      } else if (linuxAideEl) {
        linuxAideEl.className = "badge bg-secondary fw-bold";
        linuxAideEl.innerHTML = "Not Installed";
      }

      // Check fail2ban (Intrusion Prevention)
      if (firewall && firewall.antivirus && firewall.antivirus.fail2ban && firewall.antivirus.fail2ban.installed) {
        if (linuxFail2banEl) {
          linuxFail2banEl.className = firewall.antivirus.fail2ban.enabled ? "badge bg-success fw-bold" : "badge bg-warning text-dark fw-bold";
          linuxFail2banEl.innerHTML = firewall.antivirus.fail2ban.enabled ? "Active" : "Installed";
        }
      } else if (linuxFail2banEl) {
        linuxFail2banEl.className = "badge bg-secondary fw-bold";
        linuxFail2banEl.innerHTML = "Not Installed";
      }
    }
    
    // macOS: Basic firewall
    else if (platform === "Darwin") {
      if (macComponents) macComponents.style.display = "block";
      // macOS support can be expanded here
    }
  }

  // Helper: render disks
  function renderDisks(disks) {
    const dc = document.getElementById("disksContainer");
    if (!dc || !disks) return;

    dc.innerHTML = "";
    disks.forEach(d => {
      const p = (d.usage && d.usage.percent) || 0;
      const color = p > 90 ? "badge-crit" : (p > 75 ? "badge-warn" : "badge-ok");
      const html = `<div class="mb-2"><strong>${d.device}</strong>
        <div class="progress mt-1" style="height:14px;">
          <div class="progress-bar ${color === 'badge-crit' ? 'bg-danger' : (color==='badge-warn' ? 'bg-warning' : 'bg-success')}" role="progressbar" style="width: ${p}%">${p}%</div>
        </div></div>`;
      dc.insertAdjacentHTML("beforeend", html);
    });
  }

  // Helper: render meta info
  function renderMetaInfo(meta, collectedAt) {
    const hostnameEls = document.querySelectorAll("p");
    hostnameEls.forEach(p => {
      if (p.textContent.includes("Host:")) {
        p.innerHTML = `Host: <strong>${meta?.hostname || 'Unknown'}</strong>`;
      } else if (p.textContent.includes("OS:")) {
        p.innerHTML = `OS: <strong>${meta?.platform || 'Unknown'}</strong>`;
      } else if (p.textContent.includes("Collected:")) {
        p.innerHTML = `Collected: <strong>${collectedAt || '-'}</strong>`;
      }
    });
  }

  // Initial render
  renderScoreGauge(window.score || 0);
  
  console.log("Initial snapshot:", window.snapshot);
  
  if (window.snapshot && window.snapshot.system) {
    const snap = window.snapshot;
    const cpuPercent = snap.system.cpu?.cpu_percent || 0;
    const memPercent = snap.system.memory?.percent || 0;
    const hasDisks = snap.system.disks && snap.system.disks.length > 0;
    
    console.log("CPU:", cpuPercent, "Memory:", memPercent, "Disks:", snap.system.disks);
    
    renderCPUChart(cpuPercent, memPercent);
    renderBadges(snap.firewall, snap.defender, snap.meta?.platform);
    if (hasDisks) {
      renderDisks(snap.system.disks);
    } else {
      console.warn("No disk data available");
    }
    renderMetaInfo(snap.meta, window.snapshot.created_at);
    
    // Update health status
    const healthStatus = snap.system?.cpu?.cpu_percent > 80 ? 'Warning' : 'Good';
    const healthEl = document.getElementById('healthStatus');
    if (healthEl) healthEl.textContent = healthStatus;
  } else {
    console.warn("Snapshot or system data not available");
    const healthEl = document.getElementById('healthStatus');
    if (healthEl) healthEl.textContent = 'No Data';
  }

  // Auto-refresh dashboard
  function updateDashboard() {
    axios.get("/api/latest_snapshot")
      .then(resp => {
        const data = resp.data;
        if (!data.data) return;

        const snap = data.data;
        const score = data.score;
        window.score = score;

        renderScoreGauge(score);
        renderCPUChart(
          snap.system?.cpu?.cpu_percent || 0,
          snap.system?.memory?.percent || 0
        );
        renderBadges(snap.firewall, snap.defender, snap.meta?.platform);
        renderDisks(snap.system?.disks);
        renderMetaInfo(snap.meta, data.created_at);
      })
      .catch(err => {
        console.error("Failed to fetch latest snapshot:", err);
      });
  }

  setInterval(updateDashboard, 30000);

  // Collect now button
  const collectBtn = document.getElementById("collectBtn");
  if (collectBtn) {
    collectBtn.addEventListener("click", function(e) {
      e.preventDefault();
      e.stopPropagation();
      console.log("Collect button clicked");
      collectBtn.disabled = true;
      collectBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Collecting...';
      
      // Check if axios is available
      if (typeof axios === 'undefined') {
        showToast("Error: Axios library not loaded. Please refresh the page.", 'error');
        collectBtn.disabled = false;
        collectBtn.innerHTML = 'Collect Now';
        return;
      }
      
      axios.post("/api/collect")
        .then(resp => {
          console.log("Collection successful:", resp.data);
          updateDashboard();
          collectBtn.disabled = false;
          collectBtn.innerHTML = 'Collect Now';
          showToast("Data collected successfully!", 'success');
        })
        .catch(err => {
          console.error("Collection error:", err);
          const errorMsg = err.response?.data?.message || err.response?.data || err.message || "Unknown error";
          showToast("Collection failed: " + errorMsg, 'error');
          collectBtn.disabled = false;
          collectBtn.innerHTML = 'Collect Now';
        });
    });
  } else {
    console.warn("Collect button (#collectBtn) not found in DOM");
  }
}

// Ensure init runs whether the script loads before or after DOMContentLoaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initSysHealth);
} else {
  initSysHealth();
}
