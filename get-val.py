import cv2
import numpy as np
import pytesseract
import subprocess
import sys
import time
import re
import os
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

# Supabase client — only initialised when env vars are present.
# Uses the service role key so it can INSERT regardless of RLS policies.
_supabase = None
_supabase_url = os.getenv("SUPABASE_URL", "")
_supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
if _supabase_url and _supabase_key:
    from supabase import create_client
    _supabase = create_client(_supabase_url, _supabase_key)
    print("Supabase: connected, writes enabled.")
else:
    print("Supabase: env vars missing — running in print-only mode.")

# Either a page URL (resolved via yt-dlp) or a direct .m3u8 / .mpd stream URL.
# To get the direct stream URL: open DevTools → Network → filter "m3u8" → copy the URL.
STREAM_URL = "https://rbmn-live.akamaized.net/hls/live/2005280/RedBullCyborgSeasonUltra600USFinalsS/master_6660.m3u8"

# All ROIs as fractions of frame width/height so they scale with any stream resolution.
# Calibrated against the Red Bull Cyborg Season Ultra 600 overlay (16:9, ~1456×816).
# Each ROI covers only the numeric value — unit labels ("BPM", "/ M", "/ FT", column
# headers, etc.) are intentionally excluded so Tesseract never sees characters it has
# to suppress via the whitelist, which was the root cause of heart_rate / elevation_gain
# misreads. Bottom bar value row 1 sits at y ≈ 748–782 px (0.917–0.958); row 2 at
# y ≈ 785–810 px (0.962–0.992). If values come out wrong, inspect the "ROI Debug" window.
ROIS: dict[str, tuple[float, float, float, float]] = {
    # ── Top-left elapsed-time badge (white text on dark-maroon box) ────────────
    "elapsed_time":        (0.010, 0.046, 0.179, 0.095),

    # ── Right sidebar — Course Data value rows (left edge ≈ x 1163 px) ─────────
    "local_time_pst":      (0.799, 0.260, 0.934, 0.304),
    "weather_c":           (0.799, 0.359, 0.903, 0.401),
    "weather_f":           (0.799, 0.405, 0.900, 0.445),
    "distance_covered_km": (0.799, 0.502, 0.920, 0.543),
    "distance_covered_mi": (0.799, 0.544, 0.917, 0.586),
    "remaining_dist_km":   (0.799, 0.634, 0.920, 0.676),
    "remaining_dist_mi":   (0.799, 0.677, 0.906, 0.717),

    # ── Bottom bar — Performance Data ──────────────────────────────────────────
    "heart_rate":          (0.014, 0.899, 0.065, 0.940),   # "117" only — BPM excluded
    "pace_km":             (0.158, 0.899, 0.213, 0.940),
    "pace_mi":             (0.158, 0.950, 0.227, 0.980),
    "avg_pace_km":         (0.301, 0.899, 0.349, 0.940),
    "avg_pace_mi":         (0.301, 0.950, 0.349, 0.980),
    "elevation_gain_m":    (0.461, 0.899, 0.516, 0.940),   # "4,479" only — "/ M" excluded
    "elevation_gain_ft":   (0.461, 0.950, 0.531, 0.980),   # "14,694" only — "/ FT" excluded
    "elapsed_time_perf":   (0.625, 0.899, 0.680, 0.940),
}

# Narrow per-field whitelists cut Tesseract error rate significantly
WHITELIST: dict[str, str] = {
    "elapsed_time":        "0123456789:",
    "local_time_pst":      "0123456789:",
    "weather_c":           "0123456789.",
    "weather_f":           "0123456789.",
    "distance_covered_km": "0123456789.",
    "distance_covered_mi": "0123456789.",
    "remaining_dist_km":   "0123456789.",
    "remaining_dist_mi":   "0123456789.",
    "heart_rate":          "0123456789",
    "pace_km":             "0123456789:/",
    "pace_mi":             "0123456789:/",
    "avg_pace_km":         "0123456789:/",
    "avg_pace_mi":         "0123456789:/",
    # comma is the thousands separator in the stream ("4,477")
    "elevation_gain_m":    "0123456789,",
    "elevation_gain_ft":   "0123456789,",
    "elapsed_time_perf":   "0123456789:",
}

# Fields whose value is a formatted string, not a plain number
STRING_FIELDS = {
    "elapsed_time", "local_time_pst",
    "pace_km", "pace_mi", "avg_pace_km", "avg_pace_mi",
    "elapsed_time_perf",
}


def get_stream_url(url: str) -> str:
    # Direct stream URLs (m3u8/mpd) are passed straight through — no yt-dlp needed.
    if any(url.endswith(ext) or ext + "?" in url for ext in (".m3u8", ".mpd", ".mp4")):
        return url
    # For page URLs, resolve via yt-dlp. -f b picks the best combined format so
    # OpenCV gets a single URL; take only the first line for providers that return
    # separate video/audio streams.
    result = subprocess.run(
        ["yt-dlp", "-g", "-f", "b", url],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(result.stderr.strip(), file=sys.stderr)
        return ""
    return result.stdout.strip().splitlines()[0]


def preprocess(crop: np.ndarray) -> np.ndarray:
    """Scale up and binarise a white-on-dark overlay crop for Tesseract.

    3× upscaling is the single biggest quality boost for small overlay text.
    Otsu's method picks the binarisation threshold automatically, which handles
    both the semi-transparent sidebar and the fully opaque bottom bar.
    """
    h, w = crop.shape[:2]
    scaled = cv2.resize(crop, (w * 3, h * 3), interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(scaled, cv2.COLOR_BGR2GRAY)
    # Invert: white overlay text → dark ink on white background (what Tesseract expects)
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    # Light dilation closes gaps in antialiased thin strokes
    kernel = np.ones((2, 2), np.uint8)
    return cv2.dilate(bw, kernel, iterations=1)


def ocr(img: np.ndarray, field: str) -> str:
    wl = WHITELIST.get(field, "0123456789")
    cfg = f"--psm 7 -c tessedit_char_whitelist={wl}"
    return pytesseract.image_to_string(img, config=cfg).strip()


def extract_number(text: str) -> Optional[float]:
    # Strip thousands-separator commas before matching so "4,479" → 4479 and a
    # comma misread as a period ("4.479") doesn't silently produce 4.479.
    normalized = text.replace(",", "")
    m = re.search(r"\d+(?:\.\d+)?", normalized)
    return float(m.group()) if m else None


RACE_MAX_KM          = 600.0
RACE_MAX_ELAPSED_SEC = 96 * 3600  # 345 600 s

# Carries the last accepted reading so delta/context checks can reference it
_last_good: dict = {}


def hms_to_seconds(hms: str) -> Optional[int]:
    """Convert HH:MM:SS string to total seconds.
    Each colon-separated part is stripped individually to survive OCR whitespace."""
    parts = [p.strip() for p in hms.strip().split(":")]
    if len(parts) != 3:
        return None
    try:
        h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
        if not (0 <= m < 60 and 0 <= s < 60):
            return None
        return h * 3600 + m * 60 + s
    except ValueError:
        return None


def pace_to_kmh(pace_str: str) -> Optional[float]:
    """Convert 'M:SS' pace string (min/km) to km/h, rounded to 2 decimal places."""
    parts = [p.strip() for p in pace_str.strip().split(":")]
    if len(parts) != 2:
        return None
    try:
        sec_per_km = int(parts[0]) * 60 + int(parts[1])
        return round(3600 / sec_per_km, 2) if sec_per_km > 0 else None
    except ValueError:
        return None


def _correct_digit(val: float, lo: float, hi: float, label: str) -> Optional[float]:
    """Return val if it's within [lo, hi]. Otherwise try val÷10 once (extra OCR digit).
    Returns None when the value cannot be salvaged."""
    if lo <= val <= hi:
        return val
    candidate = round(val / 10, 2)
    if lo <= candidate <= hi:
        print(f"  [plausibility] {label}: {val} → {candidate} (÷10 correction)")
        return candidate
    print(f"  [plausibility] {label}: {val} out of [{lo}, {hi}], discarded")
    return None


def validate_and_correct(values: dict) -> dict:
    """Check OCR fields for plausibility. Corrects obvious extra-digit errors; drops
    values that are out of range and cannot be fixed."""
    out = dict(values)

    # ── elapsed_time: must parse as valid HH:MM:SS within race window ────────────
    # No monotonicity check — a single bad reading in _last_good would wrongly
    # reject all subsequent valid values, so range alone is the guard here.
    if "elapsed_time" in out:
        sec = hms_to_seconds(str(out["elapsed_time"]))
        if sec is None or not (0 < sec <= RACE_MAX_ELAPSED_SEC):
            print(f"  [plausibility] elapsed_time '{out['elapsed_time']}' discarded (unparseable or outside 0–96 h)")
            del out["elapsed_time"]

    # ── heart_rate: 50–200 bpm; correct extra digit (1400 → 140) ────────────────
    if "heart_rate" in out:
        result = _correct_digit(float(out["heart_rate"]), 50, 200, "heart_rate")
        if result is None:
            del out["heart_rate"]
        else:
            out["heart_rate"] = int(round(result))

    # ── distance_covered_km: 0–RACE_MAX_KM, no implausible jumps ────────────────
    if "distance_covered_km" in out:
        d = float(out["distance_covered_km"])
        prev_d = _last_good.get("distance_covered_km")

        # Extra digit: 3835 → 383.5
        if d > RACE_MAX_KM:
            fixed = _correct_digit(d, 0, RACE_MAX_KM, "distance_covered_km")
            if fixed is None:
                del out["distance_covered_km"]
            else:
                out["distance_covered_km"] = fixed
                d = fixed

        if "distance_covered_km" in out and prev_d is not None:
            d = float(out["distance_covered_km"])
            if d > prev_d + 2.0:
                # Jump > 2 km in 60 s → try ÷10 before discarding
                candidate = round(d / 10, 1)
                if abs(candidate - prev_d) <= 2.0:
                    print(f"  [plausibility] distance_covered_km: {d} → {candidate} (jump from {prev_d:.1f}, ÷10)")
                    out["distance_covered_km"] = candidate
                else:
                    print(f"  [plausibility] distance_covered_km: {d} discarded (implausible jump from {prev_d:.1f})")
                    del out["distance_covered_km"]
            elif d < prev_d - 1.0:
                print(f"  [plausibility] distance_covered_km: {d} discarded (dropped from {prev_d:.1f})")
                del out["distance_covered_km"]

    # ── pace_km: must parse as M:SS and fall within 4:00–25:00 min/km ───────────
    if "pace_km" in out:
        parts = [p.strip() for p in str(out["pace_km"]).split(":")]
        valid = False
        if len(parts) == 2:
            try:
                sec_per_km = int(parts[0]) * 60 + int(parts[1])
                if 240 <= sec_per_km <= 1500:
                    valid = True
                else:
                    print(f"  [plausibility] pace_km '{out['pace_km']}' discarded ({sec_per_km} s/km outside 4:00–25:00)")
            except ValueError:
                pass
        if not valid:
            del out["pace_km"]

    return out


def push_to_supabase(values: dict) -> None:
    """Insert one validated OCR reading into athlete_stats."""
    if _supabase is None:
        return

    elapsed_raw = values.get("elapsed_time", "")
    elapsed_sec = hms_to_seconds(str(elapsed_raw)) if elapsed_raw else None
    distance_km = values.get("distance_covered_km")
    heart_rate  = values.get("heart_rate")

    if elapsed_sec is None or distance_km is None or heart_rate is None:
        print("  [supabase] skipped — missing elapsed_time / distance / heart_rate")
        return

    row = {
        "elapsed_seconds": elapsed_sec,
        "distance_km":     float(distance_km),
        "heart_rate":      int(heart_rate),
        "current_speed":   pace_to_kmh(str(values["pace_km"])) if values.get("pace_km") else None,
    }

    row = {k: v for k, v in row.items() if v is not None}

    try:
        _supabase.table("athlete_stats").insert(row).execute()
        print(f"  [supabase] inserted: {row}")
    except Exception as exc:
        print(f"  [supabase] insert failed: {exc}", file=sys.stderr)


def parse(raw: dict[str, str]) -> dict[str, float | str]:
    out: dict[str, float | str] = {}
    for k, v in raw.items():
        v = v.strip()
        if not v:
            continue
        if k in STRING_FIELDS:
            out[k] = v
        else:
            n = extract_number(v)
            if n is not None:
                out[k] = n
    return out


stream_url = get_stream_url(STREAM_URL)
if not stream_url:
    print("Error: Could not get stream URL. Check that yt-dlp is installed and the YouTube URL is valid.", file=sys.stderr)
    sys.exit(1)

cap = cv2.VideoCapture(stream_url)
if not cap.isOpened():
    print(f"Error: Could not open video stream: {stream_url}", file=sys.stderr)
    sys.exit(1)

last_run = 0.0
INTERVAL = 60  # seconds between OCR passes

while True:
    ret, frame = cap.read()
    if not ret:
        break

    now = time.time()
    if now - last_run < INTERVAL:
        if cv2.waitKey(1) & 0xFF == 27:
            break
        continue

    last_run = now
    fh, fw = frame.shape[:2]

    raw: dict[str, str] = {}
    crops: dict[str, np.ndarray] = {}

    for name, (rx1, ry1, rx2, ry2) in ROIS.items():
        x1, y1 = int(rx1 * fw), int(ry1 * fh)
        x2, y2 = int(rx2 * fw), int(ry2 * fh)
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            continue
        proc = preprocess(crop)
        raw[name] = ocr(proc, name)
        crops[name] = proc

    values = parse(raw)
    values = validate_and_correct(values)

    ts = time.strftime("%H:%M:%S")
    print(f"\n[{ts}]")
    for k, v in values.items():
        print(f"  {k:25s}: {v}")

    # Keep reference for next round's delta checks
    if "distance_covered_km" in values:
        _last_good["distance_covered_km"] = float(values["distance_covered_km"])

    push_to_supabase(values)

    # Horizontal strip of all ROI crops — useful for calibrating ROI coordinates
    if crops:
        max_h = max(c.shape[0] for c in crops.values())
        strips = []
        for name, c in crops.items():
            pad = cv2.copyMakeBorder(
                c, 0, max_h - c.shape[0], 0, 2,
                cv2.BORDER_CONSTANT, value=128
            )
            strips.append(pad)
        cv2.imshow("ROI Debug", np.hstack(strips))

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
