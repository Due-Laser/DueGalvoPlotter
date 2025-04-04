import time

from shapely import Polygon
from due import utils
from due.hatching import HatchingType, generate_hatching, points_to_polygons
from due.svg2gcode import convert_svg_to_gcode

def process_polygons(polygons):
    start_time = time.time()
    processed_polygons = []
    polygons.reverse()  # Inverte a ordem dos polígonos para processamento
    isPreviousPolygonHole = False

    for i in range(0, len(polygons)):
        current_polygon = polygons[i]
        previous_polygon = polygons[i - 1]
        print("Polígono atual:", list(current_polygon.exterior.coords)[0], ">", list(current_polygon.exterior.coords)[1], "| Horário:", current_polygon.exterior.is_ccw)
        if current_polygon.exterior.is_ccw:
            # Polígono é pai (anti-horário)
            if isPreviousPolygonHole:
                print("Polígono anterior: ", previous_polygon)
                print("Polígono atual: ", current_polygon)
                shell = list(current_polygon.exterior.coords)
                hole = list(previous_polygon.exterior.coords)
                processed_polygon = Polygon(shell, [hole])
                print("Polígono processado:", processed_polygon)
                processed_polygons.append(processed_polygon)
            else:
                processed_polygons.append(current_polygon)
            isPreviousPolygonHole = False
        else:
            # Polígono é filho (horário)
            isPreviousPolygonHole = True

    processed_polygons.reverse()  # Inverte a ordem dos polígonos processados
    end_time = time.time()
    print("Tempo de processamento dos polígonos: {:.2f} segundos".format(end_time - start_time))
    return processed_polygons

def convert_points_to_hatching(points):
    start_time = time.time()
    polygons = points_to_polygons(points)
    processed_polygons = process_polygons(polygons)
    print("Polígonos processados:", len(processed_polygons))
    hatching_points = []
    for polygon in processed_polygons:
        #print("Polígono: ", polygon)
        hatching_points += generate_hatching(HatchingType.Vertical, polygon, line_spacing=5.0, power=555.0)

    #print ("Hatching points: ", hatching_points)
    end_time = time.time()
    print ("Tempo de conversão em hatching: {:.2f} segundos".format(end_time - start_time))
    return hatching_points

svg_filepath = "svgs/kip22.svg"
gcodes_folder = "C:/Users/User/Documents/Due Laser/Github/DueGalvoPlotter/due/gcodes/"
convert_svg_to_gcode(svg_filepath, gcodes_folder+"kip22.gcode")
gcode_filepath = "gcodes/kip22.gcode"
points = utils.parse_gcode(gcode_filepath)
#print("points: ", points)
polygons = points_to_polygons(points)
#print("polygons: ", polygons)
processed_polygons = process_polygons(polygons)
#print("Polígonos processados:", len(processed_polygons))
hatching_points = convert_points_to_hatching(points)
#print("Hatching points: ", hatching_points)

import matplotlib.pyplot as plt
from shapely.geometry import Polygon

# Desenhar
for poly in polygons:
    x, y = poly.exterior.xy
    plt.plot(x, y, marker='o')
    plt.fill(x, y, alpha=0.2)
plt.title("Polígono desenhado")
plt.gca().set_aspect('equal', adjustable='box')
plt.grid(True)
plt.show()

for poly in processed_polygons:
    # Desenhar a casca externa
    x, y = poly.exterior.xy
    plt.plot(x, y, color='blue', marker='o')
    plt.fill(x, y, alpha=0.3, facecolor='blue')

    # Desenhar os buracos (interior rings)
    for interior in poly.interiors:
        xh, yh = interior.xy
        plt.plot(xh, yh, color='red', marker='x')  # contorno do buraco
        plt.fill(xh, yh, alpha=0.4, facecolor='white')  # preenchimento do buraco

plt.title("Polígonos com holes")
plt.gca().set_aspect('equal', adjustable='box')
plt.grid(True)
plt.show()