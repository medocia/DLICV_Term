import cv2
from cv2 import dnn_superres
from Bit_Conversion import convert_to_8Bit
import os
import glob

def process_folder(input_folder, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    input_files = glob.glob(os.path.join(input_folder, '*'))
    
    for input_file in input_files:
        if input_file.endswith('.tif') or input_file.endswith('.tiff'):
            output_file = os.path.join(output_folder, os.path.basename(input_file).replace('.tif', '_8bit.tif'))
            convert_to_8Bit(input_file, output_file)
            print(f"Converted: {input_file} -> {output_file}")

if __name__ == "__main__":
    input_folder = "/home/marisa3004/spacenet/01-ohhan777/code/wdata/train/AOI_3_Paris/POST-event"
    output_folder = "/home/marisa3004/spacenet/01-ohhan777/code/wdata/train/AOI_3_Paris/PRE-event"
    process_folder(input_folder, output_folder)