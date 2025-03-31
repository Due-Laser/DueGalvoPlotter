
import re

def mm_to_galvo(x_mm, y_mm, field_size_mm=200, galvo_range=65536, correction_x=0.8333, correction_y=0.8333):
    scale = galvo_range / field_size_mm
    center_offset = galvo_range / 2  
    galvo_x = x_mm * scale * correction_x + center_offset
    galvo_y = y_mm * scale * correction_y + center_offset
    return int(galvo_x), int(galvo_y)

def parse_gcode(file_path):
    points = []      
    current_x = None 
    current_y = None 
    current_s = None

    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(";") or line.startswith("Frame:"):
                continue
            x_match = re.search(r'X([-+]?[0-9]*\.?[0-9]+)', line)
            y_match = re.search(r'Y([-+]?[0-9]*\.?[0-9]+)', line)
            s_match = re.search(r'S([-+]?[0-9]*\.?[0-9]+)', line)
            if x_match:
                current_x = float(x_match.group(1))
            if y_match:
                current_y = float(y_match.group(1))
            if s_match:
                current_s = float(s_match.group(1))
            if current_x is not None and current_y is not None and current_s is not None:
                points.append((current_x, current_y, current_s))
    #print (points)
    return points