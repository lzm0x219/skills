#!/usr/bin/env node
import { readFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const LLMS_URL = 'https://mise.jdx.dev/llms.txt'
const SITEMAP_URL = 'https://mise.jdx.dev/sitemap.xml'
const SITE_ORIGIN = 'https://mise.jdx.dev'
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
  const parsed = new URL(url, SITE_ORIGIN)
  parsed.hash = ''
  parsed.search = ''
  parsed.pathname = parsed.pathname.replace(/\/index\.html$/, '/')
  if (parsed.pathname !== '/') parsed.pathname = parsed.pathname.replace(/\/$/, '')
  return parsed.toString().replace(/\/$/, '')
}

function parseLlmsIndex(markdown) {
  const pages = []
  for (const line of markdown.split('\n')) {
    const link = line.match(/^- \[[^\]]+\]\((https:\/\/mise\.jdx\.dev\/[^)]+)\)/)
    if (link) pages.push(canonicalize(link[1]))
  }
  if (pages.length === 0) {
    throw new Error('No mise.jdx.dev pages found in the official llms.txt index.')
  }
  return new Set(pages)
}

function parseSitemap(xml) {
  const pages = []
  for (const match of xml.matchAll(/<loc>(https:\/\/mise\.jdx\.dev\/[^<]+)<\/loc>/g)) {
    pages.push(canonicalize(match[1]))
  }
  if (pages.length === 0) {
    throw new Error('No mise.jdx.dev pages found in the official sitemap.')
  }
  return new Set(pages)
}

function parseRecordedPages(markdown) {
  const skippedPaths = new Set(['/llms.txt', '/sitemap.xml'])
  const pages = new Set()
  for (const match of markdown.matchAll(/https:\/\/mise\.jdx\.dev\/[^\s)\]`]+/g)) {
    const url = canonicalize(match[0])
    const parsed = new URL(url)
    if (!skippedPaths.has(parsed.pathname)) pages.add(url)
  }
  if (pages.size === 0) {
    throw new Error('No official mise page URLs found in the local inventory.')
  }
  return pages
}

async function fetchText(url) {
  const response = await fetch(url, {
    headers: { accept: 'text/markdown,text/plain,text/html;q=0.9,*/*;q=0.1' },
  })
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`)
  return response.text()
}

async function fetchRecordedPage(url) {
  const parsed = new URL(url)
  const candidates = parsed.pathname.includes('.') ? [url] : [url, `${url}/`]
  let lastError
  for (const candidate of candidates) {
    try {
      return await fetchText(candidate)
    } catch (error) {
      lastError = error
    }
  }
  throw lastError
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
  console.log(`Usage: node scripts/verify-official-docs-inventory.mjs [--check] [--verify-links] [--print-live]\n\nChecks that every documented mise topic URL is still present in the official https://mise.jdx.dev/llms.txt or sitemap.xml index.\n--check         Run the index comparison (the default action).\n--verify-links  Fetch every topic URL after the index comparison.\n--print-live    Print the live official URL count.`)
  process.exit(0)
}

const [liveIndex, liveSitemap, inventory] = await Promise.all([
  fetchText(LLMS_URL),
  fetchText(SITEMAP_URL),
  readFile(inventoryPath, 'utf8'),
])
const llmsPages = parseLlmsIndex(liveIndex)
const sitemapPages = parseSitemap(liveSitemap)
const livePages = new Set([...llmsPages, ...sitemapPages])
const recordedPages = parseRecordedPages(inventory)
const missing = [...recordedPages].filter((url) => !livePages.has(url)).sort()

if (args.has('--print-live')) {
  console.log(`Official index URLs: llms ${llmsPages.size}, sitemap ${sitemapPages.size}, union ${livePages.size}.`)
}

console.log(
  `Official index URLs: llms ${llmsPages.size}, sitemap ${sitemapPages.size}; recorded topic pages: ${recordedPages.size}.`,
)
if (missing.length) {
  console.error(`Missing from the current official index:\n${missing.join('\n')}`)
  process.exitCode = 1
} else {
  console.log('Every recorded topic URL is present in a current official index.')
}

if (args.has('--verify-links') && process.exitCode !== 1) {
  const failures = (await mapPool([...recordedPages].sort(), 8, async (url) => {
    try {
      await fetchRecordedPage(url)
      return null
    } catch (error) {
      return `${url}: ${error.message}`
    }
  })).filter(Boolean)
  if (failures.length) {
    console.error(`Unreachable recorded topic pages:\n${failures.join('\n')}`)
    process.exitCode = 1
  } else {
    console.log(`Verified ${recordedPages.size} recorded official topic URLs.`)
  }
}
