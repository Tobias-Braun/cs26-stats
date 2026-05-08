<script setup lang="ts">
import type { ElevationPoint } from '~/composables/useElevationData'
import { TOTAL_KM } from '~/utils/constants'

const props = defineProps<{
  points: ElevationPoint[]
  progressKm: number
  athleteName?: string
}>()

// SVG canvas constants
const W = 1560
const H = 320
const PAD_L = 56
const PAD_R = 24
const PAD_T = 14
const PAD_B = 36
const INNER_W = W - PAD_L - PAD_R
const INNER_H = H - PAD_T - PAD_B

const elevations = computed(() => props.points.map(p => p.elevationM))
const minElev = computed(() => Math.min(...elevations.value))
const maxElev = computed(() => Math.max(...elevations.value))

const xFor = (km: number) => PAD_L + (km / TOTAL_KM) * INNER_W
const yFor = (e: number) => {
  const range = maxElev.value - minElev.value || 1
  return PAD_T + INNER_H - ((e - minElev.value) / range) * INNER_H
}

/** OKLCH color ramp from green (flat) → red (steep), matching the HTML design. */
function slopeColor(absSlopePct: number): string {
  const stops: [number, [number, number, number]][] = [
    [0,  [0.72, 0.20, 145]],
    [3,  [0.82, 0.18, 100]],
    [6,  [0.80, 0.20, 70]],
    [9,  [0.74, 0.22, 35]],
    [13, [0.66, 0.27, 12]],
  ]
  let i = 0
  while (i < stops.length - 1 && absSlopePct > stops[i + 1][0]) i++
  const a = stops[i]
  const b = stops[Math.min(i + 1, stops.length - 1)]
  const t = a === b ? 0 : Math.min(1, Math.max(0, (absSlopePct - a[0]) / (b[0] - a[0])))
  const L = a[1][0] + (b[1][0] - a[1][0]) * t
  const C = a[1][1] + (b[1][1] - a[1][1]) * t
  let dh = b[1][2] - a[1][2]
  if (dh > 180) dh -= 360
  else if (dh < -180) dh += 360
  const H = (a[1][2] + dh * t + 360) % 360
  return `oklch(${(L * 100).toFixed(1)}% ${C.toFixed(3)} ${H.toFixed(1)})`
}

interface Segment {
  x1: number; y1: number
  x2: number; y2: number
  yB: number
  color: string
  slopePct: number
}

const segments = computed((): Segment[] => {
  const pts = props.points
  if (pts.length < 2) return []
  const W_SMOOTH = 2
  return pts.slice(1).map((b, idx) => {
    const a = pts[idx]
    const dKmM = (b.distanceKm - a.distanceKm) * 1000
    const rawSlope = dKmM > 0 ? ((b.elevationM - a.elevationM) / dKmM) * 100 : 0

    // smooth slope over a small window to reduce single-sample noise
    let acc = 0; let cnt = 0
    const i = idx + 1
    for (let k = Math.max(1, i - W_SMOOTH); k <= Math.min(pts.length - 1, i + W_SMOOTH); k++) {
      const dh = (pts[k].distanceKm - pts[k - 1].distanceKm) * 1000
      if (dh > 0) { acc += ((pts[k].elevationM - pts[k - 1].elevationM) / dh) * 100; cnt++ }
    }
    const smoothed = cnt ? acc / cnt : rawSlope

    return {
      x1: xFor(a.distanceKm),
      y1: yFor(a.elevationM),
      x2: xFor(b.distanceKm),
      y2: yFor(b.elevationM),
      yB: PAD_T + INNER_H,
      color: slopeColor(Math.abs(smoothed)),
      slopePct: smoothed,
    }
  })
})

const yTicks = computed(() =>
  [0, 0.25, 0.5, 0.75, 1].map(t => ({
    e: minElev.value + t * (maxElev.value - minElev.value),
    y: PAD_T + INNER_H - t * INNER_H,
  })),
)

const xTicks = computed(() => {
  const ticks: number[] = []
  for (let k = 0; k <= TOTAL_KM; k += 60) ticks.push(k)
  return ticks
})

const hereX = computed(() => xFor(props.progressKm))
const hereIdx = computed(() =>
  Math.min(props.points.length - 1, Math.max(0, Math.round((props.progressKm / TOTAL_KM) * (props.points.length - 1)))),
)
const herePoint = computed(() => props.points[hereIdx.value] ?? props.points[0])
const hereY = computed(() => herePoint.value ? yFor(herePoint.value.elevationM) : PAD_T)

const hereSegment = computed(() => segments.value[Math.min(segments.value.length - 1, Math.max(0, hereIdx.value))])

const tooltipX = computed(() => Math.min(hereX.value + 12, PAD_L + INNER_W - 158))
const tooltipY = computed(() => Math.max(hereY.value - 50, PAD_T + 10))
</script>

<template>
  <div class="chart-wrap">
    <div class="chart-head">
      <div>
        <div class="chart-title">
          Course Elevation
          <small>{{ TOTAL_KM }} KM</small>
        </div>
      </div>
      <div class="chart-legend">
        <span>SLOPE</span>
        <div style="display: flex; flex-direction: column; gap: 3px">
          <span class="grad-key" />
          <div class="grad-key-tics">
            <span style="left: 0%">0%</span>
            <span style="left: 25%">3%</span>
            <span style="left: 50%">6%</span>
            <span style="left: 75%">9%</span>
            <span style="left: 100%">13%+</span>
          </div>
        </div>
      </div>
    </div>

    <svg
      :viewBox="`0 0 ${W} ${H}`"
      width="100%"
      style="display: block; margin-top: 14px"
    >
      <defs>
        <clipPath id="clip-done">
          <rect :x="PAD_L" :y="PAD_T" :width="Math.max(0, hereX - PAD_L)" :height="INNER_H" />
        </clipPath>
        <clipPath id="clip-todo">
          <rect :x="hereX" :y="PAD_T" :width="Math.max(0, PAD_L + INNER_W - hereX)" :height="INNER_H" />
        </clipPath>
      </defs>

      <!-- y-axis gridlines + labels -->
      <g v-for="(t, i) in yTicks" :key="'yt' + i">
        <line
          :x1="PAD_L" :x2="PAD_L + INNER_W"
          :y1="t.y" :y2="t.y"
          stroke="rgba(255,255,255,0.06)"
          stroke-dasharray="2 6"
        />
        <text
          :x="PAD_L - 10" :y="t.y + 4"
          text-anchor="end"
          font-family="JetBrains Mono, monospace"
          font-size="10.5"
          fill="rgba(255,255,255,0.40)"
          letter-spacing="0.08em"
        >{{ Math.round(t.e) }} m</text>
      </g>

      <!-- x-axis distance ticks -->
      <g v-for="k in xTicks" :key="'xt' + k">
        <line
          :x1="xFor(k)" :x2="xFor(k)"
          :y1="PAD_T" :y2="PAD_T + INNER_H"
          stroke="rgba(255,255,255,0.04)"
        />
        <text
          :x="xFor(k)" :y="PAD_T + INNER_H + 18"
          text-anchor="middle"
          font-family="JetBrains Mono, monospace"
          font-size="10.5"
          fill="rgba(255,255,255,0.45)"
          letter-spacing="0.1em"
        >{{ k }} KM</text>
      </g>

      <!-- upcoming section — faded slope-colored fill + stroke -->
      <g clip-path="url(#clip-todo)" opacity="0.55">
        <polygon
          v-for="(s, i) in segments"
          :key="'tu' + i"
          :points="`${s.x1},${s.y1} ${s.x2},${s.y2} ${s.x2},${s.yB} ${s.x1},${s.yB}`"
          :fill="s.color"
          fill-opacity="0.18"
          stroke="none"
        />
        <line
          v-for="(s, i) in segments"
          :key="'tul' + i"
          :x1="s.x1" :x2="s.x2"
          :y1="s.y1" :y2="s.y2"
          :stroke="s.color"
          stroke-opacity="0.6"
          stroke-width="1.3"
        />
      </g>

      <!-- completed section — full opacity fill + stroke -->
      <g clip-path="url(#clip-done)">
        <polygon
          v-for="(s, i) in segments"
          :key="'do' + i"
          :points="`${s.x1},${s.y1} ${s.x2},${s.y2} ${s.x2},${s.yB} ${s.x1},${s.yB}`"
          :fill="s.color"
          fill-opacity="0.42"
          stroke="none"
        />
        <line
          v-for="(s, i) in segments"
          :key="'dol' + i"
          :x1="s.x1" :x2="s.x2"
          :y1="s.y1" :y2="s.y2"
          :stroke="s.color"
          stroke-width="1.9"
        />
      </g>

      <!-- current position marker -->
      <line
        :x1="hereX" :x2="hereX"
        :y1="PAD_T" :y2="PAD_T + INNER_H"
        stroke="oklch(85% 0.18 350)"
        stroke-width="1.2"
        stroke-dasharray="3 4"
        opacity="0.85"
      />
      <circle :cx="hereX" :cy="hereY" r="6" fill="oklch(78% 0.26 10)" stroke="white" stroke-width="1.6">
        <animate attribute-name="r" values="5;9;5" dur="1.6s" repeat-count="indefinite" />
      </circle>

      <!-- tooltip at current position -->
      <g v-if="herePoint" :transform="`translate(${tooltipX}, ${tooltipY})`">
        <rect width="158" height="44" rx="6" fill="rgba(20,8,16,0.88)" stroke="rgba(255,90,120,0.5)" />
        <text x="10" y="13" font-family="JetBrains Mono, monospace" font-size="9.5" letter-spacing="0.16em"
              fill="rgba(255,255,255,0.55)">
          {{ (athleteName ?? 'YOU').toUpperCase() }} · KM {{ progressKm.toFixed(1) }}
        </text>
        <text x="10" y="27" font-family="JetBrains Mono, monospace" font-size="11" letter-spacing="0.06em"
              fill="white" font-weight="600">
          {{ Math.round(herePoint.elevationM) }} m elevation
        </text>
        <text x="10" y="40" font-family="JetBrains Mono, monospace" font-size="10.5" letter-spacing="0.08em"
              :fill="hereSegment?.color ?? 'white'" font-weight="600">
          {{ hereSegment && hereSegment.slopePct >= 0 ? '↗' : '↘' }}
          {{ hereSegment ? Math.abs(hereSegment.slopePct).toFixed(1) : '0.0' }}% slope
        </text>
      </g>
    </svg>
  </div>
</template>
