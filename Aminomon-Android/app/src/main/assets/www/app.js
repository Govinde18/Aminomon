/* Aminomon web shell: canvas terminal, touch controls, audio, saves. */
"use strict";
(() => {
  const $ = (id) => document.getElementById(id);
  const canvas = $("term"), ctx = canvas.getContext("2d", { alpha: false });
  const stage = $("stage"), loader = $("loader"), statusEl = $("status");
  const DEF_BG = "#121212", DEF_FG = "#d0d0d0";
  const ADV = 0.60205, LH = 1.2, ASC = 0.928, DESC = 0.236;   // DejaVu Sans Mono metrics
  const N = 512;                                              // ring slots (see worker.js)

  // ------------------------------------------------------------ helpers
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* private mode */ } },
    del(k) { try { localStorage.removeItem(k); } catch (e) { /* ignore */ } },
    keys() { try { return Object.keys(localStorage); } catch (e) { return []; } },
  };
  function fail(msg) {
    loader.classList.remove("hide");
    $("spin").style.display = "none";
    statusEl.textContent = msg;
    statusEl.classList.add("err");
  }

  // ------------------------------------------------------------ palette
  const pal = [];
  (function () {
    const base = ["#000000", "#cd0000", "#00cd00", "#cdcd00", "#0000ee", "#cd00cd", "#00cdcd", "#e5e5e5",
      "#7f7f7f", "#ff0000", "#00ff00", "#ffff00", "#5c5cff", "#ff00ff", "#00ffff", "#ffffff"];
    for (const c of base) pal.push(c);
    const lv = [0, 95, 135, 175, 215, 255];
    for (let i = 0; i < 216; i++) pal.push(`rgb(${lv[(i / 36) | 0]},${lv[((i / 6) | 0) % 6]},${lv[i % 6]})`);
    for (let i = 0; i < 24; i++) { const v = 8 + 10 * i; pal.push(`rgb(${v},${v},${v})`); }
  })();

  // ------------------------------------------------------------ geometry
  let rows = 24, cols = 80, cw = 8, chh = 16, dpr = 1, fontPx = 13, baseY = 12;
  let userFont = parseFloat(store.get("amn:font") || "0") || 0;      // CSS px; 0 = auto
  let showPad = store.get("amn:pad");
  showPad = showPad === null ? matchMedia("(pointer: coarse)").matches : showPad === "1";
  let cells = [];     // cells[y] = { ch: string[], fg: [], bg: [], fl: [] } per column
  let dirty = new Set(), raf = 0;

  function gutters() {
    if (!showPad) return [0, 0];
    const w = innerWidth;
    const g = Math.max(84, Math.min(150, Math.round(w * 0.13)));
    return [g, g];
  }

  function computeGeometry() {
    dpr = window.devicePixelRatio || 1;
    const [gl, gr] = gutters();
    const W = Math.max(100, innerWidth - gl - gr), H = Math.max(100, innerHeight);
    const dims = (f) => {
      const c = Math.max(3, Math.round(f * ADV * dpr)), fp = c / ADV, h = Math.round(fp * LH);
      return { cw: c, fontPx: fp, chh: h, cols: Math.floor((W * dpr) / c), rows: Math.floor((H * dpr) / h) };
    };
    let f = userFont, d;
    if (!f) {                                    // auto: biggest font that still fits 80x24
      f = 5;
      for (let t = 5; t <= 18; t += 0.25) {
        const x = dims(t);
        if (x.cols >= 80 && x.rows >= 24) f = t; else if (t > 8) break;
      }
    }
    d = dims(f);
    cw = d.cw; fontPx = d.fontPx; chh = d.chh;
    baseY = Math.round((chh - fontPx * (ASC + DESC)) / 2 + fontPx * ASC);
    cols = Math.max(20, d.cols);
    rows = Math.max(8, d.rows);
    canvas.width = cols * cw; canvas.height = rows * chh;
    canvas.style.width = canvas.width / dpr + "px";
    canvas.style.height = canvas.height / dpr + "px";
    stage.style.setProperty("--gl", gl + "px");
    stage.style.setProperty("--gr", gr + "px");
    $("pad").style.display = showPad ? "" : "none";
    $("acts").style.display = showPad ? "" : "none";
    cells = [];
    for (let y = 0; y < rows; y++) cells.push(newRow());
    ctx.textBaseline = "alphabetic";
    ctx.fillStyle = DEF_BG; ctx.fillRect(0, 0, canvas.width, canvas.height);
  }
  function newRow() {
    return { ch: new Array(cols).fill(" "), fg: new Array(cols).fill(-1), bg: new Array(cols).fill(-1), fl: new Array(cols).fill(0) };
  }

  // ------------------------------------------------------------ drawing
  const LIGHT = { "─": "LR", "│": "UD", "┌": "RD", "┐": "LD", "└": "RU", "┘": "LU", "┬": "LRD", "┴": "LRU", "├": "UDR", "┤": "UDL", "┼": "LRUD" };
  function drawGlyph(ch, px, py, color, bold, ul) {
    const t = Math.max(1, Math.round(dpr));
    ctx.fillStyle = color;
    const cp = ch.codePointAt(0);
    if (cp === 0x2588) { ctx.fillRect(px, py, cw, chh); return; }                 // █
    if (cp === 0x2580) { ctx.fillRect(px, py, cw, chh >> 1); return; }            // ▀
    if (cp === 0x2584) { ctx.fillRect(px, py + (chh >> 1), cw, chh - (chh >> 1)); return; } // ▄
    if (cp === 0x2591 || cp === 0x2592 || cp === 0x2593) {                        // ░ ▒ ▓
      const a = ctx.globalAlpha; ctx.globalAlpha = a * (cp === 0x2591 ? 0.25 : cp === 0x2592 ? 0.5 : 0.75);
      ctx.fillRect(px, py, cw, chh); ctx.globalAlpha = a; return;
    }
    const seg = LIGHT[ch];
    const cx = px + (cw >> 1) - (t >> 1), cy = py + (chh >> 1) - (t >> 1);
    if (seg) {
      if (seg.includes("L")) ctx.fillRect(px, cy, cx - px + t, t);
      if (seg.includes("R")) ctx.fillRect(cx, cy, px + cw - cx, t);
      if (seg.includes("U")) ctx.fillRect(cx, py, t, cy - py + t);
      if (seg.includes("D")) ctx.fillRect(cx, cy, t, py + chh - cy);
      return;
    }
    if (cp === 0x2550) {                                                           // ═
      const g = Math.max(2, Math.round(chh / 6));
      ctx.fillRect(px, cy - g, cw, t); ctx.fillRect(px, cy + g, cw, t); return;
    }
    if (cp === 0x2551) {                                                           // ║
      const g = Math.max(2, Math.round(cw / 4));
      ctx.fillRect(cx - g, py, t, chh); ctx.fillRect(cx + g, py, t, chh); return;
    }
    if (ch !== " ") {
      ctx.font = (bold ? "bold " : "") + fontPx + "px GVMono, 'DejaVu Sans Mono', monospace";
      ctx.fillText(ch, px, py + baseY);
    }
    if (ul) ctx.fillRect(px, py + chh - t - 1, cw, t);
  }

  function paintRow(y) {
    const r = cells[y]; if (!r) return;
    const py = y * chh;
    ctx.globalAlpha = 1;
    ctx.fillStyle = DEF_BG; ctx.fillRect(0, py, canvas.width, chh);
    // backgrounds first (merge equal neighbours), then glyphs
    let x = 0;
    while (x < cols) {
      const fl = r.fl[x], bgi = r.bg[x], fgi = r.fg[x];
      const rev = fl & 8;
      const bgc = rev ? (fgi < 0 ? DEF_FG : pal[fgi]) : (bgi < 0 ? null : pal[bgi]);
      let e = x + 1;
      while (e < cols && r.bg[e] === bgi && r.fg[e] === fgi && (r.fl[e] & 8) === rev) e++;
      if (bgc) { ctx.fillStyle = bgc; ctx.fillRect(x * cw, py, (e - x) * cw, chh); }
      x = e;
    }
    for (let i = 0; i < cols; i++) {
      const ch = r.ch[i]; const fl = r.fl[i];
      if (ch === " " && !(fl & 4)) continue;
      const rev = fl & 8;
      const fgi = r.fg[i], bgi = r.bg[i];
      const color = rev ? (bgi < 0 ? DEF_BG : pal[bgi]) : (fgi < 0 ? DEF_FG : pal[fgi]);
      ctx.globalAlpha = fl & 2 ? 0.6 : 1;
      drawGlyph(ch, i * cw, py, color, fl & 1, fl & 4);
    }
    ctx.globalAlpha = 1;
  }
  function flush() {
    raf = 0;
    for (const y of dirty) paintRow(y);
    dirty.clear();
  }
  function schedule() { if (!raf) raf = requestAnimationFrame(flush); }

  function onDraw(json) {
    const m = JSON.parse(json);
    if (m.rows !== rows || m.cols !== cols) return;          // stale frame from before a resize
    if (m.full) for (let y = 0; y < rows; y++) dirty.add(y);
    for (const [y, text, runs] of m.r) {
      const row = cells[y]; if (!row) continue;
      const chars = Array.from(text);
      for (let i = 0; i < cols; i++) row.ch[i] = chars[i] || " ";
      for (const [x, n, fg, bg, fl] of runs) {
        for (let i = x; i < x + n && i < cols; i++) { row.fg[i] = fg; row.bg[i] = bg; row.fl[i] = fl; }
      }
      dirty.add(y);
    }
    if (!loader.classList.contains("hide")) {
      loader.classList.add("hide");
      stage.classList.add("on");
    }
    schedule();
  }

  // ------------------------------------------------------------ worker + input ring
  let worker = null, sab = null, A = null, gen = 0;
  const K = { DOWN: 258, UP: 259, LEFT: 260, RIGHT: 261, BACKSPACE: 263, DC: 330, NPAGE: 338, PPAGE: 339, HOME: 262, END: 360 };

  function push(type, a, b, c) {
    if (!A) return;
    const head = Atomics.load(A, 0), tail = Atomics.load(A, 1);
    if (head - tail >= N) return;
    const o = 8 + (head % N) * 4;
    A[o] = type; A[o + 1] = a | 0; A[o + 2] = b | 0; A[o + 3] = c | 0;
    Atomics.store(A, 0, head + 1);
    Atomics.notify(A, 0);
  }
  const key = (cp) => push(1, cp, 0, 0);
  const special = (code) => push(4, code, 0, 0);
  const click = (x, y) => push(2, x, y, 1);
  const wheel = (x, y, up) => push(2, x, y, up ? 4 : 5);

  function sendSize() {
    if (!A) return;
    Atomics.store(A, 2, rows); Atomics.store(A, 3, cols);
    push(3, cols, rows, 0);
  }

  function startWorker() {
    const my = ++gen;
    if (worker) worker.terminate();
    loader.classList.remove("hide"); stage.classList.remove("on");
    $("spin").style.display = ""; statusEl.classList.remove("err");
    statusEl.textContent = "Starting…";
    sab = new SharedArrayBuffer(4 * (8 + N * 4));
    A = new Int32Array(sab);
    Atomics.store(A, 2, rows); Atomics.store(A, 3, cols);
    const files = {};
    for (const k of store.keys()) if (k.startsWith("amn:f:")) files[k.slice(6)] = store.get(k);
    const lang = ((navigator.languages && navigator.languages[0]) || navigator.language || "en").replace("-", "_");
    worker = new Worker("worker.js", { type: "module" });
    worker.onmessage = (e) => {
      if (my !== gen) return;
      const m = e.data;
      switch (m.t) {
        case "status": statusEl.textContent = m.s; break;
        case "draw": onDraw(m.d); break;
        case "sound": playTones(JSON.parse(m.d)); break;
        case "save": store.set("amn:f:" + m.name, m.text); break;
        case "restart": startWorker(); break;
        case "exit": showExit(); break;
        case "fatal": fail("Something went wrong:\n" + m.text); break;
        default: break;
      }
    };
    worker.onerror = (e) => { if (my === gen) fail("The game could not start: " + (e.message || e)); };
    worker.postMessage({ t: "init", sab, files, lang: lang + ".UTF-8" });
  }
  function showExit() {
    $("exit").classList.remove("hide");
  }

  // ------------------------------------------------------------ audio
  let actx = null, busyUntil = 0;
  function unlockAudio() {
    try {
      if (!actx) actx = new (window.AudioContext || window.webkitAudioContext)();
      if (actx.state === "suspended") actx.resume();
    } catch (e) { /* no audio */ }
  }
  function playTones(notes) {
    if (!actx || actx.state !== "running") return;
    const now = actx.currentTime;
    if (now < busyUntil) return;                       // like the Windows version: skip, don't pile up
    let t = now;
    for (const [f, ms] of notes) {
      const o = actx.createOscillator(), g = actx.createGain();
      o.type = "square"; o.frequency.value = f;
      g.gain.setValueAtTime(0.035, t);
      g.gain.setValueAtTime(0.0001, t + ms / 1000 - 0.004);
      o.connect(g); g.connect(actx.destination);
      o.start(t); o.stop(t + ms / 1000);
      t += ms / 1000;
    }
    busyUntil = t;
  }

  // ------------------------------------------------------------ keyboard
  const KEYMAP = {
    ArrowUp: () => special(K.UP), ArrowDown: () => special(K.DOWN), ArrowLeft: () => special(K.LEFT),
    ArrowRight: () => special(K.RIGHT), Backspace: () => special(K.BACKSPACE), Delete: () => special(K.DC),
    PageUp: () => special(K.PPAGE), PageDown: () => special(K.NPAGE), Home: () => special(K.HOME),
    End: () => special(K.END), Enter: () => key(10), Escape: () => key(27), Tab: () => key(9),
  };
  addEventListener("keydown", (e) => {
    unlockAudio();
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.target && /^(INPUT|TEXTAREA)$/.test(e.target.tagName)) return;
    const f = KEYMAP[e.key];
    if (f) { f(); e.preventDefault(); return; }
    if (e.key && [...e.key].length === 1) { key(e.key.codePointAt(0)); e.preventDefault(); }
  });

  // ------------------------------------------------------------ pointer on the screen
  let down = null;
  canvas.style.touchAction = "none";
  function cellAt(e) {
    const r = canvas.getBoundingClientRect();
    const x = Math.floor(((e.clientX - r.left) * dpr) / cw), y = Math.floor(((e.clientY - r.top) * dpr) / chh);
    return [Math.max(0, Math.min(cols - 1, x)), Math.max(0, Math.min(rows - 1, y))];
  }
  canvas.addEventListener("pointerdown", (e) => {
    unlockAudio();
    down = { id: e.pointerId, x: e.clientX, y: e.clientY, t: performance.now(), scrolled: 0, last: e.clientY };
    try { canvas.setPointerCapture(e.pointerId); } catch (err) { /* ignore */ }
  });
  canvas.addEventListener("pointermove", (e) => {
    if (!down || e.pointerId !== down.id || e.pointerType === "mouse") return;
    const step = (chh / dpr) * 2.2;                                 // vertical drag = wheel
    const dy = e.clientY - down.last;
    if (Math.abs(dy) >= step) {
      const [cx, cy] = cellAt(e);
      wheel(cx, cy, dy > 0);
      down.last = e.clientY; down.scrolled++;
    }
  });
  canvas.addEventListener("pointerup", (e) => {
    if (!down || e.pointerId !== down.id) return;
    const d = down; down = null;
    const moved = Math.hypot(e.clientX - d.x, e.clientY - d.y);
    if (d.scrolled || moved > 14 || performance.now() - d.t > 900) return;
    const [cx, cy] = cellAt(e); click(cx, cy);
  });
  canvas.addEventListener("pointercancel", () => { down = null; });
  canvas.addEventListener("wheel", (e) => {
    e.preventDefault();
    const [cx, cy] = cellAt(e); wheel(cx, cy, e.deltaY < 0);
  }, { passive: false });
  canvas.addEventListener("contextmenu", (e) => e.preventDefault());

  // ------------------------------------------------------------ on-screen buttons
  function bindButton(el, fire, repeat) {
    let t1 = 0, t2 = 0;
    const stop = () => { clearTimeout(t1); clearInterval(t2); el.classList.remove("on"); };
    el.addEventListener("pointerdown", (e) => {
      e.preventDefault(); unlockAudio(); el.classList.add("on");
      try { el.setPointerCapture(e.pointerId); } catch (err) { /* ignore */ }
      fire();
      if (repeat) { t1 = setTimeout(() => { t2 = setInterval(fire, 85); }, 320); }
    });
    for (const ev of ["pointerup", "pointercancel", "lostpointercapture"]) el.addEventListener(ev, stop);
    el.addEventListener("contextmenu", (e) => e.preventDefault());
  }
  for (const b of document.querySelectorAll("[data-k]")) {
    const k = b.dataset.k;
    const fire = { up: () => special(K.UP), down: () => special(K.DOWN), left: () => special(K.LEFT), right: () => special(K.RIGHT),
      enter: () => key(10), esc: () => key(27), space: () => key(32) }[k];
    if (fire) bindButton(b, fire, ["up", "down", "left", "right"].includes(k));
  }

  // ------------------------------------------------------------ menu
  const menu = $("menu");
  const toggleMenu = (v) => menu.classList.toggle("hide", v === undefined ? !menu.classList.contains("hide") : !v);
  $("menubtn").addEventListener("pointerdown", (e) => { e.preventDefault(); unlockAudio(); toggleMenu(); });
  function relayout() {
    computeGeometry(); sendSize();
    $("fontlbl").textContent = userFont ? userFont.toFixed(1) + " px" : "auto";
    updateRotate();
  }
  const act = {
    smaller() { userFont = Math.max(5, (userFont || currentF()) - 0.75); store.set("amn:font", userFont); relayout(); },
    bigger() { userFont = Math.min(40, (userFont || currentF()) + 0.75); store.set("amn:font", userFont); relayout(); },
    auto() { userFont = 0; store.del("amn:font"); relayout(); },
    pad() { showPad = !showPad; store.set("amn:pad", showPad ? "1" : "0"); relayout(); },
    full() {
      const d = document.documentElement;
      if (document.fullscreenElement) document.exitFullscreen();
      else if (d.requestFullscreen) d.requestFullscreen().then(lockLandscape).catch(() => {});
    },
    export() {
      const o = {};
      for (const k of store.keys()) if (k.startsWith("amn:f:")) o[k.slice(6)] = store.get(k);
      const blob = new Blob([JSON.stringify(o)], { type: "application/json" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob); a.download = "aminomon-save.json";
      document.body.appendChild(a); a.click(); a.remove();
    },
    import() { $("file").click(); },
    restart() { if (confirm("Restart the game? (Your saved game is kept.)")) startWorker(); toggleMenu(false); },
    close() { toggleMenu(false); },
  };
  for (const b of document.querySelectorAll("[data-a]")) {
    b.addEventListener("click", () => { const f = act[b.dataset.a]; if (f) f(); });
  }
  $("file").addEventListener("change", async (e) => {
    const f = e.target.files[0]; e.target.value = "";
    if (!f) return;
    try {
      const o = JSON.parse(await f.text());
      let n = 0;
      for (const [k, v] of Object.entries(o)) if (/^\.aminomon[\w.]*$/.test(k) && typeof v === "string") { store.set("amn:f:" + k, v); n++; }
      if (!n) throw new Error("no save data");
      alert("Save restored. The game will restart."); toggleMenu(false); startWorker();
    } catch (err) { alert("That file is not an Aminomon save."); }
  });
  if (window.AndroidBridge) $("quit").classList.remove("hide");
  $("quit").addEventListener("click", () => { try { window.AndroidBridge.quit(); } catch (e) { /* ignore */ } });
  $("again").addEventListener("click", () => { $("exit").classList.add("hide"); startWorker(); });
  function currentF() { return Math.round((cw / ADV) / dpr * 4) / 4; }

  // ------------------------------------------------------------ orientation / fullscreen
  function lockLandscape() {
    try { screen.orientation.lock("landscape").catch(() => {}); } catch (e) { /* unsupported */ }
  }
  let rotateDismissed = false;
  function updateRotate() {
    const portrait = innerHeight > innerWidth && innerWidth < 700;
    $("rotate").classList.toggle("hide", !(portrait && !rotateDismissed));
  }
  $("rotateok").addEventListener("click", () => { rotateDismissed = true; updateRotate(); });
  let rt = 0;
  const onResize = () => { clearTimeout(rt); rt = setTimeout(relayout, 120); };
  addEventListener("resize", onResize);
  addEventListener("orientationchange", () => { rotateDismissed = false; onResize(); });
  // The page itself must never scroll or zoom
  document.addEventListener("touchmove", (e) => { if (e.target === document.body) e.preventDefault(); }, { passive: false });
  // Android's Back button (native wrapper calls this) acts as Esc
  window.gvBack = () => {
    const ex = $("exit"), mn = $("menu");
    if (!ex.classList.contains("hide")) return "quit";
    if (!mn.classList.contains("hide")) { toggleMenu(false); return "ok"; }
    key(27); return "ok";
  };

  // ------------------------------------------------------------ boot
  async function boot() {
    if (!window.crossOriginIsolated || typeof SharedArrayBuffer === "undefined") {
      // GitHub Pages / any static host: a service worker adds the needed headers
      if ("serviceWorker" in navigator && location.protocol !== "file:") {
        try {
          statusEl.textContent = "Preparing offline mode…";
          const reg = await navigator.serviceWorker.register("sw.js");
          await navigator.serviceWorker.ready;
          if (!navigator.serviceWorker.controller) { location.reload(); return; }
          if (!window.crossOriginIsolated) {
            if (!sessionStorage.getItem("amn:reloaded")) { sessionStorage.setItem("amn:reloaded", "1"); location.reload(); return; }
          }
        } catch (e) { /* handled below */ }
      }
      if (!window.crossOriginIsolated) {
        fail("This browser cannot run the game here.\nOpen it with Chrome (Android) over https, or install the Aminomon app.");
        return;
      }
    } else if (!window.AndroidBridge && "serviceWorker" in navigator && location.protocol.startsWith("http")) {
      navigator.serviceWorker.register("sw.js").catch(() => {});
    }
    try { navigator.storage && navigator.storage.persist && navigator.storage.persist(); } catch (e) { /* ignore */ }
    try {
      await Promise.all([
        new FontFace("GVMono", "url(fonts/mono.woff)", { weight: "400" }).load().then((f) => document.fonts.add(f)),
        new FontFace("GVMono", "url(fonts/mono-Bold.woff)", { weight: "700" }).load().then((f) => document.fonts.add(f)),
      ]);
    } catch (e) { /* falls back to the system monospace font */ }
    relayout();
    startWorker();
  }
  boot();
  window.gvDebug = { get cols() { return cols; }, get rows() { return rows; }, get cells() { return cells; }, key, click, special };
})();
