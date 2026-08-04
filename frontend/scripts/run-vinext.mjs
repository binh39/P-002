import { spawnSync } from "node:child_process";

const command = process.platform === "win32" ? "vinext.cmd" : "vinext";
const result = spawnSync(command, [process.argv[2] ?? "dev"], {
  env: {
    ...process.env,
    WRANGLER_LOG_PATH: ".wrangler/wrangler.log",
  },
  stdio: "inherit",
  shell: process.platform === "win32",
});

process.exit(result.status ?? 1);
