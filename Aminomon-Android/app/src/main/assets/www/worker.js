/* Module web worker: runs Aminomon (Python) in Pyodide. Blocking input uses a
   SharedArrayBuffer ring written by app.js; see src/curses.py. */
"use strict";
import { loadPyodide } from "./pyodide/pyodide.mjs";
const N = 512;            // ring slots, 4 ints each, starting at index 8
let A = null;

self.gvWait = (ms) => {
  const tail = Atomics.load(A, 1);
  let head = Atomics.load(A, 0);
  if (head === tail) {
    Atomics.wait(A, 0, head, ms < 0 ? 1e9 : ms);
    head = Atomics.load(A, 0);
    if (head === tail) return "";
  }
  const o = 8 + (tail % N) * 4;
  const s = A[o] + "," + A[o + 1] + "," + A[o + 2] + "," + A[o + 3];
  Atomics.store(A, 1, tail + 1);
  return s;
};
self.gvSleep = (ms) => { if (ms > 0) Atomics.wait(A, 4, 0, ms); };
self.gvFlush = () => Atomics.store(A, 1, Atomics.load(A, 0));
self.gvRows = () => Atomics.load(A, 2);
self.gvCols = () => Atomics.load(A, 3);
self.gvDraw = (j) => postMessage({ t: "draw", d: j });
self.gvSound = (j) => postMessage({ t: "sound", d: j });
self.gvSave = (name, text) => postMessage({ t: "save", name, text });
self.gvRestart = () => postMessage({ t: "restart" });
self.gvExit = () => postMessage({ t: "exit" });
self.gvFatal = (text) => postMessage({ t: "fatal", text });

self.onmessage = async (e) => {
  const m = e.data;
  if (m.t !== "init") return;
  A = new Int32Array(m.sab);
  try {
    postMessage({ t: "status", s: "Loading Python…" });
    const py = await loadPyodide({ indexURL: "pyodide/" });
    postMessage({ t: "status", s: "Loading game…" });
    const zip = await (await fetch("game.zip")).arrayBuffer();
    py.unpackArchive(zip, "zip", { extractDir: "/game" });
    const home = "/home/pyodide";
    py.FS.mkdirTree(home);
    for (const [name, text] of Object.entries(m.files || {})) {
      py.FS.writeFile(home + "/" + name, text, { encoding: "utf8" });
    }
    py.runPython(
      "import os\nos.environ['HOME']='" + home + "'\nos.environ['LANG']=" +
      JSON.stringify(m.lang || "en_US.UTF-8") + "\nos.environ['TERM']='xterm-256color'"
    );
    postMessage({ t: "ready" });
    py.runPython("import sys; sys.path.insert(0,'/game'); import boot");
  } catch (err) {
    postMessage({ t: "fatal", text: String((err && err.stack) || err) });
  }
};
