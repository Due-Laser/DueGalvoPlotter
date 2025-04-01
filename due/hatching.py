
from enum import Enum
from shapely.geometry import Polygon, LineString

class HatchingType(Enum):
    Horizontal = 1
    Vertical = 2

def points_to_polygons(points):
    polygons = []
    current_polygon = []

    return polygons

def generate_hatching(hatching_type: HatchingType, polygon: Polygon, line_spacing: float, power: float):
    match hatching_type:
        #case HatchingType.Horizontal:
        #    return generate_horizontal_hatching(polygon, line_spacing, power)
        case HatchingType.Vertical:
            return generate_vertical_hatching(polygon, line_spacing, power)

def generate_vertical_hatching(polygon: Polygon, line_spacing: float, power: float):
    """Gera hatching vertical dentro de um polígono e formata no estilo (X, Y, Potência)."""
    min_x, min_y, max_x, max_y = polygon.bounds  # Obtém os limites do polígono
    hatching_points = [(min_x, min_y, 0)]  # Posição inicial com potência 0
    
    y = min_y
    while y <= max_y:
        line = LineString([(min_x, y), (max_x, y)])
        clipped_line = polygon.intersection(line)  # Mantém apenas a parte dentro do polígono
        
        if not clipped_line.is_empty:
            if clipped_line.geom_type == "MultiLineString":
                for segment in clipped_line.geoms:
                    x1, y1 = segment.coords[0]
                    x2, y2 = segment.coords[-1]
                    hatching_points.append((x1, y1, 0))  # Move para início da linha sem potência
                    hatching_points.append((x1, y1, power))  # Ativa potência
                    hatching_points.append((x2, y2, power))  # Final da linha com potência
                    hatching_points.append((x2, y2, 0))  # Desativa potência
            else:
                x1, y1 = clipped_line.coords[0]
                x2, y2 = clipped_line.coords[-1]
                hatching_points.append((x1, y1, 0))  # Move sem potência
                hatching_points.append((x1, y1, power))  # Ativa potência
                hatching_points.append((x2, y2, power))  # Finaliza linha
                hatching_points.append((x2, y2, 0))  # Desliga potência
        
        y += line_spacing  # Próxima linha horizontal
    
    return hatching_points

# Exemplo: Criando um polígono (retângulo)
polygon = Polygon([(0, 0), (50, 0), (50, 50), (0, 50)])  # Quadrado 50x50
hatching_gcode = generate_vertical_hatching(polygon, line_spacing=5.0, power=555.0)

# Exibir o resultado
for point in hatching_gcode:
    print(point)