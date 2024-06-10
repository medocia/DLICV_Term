import os
import geopandas as gpd
from shapely.geometry import Polygon
from osgeo import gdal
from pathlib import Path
import overpy
from tqdm import tqdm
from retry import retry
import csv

def get_extent(raster_file):
    raster = gdal.Open(raster_file)
    transform = raster.GetGeoTransform()
    min_x = transform[0]
    max_x = transform[0] + raster.RasterXSize * transform[1]
    min_y = transform[3] + raster.RasterYSize * transform[5]
    max_y = transform[3]
    return min_x, min_y, max_x, max_y

def get_all_extents(folder):
    extents = {}
    for file in os.listdir(folder):
        if file.endswith('.tif'):
            file_path = os.path.join(folder, file)
            extent = get_extent(file_path)
            extents[file] = extent
    return extents

def save_elements(elements, shapefile_filename, csv_filename):
    gdf = gpd.GeoDataFrame(elements, columns=['geometry'], crs="EPSG:4326")
    gdf.to_file(shapefile_filename)

    with open(csv_filename, 'w', newline='') as csvfile:
        fieldnames = ['ImageId', 'BuildingId', 'PolygonWKT_Pix', 'Confidence']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for i, element in enumerate(elements, start=1):
            writer.writerow({
                'ImageId': element['ImageId'],
                'BuildingId': i,
                'PolygonWKT_Pix': element['geometry'].wkt,
                'Confidence': element['Confidence']
            })

def create_query(north, south, east, west):
    return f"""
    [out:json];
    (
      way["building"]({south},{west},{north},{east});
      relation["building"]({south},{west},{north},{east});
    );
    out body;
    >;
    out skel qt;
    """

@retry(tries=3, delay=2, backoff=2, exceptions=(overpy.exception.OverpassGatewayTimeout, overpy.exception.OverpassTooManyRequests, overpy.exception.OverpassBadRequest, overpy.exception.OverpassError))
def run_query(query):
    api = overpy.Overpass()
    return api.query(query)

if __name__ == "__main__":
    tif_folder = "/content/drive/MyDrive/bbox_paris"
    extents = get_all_extents(tif_folder)
    output_dir = "/content/drive/MyDrive/paris_csv"
    shapefile_dir = os.path.join(output_dir, "shapefiles")
    geojson_dir = os.path.join(output_dir, "geojsons")
    csv_dir = os.path.join(output_dir, "csvs")


    Path(shapefile_dir).mkdir(parents=True, exist_ok=True)
    Path(geojson_dir).mkdir(parents=True, exist_ok=True)
    Path(csv_dir).mkdir(parents=True, exist_ok=True)

    for tif_name, extent in extents.items():
        min_x, min_y, max_x, max_y = extent
        query = create_query(max_y, min_y, max_x, min_x)

        try:
            result = run_query(query)
            elements = []
            for way in result.ways:
                nodes = [(float(node.lon), float(node.lat)) for node in way.nodes]
                try:
                    polygon = Polygon(nodes)
                    elements.append({
                        "ImageId": os.path.splitext(tif_name)[0],
                        "geometry": polygon,
                        "Confidence": 1
                    })
                except ValueError:
                    # 
                    continue

            filename = os.path.splitext(tif_name)[0] + "_buildings.shp"
            shapefile_path = os.path.join(shapefile_dir, filename)
            csv_path = os.path.join(csv_dir, os.path.splitext(tif_name)[0] + "_buildings.csv")
            save_elements(elements, shapefile_path, csv_path)

            print(f"Shapefile and CSV saved for TIFF file: {tif_name}")

        except Exception as e:
            print(f"Error for TIFF file {tif_name}: {e}")

    print("All Shapefiles and CSVs saved successfully.")