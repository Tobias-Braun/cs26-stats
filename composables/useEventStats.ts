import { TOTAL_KM, CUTOFF_SECONDS, PACE_BAR_MIN_SEC, PACE_BAR_MAX_SEC } from '~/utils/constants'

interface Reading {
  elapsedSeconds: number
  distanceKm: number
  heartRate: number
  /** Direct pace from OCR, converted from km/h → sec/km. null = not available. */
  currentPaceSec: number | null
  /** Wall-clock timestamp when this reading was received */
  capturedAt: number
}

/** Supabase table row shape. Mirrors what get-val.py writes. */
interface AthleteStatsRow {
  elapsed_seconds: number
  distance_km: number
  heart_rate: number
  current_speed: number | null  // km/h
  recorded_at: string
}

const STUB_READING: Reading = {
  elapsedSeconds: 75 * 3600 + 24 * 60 + 27,
  distanceKm: 381.2,
  heartRate: 142,
  currentPaceSec: null,
  capturedAt: 0, // set on mount so interpolation starts from now
}

export function useEventStats() {
  const config = useRuntimeConfig()
  const supabaseEnabled = config.public.supabaseEnabled as boolean

  const readings = ref<Reading[]>([])
  const hrHistory = ref<number[]>(
    Array.from({ length: 80 }, (_, i) => 140 + Math.sin(i / 6) * 6),
  )
  // Increments every second — used as a reactive dependency for time-interpolated values
  const tick = ref(0)

  // ── derived: always based on the latest reading + wall-clock extrapolation ──

  const latest = computed(() => readings.value[readings.value.length - 1])
  const prev = computed(() =>
    readings.value.length >= 2 ? readings.value[readings.value.length - 2] : null,
  )

  /** Average pace in sec/km based purely on the last persisted reading (no extrapolation). */
  const rawAvgPaceSec = computed(() => {
    const d = latest.value?.distanceKm ?? 0
    const e = latest.value?.elapsedSeconds ?? 1
    return d > 0 ? e / d : 0
  })

  /**
   * Current pace in sec/km.
   * Prefers the direct OCR value from Supabase (converted from km/h).
   * Falls back to delta between last two readings, then to overall avg.
   */
  const currentPaceSec = computed(() => {
    if (latest.value?.currentPaceSec) return latest.value.currentPaceSec
    if (!prev.value || !latest.value) return rawAvgPaceSec.value
    const dKm = latest.value.distanceKm - prev.value.distanceKm
    const dSec = latest.value.elapsedSeconds - prev.value.elapsedSeconds
    if (dKm < 0.001 || dSec <= 0) return rawAvgPaceSec.value
    return dSec / dKm
  })

  /** Elapsed seconds since event start, extrapolated from last reading using wall clock. */
  const elapsedSeconds = computed(() => {
    tick.value // subscribe to per-second tick
    if (!latest.value) return 0
    return latest.value.elapsedSeconds + (Date.now() - latest.value.capturedAt) / 1000
  })

  /** Distance covered, extrapolated from last reading at current pace. */
  const distanceDone = computed(() => {
    tick.value
    if (!latest.value) return 0
    const secSince = (Date.now() - latest.value.capturedAt) / 1000
    return Math.min(TOTAL_KM, latest.value.distanceKm + secSince / currentPaceSec.value)
  })

  /** Average pace over the full run so far — re-calculated live. */
  const avgPaceSec = computed(() => {
    const d = distanceDone.value
    return d > 0 ? elapsedSeconds.value / d : 0
  })

  const distanceRemaining = computed(() => Math.max(0, TOTAL_KM - distanceDone.value))
  const progressPct = computed(() => (distanceDone.value / TOTAL_KM) * 100)
  const cutoffRemainingSeconds = computed(() => Math.max(0, CUTOFF_SECONDS - elapsedSeconds.value))

  /** Projected time to finish at current avg pace. */
  const projectedRemainingSeconds = computed(() => avgPaceSec.value * distanceRemaining.value)

  /** Pace required to finish within the 96h cutoff. */
  const requiredPaceSec = computed(() => {
    const d = distanceRemaining.value
    return d > 0 ? cutoffRemainingSeconds.value / d : 0
  })

  const isOnTrack = computed(
    () => projectedRemainingSeconds.value + elapsedSeconds.value <= CUTOFF_SECONDS,
  )
  const cutoffMarginSeconds = computed(
    () => CUTOFF_SECONDS - elapsedSeconds.value - projectedRemainingSeconds.value,
  )

  const heartRate = computed(() => Math.round(latest.value?.heartRate ?? 0))

  const hrZone = computed(() => {
    const hr = heartRate.value
    if (hr < 115) return { num: 1, name: 'ERHOLUNG' }
    if (hr < 130) return { num: 2, name: 'AEROB' }
    if (hr < 145) return { num: 3, name: 'TEMPO' }
    if (hr < 160) return { num: 4, name: 'SCHWELLE' }
    return { num: 5, name: 'MAX' }
  })

  const eta = computed(() => new Date(Date.now() + projectedRemainingSeconds.value * 1000))

  /** Maps a pace (sec/km) to a 0-100 percentage on the comparison bar. */
  function pacePct(secPerKm: number): number {
    return Math.max(
      0,
      Math.min(
        100,
        ((secPerKm - PACE_BAR_MIN_SEC) / (PACE_BAR_MAX_SEC - PACE_BAR_MIN_SEC)) * 100,
      ),
    )
  }

  function rowToReading(r: AthleteStatsRow): Reading {
    return {
      elapsedSeconds: r.elapsed_seconds,
      distanceKm: r.distance_km,
      heartRate: r.heart_rate,
      // km/h → sec/km: 3600 / kmh
      currentPaceSec: r.current_speed ? 3600 / r.current_speed : null,
      capturedAt: Date.now(),
    }
  }

  function pushReading(r: AthleteStatsRow) {
    readings.value = [...readings.value.slice(-4), rowToReading(r)]
  }

  onMounted(() => {
    // Seed with stub data so the UI renders immediately in demo mode
    if (readings.value.length === 0) {
      readings.value = [{ ...STUB_READING, capturedAt: Date.now() }]
    }

    const tickId = setInterval(() => tick.value++, 1000)

    // Animate the HR sparkline independently of the data refresh cycle
    const hrId = setInterval(() => {
      const last = hrHistory.value[hrHistory.value.length - 1]
      const target = (latest.value?.heartRate ?? 142) + (Math.random() - 0.5) * 6
      const next = Math.max(110, Math.min(185, last + (target - last) * 0.35 + (Math.random() - 0.5) * 4))
      hrHistory.value = [...hrHistory.value.slice(1), next]
    }, 380)

    onUnmounted(() => {
      clearInterval(tickId)
      clearInterval(hrId)
    })

    if (!supabaseEnabled) return

    const supabase = useSupabaseClient()

    // Hydrate with the two most recent persisted readings (needed for pace delta)
    supabase
      .from('athlete_stats')
      .select('elapsed_seconds, distance_km, heart_rate, current_speed, recorded_at')
      .order('recorded_at', { ascending: false })
      .limit(2)
      .then(({ data, error }) => {
        if (error) {
          console.error('[stats] initial fetch failed:', error.message)
          return
        }
        if (data && data.length > 0) {
          readings.value = (data as AthleteStatsRow[]).reverse().map(rowToReading)
          console.log(`[stats] loaded ${data.length} initial readings`)
        }
      })

    // Subscribe to new rows inserted by get-val.py
    supabase
      .channel('athlete_stats_live')
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'athlete_stats' },
        payload => pushReading(payload.new as AthleteStatsRow),
      )
      .subscribe((status) => {
        if (status === 'SUBSCRIBED') {
          console.log('[stats] realtime subscribed')
        }
      })
  })

  return {
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
    hrZone,
    hrHistory,
    eta,
    pacePct,
    supabaseEnabled,
  }
}
