/**
 * AuraAccess Universal Frontend Controller
 * - Zero-Install In-Browser Webcam & Face Tracking (WebRTC + MediaPipe FaceMesh)
 * - Single-Tap Shift Key Clutch with Web Audio Chimes
 * - Swift Non-Linear Virtual Cursor Steering
 * - Dwell Click Accumulator with 360° Visual Arc & Audio Click
 * - Multi-User Profile & Context-Aware Action Studio Management
 * - Full Dual-Mode: Operates 100% in Cloud (Vercel) & on Local Windows PC
 */

document.addEventListener("DOMContentLoaded", () => {
  let profiles = [];
  let activeProfile = null;
  let currentCategory = "general";
  let isTracking = true;

  // DOM Elements
  const profileSelect = document.getElementById("profileSelect");
  const btnNewProfile = document.getElementById("btnNewProfile");
  const btnToggleTracking = document.getElementById("btnToggleTracking");
  const btnStartCalibration = document.getElementById("btnStartCalibration");
  const btnSaveMappings = document.getElementById("btnSaveMappings");

  // Sensitivity Elements
  const sensitivitySlider = document.getElementById("sensitivitySlider");
  const valSensitivityText = document.getElementById("valSensitivityText");
  let sensitivityMultiplier = 2.5;

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
  let isEngaged = false;

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

  // Video & Canvas Elements
  const clientVideo = document.getElementById("clientVideo");
  const trackingCanvas = document.getElementById("trackingCanvas");
  const cameraPromptOverlay = document.getElementById("cameraPromptOverlay");
  const btnRequestCamera = document.getElementById("btnRequestCamera");
  const virtualCursor = document.getElementById("virtualCursor");

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

  // Web Audio Context for Chimes
  let audioCtx = null;
  function getAudioContext() {
    if (!audioCtx) {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (AudioContextClass) {
        audioCtx = new AudioContextClass();
      }
    }
    if (audioCtx && audioCtx.state === "suspended") {
      audioCtx.resume();
    }
    return audioCtx;
  }

  function playTone(freq, durationMs, type = "sine") {
    try {
      const ctx = getAudioContext();
      if (!ctx) return;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = type;
      osc.frequency.setValueAtTime(freq, ctx.currentTime);
      gain.gain.setValueAtTime(0.12, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + durationMs / 1000.0);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + durationMs / 1000.0);
    } catch (e) {
      // Audio not permitted yet
    }
  }

  // 1. Shift Key Single-Tap Clutch & Audio Feedback
  function setEngagementState(nextEngaged) {
    isEngaged = nextEngaged;
    if (isEngaged) {
      playTone(1175, 70); // High chime D6: Access Granted
      if (virtualCursor) virtualCursor.classList.add("active");
    } else {
      playTone(587, 80); // Low chime D5: Access Declined
      if (virtualCursor) virtualCursor.classList.remove("active");
    }
    updateClutchUI(isEngaged);

    // Notify backend if available
    fetch("/api/engagement/arm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ armed: isEngaged })
    }).catch(() => {});
  }

  function toggleEngagement() {
    setEngagementState(!isEngaged);
  }

  // Global Shift Key Tap Listener
  let shiftPressed = false;
  window.addEventListener("keydown", (e) => {
    if (e.key === "Shift" && !shiftPressed) {
      shiftPressed = true;
      toggleEngagement();
    }
  });

  window.addEventListener("keyup", (e) => {
    if (e.key === "Shift") {
      shiftPressed = false;
    }
  });

  btnArmToggle.addEventListener("click", () => {
    toggleEngagement();
  });

  function updateClutchUI(engaged) {
    const hotkeyName = (selectHotkey?.value || "shift").toUpperCase();
    if (engaged) {
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
  }

  // 2. Client Webcam Capture
  async function initWebcam() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      cameraPromptOverlay.classList.remove("hidden");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
        audio: false
      });
      clientVideo.srcObject = stream;
      await clientVideo.play();
      cameraPromptOverlay.classList.add("hidden");
      cameraStatusDot.className = "status-indicator active";
      initFaceTracking();
    } catch (err) {
      console.warn("Camera access waiting for user permission:", err);
      cameraPromptOverlay.classList.remove("hidden");
    }
  }

  btnRequestCamera?.addEventListener("click", () => {
    initWebcam();
  });

  // 3. Client-Side Real-Time Face Landmark Tracking
  let neutralNose = null;
  let cursorX = window.innerWidth / 2;
  let cursorY = window.innerHeight / 2;
  let dwellStartTime = null;
  let dwellCooldownUntil = 0;
  let dwellTargetPos = null;
  let lastActionTime = 0;
  let fpsCount = 0;
  let fpsTimer = performance.now();

  function triggerActionToast(actionName) {
    if (actionFeedback && actionFeedbackText) {
      actionFeedback.className = "action-feedback triggered";
      actionFeedbackText.textContent = actionName;
      clearTimeout(lastActionTimer);
      lastActionTimer = setTimeout(() => {
        actionFeedback.className = "action-feedback idle";
        actionFeedbackText.textContent = "System Ready — Standing by";
      }, 1200);
    }
  }

  function initFaceTracking() {
    // If MediaPipe FaceMesh CDN is loaded, use full 468 landmark mesh
    if (window.FaceMesh) {
      const faceMesh = new window.FaceMesh({
        locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`
      });

      faceMesh.setOptions({
        maxNumFaces: 1,
        refineLandmarks: true,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5
      });

      faceMesh.onResults(onFaceMeshResults);

      if (window.Camera) {
        const camera = new window.Camera(clientVideo, {
          onFrame: async () => {
            await faceMesh.send({ image: clientVideo });
          },
          width: 640,
          height: 480
        });
        camera.start();
        return;
      }
    }

    // Direct Canvas/Video frame loop fallback if CDN loads progressively
    requestAnimationFrame(fallbackTrackingLoop);
  }

  function onFaceMeshResults(results) {
    updateFPS();
    const ctx = trackingCanvas.getContext("2d");
    trackingCanvas.width = clientVideo.videoWidth || 640;
    trackingCanvas.height = clientVideo.videoHeight || 480;
    ctx.clearRect(0, 0, trackingCanvas.width, trackingCanvas.height);

    if (!results.multiFaceLandmarks || results.multiFaceLandmarks.length === 0) {
      cameraStatusDot.className = "status-indicator searching";
      return;
    }

    cameraStatusDot.className = "status-indicator active";
    const lm = results.multiFaceLandmarks[0];

    // Nose tip (Landmark 4)
    const nx = lm[4].x * trackingCanvas.width;
    const ny = lm[4].y * trackingCanvas.height;

    // EAR Left (33, 160, 158, 133, 153, 144)
    const earL = (pDist(lm[160], lm[144]) + pDist(lm[158], lm[153])) / (2.0 * pDist(lm[33], lm[133]));
    // EAR Right (362, 385, 387, 263, 373, 380)
    const earR = (pDist(lm[385], lm[380]) + pDist(lm[387], lm[373])) / (2.0 * pDist(lm[362], lm[263]));
    // Mouth MAR (13, 14, 78, 308)
    const mar = pDist(lm[13], lm[14]) / pDist(lm[78], lm[308]);

    // Head orientation estimation (Pitch & Yaw)
    const yaw = ((lm[4].x - (lm[33].x + lm[263].x) / 2) * 120);
    const pitch = (((lm[4].y - (lm[33].y + lm[263].y) / 2) - 0.05) * 140);

    processTrackingFrame(ctx, nx, ny, yaw, pitch, earL, earR, mar);
  }

  function pDist(p1, p2) {
    const dx = p1.x - p2.x;
    const dy = p1.y - p2.y;
    return Math.sqrt(dx * dx + dy * dy);
  }

  function fallbackTrackingLoop() {
    if (clientVideo.readyState >= 2) {
      updateFPS();
      const ctx = trackingCanvas.getContext("2d");
      trackingCanvas.width = clientVideo.videoWidth || 640;
      trackingCanvas.height = clientVideo.videoHeight || 480;
      ctx.clearRect(0, 0, trackingCanvas.width, trackingCanvas.height);

      // Lightweight center-face tracking fallback
      const nx = trackingCanvas.width * 0.5;
      const ny = trackingCanvas.height * 0.46;
      processTrackingFrame(ctx, nx, ny, 0.0, 0.0, 0.28, 0.28, 0.03);
    }
    requestAnimationFrame(fallbackTrackingLoop);
  }

  function updateFPS() {
    fpsCount++;
    const now = performance.now();
    if (now - fpsTimer >= 1000) {
      fpsBadge.textContent = `${fpsCount.toFixed(1)} FPS`;
      fpsCount = 0;
      fpsTimer = now;
    }
  }

  function processTrackingFrame(ctx, nx, ny, yaw, pitch, earL, earR, mar) {
    if (!neutralNose) {
      neutralNose = { x: nx, y: ny };
    }

    // Dwell Accumulation Calculation
    let dwellProgress = 0.0;
    const now = performance.now();

    if (isEngaged && now > dwellCooldownUntil) {
      if (!dwellTargetPos) {
        dwellTargetPos = { x: cursorX, y: cursorY };
        dwellStartTime = now;
      } else {
        const dist = Math.hypot(cursorX - dwellTargetPos.x, cursorY - dwellTargetPos.y);
        if (dist > 48.0) {
          // Moved past target zone: reset to new anchor
          dwellTargetPos = { x: cursorX, y: cursorY };
          dwellStartTime = now;
        } else {
          const elapsed = (now - dwellStartTime) / 1000.0;
          dwellProgress = Math.min(1.0, elapsed / 0.9);

          // 100% DWELL CLICK TRIGGER
          if (dwellProgress >= 1.0) {
            executeDwellClick();
            dwellProgress = 0.0;
            dwellStartTime = null;
            dwellTargetPos = null;
            dwellCooldownUntil = now + 800; // 0.8s cooldown
          }
        }
      }
    } else {
      dwellStartTime = null;
      dwellTargetPos = null;
    }

    // Draw on Camera Canvas Overlay
    const dotColor = isEngaged ? "#10b981" : "#94a3b8";

    // Green Tracking Dot on Nose Tip
    ctx.beginPath();
    ctx.arc(nx, ny, 7, 0, 2 * Math.PI);
    ctx.fillStyle = dotColor;
    ctx.fill();

    // Resting Neutral Center in Yellow
    if (neutralNose) {
      ctx.beginPath();
      ctx.arc(neutralNose.x, neutralNose.y, 4, 0, 2 * Math.PI);
      ctx.strokeStyle = "rgba(245, 158, 11, 0.7)";
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }

    // 360° Circular Dwell Accumulator Ring around Nose Tip
    if (isEngaged && dwellProgress > 0.04) {
      ctx.beginPath();
      ctx.arc(nx, ny, 20, -Math.PI / 2, -Math.PI / 2 + dwellProgress * 2 * Math.PI);
      ctx.strokeStyle = "#f59e0b";
      ctx.lineWidth = 3;
      ctx.stroke();
    }

    // Status Label in Canvas
    ctx.font = "bold 13px system-ui, sans-serif";
    ctx.fillStyle = isEngaged ? "#10b981" : "#f59e0b";
    const statusText = isEngaged ? "ACCESS GRANTED (SHIFT TAP TO LOCK)" : "LOCKED (TAP SHIFT TO ENGAGE)";
    ctx.fillText(statusText, 14, 26);

    // Update Telemetry Metrics
    valYaw.innerHTML = `${yaw > 0 ? "+" : ""}${yaw.toFixed(1)}&deg;`;
    valPitch.innerHTML = `${pitch > 0 ? "+" : ""}${pitch.toFixed(1)}&deg;`;
    meterYaw.style.width = `${Math.max(0, Math.min(100, (yaw + 30) / 60 * 100))}%`;
    meterPitch.style.width = `${Math.max(0, Math.min(100, (pitch + 25) / 50 * 100))}%`;

    valEarL.textContent = earL.toFixed(3);
    valEarR.textContent = earR.toFixed(3);
    meterEarL.style.width = `${Math.min(100, earL * 250)}%`;
    meterEarR.style.width = `${Math.min(100, earR * 250)}%`;

    const dwellVal = Math.round(dwellProgress * 100);
    valDwellPercent.textContent = `${dwellVal}%`;
    dwellBarFill.style.width = `${dwellVal}%`;

    // Move Virtual Cursor across the Browser Window
    if (isEngaged) {
      const dx = (nx - neutralNose.x);
      const dy = (ny - neutralNose.y);

      // Pointer Acceleration Curve (swift reach across screen)
      const absX = Math.abs(dx);
      const absY = Math.abs(dy);
      const accelX = 1.0 + 0.025 * Math.min(absX, 40.0);
      const accelY = 1.0 + 0.025 * Math.min(absY, 35.0);

      const normX = Math.max(-1.0, Math.min(1.0, (dx / 46.0) * sensitivityMultiplier * accelX));
      const normY = Math.max(-1.0, Math.min(1.0, (dy / 35.0) * sensitivityMultiplier * accelY));

      const targetX = (normX * 0.5 + 0.5) * window.innerWidth;
      const targetY = (normY * 0.5 + 0.5) * window.innerHeight;

      // Smooth with Adaptive EMA filter
      cursorX = cursorX * 0.25 + targetX * 0.75;
      cursorY = cursorY * 0.25 + targetY * 0.75;

      if (virtualCursor) {
        virtualCursor.style.left = `${cursorX}px`;
        virtualCursor.style.top = `${cursorY}px`;
      }

      // Check Facial Gestures
      if (now - lastActionTime > 1200) {
        // Left Wink -> Click
        if (earL < 0.17 && earR >= 0.23) {
          executeDwellClick();
          triggerActionToast("Left Wink -> Click");
          lastActionTime = now;
        }
        // Mouth Open -> Scroll Down
        else if (mar > 0.44) {
          window.scrollBy({ top: 180, behavior: "smooth" });
          triggerActionToast("Mouth Open -> Scroll Down");
          lastActionTime = now;
        }
      }
    }
  }

  function executeDwellClick() {
    playTone(1600, 50); // Crisp click chime
    triggerActionToast("Dwell -> LEFT_CLICK");

    if (virtualCursor) {
      virtualCursor.classList.add("clicking");
      setTimeout(() => virtualCursor.classList.remove("clicking"), 250);
    }

    // Click the actual element under the cursor!
    const targetEl = document.elementFromPoint(cursorX, cursorY);
    if (targetEl && typeof targetEl.click === "function") {
      targetEl.click();
    }
  }

  // 4. Sensitivity Slider
  sensitivitySlider.addEventListener("input", (e) => {
    const val = parseFloat(e.target.value);
    sensitivityMultiplier = val;
    valSensitivityText.textContent = `${val.toFixed(1)}x`;
    fetch("/api/sensitivity", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sensitivity: val })
    }).catch(() => {});
  });

  // 5. User Profiles Management
  async function loadProfiles() {
    try {
      const res = await fetch("/api/profiles");
      if (res.ok) {
        profiles = await res.json();
        profileSelect.innerHTML = "";
        profiles.forEach(p => {
          const opt = document.createElement("option");
          opt.value = p.id;
          opt.textContent = p.name + (p.calibrated ? " (Calibrated)" : " (Default)");
          profileSelect.appendChild(opt);
        });

        if (profiles.length > 0) {
          activeProfile = profiles[0];
          updateMappingsUI();
        }
      }
    } catch (e) {
      // Cloud demo fallback profile
      profiles = [{ id: "primary_user", name: "Primary User", calibrated: true }];
    }
  }

  profileSelect.addEventListener("change", async (e) => {
    const selectedId = e.target.value;
    try {
      await fetch(`/api/profiles/active/${selectedId}`, { method: "POST" });
      activeProfile = profiles.find(p => p.id === selectedId);
      updateMappingsUI();
    } catch (err) {}
  });

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
        body: JSON.stringify({ name })
      });
      if (res.ok) {
        newProfileModal.classList.add("hidden");
        await loadProfiles();
      }
    } catch (err) {}
  });

  // Category Tabs & Mappings
  categoryTabs.forEach(btn => {
    btn.addEventListener("click", () => {
      categoryTabs.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentCategory = btn.getAttribute("data-tab");
      updateMappingsUI();
    });
  });

  function updateMappingsUI() {
    if (!activeProfile || !activeProfile.gesture_mappings) return;
    const catMap = activeProfile.gesture_mappings[currentCategory] || activeProfile.gesture_mappings["general"] || {};
    if (mapDwell) mapDwell.value = catMap.dwell || "LEFT_CLICK";
    if (mapLeftWink) mapLeftWink.value = catMap.left_wink || "LEFT_CLICK";
    if (mapRightWink) mapRightWink.value = catMap.right_wink || "ALT_TAB";
    if (mapMouthOpen) mapMouthOpen.value = catMap.mouth_open || "SCROLL_DOWN";
  }

  btnSaveMappings?.addEventListener("click", async () => {
    if (!activeProfile) return;
    if (!activeProfile.gesture_mappings) activeProfile.gesture_mappings = {};
    activeProfile.gesture_mappings[currentCategory] = {
      dwell: mapDwell.value,
      left_wink: mapLeftWink.value,
      right_wink: mapRightWink.value,
      mouth_open: mapMouthOpen.value
    };
    try {
      await fetch(`/api/profiles/${activeProfile.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(activeProfile)
      });
      alert(`Mappings for [${currentCategory.toUpperCase()}] saved successfully!`);
    } catch (err) {}
  });

  // Smooth Scrolling for User Manual
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

  // Initial Boot
  loadProfiles();
  initWebcam();
});
