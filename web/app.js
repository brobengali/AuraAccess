/**
 * AuraAccess Frontend Controller
 * Connects to local FastAPI WebSocket & REST APIs.
 * Supports multi-user profile switching, dynamic gesture mappings, and real-time telemetry.
 */

document.addEventListener("DOMContentLoaded", () => {
  let profiles = [];
  let activeProfile = null;
  let currentCategory = "general";
  let isTracking = false;

  // DOM Elements
  const profileSelect = document.getElementById("profileSelect");
  const btnNewProfile = document.getElementById("btnNewProfile");
  const btnToggleTracking = document.getElementById("btnToggleTracking");
  const btnStartCalibration = document.getElementById("btnStartCalibration");
  const btnSaveMappings = document.getElementById("btnSaveMappings");

  // Sensitivity Elements
  const sensitivitySlider = document.getElementById("sensitivitySlider");
  const valSensitivityText = document.getElementById("valSensitivityText");

  // Engagement / Clutch Elements
  const engagementStatusBanner = document.getElementById("engagementStatusBanner");
  const engagementIcon = document.getElementById("engagementIcon");
  const engagementTitle = document.getElementById("engagementTitle");
  const engagementHint = document.getElementById("engagementHint");
  const selectHotkey = document.getElementById("selectHotkey");
  const selectEngageMode = document.getElementById("selectEngageMode");
  const btnArmToggle = document.getElementById("btnArmToggle");
  const armBtnText = document.getElementById("armBtnText");
  const navClutchIndicator = document.getElementById("navClutchIndicator");
  const navClutchIcon = document.getElementById("navClutchIcon");
  const navClutchLabel = document.getElementById("navClutchLabel");
  let softwareArmed = false;

  btnArmToggle.addEventListener("click", async () => {
    softwareArmed = !softwareArmed;
    try {
      const res = await fetch("/api/engagement/arm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ armed: softwareArmed })
      });
      const data = await res.json();
      updateArmButton(data.engaged);
    } catch (e) {
      console.error("Error setting arm toggle:", e);
    }
  });

  function updateArmButton(isArmed) {
    softwareArmed = isArmed;
    if (isArmed) {
      btnArmToggle.className = "btn btn-arm-toggle on";
      armBtnText.textContent = "Decline Access (Lock)";
      engagementIcon.textContent = "🟢";
      if (navClutchIndicator) {
        navClutchIndicator.className = "clutch-header-badge active";
        navClutchIcon.textContent = "🟢";
        navClutchLabel.innerHTML = "Control: <strong>ACTIVE</strong> (Tap Shift to lock)";
      }
    } else {
      btnArmToggle.className = "btn btn-arm-toggle off";
      armBtnText.textContent = "Grant Access (Tap Shift)";
      engagementIcon.textContent = "🔒";
      if (navClutchIndicator) {
        navClutchIndicator.className = "clutch-header-badge locked";
        navClutchIcon.textContent = "🔒";
        navClutchLabel.innerHTML = "Tap <strong>SHIFT</strong> to Grant Access";
      }
    }
  }

  // Telemetry Elements
  const cameraStatusDot = document.getElementById("cameraStatusDot");
  const fpsBadge = document.getElementById("fpsBadge");
  const valYaw = document.getElementById("valYaw");
  const meterYaw = document.getElementById("meterYaw");
  const valPitch = document.getElementById("valPitch");
  const meterPitch = document.getElementById("meterPitch");
  const valEarL = document.getElementById("valEarL");
  const meterEarL = document.getElementById("meterEarL");
  const valEarR = document.getElementById("valEarR");
  const meterEarR = document.getElementById("meterEarR");
  const valDwellPercent = document.getElementById("valDwellPercent");
  const dwellBarFill = document.getElementById("dwellBarFill");
  const detectedAppTitle = document.getElementById("detectedAppTitle");
  const detectedAppCategory = document.getElementById("detectedAppCategory");
  const actionFeedback = document.getElementById("actionFeedback");
  const actionFeedbackText = document.getElementById("actionFeedbackText");

  // Modal Elements
  const newProfileModal = document.getElementById("newProfileModal");
  const newProfileName = document.getElementById("newProfileName");
  const btnCancelNewProfile = document.getElementById("btnCancelNewProfile");
  const btnSaveNewProfile = document.getElementById("btnSaveNewProfile");

  // Mapping Selectors
  const mapDwell = document.getElementById("map_dwell");
  const mapLeftWink = document.getElementById("map_left_wink");
  const mapRightWink = document.getElementById("map_right_wink");
  const mapMouthOpen = document.getElementById("map_mouth_open");
  const categoryTabs = document.querySelectorAll(".tab-btn");

  // 1. Fetch & Initialize User Profiles
  async function loadProfiles() {
    try {
      const res = await fetch("/api/profiles");
      profiles = await res.json();
      profileSelect.innerHTML = "";

      profiles.forEach(p => {
        const opt = document.createElement("option");
        opt.value = p.id;
        opt.textContent = p.name + (p.calibrated ? " (Calibrated)" : " (Uncalibrated)");
        profileSelect.appendChild(opt);
      });

      if (profiles.length > 0) {
        // Find active profile
        const statusRes = await fetch("/api/status");
        const status = await statusRes.json();
        const activeId = status.active_profile_id || profiles[0].id;
        profileSelect.value = activeId;
        activeProfile = profiles.find(p => p.id === activeId) || profiles[0];
        updateMappingsUI();
        updateTrackingButton(status.tracking_enabled);
      }
    } catch (err) {
      console.error("Failed to load profiles:", err);
    }
  }

  // 2. Profile Selection Change
  profileSelect.addEventListener("change", async (e) => {
    const selectedId = e.target.value;
    try {
      await fetch(`/api/profiles/active/${selectedId}`, { method: "POST" });
      activeProfile = profiles.find(p => p.id === selectedId);
      updateMappingsUI();
    } catch (err) {
      console.error("Failed to switch profile:", err);
    }
  });

  // 3. New Profile Modal
  btnNewProfile.addEventListener("click", () => {
    newProfileName.value = "";
    newProfileModal.classList.remove("hidden");
    newProfileName.focus();
  });

  btnCancelNewProfile.addEventListener("click", () => {
    newProfileModal.classList.add("hidden");
  });

  btnSaveNewProfile.addEventListener("click", async () => {
    const name = newProfileName.value.trim();
    if (!name) return;

    try {
      const res = await fetch("/api/profiles", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name })
      });
      const created = await res.json();
      newProfileModal.classList.add("hidden");
      await loadProfiles();
      profileSelect.value = created.id;
      activeProfile = created;
      updateMappingsUI();
      alert(`Profile "${name}" created! Please click "Recalibrate Mobility Range" to adapt to this user.`);
    } catch (err) {
      console.error("Error creating profile:", err);
    }
  });

  // 4. Update Mappings UI based on active profile and selected category tab
  function updateMappingsUI() {
    if (!activeProfile) return;
    const mappings = (activeProfile.gesture_mappings && activeProfile.gesture_mappings[currentCategory]) || {};

    mapDwell.value = mappings.dwell || "LEFT_CLICK";
    mapLeftWink.value = mappings.left_wink || "LEFT_CLICK";
    mapRightWink.value = mappings.right_wink || "ALT_TAB";
    mapMouthOpen.value = mappings.mouth_open || "SCROLL_DOWN";
  }

  // 5. Category Tabs Switching
  categoryTabs.forEach(tab => {
    tab.addEventListener("click", () => {
      categoryTabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      currentCategory = tab.dataset.tab;
      updateMappingsUI();
    });
  });

  // 6. Save Mappings
  btnSaveMappings.addEventListener("click", async () => {
    if (!activeProfile) return;
    if (!activeProfile.gesture_mappings) activeProfile.gesture_mappings = {};

    activeProfile.gesture_mappings[currentCategory] = {
      dwell: mapDwell.value,
      left_wink: mapLeftWink.value,
      right_wink: mapRightWink.value,
      mouth_open: mapMouthOpen.value
    };

    try {
      const res = await fetch(`/api/profiles/${activeProfile.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(activeProfile)
      });
      activeProfile = await res.json();
      alert(`Mappings for [${currentCategory.toUpperCase()}] saved to profile "${activeProfile.name}"!`);
    } catch (err) {
      console.error("Error saving mappings:", err);
    }
  });

  // 7. Toggle Tracking Controller
  btnToggleTracking.addEventListener("click", async () => {
    const nextState = !isTracking;
    try {
      const res = await fetch("/api/tracking/toggle", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: nextState })
      });
      const data = await res.json();
      updateTrackingButton(data.tracking_enabled);
    } catch (err) {
      console.error("Failed to toggle tracking:", err);
    }
  });

  function updateTrackingButton(trackingOn) {
    isTracking = trackingOn;
    if (trackingOn) {
      btnToggleTracking.className = "btn btn-toggle on";
      btnToggleTracking.querySelector(".toggle-text").textContent = "Tracking ACTIVE";
    } else {
      btnToggleTracking.className = "btn btn-toggle off";
      btnToggleTracking.querySelector(".toggle-text").textContent = "Tracking OFF";
    }
  }

  // 8. Trigger Calibration
  btnStartCalibration.addEventListener("click", () => {
    alert("To recalibrate, the on-screen calibration wizard will open on your desktop with visual guidance.");
    // Calibration can be run locally via terminal or triggered
  });

  // 9. Telemetry Connection (WebSocket with HTTP polling fallback for Vercel/Cloud)
  let wsRetryCount = 0;
  let pollingInterval = null;

  function startHttpPolling() {
    if (pollingInterval) return;
    pollingInterval = setInterval(async () => {
      try {
        const res = await fetch("/api/status");
        if (res.ok) {
          const data = await res.json();
          renderTelemetry(data);
        }
      } catch (e) {
        // silent catch
      }
    }, 800);
  }

  function connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/telemetry`;
    let ws = null;

    try {
      ws = new WebSocket(wsUrl);
    } catch (e) {
      startHttpPolling();
      return;
    }

    ws.onopen = () => {
      console.log("WebSocket connected to AuraAccess telemetry.");
      wsRetryCount = 0;
      if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
      }
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        renderTelemetry(data);
      } catch (e) {
        console.error("Error parsing telemetry frame", e);
      }
    };

    ws.onclose = () => {
      wsRetryCount++;
      if (wsRetryCount > 2) {
        // Fallback to HTTP polling (e.g. on serverless Vercel)
        startHttpPolling();
      } else {
        setTimeout(connectWebSocket, 2000);
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  }

  // 10. Render Live Metrics
  let lastActionTimer = null;

  function renderTelemetry(data) {
    // Camera status dot
    if (data.face_detected) {
      cameraStatusDot.className = "status-indicator active";
    } else {
      cameraStatusDot.className = "status-indicator searching";
    }

    fpsBadge.textContent = `${data.fps || 0.0} FPS`;

    // Clutch / Engagement banner
    // Clutch / Engagement state
    const hotkeyName = (data.engagement_hotkey || "shift").toUpperCase();
    if (data.engaged) {
      engagementStatusBanner.className = "engagement-banner engaged";
      engagementIcon.textContent = "🟢";
      engagementTitle.textContent = `Head Controls ACTIVE (Tap ${hotkeyName} to Decline)`;
      engagementHint.textContent = `Tap ${hotkeyName} again (or click Decline) to lock cursor instantly.`;
      btnArmToggle.className = "btn btn-arm-toggle on";
      armBtnText.textContent = "Decline Access (Lock)";
      if (navClutchIndicator) {
        navClutchIndicator.className = "clutch-header-badge active";
        navClutchIcon.textContent = "🟢";
        navClutchLabel.innerHTML = `Control: <strong>ACTIVE</strong> (Tap ${hotkeyName} to Lock)`;
      }
    } else {
      engagementStatusBanner.className = "engagement-banner disengaged";
      engagementIcon.textContent = "🔒";
      engagementTitle.textContent = "Safety Standby: Cursor & Gestures Locked";
      engagementHint.innerHTML = `Tap <strong>${hotkeyName} key</strong> (or click button) to get access. Tap again to decline access.`;
      btnArmToggle.className = "btn btn-arm-toggle off";
      armBtnText.textContent = "Grant Access (Tap Shift)";
      if (navClutchIndicator) {
        navClutchIndicator.className = "clutch-header-badge locked";
        navClutchIcon.textContent = "🔒";
        navClutchLabel.innerHTML = `Tap <strong>${hotkeyName}</strong> to Grant Access`;
      }
    }

    // Angles
    valYaw.innerHTML = `${data.yaw > 0 ? "+" : ""}${data.yaw}&deg;`;
    valPitch.innerHTML = `${data.pitch > 0 ? "+" : ""}${data.pitch}&deg;`;

    // Normalize meters: Yaw [-30 to +30] -> [0 to 100%]
    const yawPercent = Math.max(0, Math.min(100, (data.yaw + 30) / 60 * 100));
    meterYaw.style.width = `${yawPercent}%`;

    // Pitch [-25 to +25] -> [0 to 100%]
    const pitchPercent = Math.max(0, Math.min(100, (data.pitch + 25) / 50 * 100));
    meterPitch.style.width = `${pitchPercent}%`;

    // Eye aspect ratios
    valEarL.textContent = data.ear_left.toFixed(3);
    valEarR.textContent = data.ear_right.toFixed(3);
    meterEarL.style.width = `${Math.min(100, data.ear_left * 250)}%`;
    meterEarR.style.width = `${Math.min(100, data.ear_right * 250)}%`;

    // Dwell Progress
    const dwellVal = Math.round((data.dwell_progress || 0) * 100);
    valDwellPercent.textContent = `${dwellVal}%`;
    dwellBarFill.style.width = `${dwellVal}%`;

    // Detected App Context
    if (data.active_app_title) {
      detectedAppTitle.textContent = data.active_app_title;
    }
    if (data.active_app_category) {
      detectedAppCategory.textContent = data.active_app_category;
    }

    // Action Toast
    if (data.active_action) {
      actionFeedback.className = "action-feedback triggered";
      actionFeedbackText.textContent = data.active_action;

      clearTimeout(lastActionTimer);
      lastActionTimer = setTimeout(() => {
        actionFeedback.className = "action-feedback idle";
        actionFeedbackText.textContent = "System Ready — Standing by";
      }, 1200);
    }
  }

  // Sensitivity Slider input listener
  sensitivitySlider.addEventListener("input", async (e) => {
    const val = parseFloat(e.target.value);
    valSensitivityText.textContent = `${val.toFixed(1)}x`;
    try {
      await fetch("/api/sensitivity", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sensitivity: val })
      });
    } catch (err) {
      console.error("Error setting sensitivity:", err);
    }
  });

  // Engagement / Clutch listeners
  async function syncEngagementConfig() {
    try {
      await fetch("/api/engagement", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mode: selectEngageMode.value,
          hotkey: selectHotkey.value
        })
      });
    } catch (e) {
      console.error("Error setting engagement:", e);
    }
  }

  selectHotkey.addEventListener("change", syncEngagementConfig);
  selectEngageMode.addEventListener("change", syncEngagementConfig);

  // Documentation smooth scrolling listeners
  const btnOpenDocs = document.getElementById("btnOpenDocs");
  const userGuideSection = document.getElementById("userGuideSection");
  const btnBackToCockpit = document.getElementById("btnBackToCockpit");

  if (btnOpenDocs && userGuideSection) {
    btnOpenDocs.addEventListener("click", () => {
      userGuideSection.scrollIntoView({ behavior: "smooth" });
    });
  }

  if (btnBackToCockpit) {
    btnBackToCockpit.addEventListener("click", (e) => {
      e.preventDefault();
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }

  // Initial load
  loadProfiles();
  connectWebSocket();
});
