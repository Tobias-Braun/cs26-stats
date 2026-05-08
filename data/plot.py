import csv
import matplotlib.pyplot as plt

# -----------------------------
# optional smoothing
# -----------------------------
def moving_average(data, window=5):
    return [
        sum(data[max(0, i-window):i+1]) / (i - max(0, i-window) + 1)
        for i in range(len(data))
    ]


# -----------------------------
# Pace-Modell (wie vorher)
# -----------------------------
def corrected_pace(flat_pace_sec_per_km, grade_percent):

    g = grade_percent / 100.0

    if g > 0:
        factor = 1 + 3.2 * grade_percent / 100.0
    else:
        factor = 1 + 1.5 * grade_percent / 100.0
        factor = max(factor, 0.65)

    return flat_pace_sec_per_km * factor


# -----------------------------
# Plot
# -----------------------------
def plot_elevation_and_pace(csv_file):

    distance = []
    elevation = []
    grade = []
    pace = []

    BASE_PACE = 7 * 60  # 7:00 min/km in Sekunden

    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)

        for row in reader:
            distance.append(float(row['distance_km']))
            elevation.append(float(row['elevation_m']))
            grade.append(float(row['grade_percent']))

    # Pace berechnen
    smoothed_grades = moving_average(grade)
    for g in smoothed_grades:
        p = corrected_pace(BASE_PACE, g)
        pace.append(p / 60)  # min/km

    # optional smoothing
    elevation_s = moving_average(elevation, window=10)
    pace_s = moving_average(pace)

    # -----------------------------
    # Plot 1: Elevation
    # -----------------------------
    plt.figure()

    plt.plot(distance, elevation_s, label="Elevation")
    plt.xlabel("Distance (km)")
    plt.ylabel("Elevation (m)")
    plt.title("Elevation Profile + Corrected Pace")

    # -----------------------------
    # Plot 2: Pace (zweite y-Achse)
    # -----------------------------
    ax1 = plt.gca()
    ax2 = ax1.twinx()

    ax2.plot(distance, pace_s, color="orange", label="Corrected Pace (min/km)")

    ax2.set_ylabel("Pace (min/km)")

    ax1.grid()

    # Legend kombinieren
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()

    plt.legend(lines1 + lines2, labels1 + labels2, loc="best")

    plt.show()


if __name__ == "__main__":
    plot_elevation_and_pace("output_with_grade.csv")