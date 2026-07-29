#!/usr/bin/env node
import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const LLMS_URL = 'https://napi.rs/llms.txt'
const SITEMAP_URL = 'https://napi.rs/sitemap.xml'
const skillDir = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const inventoryPath = resolve(
  skillDir,
  'references/official-documentation-inventory.md',
)
const args = new Set(process.argv.slice(2))
const supportedArgs = new Set(['--check', '--verify-links', '--print-live', '--help'])
const unknownArgs = [...args].filter((arg) => !supportedArgs.has(arg))

if (unknownArgs.length) {
  console.error(`Unknown option(s): ${unknownArgs.join(', ')}`)
  process.exit(2)
}

function canonicalize(url) {
  const parsed = new URL(url, 'https://napi.rs')
  parsed.hash = ''
  parsed.search = ''
  parsed.pathname = parsed.pathname.replace(/\.md$/, '').replace(/\/$/, '') || '/'
  return parsed.toString().replace(/\/$/, '')
}

function parseLlmsIndex(markdown) {
  let group = null
  const pages = []
  for (const line of markdown.split('\n')) {
    const heading = line.match(/^## (.+)$/)
    if (heading) {
      group = heading[1]
      continue
    }
    const link = line.match(/^- \[([^\]]+)\]\((\/[^)]+\.md)\)/)
    if (link && (group === 'Docs' || group === 'Blog')) {
      pages.push({ group, title: link[1], url: canonicalize(link[2]) })
    }
  }
  if (pages.length === 0) {
    throw new Error('No Docs or Blog pages found in the official llms.txt index.')
  }
  return pages
}

function parseSitemap(xml) {
  const pages = []
  for (const match of xml.matchAll(/<loc>(https:\/\/napi\.rs\/(?:docs|blog)\/[^<]+)<\/loc>/g)) {
    const url = canonicalize(match[1])
    pages.push({
      group: new URL(url).pathname.startsWith('/docs/') ? 'Docs' : 'Blog',
      title: null,
      url,
    })
  }
  if (pages.length === 0) {
    throw new Error('No canonical Docs or Blog pages found in the official sitemap.')
  }
  return pages
}

function parseRecordedUrls(markdown) {
  return new Set(
    [...markdown.matchAll(/https:\/\/napi\.rs\/(?:docs|blog)\/[^\s)#\]`]+/g)].map((match) =>
      canonicalize(match[0]),
    ),
  )
}

async function fetchText(url) {
  const response = await fetch(url, {
    headers: { accept: 'text/markdown,text/plain,text/html;q=0.9,*/*;q=0.1' },
  })
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`)
  return response.text()
}

async function mapPool(items, limit, mapper) {
  const results = new Array(items.length)
  let cursor = 0
  await Promise.all(
    Array.from({ length: Math.min(limit, items.length) }, async () => {
      while (cursor < items.length) {
        const index = cursor++
        results[index] = await mapper(items[index])
      }
    }),
  )
  return results
}

if (args.has('--help')) {
  console.log(`Usage: node scripts/verify-official-docs-coverage.mjs [--check] [--verify-links] [--print-live]\n\nCompares the checked-in official documentation inventory with the union of https://napi.rs/llms.txt and https://napi.rs/sitemap.xml.\n--check         Run the coverage comparison (the default action).\n--verify-links  Fetch every current official Docs and Blog page after the set comparison.\n--print-live    Print the parsed current page list as JSON.`)
  process.exit(0)
}

const [liveIndex, liveSitemap, inventory] = await Promise.all([
  fetchText(LLMS_URL),
  fetchText(SITEMAP_URL),
  readFile(inventoryPath, 'utf8'),
])
const llmsPages = parseLlmsIndex(liveIndex)
const sitemapPages = parseSitemap(liveSitemap)
const livePages = [...new Map([...llmsPages, ...sitemapPages].map((page) => [page.url, page])).values()]
const liveUrls = new Set(livePages.map((page) => page.url))
const recordedUrls = parseRecordedUrls(inventory)
const missing = [...liveUrls].filter((url) => !recordedUrls.has(url)).sort()
const stale = [...recordedUrls].filter((url) => !liveUrls.has(url)).sort()
const counts = livePages.reduce(
  (result, page) => ({ ...result, [page.group]: (result[page.group] ?? 0) + 1 }),
  {},
)

if (args.has('--print-live')) {
  console.log(JSON.stringify(livePages, null, 2))
}

console.log(
  `Official index: Docs ${counts.Docs ?? 0}, Blog ${counts.Blog ?? 0}; inventory links: ${recordedUrls.size}.`,
)
if (missing.length || stale.length) {
  if (missing.length) console.error(`Missing from inventory:\n${missing.join('\n')}`)
  if (stale.length) console.error(`No longer in official index:\n${stale.join('\n')}`)
  process.exitCode = 1
} else {
  console.log('Coverage inventory matches the current official llms.txt/sitemap union.')
}

if (args.has('--verify-links') && process.exitCode !== 1) {
  const failures = (await mapPool(livePages, 8, async (page) => {
    try {
      await fetchText(page.url)
      return null
    } catch (error) {
      return `${page.url}: ${error.message}`
    }
  })).filter(Boolean)
  if (failures.length) {
    console.error(`Unreachable official pages:\n${failures.join('\n')}`)
    process.exitCode = 1
  } else {
    console.log(`Verified ${livePages.length} official page URLs.`)
  }
}
