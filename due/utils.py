
import re
import time
from shapely import Polygon
from due.hatching import HatchingType, generate_hatching, points_to_polygons

def mm_to_galvo(x_mm, y_mm, field_size_mm=200, galvo_range=65536, correction_x=0.8333, correction_y=0.8333):
    scale = galvo_range / field_size_mm
    center_offset = galvo_range / 2  
    galvo_x = x_mm * scale * correction_x + center_offset
    galvo_y = y_mm * scale * correction_y + center_offset
    return int(galvo_x), int(galvo_y)

def parse_gcode(file_path):
    start_time = time.time()
    points = []      
    current_x = None 
    current_y = None 
    current_s = None
    current_laser_on = None
    current_laser_power = 0

    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(";") or line.startswith("Frame:"):
                continue
            x_match = re.search(r'X([-+]?[0-9]*\.?[0-9]+)', line)
            y_match = re.search(r'Y([-+]?[0-9]*\.?[0-9]+)', line)
            s_match = re.search(r'S([-+]?[0-9]*\.?[0-9]+)', line)
            m3_match = re.search(r'\bm0?3\b', line, re.IGNORECASE)
            m4_match = re.search(r'\bm0?4\b', line, re.IGNORECASE)
            m5_match = re.search(r'\bm0?5\b', line, re.IGNORECASE)
            if x_match:
                current_x = float(x_match.group(1))
            if y_match:
                current_y = float(y_match.group(1))
            if s_match:
                current_s = float(s_match.group(1))
            if m3_match:
                current_laser_on = True
            if m4_match:
                current_laser_on = True
            if m5_match:
                current_laser_on = False
            if current_laser_on is not None:
                if current_laser_on:
                    if current_s is not None:
                        current_laser_power = current_s
                    else:
                        current_laser_power = 0
                else:
                    current_laser_power = 0
            if current_x is not None and current_y is not None:
                points.append((current_x, current_y, current_laser_power))
    #print (points)
    end_time = time.time()
    print ("Tempo de leitura do arquivo: {:.2f} segundos".format(end_time - start_time))
    return points

def convert_points_to_hatching(points):
    start_time = time.time()
    polygons = points_to_polygons(points)
    
    hatching_points = []
    for polygon in polygons:
        print("Polígono: ", polygon)
        hatching_points += generate_hatching(HatchingType.Vertical, polygon, line_spacing=0.5, power=555.0)

    print ("Hatching points: ", hatching_points)
    end_time = time.time()
    print ("Tempo de conversão em hatching: {:.2f} segundos".format(end_time - start_time))
    return hatching_points