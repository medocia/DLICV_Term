import os
import rasterio
from rasterio.features import rasterize
import pandas as pd
import geopandas as gpd
from shapely.geometry import mapping, Polygon
from shapely.ops import cascaded_union
import numpy as np
import cv2

def generate_mask(raster_path, shape_path, output_path, file_name, combined_df):

    """Function that generates a binary mask from a vector file (shp or geojson)

    raster_path = path to the .tif;

    shape_path = path to the shapefile or GeoJson.

    output_path = Path to save the binary mask.

    file_name = Name of the file.

    """

    with rasterio.open(raster_path, "r") as src:
        raster_meta = src.meta

    train_df = gpd.read_file(shape_path)

    if train_df.crs != src.crs:
        print("Raster crs : {}, Vector crs : {}.\nConvert vector and raster to the same CRS.".format(src.crs, train_df.crs))

    def poly_from_utm(polygon, transform):
        poly_pts = []
        poly = cascaded_union(polygon)
        for i in np.array(poly.exterior.coords):
            transformed_point = ~transform * tuple(i)
            poly_pts.append(transformed_point)
        new_poly = Polygon(poly_pts)
        return new_poly

    poly_shp = []
    poly_wkt_pix = []
    im_size = (src.meta['height'], src.meta['width'])

    if not train_df.empty:
        for num, row in train_df.iterrows():
            if row['geometry'].geom_type == 'Polygon':
                poly = poly_from_utm(row['geometry'], src.meta['transform'])
                poly_shp.append(poly)
                coords_pix = []
                for point in row['geometry'].exterior.coords:
                    px, py = ~src.transform * point
                    coords_pix.append(f"{px} {py} 0")
                poly_wkt_pix.append(f"POLYGON(({', '.join(coords_pix)}))")
            else:
                for p in row['geometry']:
                    poly = poly_from_utm(p, src.meta['transform'])
                    poly_shp.append(poly)
                    coords_pix = []
                    for point in p.exterior.coords:
                        px, py = ~src.transform * point
                        coords_pix.append(f"{px} {py} 0")
                    poly_wkt_pix.append(f"POLYGON(({', '.join(coords_pix)}))")

    if not poly_shp:
        mask = np.zeros(im_size, dtype=np.uint8)
    else:
        mask = rasterize(shapes=poly_shp, out_shape=im_size)

    png_path = os.path.join(output_path, file_name + '.png')
    cv2.imwrite(png_path, mask.astype("uint8") * 255)

    if poly_shp:
        df = pd.DataFrame({
            'ImageId': [file_name.split('_mask')[0]] * len(poly_shp),
            'BuildingId': [x + 1 for x in range(len(poly_shp))],
            'PolygonWKT_Pix': poly_wkt_pix,
            'Confidence': [1] * len(poly_shp)
        })
        combined_df = pd.concat([combined_df, df], ignore_index=True)

    return combined_df



combined_df = pd.DataFrame(columns=['ImageId', 'BuildingId', 'PolygonWKT_Pix', 'Confidence'])
raster_path = sorted(os.listdir('/content/drive/MyDrive/bbox_paris'))
shapefile_path = sorted([file.replace('_buildings', '') for file in os.listdir('/content/drive/MyDrive/full_gt_paris/shp') if file.endswith('.shp')])
output_path = '/content/drive/MyDrive/full_gt_paris/mask'

for i, j in zip(raster_path, shapefile_path):
    rp = os.path.join('/content/drive/MyDrive/bbox_paris', i)
    sp = os.path.join('/content/drive/MyDrive/full_gt_paris/shp', j.split('.')[0] + '_buildings.shp')
    combined_df = generate_mask(rp, sp, output_path, f"{i.split('.')[0]}_mask", combined_df)
    print(i, j, 'mask processed')

combined_csv_path = os.path.join(output_path, 'full_gt_masks_fixed.csv')
combined_df.to_csv(combined_csv_path, index=False)