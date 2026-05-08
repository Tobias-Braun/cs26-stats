<script setup lang="ts">
const props = defineProps<{ history: number[] }>()

const W = 360
const H = 64
const PAD = 4
const MIN = 110
const MAX = 185

const xs = (i: number) => PAD + (i / (props.history.length - 1)) * (W - PAD * 2)
const ys = (v: number) => PAD + (1 - (v - MIN) / (MAX - MIN)) * (H - PAD * 2)

const path = computed(() =>
  props.history
    .map((v, i) => `${i === 0 ? 'M' : 'L'}${xs(i).toFixed(1)},${ys(v).toFixed(1)}`)
    .join(' '),
)

const lastX = computed(() => xs(props.history.length - 1))
const lastY = computed(() => ys(props.history[props.history.length - 1]))
</script>

<template>
  <svg
    class="hr-trace"
    :viewBox="`0 0 ${W} ${H}`"
    preserveAspectRatio="none"
  >
    <defs>
      <linearGradient id="hr-grad" x1="0" x2="1">
        <stop offset="0" stop-color="oklch(68% 0.27 8)" stop-opacity="0" />
        <stop offset=".4" stop-color="oklch(72% 0.27 10)" stop-opacity=".9" />
        <stop offset="1" stop-color="oklch(78% 0.26 350)" stop-opacity="1" />
      </linearGradient>
    </defs>
    <path :d="path" fill="none" stroke="url(#hr-grad)" stroke-width="1.6" />
    <circle :cx="lastX" :cy="lastY" r="3" fill="white">
      <animate attribute-name="r" values="2.5;5;2.5" dur="1s" repeat-count="indefinite" />
    </circle>
  </svg>
</template>
