"use strict";

const express = require("express");
const path = require("path");
const { spawn } = require("child_process");

const PORT = Number.parseInt(process.env.PORT || "8080", 10);
const WORKER = path.join(__dirname, "worker.js");
const MAX_REQUEST = 48 * 1024;
const MAX_WORKER_OUTPUT = 128 * 1024;
const WORKER_ARGUMENTS = [
  "--permission",
  "--allow-fs-read=/challenge",
  "--allow-fs-read=/tmp/lika/flag.txt",
  "--max-old-space-size=48",
  WORKER,
];
const activeWorkerGroups = new Set();

const app = express();
app.disable("x-powered-by");
app.use(express.json({ limit: MAX_REQUEST, strict: true }));
app.use(express.static(path.join(__dirname, "static"), {
  etag: false,
  maxAge: 0,
}));

function isRecord(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function containsBlockedKey(value, seen = new Set()) {
  if (value === null || typeof value !== "object" || seen.has(value)) {
    return false;
  }

  seen.add(value);
  for (const key of Object.keys(value)) {
    if (key === "__proto__") {
      return true;
    }
    if (containsBlockedKey(value[key], seen)) {
      return true;
    }
  }
  return false;
}

function validateJob(body) {
  if (!isRecord(body)) {
    return "Preview data must be a JSON object";
  }
  if (typeof body.template !== "string" || body.template.length > 8192) {
    return "Template must be a string of at most 8192 characters";
  }
  if (!isRecord(body.theme) || !isRecord(body.model)) {
    return "Theme and model must be JSON objects";
  }
  if (containsBlockedKey(body.theme) || containsBlockedKey(body.model)) {
    return "Unsupported legacy key";
  }

  if (/\{\{~?\s*>\s*\(/u.test(body.template)) {
    return "Dynamic partial expressions are not supported";
  }

  if (/\{\{~?#\*\s*inline\b/u.test(body.template)) {
    return "Custom inline layouts are not supported";
  }

  const partialTag = /\{\{~?#?>~?\s*([^\s}~]+)/gu;
  const allowedPartials = new Set(["@partial-block", "myPartial"]);
  for (const match of body.template.matchAll(partialTag)) {
    if (!allowedPartials.has(match[1])) {
      return "Only the myPartial postcard layout is supported";
    }
  }
  return null;
}

function killWorkerGroup(pid) {
  if (!pid) return;
  activeWorkerGroups.delete(pid);
  try {
    process.kill(-pid, "SIGKILL");
  } catch (error) {
    if (error.code !== "ESRCH") throw error;
  }
}

function runWorker(job, signal) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, WORKER_ARGUMENTS, {
      detached: true,
      stdio: ["pipe", "pipe", "pipe"],
      env: {
        PATH: process.env.PATH || "/usr/bin:/bin",
        FLAG_PATH: process.env.FLAG_PATH || "/tmp/lika/flag.txt",
      },
    });
    activeWorkerGroups.add(child.pid);

    let stdout = Buffer.alloc(0);
    let stderr = Buffer.alloc(0);
    let settled = false;

    const finish = (callback, value) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      signal?.removeEventListener("abort", abortWorker);
      callback(value);
    };

    const abortWorker = () => {
      killWorkerGroup(child.pid);
      finish(reject, new Error("Print request was cancelled"));
    };

    const timer = setTimeout(() => {
      killWorkerGroup(child.pid);
      finish(reject, new Error("Print worker timed out"));
    }, 3000);

    if (signal?.aborted) {
      abortWorker();
      return;
    }
    signal?.addEventListener("abort", abortWorker, { once: true });

    child.stdout.on("data", (chunk) => {
      stdout = Buffer.concat([stdout, chunk]);
      if (stdout.length > MAX_WORKER_OUTPUT) {
        killWorkerGroup(child.pid);
        finish(reject, new Error("Print worker returned too much data"));
      }
    });
    child.stderr.on("data", (chunk) => {
      stderr = Buffer.concat([stderr, chunk]);
      if (stderr.length > MAX_WORKER_OUTPUT) {
        killWorkerGroup(child.pid);
        finish(reject, new Error("Print worker returned too much diagnostic data"));
      }
    });
    child.on("error", (error) => {
      activeWorkerGroups.delete(child.pid);
      finish(reject, error);
    });
    child.on("exit", () => killWorkerGroup(child.pid));
    child.on("close", (code) => {
      killWorkerGroup(child.pid);
      if (settled) return;
      try {
        const response = JSON.parse(stdout.toString("utf8"));
        if (code !== 0 && response.ok !== false) {
          throw new Error("Print worker stopped unexpectedly");
        }
        finish(resolve, response);
      } catch {
        const diagnostic = stderr.toString("utf8").trim();
        finish(reject, new Error(diagnostic || "Invalid print worker response"));
      }
    });

    child.stdin.end(JSON.stringify(job));
  });
}

app.post("/api/preview", async (request, response) => {
  const problem = validateJob(request.body);
  if (problem) {
    response.status(400).json({ error: problem });
    return;
  }

  const controller = new AbortController();
  request.once("aborted", () => controller.abort());
  response.once("close", () => {
    if (!response.writableEnded) controller.abort();
  });

  try {
    const result = await runWorker(request.body, controller.signal);
    response.status(result.ok ? 200 : 422).json(result);
  } catch (error) {
    response.status(502).json({ error: error.message });
  }
});

app.use((error, _request, response, _next) => {
  if (error instanceof SyntaxError) {
    response.status(400).json({ error: "Invalid JSON request" });
    return;
  }
  console.error(error);
  response.status(500).json({ error: "Unexpected archive error" });
});

function prepareFlag() {
  const fs = require("fs");
  const directory = "/tmp/lika";
  fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
  const flag = process.env.FLAG || "FortID{development_flag}";
  fs.writeFileSync(path.join(directory, "flag.txt"), `${flag}\n`, { mode: 0o400 });
  delete process.env.FLAG;
}

if (require.main === module) {
  prepareFlag();
  const server = app.listen(PORT, "0.0.0.0", () => {
    console.log(`Lika postcard desk listening on ${PORT}`);
  });

  const shutDown = () => {
    for (const pid of [...activeWorkerGroups]) {
      killWorkerGroup(pid);
    }
    server.close(() => process.exit(0));
  };
  process.once("SIGTERM", shutDown);
  process.once("SIGINT", shutDown);
}

module.exports = {
  app,
  activeWorkerGroups,
  containsBlockedKey,
  killWorkerGroup,
  runWorker,
  validateJob,
};
