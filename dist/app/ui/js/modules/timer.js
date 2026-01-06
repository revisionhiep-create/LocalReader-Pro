export function initTimer() {
  console.log("[TIMER] Initializing sleep timer...");

  const btn = document.getElementById("timerSettingsBtn");
  const drawer = document.getElementById("timerSettingsDrawer");
  const closeBtn = document.getElementById("closeTimerDrawerBtn");
  const overlay = document.getElementById("drawerOverlay"); // Reused from voice drawer

  // Controls
  const hoursInput = document.getElementById("timerHours");
  const minutesInput = document.getElementById("timerMinutes");
  const startBtn = document.getElementById("startTimerBtn");
  const stopBtn = document.getElementById("stopTimerBtn");
  const statusText = document.getElementById("timerStatusText");
  const countdownDisplay = document.getElementById("timerCountdown");

  // Button Display
  const btnIcon = btn.querySelector("i");
  const btnText = document.getElementById("timerBtnText");

  let statusInterval = null;

  // Toggle Drawer
  function toggleDrawer(show) {
    if (show) {
      drawer.classList.add("open");
      overlay.classList.add("active");
    } else {
      drawer.classList.remove("open");
      overlay.classList.remove("active");
    }
  }

  btn.addEventListener("click", () => {
    toggleDrawer(true);
    fetchStatus();
  });

  closeBtn.addEventListener("click", () => toggleDrawer(false));

  // Close on overlay click (if unique overlay usage doesn't conflict)
  // The existing overlay likely has a click listener that closes voice drawer.
  // We should piggyback or ensure it closes both.
  overlay.addEventListener("click", () => {
    toggleDrawer(false);
  });

  // API Calls
  async function startTimer() {
    const hours = parseInt(hoursInput.value) || 0;
    const minutes = parseInt(minutesInput.value) || 0;
    const totalMinutes = hours * 60 + minutes;

    if (totalMinutes <= 0) {
      alert("Please set a time greater than 1 minute.");
      return;
    }

    try {
      const res = await fetch("/api/timer/set", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ minutes: totalMinutes }),
      });
      const data = await res.json();
      updateUI(data);
    } catch (e) {
      console.error("[TIMER] Failed to set timer", e);
    }
  }

  async function stopTimer() {
    try {
      const res = await fetch("/api/timer/stop", { method: "POST" });
      const data = await res.json();
      updateUI(data);
    } catch (e) {
      console.error("[TIMER] Failed to stop timer", e);
    }
  }

  async function fetchStatus() {
    try {
      const res = await fetch("/api/timer/status");
      const data = await res.json();
      updateUI(data);
    } catch (e) {
      console.error("[TIMER] Failed to fetch status", e);
    }
  }

  function formatTime(seconds) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);

    if (h > 0) {
      return `${h}h ${m}m`; // Seconds hidden per request for button/neutral view
    }
    return `${m}m`;
  }

  function formatTimeFull(seconds) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    return `${h.toString().padStart(2, "0")}:${m
      .toString()
      .padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  }

  function updateUI(data) {
    if (data.active) {
      // Drawer UI
      stopBtn.classList.remove("hidden");
      startBtn.classList.add("hidden");
      statusText.textContent = "Timer Running";
      statusText.className = "text-green-400 font-bold text-sm mb-2";
      countdownDisplay.textContent = formatTimeFull(data.remaining_seconds);

      // Button UI (Neutral colors, counting down)
      // Override active style to be neutral
      btn.classList.add("active"); // Keep class for potential other hooks, but override styles
      btn.style.background = "#27272a"; 
      btn.style.width = "auto";
      btn.style.padding = "0 12px";
      btn.style.borderRadius = "24px";
      btn.style.borderColor = "#3f3f46";
      
      btnIcon.style.display = "none";
      btnText.style.display = "block";
      btnText.textContent = formatTime(data.remaining_seconds);
      btnText.className = "text-xs font-bold font-mono text-zinc-300";

      // Inputs disabled
      hoursInput.disabled = true;
      minutesInput.disabled = true;
    } else {
      // Drawer UI
      stopBtn.classList.add("hidden");
      startBtn.classList.remove("hidden");
      statusText.textContent = "Timer Inactive";
      statusText.className = "text-zinc-500 font-bold text-sm mb-2";
      countdownDisplay.textContent = "--:--:--";

      // Button UI
      btn.classList.remove("active");
      btn.style.background = ""; // Reset
      btn.style.width = "";
      btn.style.padding = "";
      btn.style.borderRadius = "";
      btn.style.borderColor = "";

      btnIcon.style.display = "block";
      btnText.style.display = "none";

      // Inputs enabled
      hoursInput.disabled = false;
      minutesInput.disabled = false;
    }
  }

  // Bind Actions
  startBtn.addEventListener("click", startTimer);
  stopBtn.addEventListener("click", stopTimer);

  // Initial check
  fetchStatus();

  // Poll status every 30 seconds to sync (and rely on local countdown for smoothness if needed, but simple polling is safer for now)
  // Actually, for a countdown, we want to update every second if drawer is open.
  // If drawer is closed, update button every minute?

  // Let's toggle polling based on visibility or just poll every 1s (local is cheap)
  statusInterval = setInterval(fetchStatus, 1000);
}
