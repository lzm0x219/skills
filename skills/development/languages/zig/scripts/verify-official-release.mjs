#!/usr/bin/env node

const INDEX_URL = "https://ziglang.org/download/index.json";
const argv = process.argv.slice(2);
let expectedVersion;
let verifyLinks = false;
let printJson = false;

for (let index = 0; index < argv.length; index += 1) {
  const argument = argv[index];
  if (argument === "--check") continue;
  if (argument === "--verify-links") {
    verifyLinks = true;
    continue;
  }
  if (argument === "--json") {
    printJson = true;
    continue;
  }
  if (argument === "--expect") {
    expectedVersion = argv[index + 1];
    if (!expectedVersion) {
      console.error("--expect requires a stable Zig version.");
      process.exit(2);
    }
    index += 1;
    continue;
  }
  if (argument === "--help") {
    console.log(
      "Usage: node scripts/verify-official-release.mjs [--check] [--expect VERSION] [--verify-links] [--json]\n\nReads the official Zig download index, excludes master/development builds, and reports the newest stable release. --expect fails when the current release differs; --verify-links fetches its docs, stdDocs, and notes URLs.",
    );
    process.exit(0);
  }
  console.error(`Unknown option: ${argument}`);
  process.exit(2);
}

function parseStableVersion(version) {
  const match = /^(\d+)\.(\d+)\.(\d+)$/.exec(version);
  return match ? match.slice(1).map(Number) : null;
}

function compareVersions(left, right) {
  const leftParts = parseStableVersion(left);
  const rightParts = parseStableVersion(right);
  for (let index = 0; index < 3; index += 1) {
    if (leftParts[index] !== rightParts[index]) return leftParts[index] - rightParts[index];
  }
  return 0;
}

async function fetchResponse(url) {
  const response = await fetch(url, {
    headers: { accept: "application/json,text/html;q=0.9,*/*;q=0.1" },
  });
  if (!response.ok) throw new Error(`${url}: ${response.status} ${response.statusText}`);
  return response;
}

function requireVersionedUrl(value, field, version) {
  if (typeof value !== "string") throw new Error(`Latest stable release has no ${field} URL.`);
  const url = new URL(value);
  if (url.protocol !== "https:" || url.hostname !== "ziglang.org") {
    throw new Error(`${field} is not an official HTTPS Zig URL: ${value}`);
  }
  if (!url.pathname.includes(`/${version}/`)) {
    throw new Error(`${field} does not point at Zig ${version}: ${value}`);
  }
  return value;
}

const indexResponse = await fetchResponse(INDEX_URL);
const releases = await indexResponse.json();
const stableVersions = Object.keys(releases).filter(parseStableVersion).sort(compareVersions);
if (stableVersions.length === 0) throw new Error("Official Zig index contains no stable releases.");

const version = stableVersions.at(-1);
const release = releases[version];
const result = {
  version,
  date: release.date,
  docs: requireVersionedUrl(release.docs, "docs", version),
  stdDocs: requireVersionedUrl(release.stdDocs, "stdDocs", version),
  notes: requireVersionedUrl(release.notes, "notes", version),
  masterVersion: releases.master?.version ?? null,
};

if (expectedVersion && expectedVersion !== version) {
  console.error(
    `Expected latest stable Zig ${expectedVersion}, but the official index reports ${version}.`,
  );
  process.exit(1);
}

if (verifyLinks) {
  for (const url of [result.docs, result.stdDocs, result.notes]) {
    const response = await fetchResponse(url);
    await response.body?.cancel();
  }
}

if (printJson) {
  console.log(JSON.stringify(result, null, 2));
} else {
  console.log(`Latest stable Zig: ${result.version} (${result.date}).`);
  if (result.masterVersion)
    console.log(`Current master development build: ${result.masterVersion}.`);
  console.log(
    `Verified versioned docs, stdDocs, and notes metadata${verifyLinks ? " and reachability" : ""}.`,
  );
}
