import fs from "node:fs";
import net from "node:net";
import path from "node:path";
import process from "node:process";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..");
const tauriDriverPath = process.env.TAURI_DRIVER_PATH;
const nativeDriverPath = process.env.MSEDGEDRIVER_PATH;
const seedMode = (process.env.E2E_SEED_MODE || "").trim();
const rawSpecGlob = (process.env.E2E_SPEC_GLOB || "").trim();
const specGlob = rawSpecGlob
  ? path.isAbsolute(rawSpecGlob)
    ? rawSpecGlob
    : path.resolve(repoRoot, rawSpecGlob)
  : path.join(__dirname, "specs", "*.e2e.mjs");
const skipBuild = process.env.E2E_SKIP_BUILD === "1";
const pythonBinary = process.platform === "win32" ? "python" : "python3";
const corepackBinary = process.platform === "win32" ? "corepack.cmd" : "corepack";
const appBinary = path.join(
  repoRoot,
  "src-tauri",
  "target",
  "debug",
  process.platform === "win32"
    ? "student-budget-tracker.exe"
    : "student-budget-tracker",
);
const isolatedDataDir = path.join(repoRoot, ".e2e-data");
const isolatedLegacyDir = path.join(repoRoot, ".e2e-legacy");
const seedScript = path.join(__dirname, "scripts", "prepare-e2e-data.py");

let tauriDriverProcess;
let exitRequested = false;

function runCommand(command, args, cwd = repoRoot) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd,
      env: {
        ...process.env,
        STUDENT_BUDGET_TRACKER_DATA_DIR: isolatedDataDir,
        OFFLINE_BUDGET_TRACKER_DATA_DIR: isolatedLegacyDir,
      },
      shell: process.platform === "win32",
      stdio: "inherit",
    });

    child.on("error", reject);
    child.on("exit", (code) => {
      if (code === 0) {
        resolve();
        return;
      }
      reject(new Error(`${command} ${args.join(" ")} exited with code ${code}.`));
    });
  });
}

function waitForPort(port, timeoutMs = 30000) {
  const startedAt = Date.now();

  return new Promise((resolve, reject) => {
    const attempt = () => {
      const socket = net.createConnection({ host: "127.0.0.1", port }, () => {
        socket.end();
        resolve();
      });

      socket.on("error", () => {
        socket.destroy();
        if (Date.now() - startedAt > timeoutMs) {
          reject(new Error(`Timed out waiting for port ${port}.`));
          return;
        }
        setTimeout(attempt, 250);
      });
    };

    attempt();
  });
}

export const config = {
  runner: "local",
  specs: [specGlob],
  maxInstances: 1,
  logLevel: "error",
  waitforTimeout: 10000,
  connectionRetryTimeout: 120000,
  connectionRetryCount: 2,
  framework: "mocha",
  reporters: ["spec"],
  mochaOpts: {
    ui: "bdd",
    timeout: 120000,
  },
  host: "127.0.0.1",
  port: 4444,
  capabilities: [
    {
      maxInstances: 1,
      "tauri:options": {
        application: appBinary,
      },
    },
  ],
  onPrepare: async function () {
    if (!tauriDriverPath || !fs.existsSync(tauriDriverPath)) {
      throw new Error(
        "TAURI_DRIVER_PATH must point to an installed tauri-driver binary before running E2E tests.",
      );
    }

    if (!nativeDriverPath || !fs.existsSync(nativeDriverPath)) {
      throw new Error(
        "MSEDGEDRIVER_PATH must point to a working msedgedriver.exe before running E2E tests.",
      );
    }

    fs.rmSync(isolatedDataDir, { force: true, recursive: true });
    fs.mkdirSync(isolatedDataDir, { recursive: true });
    fs.rmSync(isolatedLegacyDir, { force: true, recursive: true });
    fs.mkdirSync(isolatedLegacyDir, { recursive: true });

    if (seedMode) {
      const seedArgs = [
        seedScript,
        "--mode",
        seedMode,
        "--repo-root",
        repoRoot,
        "--data-dir",
        isolatedDataDir,
        "--legacy-dir",
        isolatedLegacyDir,
      ];
      if (process.env.E2E_SOURCE_DB) {
        seedArgs.push("--source-db", process.env.E2E_SOURCE_DB);
      }
      await runCommand(pythonBinary, seedArgs);
    }

    if (!skipBuild) {
      await runCommand(corepackBinary, [
        "pnpm",
        "tauri",
        "build",
        "--debug",
        "--no-bundle",
      ]);
    }

    if (!fs.existsSync(appBinary)) {
      throw new Error(`Expected debug application at ${appBinary}.`);
    }

  },
  beforeSession: async function () {
    tauriDriverProcess = spawn(tauriDriverPath, ["--native-driver", nativeDriverPath], {
      env: {
        ...process.env,
        STUDENT_BUDGET_TRACKER_DATA_DIR: isolatedDataDir,
        OFFLINE_BUDGET_TRACKER_DATA_DIR: isolatedLegacyDir,
      },
      stdio: [null, process.stdout, process.stderr],
    });

    tauriDriverProcess.on("error", (error) => {
      console.error("tauri-driver error:", error);
      process.exit(1);
    });

    tauriDriverProcess.on("exit", (code) => {
      if (!exitRequested) {
        console.error("tauri-driver exited with code:", code);
        process.exit(1);
      }
    });

    await waitForPort(4444);
  },
  afterSession: async function () {
    exitRequested = true;
    tauriDriverProcess?.kill();
  },
  onComplete: async function () {
    exitRequested = true;
    tauriDriverProcess?.kill();
  },
};
