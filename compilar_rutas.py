import os
import glob
import json
import xml.etree.ElementTree as ET
import math

def calcular_distancia(coord1, coord2):
    """Calcula la distancia Haversine en km entre dos puntos."""
    lon1, lat1 = coord1
    lon2, lat2 = coord2
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def procesar_archivo_gpx(ruta_archivo, paso=2):
    """Parsea un GPX de Strava / Garmin / Wikiloc y devuelve un Feature GeoJSON."""
    tree = ET.parse(ruta_archivo)
    root = tree.getroot()

    # Namespace GPX
    ns = {'gpx': 'http://www.topografix.com/GPX/1/1'}
    # Si no tiene namespace declarado explícito en las etiquetas
    if not root.tag.startswith('{'):
        ns = {'gpx': ''}

    # Extraer el nombre de la ruta
    nombre = os.path.splitext(os.path.basename(ruta_archivo))[0]
    name_el = root.find('.//{http://www.topografix.com/GPX/1/1}name')
    if name_el is None:
        name_el = root.find('.//name')
    if name_el is not None and name_el.text:
        nombre = name_el.text.strip()

    # Extraer coordenadas y elevación
    puntos_brutos = []
    trkpts = root.findall('.//{http://www.topografix.com/GPX/1/1}trkpt')
    if not trkpts:
        trkpts = root.findall('.//trkpt')

    for pt in trkpts:
        lat = float(pt.attrib.get('lat'))
        lon = float(pt.attrib.get('lon'))
        ele_el = pt.find('{http://www.topografix.com/GPX/1/1}ele')
        if ele_el is None:
            ele_el = pt.find('ele')
        ele = float(ele_el.text) if ele_el is not None and ele_el.text else 0.0
        puntos_brutos.append((lon, lat, ele))

    if not puntos_brutos:
        return None

    # Muestreo para aligerar carga (1 de cada 2 puntos conserva todas las curvas)
    coordenadas = []
    distancia_total = 0.0
    desnivel_positivo = 0.0
    prev_ele = None

    for i, p in enumerate(puntos_brutos):
        lon, lat, ele = p
        if prev_ele is not None and ele > prev_ele:
            desnivel_positivo += (ele - prev_ele)
        prev_ele = ele

        if i > 0:
            distancia_total += calcular_distancia((puntos_brutos[i-1][0], puntos_brutos[i-1][1]), (lon, lat))

        if i % paso == 0 or i == len(puntos_brutos) - 1:
            coordenadas.append([round(lon, 5), round(lat, 5)])

    id_ruta = os.path.splitext(os.path.basename(ruta_archivo))[0].lower().replace(" ", "_")

    return {
        "type": "Feature",
        "id": id_ruta,
        "properties": {
            "name": nombre,
            "distancia_km": round(distancia_total, 1),
            "desnivel_m": int(desnivel_positivo),
            "puntos": len(coordenadas)
        },
        "geometry": {
            "type": "LineString",
            "coordinates": coordenadas
        }
    }

def compilar_todas():
    # Busca en rutas_gpx o en la carpeta actual
    archivos = glob.glob("rutas_gpx/*.gpx")
    if not archivos:
        archivos = glob.glob("*.gpx")

    if not archivos:
        print("⚠️ No se encontraron archivos .gpx. Crea la carpeta 'rutas_gpx' y copia tus rutas dentro.")
        return

    features = []
    print(f"🔄 Compilando {len(archivos)} rutas GPX reales...")

    for f in sorted(archivos):
        feat = procesar_archivo_gpx(f)
        if feat:
            features.append(feat)
            props = feat['properties']
            print(f"  ✓ {props['name']} | {props['distancia_km']} km | +{props['desnivel_m']}m ({props['puntos']} puntos)")

    geojson_final = {
        "type": "FeatureCollection",
        "features": features
    }

    with open("rutas.geojson", "w", encoding="utf-8") as out:
        json.dump(geojson_final, out, ensure_ascii=False, indent=2)

    tamano_kb = os.path.getsize("rutas.geojson") / 1024
    print(f"\n✅ Archivo 'rutas.geojson' generado con éxito ({tamano_kb:.1f} KB).")

if __name__ == "__main__":
    compilar_todas()