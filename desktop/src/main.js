const { app, BrowserWindow, dialog, shell } = require("electron");
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");

const APP_NAME = "VerityDesk";
const BACKEND_PORT = process.env.VERITYDESK_BACKEND_PORT || "8000";
const FRONTEND_PORT = process.env.VERITYDESK_FRONTEND_PORT || "3000";
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`;
const FRONTEND_URL = `http://127.0.0.1:${FRONTEND_PORT}`;
const DATABASE_FILENAME = "veritydesk.db";
const CONFIG_FILENAME = "config.env";
const DESKTOP_MODE = process.env.VERITYDESK_DESKTOP_MODE || "dev";

const repoRoot = path.resolve(__dirname, "..", "..");
const frontendDir = path.join(repoRoot, "frontend");
const backendDir = path.join(repoRoot, "backend");
const localNodeBin = path.join(repoRoot, ".runtime", "node-v22.23.2-darwin-arm64", "bin");
const localNpm = path.join(localNodeBin, "npm");
const pythonBin = path.join(repoRoot, ".venv", "bin", "python");
const uvicornBin = path.join(repoRoot, ".venv", "bin", "uvicorn");
const alembicBin = path.join(repoRoot, ".venv", "bin", "alembic");

const children = new Set();
let mainWindow = null;

app.setName(APP_NAME);

function commandPath(preferredPath, fallback) {
  return fs.existsSync(preferredPath) ? preferredPath : fallback;
}

function sqliteDatabaseUrl(databasePath) {
  return `sqlite:///${databasePath}`;
}

function parseEnvFile(filePath) {
  if (!fs.existsSync(filePath)) {
    return {};
  }

  const parsed = {};
  const content = fs.readFileSync(filePath, "utf8");
  for (const rawLine of content.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) {
      continue;
    }

    const separatorIndex = line.indexOf("=");
    if (separatorIndex === -1) {
      continue;
    }

    const key = line.slice(0, separatorIndex).trim();
    let value = line.slice(separatorIndex + 1).trim();
    if (!key) {
      continue;
    }
    if (
      (value.startsWith("\"") && value.endsWith("\"")) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    parsed[key] = value;
  }

  return parsed;
}

function ensureConfigFile(configPath) {
  if (fs.existsSync(configPath)) {
    return;
  }

  const template = [
    "# VerityDesk local desktop config",
    "# Fill in the keys you want the desktop app to use.",
    "# Do not commit this file to GitHub.",
    "",
    "OPENAI_API_KEY=",
    "OPENAI_MODEL=gpt-5-mini",
    "TAVILY_API_KEY=",
    "LIVE_WEB_SEARCH_PROVIDER=tavily",
    "FRED_API_KEY=",
    "CENSUS_API_KEY=",
    "ALPHA_VANTAGE_API_KEY=",
    "FINNHUB_API_KEY=",
    "NEWSAPI_KEY=",
    "GDELT_API_KEY=",
    "OWNER_EMAIL=",
    "INVESTORAGENT_USER_AGENT=VerityDesk/0.1 contact@example.com",
    "",
  ].join("\n");

  fs.writeFileSync(configPath, template, { mode: 0o600 });
}

function desktopRuntimePaths() {
  const dataDir = process.env.VERITYDESK_DESKTOP_DATA_DIR || app.getPath("userData");
  const logsDir = process.env.VERITYDESK_DESKTOP_LOG_DIR || path.join(app.getPath("logs"), APP_NAME);
  const databasePath = path.join(dataDir, DATABASE_FILENAME);
  const configPath = process.env.VERITYDESK_DESKTOP_CONFIG_PATH || path.join(dataDir, CONFIG_FILENAME);

  fs.mkdirSync(dataDir, { recursive: true });
  fs.mkdirSync(logsDir, { recursive: true });
  ensureConfigFile(configPath);

  return {
    dataDir,
    logsDir,
    databasePath,
    configPath,
    configEnv: parseEnvFile(configPath),
    databaseUrl: process.env.VERITYDESK_DESKTOP_DATABASE_URL || sqliteDatabaseUrl(databasePath),
  };
}

function childEnv(runtimePaths, extra = {}) {
  return {
    ...process.env,
    ...runtimePaths.configEnv,
    PATH: `${localNodeBin}:${process.env.PATH || ""}`,
    DATABASE_URL: runtimePaths.databaseUrl,
    FRONTEND_ORIGIN: FRONTEND_URL,
    NEXT_PUBLIC_API_BASE_URL: BACKEND_URL,
    VERITYDESK_DESKTOP: "1",
    VERITYDESK_DESKTOP_DATA_DIR: runtimePaths.dataDir,
    VERITYDESK_DESKTOP_LOG_DIR: runtimePaths.logsDir,
    ...extra,
  };
}

function spawnProcess(label, command, args, runtimePaths, options = {}) {
  const child = spawn(command, args, {
    cwd: options.cwd || repoRoot,
    env: childEnv(runtimePaths, options.env),
    stdio: ["ignore", "pipe", "pipe"],
  });

  children.add(child);
  child.stdout.on("data", (data) => console.log(`[${label}] ${data.toString().trimEnd()}`));
  child.stderr.on("data", (data) => console.error(`[${label}] ${data.toString().trimEnd()}`));
  child.on("exit", (code, signal) => {
    children.delete(child);
    console.log(`[${label}] exited with code ${code ?? "null"} signal ${signal ?? "null"}`);
  });
  child.on("error", (error) => {
    children.delete(child);
    console.error(`[${label}] failed to start`, error);
  });

  return child;
}

async function runProcess(label, command, args, runtimePaths, options = {}) {
  await new Promise((resolve, reject) => {
    const child = spawnProcess(label, command, args, runtimePaths, options);
    child.on("exit", (code) => {
      if (code === 0) {
        resolve();
        return;
      }
      reject(new Error(`${label} exited with code ${code}`));
    });
    child.on("error", reject);
  });
}

async function waitForUrl(url, timeoutMs = 90000) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        return;
      }
    } catch {
      // Service is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 750));
  }
  throw new Error(`Timed out waiting for ${url}`);
}

async function startServices() {
  if (!fs.existsSync(uvicornBin) || !fs.existsSync(alembicBin) || !fs.existsSync(pythonBin)) {
    throw new Error("Missing Python environment. Run: python3 -m venv .venv && .venv/bin/pip install -e backend[dev]");
  }

  const npmCommand = commandPath(localNpm, "npm");
  const runtimePaths = desktopRuntimePaths();
  const frontendArgs =
    DESKTOP_MODE === "production"
      ? ["run", "start", "--", "--hostname", "127.0.0.1", "--port", FRONTEND_PORT]
      : ["run", "dev", "--", "--hostname", "127.0.0.1", "--port", FRONTEND_PORT];

  console.log(`[desktop] data directory: ${runtimePaths.dataDir}`);
  console.log(`[desktop] database: ${runtimePaths.databasePath}`);
  console.log(`[desktop] config: ${runtimePaths.configPath}`);
  console.log(`[desktop] mode: ${DESKTOP_MODE}`);

  await runProcess("migrations", alembicBin, ["upgrade", "head"], runtimePaths, { cwd: backendDir });

  spawnProcess("backend", uvicornBin, ["app.main:app", "--host", "127.0.0.1", "--port", BACKEND_PORT], runtimePaths, {
    cwd: backendDir,
  });
  spawnProcess("frontend", npmCommand, frontendArgs, runtimePaths, {
    cwd: frontendDir,
  });

  await waitForUrl(`${BACKEND_URL}/health`);
  await waitForUrl(FRONTEND_URL);
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 960,
    minWidth: 1100,
    minHeight: 720,
    title: APP_NAME,
    backgroundColor: "#020617",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  mainWindow.loadURL(FRONTEND_URL);
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });
}

function stopServices() {
  for (const child of children) {
    if (!child.killed) {
      child.kill("SIGTERM");
    }
  }
}

async function boot() {
  try {
    await startServices();
    createWindow();
  } catch (error) {
    console.error(error);
    await dialog.showMessageBox({
      type: "error",
      title: `${APP_NAME} failed to start`,
      message: `${APP_NAME} could not start.`,
      detail: error instanceof Error ? error.message : String(error),
    });
    app.quit();
  }
}

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) {
        mainWindow.restore();
      }
      mainWindow.focus();
    }
  });

  app.whenReady().then(boot);

  app.on("window-all-closed", () => {
    if (process.platform !== "darwin") {
      app.quit();
    }
  });

  app.on("before-quit", stopServices);
}
