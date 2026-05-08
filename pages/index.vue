<script setup lang="ts">
import { fmtHMS, fmtPace, fmtCEST } from "~/utils/formatters";
import { TOTAL_KM, CUTOFF_SECONDS, ATHLETE_NAME } from "~/utils/constants";

const {
  elapsedSeconds,
  distanceDone,
  distanceRemaining,
  progressPct,
  currentPaceSec,
  avgPaceSec,
  cutoffRemainingSeconds,
  projectedRemainingSeconds,
  requiredPaceSec,
  isOnTrack,
  cutoffMarginSeconds,
  heartRate,
  hrHistory,
  eta,
  pacePct,
  supabaseEnabled,
} = useEventStats();

const { points: elevationPoints, pending: elevPending } = useElevationData();

// CEST clock in the topbar — updates every minute
const utcTime = ref("");
function updateUtcTime() {
  utcTime.value = fmtCEST(new Date());
}
onMounted(() => {
  updateUtcTime();
  const id = setInterval(updateUtcTime, 60_000);
  onUnmounted(() => clearInterval(id));
});
</script>

<template>
  <div class="shell">
    <!-- ── Top bar ── -->
    <div class="topbar">
      <div class="brand">
        <div class="brand-mark" />
        <div>
          <div class="brand-name">CS26 · LIVE TELEMETRIEDATEN</div>
          <div class="brand-sub">
            athlet · {{ ATHLETE_NAME.toLowerCase() }}
            <span
              v-if="!supabaseEnabled"
              style="color: var(--warn); margin-left: 8px"
              >[demo-modus]</span
            >
          </div>
        </div>
      </div>
      <div class="top-meta">
        <div class="pill"><span class="dot" /> live</div>
        <div class="pill">cest {{ utcTime }}</div>
        <div class="pill">gps-lock</div>
      </div>
    </div>

    <!-- ── Run header ── -->
    <div class="run-head">
      <h1 class="run-title">
        {{ TOTAL_KM }} km<span style="color: var(--ink-mute)"> /</span>
        <span class="accent"> 96h</span>
      </h1>
      <div class="run-meta">
        <div>start <b>06. mai 2026 · 20:00:00 cest</b></div>
        <div>zielzeit <b>10. mai 2026 · 20:00:00 cest</b></div>
        <div>
          athlet <b>{{ ATHLETE_NAME }}</b>
        </div>
      </div>
    </div>

    <!-- ── Course progress bar ── -->
    <div class="progress-row">
      <div class="prog-label">streckenfortschritt</div>
      <div class="prog-bar">
        <div class="prog-fill" :style="{ width: `${progressPct}%` }" />
        <div class="prog-tics" />
      </div>
      <div class="prog-label mono" style="color: var(--ink)">
        {{ progressPct.toFixed(2) }} %
      </div>
    </div>

    <!-- ── KPI grid ── -->
    <div class="kpi-grid">
      <!-- 01 Elapsed time -->
      <KpiPanel class="col-7" idx="01" label="verstrichene zeit" :hot="true">
        <div class="k-value">
          <span class="num mega mono">{{ fmtHMS(elapsedSeconds) }}</span>
        </div>
        <div class="k-sub">
          <span>96:00:00 zielzeit</span>
          <span>·</span>
          <span>{{ fmtHMS(cutoffRemainingSeconds) }} verbleibend</span>
        </div>
      </KpiPanel>

      <!-- 02 Heart rate -->
      <KpiPanel class="col-5" idx="02" label="herzfrequenz">
        <div class="k-value">
          <span class="num mono">{{ heartRate }}</span>
          <span class="unit">bpm</span>
        </div>
        <div class="hr-row">
          <HRSparkline :history="hrHistory" />
        </div>
      </KpiPanel>

      <!-- 03 Current pace -->
      <KpiPanel class="col-3" idx="03" label="tempo · aktuell">
        <div class="k-value">
          <span class="num mono">{{ fmtPace(currentPaceSec) }}</span>
          <span class="unit">min/km</span>
        </div>
        <PaceBar
          :fill-pct="pacePct(currentPaceSec)"
          :ref-pct="pacePct(avgPaceSec)"
        />
      </KpiPanel>

      <!-- 04 Average pace -->
      <KpiPanel class="col-3" idx="04" label="tempo · durchschnitt">
        <div class="k-value">
          <span class="num mono">{{ fmtPace(avgPaceSec) }}</span>
          <span class="unit">min/km</span>
        </div>
        <PaceBar
          :fill-pct="pacePct(avgPaceSec)"
          :ref-pct="pacePct(requiredPaceSec)"
        />
        <div class="k-sub">
          <span>über {{ distanceDone.toFixed(1) }} km</span>
        </div>
      </KpiPanel>

      <!-- 05 Distance completed -->
      <KpiPanel class="col-3" idx="05" label="distanz · zurückgelegt">
        <div class="k-value">
          <span class="num mono">{{ distanceDone.toFixed(1) }}</span>
          <span class="unit">km</span>
        </div>
        <PaceBar :fill-pct="(distanceDone / TOTAL_KM) * 100" />
        <div class="k-sub">
          <span
            >{{ ((distanceDone / TOTAL_KM) * 100).toFixed(1) }} % von
            {{ TOTAL_KM }} km</span
          >
        </div>
      </KpiPanel>

      <!-- 06 Distance remaining -->
      <KpiPanel class="col-3" idx="06" label="distanz · verbleibend">
        <div class="k-value">
          <span class="num mono">{{ distanceRemaining.toFixed(1) }}</span>
          <span class="unit">km</span>
        </div>
        <PaceBar
          :fill-offset="(distanceDone / TOTAL_KM) * 100"
          :fill-pct="(distanceRemaining / TOTAL_KM) * 100"
          :dim-fill="true"
        />
        <div class="k-sub">
          <span
            >{{ ((distanceRemaining / TOTAL_KM) * 100).toFixed(1) }} %
            verbleibend</span
          >
        </div>
      </KpiPanel>

      <!-- Projections band -->
      <div class="col-12">
        <ProjectionBand
          :projected-remaining-seconds="projectedRemainingSeconds"
          :elapsed-seconds="elapsedSeconds"
          :cutoff-seconds="CUTOFF_SECONDS"
          :avg-pace-sec="avgPaceSec"
          :current-pace-sec="currentPaceSec"
          :required-pace-sec="requiredPaceSec"
          :is-on-track="isOnTrack"
          :cutoff-margin-seconds="cutoffMarginSeconds"
          :eta="eta"
        />
      </div>

      <!-- Elevation chart + disclaimer -->
      <div class="col-12">
        <div
          v-if="elevPending"
          style="
            padding: 40px;
            text-align: center;
            color: var(--ink-dim);
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            letter-spacing: 0.12em;
          "
        >
          HÖHENPROFIL WIRD GELADEN…
        </div>
        <ElevationChart
          v-else-if="elevationPoints"
          :points="elevationPoints"
          :progress-km="distanceDone"
          :athlete-name="ATHLETE_NAME"
        />

        <div class="footer-note">
          <div class="icon">!</div>
          <div>
            <b style="color: var(--ink)">HÖHENPROFIL · HINWEIS.</b>
            die strecke wurde manuell erfasst und ist über 600 km nicht
            konsistent genau — dieses profil dient nur der groben orientierung.
            abweichungen in position und höhe sind vorhanden.
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
