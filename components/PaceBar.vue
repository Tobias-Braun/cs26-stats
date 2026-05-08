<script setup lang="ts">
/**
 * A horizontal bar that shows pace visually.
 * `fillPct`  — how far the colored fill extends (0-100)
 * `refPct`   — optional white reference tick (e.g. avg pace or required pace)
 * `dimFill`  — renders the fill at 55% opacity (used for "remaining" bar)
 */
defineProps<{
  fillPct: number
  refPct?: number
  fillOffset?: number
  dimFill?: boolean
}>()
</script>

<template>
  <div class="pace-bar">
    <div
      class="pf"
      :style="{
        left: `${fillOffset ?? 0}%`,
        width: `${fillPct}%`,
        opacity: dimFill ? 0.55 : 1,
      }"
    />
    <div
      v-if="refPct !== undefined"
      class="ref"
      :style="{ left: `${refPct}%` }"
    />
  </div>
</template>
