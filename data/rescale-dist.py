import csv

def rescale_distance(input_csv, output_csv, target_km):
    rows = []

    with open(input_csv, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "lat": float(row["lat"]),
                "lon": float(row["lon"]),
                "elevation_m": float(row["elevation_m"]),
                "distance_km": float(row["distance_km"])
            })

    if not rows:
        print("No data.")
        return

    original_total = rows[-1]["distance_km"]
    scale_factor = target_km / original_total

    print(f"Original: {original_total:.2f} km")
    print(f"Target:   {target_km:.2f} km")
    print(f"Scale:    {scale_factor:.6f}")

    # Distanz skalieren
    for r in rows:
        r["distance_km"] *= scale_factor

    # Neue CSV schreiben
    with open(output_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["lat", "lon", "elevation_m", "distance_km"])
        for r in rows:
            writer.writerow([
                r["lat"],
                r["lon"],
                r["elevation_m"],
                round(r["distance_km"], 3)
            ])

    print(f"Saved to {output_csv}")


if __name__ == "__main__":
    rescale_distance("output.csv", "output_scaled.csv", target_km=600.0)