import xml.etree.ElementTree as ET
import math
import csv

# --- Haversine Distanz (in km) ---
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# --- GPX einlesen ---
def gpx_to_csv(gpx_file, csv_file):
    tree = ET.parse(gpx_file)
    root = tree.getroot()

    # Namespace fix
    ns = {'default': root.tag.split('}')[0].strip('{')}

    points = root.findall('.//default:trkpt', ns)

    data = []
    total_dist = 0.0

    prev_lat, prev_lon = None, None

    for pt in points:
        lat = float(pt.attrib['lat'])
        lon = float(pt.attrib['lon'])

        ele_tag = pt.find('default:ele', ns)
        ele = float(ele_tag.text) if ele_tag is not None else 0.0

        if prev_lat is not None:
            total_dist += haversine(prev_lat, prev_lon, lat, lon)

        data.append([lat, lon, ele, round(total_dist, 3)])

        prev_lat, prev_lon = lat, lon

    # --- CSV schreiben ---
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['lat', 'lon', 'elevation_m', 'distance_km'])
        writer.writerows(data)

    print(f"Saved {len(data)} points to {csv_file}")

# --- Nutzung ---
if __name__ == "__main__":
    gpx_to_csv("in.gpx", "output.csv")