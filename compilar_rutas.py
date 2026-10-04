import os
import glob
import json
import gpxpy

def procesar_gpx(archivo_gpx, paso_muestreo=3):
    """
    Lee un archivo GPX y devuelve un Feature GeoJSON con coordenadas simplificadas.
    paso_muestreo=3 toma 1 de cada 3 puntos para reducir peso sin deformar el track.
    """
    with open(archivo_gpx, 'r', encoding='utf-8') as f:
        gpx = gpxpy.parse(f)

    # Obtener el nombre de la ruta o recurrir al nombre del archivo
    nombre = os.path.splitext(os.path.basename(archivo_gpx))[0]
    if gpx.tracks and gpx.tracks[0].name:
        nombre = gpx.tracks[0].name.strip()
    elif gpx.name:
        nombre = gpx.name.strip()

    coordenadas = []
    
    # Recorrer puntos del track
    for track in gpx.tracks:
        for segment in track.segments:
            for idx, point in enumerate(segment.points):
                # Reducir densidad de puntos y redondear a 5 decimales (~1.1 m de precisión)
                if idx % paso_muestreo == 0:
                    coordenadas.append([
                        round(point.longitude, 5),
                        round(point.latitude, 5)
                    ])

    # Si no hay tracks (es una ruta de tipo <rte>)
    if not coordenadas and gpx.routes:
        for route in gpx.routes:
            for idx, point in enumerate(route.points):
                if idx % paso_muestreo == 0:
                    coordenadas.append([
                        round(point.longitude, 5),
                        round(point.latitude, 5)
                    ])

    if not coordenadas:
        return None

    # Estructura Feature GeoJSON estándar
    return {
        "type": "Feature",
        "id": os.path.splitext(os.path.basename(archivo_gpx))[0].lower().replace(" ", "_"),
        "properties": {
            "name": nombre,
            "filename": os.path.basename(archivo_gpx),
            "puntos": len(coordenadas)
        },
        "geometry": {
            "type": "LineString",
            "coordinates": coordenadas
        }
    }

def compilar_catalogo():
    archivos = glob.glob("*.gpx")
    if not archivos:
        print("No se encontraron archivos .gpx en la carpeta actual.")
        return

    features = []
    print(f"Procesando {len(archivos)} rutas...")

    for f in sorted(archivos):
        try:
            feat = procesar_gpx(f)
            if feat:
                features.append(feat)
                print(f"  ✓ {feat['properties']['name']} ({feat['properties']['puntos']} pts)")
        except Exception as e:
            print(f"  ✗ Error en {f}: {e}")

    feature_collection = {
        "type": "FeatureCollection",
        "features": features
    }

    output_path = "rutas.geojson"
    with open(output_path, "w", encoding="utf-8") as out:
        json.dump(feature_collection, out, ensure_ascii=False, separators=(',', ':'))

    tamano_kb = os.path.getsize(output_path) / 1024
    print(f"\nGenerado '{output_path}' con éxito.")
    print(f"Total: {len(features)} rutas compiladas.")
    print(f"Peso final optimizado: {tamano_kb:.1f} KB (ideal para web y móvil).")

if __name__ == "__main__":
    compilar_catalogo()