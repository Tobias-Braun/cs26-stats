<script setup lang="ts">
import { fmtHM, fmtPace, fmtCEST } from '~/utils/formatters'

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

const etaStr = computed(() => fmtCEST(props.eta))
const etaDate = computed(() =>
  props.eta.toLocaleDateString('de-DE', { day: '2-digit', month: 'short' }).toLowerCase(),
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
      <div class="proj-tag">⏱ zielprognose</div>
      <div class="proj-name">
        Projiziertes Ziel <span>· bei aktuellem Durchschnittstempo</span>
      </div>
      <div class="proj-val mono">
        {{ fmtHM(projectedRemainingSeconds) }}<span class="unit">hh:mm</span>
      </div>
      <div class="proj-foot">
        ankunft · <b>{{ etaDate }} · {{ etaStr }}</b>
        &nbsp;·&nbsp;
        <span v-if="isOnTrack" style="color: var(--good)">
          finisht vor zielzeit · puffer {{ fmtHM(cutoffMarginSeconds) }}
        </span>
        <span v-else style="color: var(--hot)">
          über zielzeit um {{ fmtHM(overCutoffBy) }}
        </span>
      </div>
    </div>

    <!-- Minimum pace needed to beat the cutoff -->
    <div class="proj">
      <div class="stripe" />
      <div class="proj-tag">⚡ erforderliches tempo</div>
      <div class="proj-name">
        Minimales Tempo erforderlich <span>· um innerhalb von 96 h zu finishen</span>
      </div>
      <div class="proj-val mono">
        {{ fmtPace(requiredPaceSec) }}<span class="unit">min/km</span>
      </div>
      <div class="proj-foot">
        <span v-if="requiredFasterThanCurr" style="color: var(--hot)">
          ▲ muss {{ fmtPace(currentPaceSec - requiredPaceSec) }} schneller laufen als aktuell
        </span>
        <span v-else style="color: var(--good)">
          ▼ puffer von {{ fmtPace(requiredPaceSec - currentPaceSec) }} unter aktuellem tempo
        </span>
        &nbsp;·&nbsp;
        vs ø <b>{{ requiredFasterThanAvg ? '▲' : '▼' }} {{ fmtPace(Math.abs(requiredPaceSec - avgPaceSec)) }}</b>
      </div>
    </div>
  </div>
</template>
