(function () {
  "use strict";

  var menuPanel = document.getElementById("menu-panel");
  var recorderPanel = document.getElementById("recorder-panel");
  var menuStatus = document.getElementById("menu-status");
  var recStatus  = document.getElementById("rec-status");

  // ---------- helpers ----------
  function setStatus(msg, isError) {
    menuStatus.textContent = msg || "";
    menuStatus.classList.toggle("error", !!isError);
    console.log("STATUS:", msg);
  }

  function showMenu() {
    recorderPanel.classList.remove("active");
    menuPanel.classList.add("active");
    document.getElementById("btn-record").focus();
  }

  function showRecorder() {
    menuPanel.classList.remove("active");
    recorderPanel.classList.add("active");
    document.getElementById("btn-stop").focus();
  }

  // ---------- storage probe ----------
  function probeStorage(cb) {
    if (typeof navigator.getDeviceStorage !== "function") {
      console.log("PROBE: no getDeviceStorage API");
      cb(null);
      return;
    }
    var names = ["sdcard", "extsdcard", "sdcard1", "internal", "music", "apps"];
    var found = null;
    var i = 0;
    function next() {
      if (i >= names.length || found) {
        console.log("PROBE: result =", found || "none");
        cb(found);
        return;
      }
      var name = names[i++];
      var sd;
      try { sd = navigator.getDeviceStorage(name); }
      catch (e) { console.log("PROBE: " + name + " threw", e.message); return next(); }
      if (!sd) { console.log("PROBE: " + name + " = null"); return next(); }
      var req = sd.available();
      req.onsuccess = function () {
        console.log("PROBE: " + name + " available =", req.result);
        if (req.result === "available") { found = name; }
        next();
      };
      req.onerror = function () {
        console.log("PROBE: " + name + " error =", req.error && req.error.name);
        next();
      };
    }
    next();
  }

  // ---------- app launcher with fallback variants ----------
  // KaiOS builds support different activity shapes. We try several and use
  // the first one that doesn't error out.
  function launchAppVariants(manifestURL, label) {
    var variants = [
      // 1. Most common: "view" with type "url" pointing at the manifest
      { name: "view", data: { type: "url", url: manifestURL } },
      // 2. Some builds: "view" with type "webapp" and manifestURL
      { name: "view", data: { type: "webapp", manifestURL: manifestURL } },
      // 3. Older Gaia: "view" with just "url" (no type)
      { name: "view", data: { url: manifestURL } }
    ];

    var idx = 0;
    function tryNext() {
      if (idx >= variants.length) {
        setStatus("Could not open " + label, true);
        return;
      }
      var v = variants[idx++];
      var settled = false;
      var a;
      try {
        a = new MozActivity(v);
      } catch (e) {
        console.log("LAUNCH " + label + ": variant " + idx + " threw:", e.message);
        return tryNext();
      }
      a.onsuccess = function () {
        if (settled) return;
        settled = true;
        console.log("LAUNCH " + label + ": variant " + idx + " ok");
      };
      a.onerror = function () {
        if (settled) return;
        settled = true;
        console.log("LAUNCH " + label + ": variant " + idx + " error:",
                    a.error && a.error.name);
        tryNext();
      };
      // If neither fires within 400ms, assume it worked (some builds don't
      // call either callback for successful system app launches).
      setTimeout(function () {
        if (!settled) {
          settled = true;
          console.log("LAUNCH " + label + ": variant " + idx + " (no callback, assuming ok)");
        }
      }, 400);
    }
    tryNext();
  }

  function openSettingsSection(section) {
    try {
      var a = new MozActivity({
        name: "configure",
        data: { target: "device", section: section }
      });
      a.onerror = function () {
        console.log("SETTINGS " + section + " error:", a.error && a.error.name);
        setStatus("No settings panel for: " + section, true);
      };
    } catch (e) {
      setStatus("Settings error: " + e.message, true);
    }
  }

  function openUrl(url) {
    try {
      var a = new MozActivity({
        name: "view",
        data: { type: "url", url: url }
      });
      a.onerror = function () {
        setStatus("Could not open URL", true);
      };
    } catch (e) {
      setStatus("URL error: " + e.message, true);
    }
  }

  // ---------- menu buttons ----------
  document.getElementById("btn-record").onclick = function () { startRecording(); };
  document.getElementById("btn-alarms").onclick = function () {
    launchAppVariants("app://clock.gaiamobile.org/manifest.webapp", "Clock");
  };
  document.getElementById("btn-hotspot").onclick = function () {
    openSettingsSection("hotspot");
  };
  document.getElementById("btn-transcribe").onclick = function () {
    openUrl("https://example.com/transcribe");
  };
  document.getElementById("btn-settings").onclick = function () {
    launchAppVariants("app://settings.gaiamobile.org/manifest.webapp", "Settings");
  };

  // ---------- recording ----------
  var mediaRecorder = null;
  var chunks = [];
  var recording = false;
  var stream = null;
  var activeStorage = null;

  function startRecording() {
    if (recording) return;

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setStatus("No microphone API on this phone", true);
      return;
    }

    probeStorage(function (storageName) {
      activeStorage = storageName;
      console.log("REC: using storage =", activeStorage || "(none found yet)");

      navigator.mediaDevices.getUserMedia({ audio: true })
        .then(function (s) {
          stream = s;
          chunks = [];

          var mimeType = "";
          var candidates = [
            "audio/ogg;codecs=opus", "audio/ogg",
            "audio/webm;codecs=opus", "audio/webm", ""
          ];
          for (var i = 0; i < candidates.length; i++) {
            if (candidates[i] === "" ||
                (window.MediaRecorder &&
                 MediaRecorder.isTypeSupported &&
                 MediaRecorder.isTypeSupported(candidates[i]))) {
              mimeType = candidates[i];
              break;
            }
          }
          console.log("REC: chosen mimeType =", mimeType || "(default)");

          try {
            mediaRecorder = mimeType
              ? new MediaRecorder(stream, { mimeType: mimeType })
              : new MediaRecorder(stream);
          } catch (e) {
            setStatus("Recorder init failed: " + e.message, true);
            cleanupStream();
            return;
          }

          mediaRecorder.ondataavailable = function (ev) {
            if (ev.data && ev.data.size > 0) {
              console.log("REC: chunk size =", ev.data.size);
              chunks.push(ev.data);
            }
          };
          mediaRecorder.onstop = function () {
            console.log("REC: stopped, total chunks =", chunks.length);
            saveRecording();
          };

          mediaRecorder.start();
          recording = true;
          showRecorder();
          recStatus.textContent = "Recording… tap center to stop";
        })
        .catch(function (err) {
          var name = err && err.name ? err.name : String(err);
          console.log("REC: getUserMedia error:", name);
          setStatus("Mic error: " + name, true);
        });
    });
  }

  function stopRecording() {
    if (!recording) return;
    recStatus.textContent = "Saving…";
    try { mediaRecorder.stop(); } catch (e) {}
  }

  function cleanupStream() {
    if (stream) {
      stream.getTracks().forEach(function (t) { t.stop(); });
      stream = null;
    }
    mediaRecorder = null;
    recording = false;
  }

  function saveRecording() {
    var blob = new Blob(chunks, { type: "audio/ogg" });
    var filename = "digit4g/rec-" + new Date().toISOString().replace(/[:.]/g, "-") + ".ogg";

    console.log("SAVE: blob size =", blob.size, "filename =", filename, "storage =", activeStorage);

    if (blob.size === 0) {
      setStatus("Nothing recorded", true);
      cleanupStream(); showMenu(); return;
    }
    if (typeof navigator.getDeviceStorage !== "function") {
      setStatus("No storage API", true);
      cleanupStream(); showMenu(); return;
    }

    var areas = [];
    if (activeStorage) areas.push(activeStorage);
    ["sdcard", "extsdcard", "sdcard1", "internal", "music", "apps", "downloads"].forEach(function (n) {
      if (areas.indexOf(n) === -1) areas.push(n);
    });

    var tryNext = function (i) {
      if (i >= areas.length) {
        setStatus("No writable storage found", true);
        cleanupStream(); showMenu(); return;
      }
      var name = areas[i];
      var sd;
      try { sd = navigator.getDeviceStorage(name); }
      catch (e) { return tryNext(i + 1); }
      if (!sd) { return tryNext(i + 1); }
      var req;
      try { req = sd.addNamed(blob, filename); }
      catch (e) { return tryNext(i + 1); }
      req.onsuccess = function () {
        console.log("SAVE: success on", name);
        setStatus("Saved to " + name + ": " + filename);
        cleanupStream(); showMenu();
      };
      req.onerror = function () {
        console.log("SAVE: error on", name, req.error && req.error.name);
        tryNext(i + 1);
      };
    };
    tryNext(0);
  }

  document.getElementById("btn-stop").onclick = stopRecording;
  document.getElementById("btn-back").onclick = function () {
    if (recording) {
      try { mediaRecorder.stop(); } catch (e) {}
      chunks = [];
      mediaRecorder.onstop = function () {
        cleanupStream();
        setStatus("Recording discarded");
        showMenu();
      };
    } else {
      showMenu();
    }
  };

  // ---------- hardware keys ----------
  document.addEventListener("keydown", function (e) {
    var k = e.key;

    if (recording) {
      if (k === "Enter") { e.preventDefault(); stopRecording(); return; }
      if (k === "SoftLeft" || k === "Backspace" || k === "EndCall") {
        e.preventDefault();
        document.getElementById("btn-back").click();
        return;
      }
    }

    if (k === "ArrowDown") { e.preventDefault(); moveFocus(1); }
    else if (k === "ArrowUp") { e.preventDefault(); moveFocus(-1); }
    else if (k === "Enter" && document.activeElement &&
             document.activeElement.tagName !== "BUTTON") {
      var first = document.querySelector(".panel.active .btn");
      if (first) first.focus();
    }
  }, true);

  function moveFocus(delta) {
    var buttons = Array.prototype.slice.call(
      document.querySelectorAll(".panel.active .btn")
    );
    if (!buttons.length) return;
    var i = buttons.indexOf(document.activeElement);
    if (i === -1) { buttons[0].focus(); return; }
    i = (i + delta + buttons.length) % buttons.length;
    buttons[i].focus();
  }

  // ---------- startup ----------
  window.addEventListener("load", function () {
    document.getElementById("btn-record").focus();
    console.log("STARTUP: getUserMedia =", !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia));
    console.log("STARTUP: MediaRecorder =", typeof window.MediaRecorder);
    console.log("STARTUP: getDeviceStorage =", typeof navigator.getDeviceStorage);
    probeStorage(function (s) {
      console.log("STARTUP: usable storage =", s || "(none found)");
    });
  });

})();