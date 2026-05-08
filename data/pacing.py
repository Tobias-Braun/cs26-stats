import csv
import math

# -----------------------------
# 1. Steigung berechnen
# -----------------------------
def add_grade(input_csv, output_csv):
    rows = []

    with open(input_csv, 'r') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({
                "lat": float(r["lat"]),
                "lon": float(r["lon"]),
                "ele": float(r["elevation_m"]),
                "dist": float(r["distance_km"])
            })

    for i in range(1, len(rows)):
        delev = rows[i]["ele"] - rows[i-1]["ele"]
        ddist = (rows[i]["dist"] - rows[i-1]["dist"]) * 1000  # km → m

        if ddist > 0:
            grade = (delev / ddist) * 100
        else:
            grade = 0.0

        rows[i]["grade"] = grade

    rows[0]["grade"] = 0.0

    with open(output_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["lat", "lon", "elevation_m", "distance_km", "grade_percent"])

        for r in rows:
            writer.writerow([
                r["lat"],
                r["lon"],
                r["ele"],
                r["dist"],
                r["grade"]
            ])

    return rows


# -----------------------------
# 2. Pace-Korrekturmodell
# -----------------------------
def corrected_pace(flat_pace_sec_per_km, grade_percent):
    """
    flat_pace_sec_per_km: Pace bei 0% (z.B. 300 = 5:00 min/km)
    grade_percent: Steigung in %
    """

    g = grade_percent / 100.0

    # Bergauf: deutlich teurer
    if g > 0:
        factor = 1 + 3.2 * grade_percent / 100.0

    # Bergab: schneller, aber limitiert
    else:
        factor = 1 + 1.5 * grade_percent / 100.0  # grade negativ → schneller

        # Safety cap: downhill wird nicht unrealistisch schnell
        min_factor = 0.65
        factor = max(factor, min_factor)

    return flat_pace_sec_per_km * factor


# -----------------------------
# 3. Beispiel-Nutzung
# -----------------------------
if __name__ == "__main__":

    rows = add_grade("output_scaled.csv", "output_with_grade.csv")

    flat_pace = 300  # 5:00 min/km

    for i in range(1, 10):
        g = rows[i]["grade"]
        p = corrected_pace(flat_pace, g)
        print(f"Grade: {g:.2f}% -> Pace: {p/60:.2f} min/km")