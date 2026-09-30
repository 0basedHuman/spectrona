#!/usr/bin/env node

const { spawnSync } = require("node:child_process");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const python = process.env.SPECTRONA_PYTHON || "python3";
const componentPaths = [
  path.join(root, "spectrona-cli", "src"),
  path.join(root, "spectrona-detection", "src"),
  path.join(root, "spectrona-gateway", "src"),
  path.join(root, "policy-engine", "src"),
  path.join(root, "mcp-inspector", "src"),
  path.join(root, "runtime-guard", "src"),
];
const existingPath = process.env.PYTHONPATH || "";
const env = {
  ...process.env,
  PYTHONPATH: existingPath ? `${componentPaths.join(path.delimiter)}${path.delimiter}${existingPath}` : componentPaths.join(path.delimiter),
};

const result = spawnSync(python, ["-m", "spectrona_cli", ...process.argv.slice(2)], {
  env,
  stdio: "inherit",
});

if (result.error) {
  console.error(`spectrona: failed to run ${python}: ${result.error.message}`);
  process.exit(127);
}

process.exit(result.status === null ? 1 : result.status);
