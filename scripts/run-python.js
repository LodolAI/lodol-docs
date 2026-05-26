#!/usr/bin/env node

const { spawnSync } = require("node:child_process");

const scriptArgs = process.argv.slice(2);
const candidates =
  process.platform === "win32"
    ? [
        { command: "py", args: ["-3"] },
        { command: "python", args: [] },
        { command: "python3", args: [] },
      ]
    : [
        { command: "python3", args: [] },
        { command: "python", args: [] },
      ];

function hasPython3(candidate) {
  const result = spawnSync(
    candidate.command,
    [
      ...candidate.args,
      "-c",
      "import sys; raise SystemExit(0 if sys.version_info[0] == 3 else 1)",
    ],
    { stdio: "ignore" },
  );
  return !result.error && result.status === 0;
}

const python = candidates.find(hasPython3);

if (!python) {
  console.error(
    "Unable to find Python 3. Install Python 3 or make one of py, python, or python3 available on PATH.",
  );
  process.exit(1);
}

const result = spawnSync(python.command, [...python.args, ...scriptArgs], {
  stdio: "inherit",
});

if (result.error) {
  console.error(`Failed to run ${python.command}: ${result.error.message}`);
  process.exit(1);
}

process.exit(result.status ?? 1);
