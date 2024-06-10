import cv2
from cv2 import dnn_superres
from Bit_Conversion import convert_to_8Bit
import os
import glob
from osgeo import gdal

sr = dnn_superres.DnnSuperResImpl_create()

def process_images_in_folder(input_folder, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
  
    for filename in os.listdir(input_folder):
        if filename.endswith(".tif"): 
            image_path = os.path.join(input_folder, filename)
            image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
            dataset = gdal.Open(image_path)
            geotransform = dataset.GetGeoTransform()
            projection = dataset.GetProjection()

        if image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
            print("Converted image from 4 channels to 3 channels.")

        # Read the desired model
        path = "/home/marisa3004/spacenet/sn2/superres/EDSR_x2.pb"
        sr.readModel(path)
        sr.setModel("edsr", 2)
        result = sr.upsample(image)

        output_name = os.path.splitext(filename)[0] + "_upsampled.tif"
        output_path = os.path.join(output_folder, output_name)

        cv2.imwrite(output_path, result)
        output_dataset = gdal.Open(output_path, gdal.GA_Update)
        output_dataset.SetGeoTransform(geotransform)
        output_dataset.SetProjection(projection)
        output_dataset = None

        print(f"Processed and saved: {result}")

input_folder = '/home/marisa3004/spacenet/sn2/superres/out_bit'
output_folder = '/home/marisa3004/spacenet/sn2/superres/sr'
process_images_in_folder(input_folder, output_folder)