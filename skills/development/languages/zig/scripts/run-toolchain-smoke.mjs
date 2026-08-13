#!/usr/bin/env node

import { copyFile, mkdir, mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const fixtureDir = resolve(scriptDir, "fixtures", "toolchain-smoke");
const argv = process.argv.slice(2);
let zig = "zig";

for (let index = 0; index < argv.length; index += 1) {
  const argument = argv[index];
  if (argument === "--zig") {
    zig = argv[index + 1];
    if (!zig) {
      console.error("--zig requires a Zig executable path.");
      process.exit(2);
    }
    if (zig.includes("/") || zig.includes("\\")) zig = resolve(zig);
    index += 1;
    continue;
  }
  if (argument === "--help") {
    console.log(
      "Usage: node scripts/run-toolchain-smoke.mjs [--zig PATH]\n\nCopies the bundled fixture to an isolated temporary directory, checks zig fmt, and runs the build-system test step. Run once for each representative Zig toolchain.",
    );
    process.exit(0);
  }
  console.error(`Unknown option: ${argument}`);
  process.exit(2);
}

function run(command, args, cwd, env) {
  const result = spawnSync(command, args, { cwd, env, encoding: "utf8" });
  if (result.error) throw result.error;
  if (result.status !== 0) {
    const output = [result.stdout, result.stderr].filter(Boolean).join("\n");
    throw new Error(`${command} ${args.join(" ")} failed with exit ${result.status}.\n${output}`);
  }
  return [result.stdout, result.stderr].filter(Boolean).join("\n");
}

const temporaryDir = await mkdtemp(join(tmpdir(), "zig-skill-smoke-"));
try {
  await mkdir(join(temporaryDir, "src"), { recursive: true });
  await copyFile(join(fixtureDir, "build.zig"), join(temporaryDir, "build.zig"));
  await copyFile(join(fixtureDir, "lib.zig"), join(temporaryDir, "src", "lib.zig"));

  const env = {
    ...process.env,
    ZIG_GLOBAL_CACHE_DIR: join(temporaryDir, "global-cache"),
    ZIG_LOCAL_CACHE_DIR: join(temporaryDir, "local-cache"),
  };
  const version = run(zig, ["version"], temporaryDir, env).trim();
  run(zig, ["fmt", "--check", "build.zig", "src/lib.zig"], temporaryDir, env);
  run(zig, ["build", "test", "--summary", "all"], temporaryDir, env);

  const marker = await readFile(join(temporaryDir, ".zig-skill-smoke-executed"), "utf8");
  if (marker !== "executed\n") {
    throw new Error(
      "Smoke test marker is missing or invalid; the test artifact may not have executed.",
    );
  }
  console.log(`PASS: Zig ${version}; formatting checked and build-system tests executed.`);
} finally {
  await rm(temporaryDir, { recursive: true, force: true });
}
