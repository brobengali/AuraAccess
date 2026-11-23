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

  // 2. Client Webcam Capture & Tracking Controller
  function setTrackingState(enabled) {
    isTracking = enabled;
    if (btnToggleTracking) {
      if (isTracking) {
        btnToggleTracking.className = "btn btn-toggle on";
        const txt = btnToggleTracking.querySelector(".toggle-text");
        if (txt) txt.textContent = "Tracking ON";
        triggerActionToast("Tracking Controller: ACTIVE");
        playTone(880, 60);
      } else {
        btnToggleTracking.className = "btn btn-toggle off";
        const txt = btnToggleTracking.querySelector(".toggle-text");
        if (txt) txt.textContent = "Tracking OFF";
        triggerActionToast("Tracking Controller: PAUSED");
        playTone(440, 80);
        if (virtualCursor) virtualCursor.classList.remove("active");
      }
    }
    fetch("/api/tracking/toggle", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: isTracking })
    }).catch(() => {});
  }

  btnToggleTracking?.addEventListener("click", () => {
    setTrackingState(!isTracking);
  });

  async function initWebcam() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      cameraPromptOverlay?.classList.remove("hidden");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
        audio: false
      });
      clientVideo.srcObject = stream;
      clientVideo.muted = true;
      clientVideo.setAttribute("playsinline", "true");
      await clientVideo.play();
      cameraPromptOverlay?.classList.add("hidden");
      cameraStatusDot.className = "status-indicator active";
      initFaceTracking();
    } catch (err) {
      console.warn("Camera access waiting for user permission:", err);
      cameraPromptOverlay?.classList.remove("hidden");
    }
  }

  btnRequestCamera?.addEventListener("click", () => {
    initWebcam();
  });

  // 3. Client-Side Real-Time Face Landmark Tracking
  let neutralNose = null;
  let lastNoseX = null;
  let lastNoseY = null;
  let cursorX = window.innerWidth / 2;
  let cursorY = window.innerHeight / 2;
  let dwellStartTime = null;
  let dwellCooldownUntil = 0;
  let dwellTargetPos = null;
  let lastActionTime = 0;
  let lastActionTimer = null;
  let fpsCount = 0;
  let fpsTimer = performance.now();
  let faceMesh = null;
  let isProcessingMesh = false;
  let lastLandmarks = null;
  let lastLandmarkTimestamp = 0;

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
    if (window.FaceMesh && !faceMesh) {
      faceMesh = new window.FaceMesh({
        locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`
      });

      faceMesh.setOptions({
        maxNumFaces: 1,
        refineLandmarks: true,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5
      });

      faceMesh.onResults((results) => {
        if (results.multiFaceLandmarks && results.multiFaceLandmarks.length > 0) {
          lastLandmarks = results.multiFaceLandmarks[0];
          lastLandmarkTimestamp = performance.now();
        } else {
          lastLandmarks = null;
        }
      });
    }

    // Unified single 60 FPS render and tracking loop
    requestAnimationFrame(trackingRenderLoop);
  }

  function pDist(p1, p2) {
    const dx = p1.x - p2.x;
    const dy = p1.y - p2.y;
    return Math.sqrt(dx * dx + dy * dy);
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

  // Recalibrate Neutral Center Anchor
  btnStartCalibration?.addEventListener("click", () => {
    if (lastNoseX !== null && lastNoseY !== null) {
      neutralNose = { x: lastNoseX, y: lastNoseY };
    } else {
      neutralNose = { x: trackingCanvas.width / 2, y: trackingCanvas.height * 0.48 };
    }
    cursorX = window.innerWidth / 2;
    cursorY = window.innerHeight / 2;
    if (virtualCursor) {
      virtualCursor.style.left = `${cursorX}px`;
      virtualCursor.style.top = `${cursorY}px`;
    }
    triggerActionToast("Center Position Calibrated 🎯");
    playTone(1320, 60);
    setTimeout(() => playTone(1760, 80), 80);
  });

  // Main Render & Tracking Loop
  function trackingRenderLoop() {
    if (clientVideo && clientVideo.readyState >= 2) {
      updateFPS();
      const ctx = trackingCanvas.getContext("2d");
      const vw = clientVideo.videoWidth || 640;
      const vh = clientVideo.videoHeight || 480;
      if (trackingCanvas.width !== vw || trackingCanvas.height !== vh) {
        trackingCanvas.width = vw;
        trackingCanvas.height = vh;
      }

      const w = trackingCanvas.width;
      const h = trackingCanvas.height;

      // STEP 1: ALWAYS RENDER THE USER'S LIVE WEBCAM VIDEO (Horizontally Mirrored)
      ctx.save();
      ctx.translate(w, 0);
      ctx.scale(-1, 1);
      ctx.drawImage(clientVideo, 0, 0, w, h);
      ctx.restore();

      // STEP 2: SEND VIDEO FRAME TO FACEMESH IF TRACKING IS ENABLED
      if (isTracking && faceMesh && !isProcessingMesh) {
        isProcessingMesh = true;
        faceMesh.send({ image: clientVideo })
          .catch((e) => console.warn("FaceMesh send error:", e))
          .finally(() => { isProcessingMesh = false; });
      }

      const now = performance.now();

      // STEP 3: IF TRACKING IS PAUSED VIA CONTROLLER
      if (!isTracking) {
        // Dark translucent overlay
        ctx.fillStyle = "rgba(11, 15, 25, 0.72)";
        ctx.fillRect(0, 0, w, h);

        // Paused Banner
        ctx.fillStyle = "#ef4444";
        ctx.font = "bold 18px system-ui, sans-serif";
        ctx.textAlign = "center";
        ctx.fillText("⏸️ TRACKING CONTROLLER PAUSED", w / 2, h / 2 - 10);
        ctx.font = "14px system-ui, sans-serif";
        ctx.fillStyle = "#cbd5e1";
        ctx.fillText("Click 'Tracking Controller' in top navigation to resume", w / 2, h / 2 + 18);
        ctx.textAlign = "left";

        cameraStatusDot.className = "status-indicator searching";
        if (virtualCursor) virtualCursor.classList.remove("active");
        requestAnimationFrame(trackingRenderLoop);
        return;
      }

      // STEP 4: ACTIVE TRACKING WITH FACIAL LANDMARKS
      const isFaceFresh = lastLandmarks && (now - lastLandmarkTimestamp < 650);

      if (isFaceFresh) {
        cameraStatusDot.className = "status-indicator active";
        const lm = lastLandmarks;

        // Horizontally mirrored coordinates matching the mirrored selfie view:
        // Landmark 4 is the nose tip
        const nx = (1.0 - lm[4].x) * w;
        const ny = lm[4].y * h;
        lastNoseX = nx;
        lastNoseY = ny;

        if (!neutralNose) {
          neutralNose = { x: nx, y: ny };
        }

        // Biometric Metrics Calculation
        const earL = (pDist(lm[160], lm[144]) + pDist(lm[158], lm[153])) / (2.0 * pDist(lm[33], lm[133]));
        const earR = (pDist(lm[385], lm[380]) + pDist(lm[387], lm[373])) / (2.0 * pDist(lm[362], lm[263]));
        const mar = pDist(lm[13], lm[14]) / pDist(lm[78], lm[308]);

        // Invert yaw sign to match mirrored selfie view
        const rawYaw = ((lm[4].x - (lm[33].x + lm[263].x) / 2) * 120);
        const yaw = -rawYaw;
        const pitch = (((lm[4].y - (lm[33].y + lm[263].y) / 2) - 0.05) * 140);

        // Update HTML Telemetry Bars
        valYaw.innerHTML = `${yaw > 0 ? "+" : ""}${yaw.toFixed(1)}&deg;`;
        valPitch.innerHTML = `${pitch > 0 ? "+" : ""}${pitch.toFixed(1)}&deg;`;
        meterYaw.style.width = `${Math.max(0, Math.min(100, (yaw + 30) / 60 * 100))}%`;
        meterPitch.style.width = `${Math.max(0, Math.min(100, (pitch + 25) / 50 * 100))}%`;
        valEarL.textContent = earL.toFixed(3);
        valEarR.textContent = earR.toFixed(3);
        meterEarL.style.width = `${Math.min(100, earL * 250)}%`;
        meterEarR.style.width = `${Math.min(100, earR * 250)}%`;

        // Calculate Head Deviation from Neutral Anchor
        const dx = nx - neutralNose.x;
        const dy = ny - neutralNose.y;
        const distFromNeutral = Math.hypot(dx, dy);

        // DRAW VISUAL FEEDBACK ON CANVAS:
        // 1. Subtle Facial Geometry Points (Eyes & Mouth)
        const eyeL_x = (1.0 - lm[33].x) * w;
        const eyeL_y = lm[33].y * h;
        const eyeR_x = (1.0 - lm[263].x) * w;
        const eyeR_y = lm[263].y * h;
        const mouth_x = (1.0 - lm[13].x) * w;
        const mouth_y = lm[13].y * h;

        ctx.fillStyle = "rgba(56, 189, 248, 0.6)";
        [ [eyeL_x, eyeL_y], [eyeR_x, eyeR_y], [mouth_x, mouth_y] ].forEach(([px, py]) => {
          ctx.beginPath();
          ctx.arc(px, py, 3, 0, 2 * Math.PI);
          ctx.fill();
        });

        // 2. Resting Neutral Center Anchor (Yellow Ring)
        ctx.beginPath();
        ctx.arc(neutralNose.x, neutralNose.y, 6, 0, 2 * Math.PI);
        ctx.strokeStyle = "rgba(245, 158, 11, 0.8)";
        ctx.lineWidth = 2;
        ctx.stroke();

        // 3. Direction Vector Line & Arrow (Showing Head Tilt)
        if (distFromNeutral >= 6) {
          ctx.beginPath();
          ctx.moveTo(neutralNose.x, neutralNose.y);
          ctx.lineTo(nx, ny);
          ctx.strokeStyle = isEngaged ? "#10b981" : "#f59e0b";
          ctx.lineWidth = 2.5;
          ctx.stroke();
        }

        // 4. Glowing Green Tracking Dot on Nose Tip
        const dotColor = isEngaged ? "#10b981" : "#38bdf8";
        ctx.beginPath();
        ctx.arc(nx, ny, 7.5, 0, 2 * Math.PI);
        ctx.fillStyle = dotColor;
        ctx.fill();
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 2;
        ctx.stroke();

        // 5. Direction HUD Banner (Top Left)
        let dirLabel = "🎯 CENTER (Neutral)";
        if (distFromNeutral >= 8) {
          const horiz = dx > 8 ? "RIGHT ➡️" : (dx < -8 ? "LEFT ⬅️" : "");
          const vert = dy > 8 ? "DOWN ⬇️" : (dy < -8 ? "UP ⬆️" : "");
          dirLabel = [horiz, vert].filter(Boolean).join(" + ");
        }

        ctx.fillStyle = "rgba(15, 23, 42, 0.85)";
        ctx.roundRect ? ctx.roundRect(12, 12, 270, 48, 8) : ctx.rect(12, 12, 270, 48);
        ctx.fill();
        ctx.strokeStyle = "rgba(255, 255, 255, 0.15)";
        ctx.stroke();

        ctx.font = "bold 13px system-ui, sans-serif";
        ctx.fillStyle = isEngaged ? "#10b981" : "#38bdf8";
        ctx.fillText(`Motion: ${dirLabel}`, 22, 32);
        ctx.font = "11px system-ui, sans-serif";
        ctx.fillStyle = "#94a3b8";
        ctx.fillText(`Yaw: ${yaw > 0 ? "+" : ""}${yaw.toFixed(1)}° | Pitch: ${pitch > 0 ? "+" : ""}${pitch.toFixed(1)}°`, 22, 50);

        // 6. Clutch Engagement Badge (Top Right)
        const clutchLabel = isEngaged ? "🟢 CONTROL ACTIVE" : "🔒 STANDBY (TAP SHIFT)";
        const clutchColor = isEngaged ? "#10b981" : "#f59e0b";
        ctx.fillStyle = "rgba(15, 23, 42, 0.85)";
        const badgeW = 200;
        ctx.roundRect ? ctx.roundRect(w - badgeW - 12, 12, badgeW, 32, 8) : ctx.rect(w - badgeW - 12, 12, badgeW, 32);
        ctx.fill();
        ctx.font = "bold 12px system-ui, sans-serif";
        ctx.fillStyle = clutchColor;
        ctx.fillText(clutchLabel, w - badgeW + 8, 32);

        // 7. Dwell Click Accumulator Logic
        let dwellProgress = 0.0;
        if (isEngaged && now > dwellCooldownUntil) {
          if (!dwellTargetPos) {
            dwellTargetPos = { x: cursorX, y: cursorY };
            dwellStartTime = now;
          } else {
            const cursorDist = Math.hypot(cursorX - dwellTargetPos.x, cursorY - dwellTargetPos.y);
            if (cursorDist > 52.0) {
              // User moved past anchor circle: reset anchor to new location
              dwellTargetPos = { x: cursorX, y: cursorY };
              dwellStartTime = now;
            } else {
              const elapsed = (now - dwellStartTime) / 1000.0;
              dwellProgress = Math.min(1.0, elapsed / 0.95);

              // 100% DWELL TRIGGERED
              if (dwellProgress >= 1.0) {
                executeDwellClick();
                dwellProgress = 0.0;
                dwellStartTime = null;
                dwellTargetPos = null;
                dwellCooldownUntil = now + 850;
              }
            }
          }
        } else {
          dwellStartTime = null;
          dwellTargetPos = null;
        }

        // Draw 360° Circular Dwell Accumulator Ring on Canvas
        if (isEngaged && dwellProgress > 0.03) {
          ctx.beginPath();
          ctx.arc(nx, ny, 22, -Math.PI / 2, -Math.PI / 2 + dwellProgress * 2 * Math.PI);
          ctx.strokeStyle = "#f59e0b";
          ctx.lineWidth = 3.5;
          ctx.stroke();
        }

        const dwellPercent = Math.round(dwellProgress * 100);
        valDwellPercent.textContent = `${dwellPercent}%`;
        dwellBarFill.style.width = `${dwellPercent}%`;

        // 8. Virtual Cursor Steering Across Window
        if (isEngaged) {
          // Swift non-linear response curve
          const absX = Math.abs(dx);
          const absY = Math.abs(dy);
          const accelX = 1.0 + 0.02 * Math.min(absX, 50.0);
          const accelY = 1.0 + 0.02 * Math.min(absY, 40.0);

          const normX = Math.max(-1.0, Math.min(1.0, (dx / 44.0) * sensitivityMultiplier * accelX));
          const normY = Math.max(-1.0, Math.min(1.0, (dy / 34.0) * sensitivityMultiplier * accelY));

          const targetX = (normX * 0.5 + 0.5) * window.innerWidth;
          const targetY = (normY * 0.5 + 0.5) * window.innerHeight;

          // Smooth exponential moving average
          cursorX = cursorX * 0.28 + targetX * 0.72;
          cursorY = cursorY * 0.28 + targetY * 0.72;

          if (virtualCursor) {
            virtualCursor.style.left = `${cursorX}px`;
            virtualCursor.style.top = `${cursorY}px`;
            virtualCursor.classList.add("active");
          }

          // Facial Gestures (Wink & Mouth Open)
          if (now - lastActionTime > 1300) {
            if (earL < 0.17 && earR >= 0.23) {
              executeDwellClick();
              triggerActionToast("Left Wink -> Click");
              lastActionTime = now;
            } else if (mar > 0.45) {
              window.scrollBy({ top: 180, behavior: "smooth" });
              triggerActionToast("Mouth Open -> Scroll Down");
              lastActionTime = now;
            }
          }
        } else {
          // Disengaged (Safety Standby)
          if (virtualCursor) virtualCursor.classList.remove("active");
        }

      } else {
        // NO FACE DETECTED: Show search guide & NEVER move the cursor!
        cameraStatusDot.className = "status-indicator searching";
        valDwellPercent.textContent = "0%";
        dwellBarFill.style.width = "0%";

        // Draw face placement oval
        ctx.save();
        ctx.strokeStyle = "rgba(245, 158, 11, 0.75)";
        ctx.lineWidth = 2.5;
        ctx.setLineDash([8, 6]);
        ctx.beginPath();
        ctx.ellipse(w / 2, h / 2, w * 0.22, h * 0.35, 0, 0, 2 * Math.PI);
        ctx.stroke();
        ctx.restore();

        // Overlay Message
        ctx.fillStyle = "rgba(15, 23, 42, 0.85)";
        ctx.roundRect ? ctx.roundRect(w / 2 - 160, h - 54, 320, 38, 8) : ctx.rect(w / 2 - 160, h - 54, 320, 38);
        ctx.fill();

        ctx.font = "bold 13px system-ui, sans-serif";
        ctx.fillStyle = "#f59e0b";
        ctx.textAlign = "center";
        ctx.fillText("👁️ Please center your face in the camera frame", w / 2, h - 30);
        ctx.textAlign = "left";

        // Virtual cursor remains inactive when face is not seen
        if (virtualCursor) virtualCursor.classList.remove("active");
      }
    }

    requestAnimationFrame(trackingRenderLoop);
  }

  function executeDwellClick() {
    playTone(1600, 50); // Crisp click chime
    triggerActionToast("Dwell -> CLICK");

    if (virtualCursor) {
      virtualCursor.classList.add("clicking");
      setTimeout(() => virtualCursor.classList.remove("clicking"), 250);
    }

    // Dispatch real click event to element under virtual cursor
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
