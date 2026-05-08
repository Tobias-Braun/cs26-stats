/**
 * Pre-build step: converts data/output_scaled.csv → public/elevation-data.json
 *
 * Runs automatically before `nuxt dev` and `nuxt build` via package.json pre-scripts.
 * Produces a static JSON file so the elevation data works on runtimes without
 * filesystem access (Cloudflare Workers).
 */

import { readFileSync, writeFileSync, mkdirSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT = resolve(__dirname, '..')
const TOTAL_KM = 600
const TARGET_POINTS = 480

const csv = readFileSync(resolve(ROOT, 'data/output_scaled.csv'), 'utf-8')
const lines = csv.trim().split('\n')

const all = []
for (let i = 1; i < lines.length; i++) {
  const parts = lines[i].split(',')
  const d = parseFloat(parts[3])
  if (d > TOTAL_KM) break
  all.push({ distanceKm: d, elevationM: parseFloat(parts[2]) })
}

const step = Math.max(1, Math.floor(all.length / TARGET_POINTS))
const sampled = all.filter((_, i) => i % step === 0)

if (sampled[sampled.length - 1] !== all[all.length - 1]) {
  sampled.push(all[all.length - 1])
}

mkdirSync(resolve(ROOT, 'public'), { recursive: true })
writeFileSync(
  resolve(ROOT, 'public/elevation-data.json'),
  JSON.stringify(sampled),
)

console.log(`[elevation] wrote ${sampled.length} points (0–${TOTAL_KM} km) → public/elevation-data.json`)
