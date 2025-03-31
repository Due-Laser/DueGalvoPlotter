from shapely.geometry import Polygon, LineString

def generate_hatching_gcode(polygon: Polygon, line_spacing: float, power: float):
    """Gera hatching horizontal dentro de um polígono e formata no estilo (X, Y, Potência)."""
    min_x, min_y, max_x, max_y = polygon.bounds  # Obtém os limites do polígono
    gcode_points = [(min_x, min_y, 0)]  # Posição inicial com potência 0
    
    y = min_y
    while y <= max_y:
        line = LineString([(min_x, y), (max_x, y)])
        clipped_line = polygon.intersection(line)  # Mantém apenas a parte dentro do polígono
        
        if not clipped_line.is_empty:
            if clipped_line.geom_type == "MultiLineString":
                for segment in clipped_line.geoms:
                    x1, y1 = segment.coords[0]
                    x2, y2 = segment.coords[-1]
                    gcode_points.append((x1, y1, 0))  # Move para início da linha sem potência
                    gcode_points.append((x1, y1, power))  # Ativa potência
                    gcode_points.append((x2, y2, power))  # Final da linha com potência
                    gcode_points.append((x2, y2, 0))  # Desativa potência
            else:
                x1, y1 = clipped_line.coords[0]
                x2, y2 = clipped_line.coords[-1]
                gcode_points.append((x1, y1, 0))  # Move sem potência
                gcode_points.append((x1, y1, power))  # Ativa potência
                gcode_points.append((x2, y2, power))  # Finaliza linha
                gcode_points.append((x2, y2, 0))  # Desliga potência
        
        y += line_spacing  # Próxima linha horizontal
    
    return gcode_points

# Exemplo: Criando um polígono (retângulo)
polygon = Polygon([(0, 0), (50, 0), (50, 50), (0, 50)])  # Quadrado 50x50
hatching_gcode = generate_hatching_gcode(polygon, line_spacing=5.0, power=555.0)

# Exibir o resultado
for point in hatching_gcode:
    print(point)