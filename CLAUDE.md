# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Goal

A **Nuxt 3 web app** displaying real-time telemetry for the Red Bull Cyborg Season 26 ultra-marathon (600 km / 96 h hard cutoff, athlete: Arda). Live metrics are scraped from the event's video stream by `get-val.py` via OCR, stored in Supabase, and rendered in a cyberpunk dashboard styled after `assets/CS26-Stats.html`.

## Dashboard Panels

- **Elapsed time** + countdown to 96 h cutoff
- **Heart rate** with animated 80-point sparkline
- **Current pace / average pace** with comparison bars
- **Distance completed / remaining** with progress percentage
- **Pace projections** — ETA at current avg pace; minimum pace required to finish within cutoff
- **Elevation profile** — SVG rendered from real GPX route data, slope-colored segments

## Architecture

```
nuxt.config.ts                   ← cloudflare-pages preset, supabase module, runtimeConfig
wrangler.toml                    ← Cloudflare Pages deployment config
pages/index.vue                  ← dashboard root, composes all panels
components/
  KpiPanel.vue                   ← generic card shell (title, value, hint slots)
  ElapsedTime.vue
  HeartRate.vue                  ← sparkline included
  PacePanel.vue                  ← current + average, comparison bar
  DistancePanel.vue
  ProjectionBand.vue             ← two projections: finish forecast + cutoff pace
  ElevationChart.vue             ← SVG from elevation-data.json prop; slope color ramp
composables/
  useEventStats.ts               ← all reactive stats; Supabase realtime; tick-based interpolation
  useElevationData.ts            ← fetches /elevation-data.json (pre-built static file)
utils/
  constants.ts                   ← TOTAL_KM, CUTOFF_SECONDS, ATHLETE_NAME, etc.
scripts/
  build-elevation.mjs            ← reads data/output_scaled.csv → public/elevation-data.json
assets/
  CS26-Stats.html                ← visual reference; do not import
  css/main.css
data/
  output_scaled.csv              ← 8,761 trackpoints: lat, lon, elevation_m, distance_km (600 km)
get-val.py                       ← OCR scraper; writes to Supabase every 60 s
```

## Data Flow

```
get-val.py  →  Supabase (athlete_stats)  →  useEventStats.ts  →  dashboard
```

**Only these raw fields are stored in Supabase** (`athlete_stats` table):
| column | type | notes |
|---|---|---|
| `elapsed_seconds` | int | from OCR `elapsed_time` HH:MM:SS |
| `distance_km` | float | from OCR `distance_covered_km` |
| `heart_rate` | int | from OCR `heart_rate` |
| `current_speed` | float (nullable) | km/h, converted from OCR `pace_km` M:SS string |
| `recorded_at` | timestamptz | auto by Supabase |

Everything else (pace in sec/km, projections, ETA, required pace, countdown, progress %) is **calculated client-side** in `useEventStats.ts`.

## Supabase Integration

- `@nuxtjs/supabase` module; guarded by `supabaseEnabled` in `runtimeConfig.public`
- When env vars are absent the app runs in demo/stub mode with hardcoded realistic values
- On mount: fetches the 2 most recent rows (needed for pace delta), then subscribes to realtime INSERT events
- `rowToReading()` converts DB rows; `current_speed` km/h → sec/km via `3600 / kmh`
- Required env vars: `SUPABASE_URL`, `SUPABASE_KEY` (anon key for frontend), `SUPABASE_SERVICE_ROLE_KEY` (for `get-val.py`)

## Event Constants (`utils/constants.ts`)

```ts
TOTAL_KM = 600
TARGET_HOURS = 96
CUTOFF_SECONDS = 345_600
ATHLETE_NAME = 'Arda'
START_UTC = '2026-05-06T06:00:00Z'
CUTOFF_UTC = '2026-05-10T06:00:00Z'
PACE_BAR_MIN_SEC = 540   // 9 min/km — slowest end of comparison bar
PACE_BAR_MAX_SEC = 960   // 16 min/km — fastest end
```

## Elevation Data Pipeline

Cloudflare Workers cannot read the filesystem at runtime, so the CSV is pre-built to a static JSON:

```bash
# Runs automatically before dev/build via package.json predev/prebuild hooks
node scripts/build-elevation.mjs
# → writes public/elevation-data.json (~480 sampled points)
```

`useElevationData.ts` fetches this static file; no server API route is needed.

The Python route-data scripts are run manually when the GPX changes:
```
in.gpx → splits.py → rescale-dist.py → output_scaled.csv → (used by build-elevation.mjs)
```

## OCR Scraper (`get-val.py`)

- Connects to an HLS stream directly or resolves a page URL via `yt-dlp`
- Crops each ROI from the frame (defined as fractional coordinates in `ROIS`), scales 3×, binarises, runs Tesseract with per-field character whitelists
- `validate_and_correct()` applies plausibility checks: range guards, ÷10 correction for extra-digit OCR misreads (e.g. "1400 bpm" → 140), and delta checks for distance jumps
- `pace_to_kmh()` converts M:SS string → float km/h before Supabase insert
- `hms_to_seconds()` strips each colon-separated part individually to survive OCR whitespace artifacts

## Design Tokens

- **Background:** `#07050a`, layered radial gradients, scanline overlay, 56 px grid
- **Accent colors (OKLCH):** hot = red-pink, warn = yellow, good = green
- **Fonts:** Space Grotesk (headlines), JetBrains Mono (data/labels)
- **Layout:** 12-column CSS grid; panels use `col-3`, `col-5`, `col-7`, `col-12`
- **Responsive breakpoint:** 1100 px → cols collapse to 6
- Elapsed time large display: `clamp(52px, 6.5vw, 104px)` to fit the card

## Development Commands

```bash
pnpm install
pnpm dev       # also runs build-elevation.mjs via predev hook
pnpm build
pnpm preview

# OCR scraper (Python 3 + requirements.txt)
pip install -r requirements.txt
python get-val.py   # STREAM_URL is hardcoded at the top of the file
```

## Deployment (Cloudflare Pages)

```bash
pnpm build     # outputs to .output/public
# deploy via Cloudflare Pages dashboard or wrangler
```

`wrangler.toml` sets `pages_build_output_dir = ".output/public"` and `compatibility_flags = ["nodejs_compat"]`. Set `SUPABASE_URL` and `SUPABASE_KEY` as environment variables in the Cloudflare Pages project settings.
