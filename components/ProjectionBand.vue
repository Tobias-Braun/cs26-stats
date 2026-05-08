<script setup lang="ts">
import { fmtHM, fmtPace, fmtTime } from '~/utils/formatters'

const props = defineProps<{
  projectedRemainingSeconds: number
  elapsedSeconds: number
  cutoffSeconds: number
  avgPaceSec: number
  currentPaceSec: number
  requiredPaceSec: number
  isOnTrack: boolean
  cutoffMarginSeconds: number
  eta: Date
}>()

const etaStr = computed(() => fmtTime(props.eta))
const etaDate = computed(() =>
  props.eta.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' }).toLowerCase(),
)
const overCutoffBy = computed(() =>
  props.projectedRemainingSeconds + props.elapsedSeconds - props.cutoffSeconds,
)
const requiredFasterThanCurr = computed(() => props.requiredPaceSec < props.currentPaceSec)
const requiredFasterThanAvg  = computed(() => props.requiredPaceSec < props.avgPaceSec)
</script>

<template>
  <div class="proj-band">
    <!-- Projected finish time at current avg pace -->
    <div class="proj">
      <div class="stripe" />
      <div class="proj-tag">⏱ finish forecast</div>
      <div class="proj-name">
        Projected finish <span>· at current avg pace</span>
      </div>
      <div class="proj-val mono">
        {{ fmtHM(projectedRemainingSeconds) }}<span class="unit">hh:mm</span>
      </div>
      <div class="proj-foot">
        eta · <b>{{ etaDate }} · {{ etaStr }}</b>
        &nbsp;·&nbsp;
        <span v-if="isOnTrack" style="color: var(--good)">
          finishes inside cutoff · margin {{ fmtHM(cutoffMarginSeconds) }}
        </span>
        <span v-else style="color: var(--hot)">
          over cutoff by {{ fmtHM(overCutoffBy) }}
        </span>
      </div>
    </div>

    <!-- Minimum pace needed to beat the cutoff -->
    <div class="proj">
      <div class="stripe" />
      <div class="proj-tag">⚡ cutoff pace</div>
      <div class="proj-name">
        Minimum pace needed <span>· to finish within 96 h</span>
      </div>
      <div class="proj-val mono">
        {{ fmtPace(requiredPaceSec) }}<span class="unit">min/km</span>
      </div>
      <div class="proj-foot">
        <span v-if="requiredFasterThanCurr" style="color: var(--hot)">
          ▲ must run {{ fmtPace(currentPaceSec - requiredPaceSec) }} faster than current
        </span>
        <span v-else style="color: var(--good)">
          ▼ buffer of {{ fmtPace(requiredPaceSec - currentPaceSec) }} below current pace
        </span>
        &nbsp;·&nbsp;
        vs avg <b>{{ requiredFasterThanAvg ? '▲' : '▼' }} {{ fmtPace(Math.abs(requiredPaceSec - avgPaceSec)) }}</b>
      </div>
    </div>
  </div>
</template>
