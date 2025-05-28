import os
import ast
import re
from collections import defaultdict
from numbers import Real
from typing import Any

# Change directory to the location of your file
directory = r'C:\Users\Daniel\Desktop\Uni\Python\TFG\GetTrayec\Helix'
os.chdir(directory)

def round_numbers(obj: Any, precision: int) -> Any:
    if isinstance(obj, Real):
        return round(obj, precision)
    elif isinstance(obj, (list, tuple)):
        return type(obj)(round_numbers(x, precision) for x in obj)
    elif isinstance(obj, dict):
        return {k: round_numbers(v, precision) for k, v in obj.items()}
    return obj

def clean_line(line: str) -> str:
    line = re.sub(r"array\('d', (\[.*?\])\)", r"\1", line)
    line = line.replace("'None'", "None")
    return line

def process_trayectorias(input_file: str, output_file: str, precision: int = 3) -> None:
    trayectorias = []
    current_section = None
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line == "TRAYECTORIAS:":
                current_section = "trayectorias"
            elif line == "PLANOS:":
                current_section = "planos"
            elif line and current_section == "trayectorias":
                try:
                    cleaned_line = clean_line(line)
                    entity = ast.literal_eval(cleaned_line)
                    entity = round_numbers(entity, precision) #Rounding 
                    trayectorias.append(entity)
                except (SyntaxError, ValueError) as e:
                    print(f"[ERROR] Línea no procesada: {line}\n{str(e)}")
                    continue

    parametros = defaultdict(list)
    
    for entity in trayectorias:
        tipo = entity["type"]
        params = {
            "type": tipo,
            "color": entity.get("color", 1),
            "weight": entity.get("weight", -1)
        }
        
        if tipo == "LINE":
            params.update({
                "start": entity.get("start_point", (0, 0, 0)),
                "end": entity.get("end_point", (0, 0, 0))
            })
        
        elif tipo == "CIRCLE":
            params.update({
                "center": entity.get("center", (0, 0, 0)),
                "radius": entity.get("radius", 0.0),
                "extrusion_vector": entity.get('extrusion', (0,0,0))
            })
        
        elif tipo == "ARC":
            params.update({
                "center": entity.get("center", (0, 0, 0)),
                "radius": entity.get("radius", 0.0),
                "start_angle": entity.get("start_angle", 0.0),
                "end_angle": entity.get("end_angle", 360.0)
            })
        
        elif tipo == "HELIX":
            axis_base = entity.get("axis_base_point", (0, 0, 0))
            start_point = entity.get("start_point", (0, 0, 0))
            axis_vector = entity.get("axis_vector", (0, 0, 0))
            # Calculate radio_base as the difference between start_point and axis_base
            dx = start_point[0] - axis_base[0]
            dy = start_point[1] - axis_base[1]
            dz = start_point[2] - axis_base[2]
            radio_base = (dx**2 + dy**2 + dz**2) ** 0.5  # Euclidean distance
            radio_base = round(radio_base, precision) 
            
            params.update({
                "axis_base": axis_base,
                "axis_vector": axis_vector,
                "start_point": start_point,
                "radius": entity.get("radius", 0.0),  
                "radio_base": radio_base,  
                "turn_height": entity.get("turn_height",0.0),
                "turns": entity.get("turns", 1.0),
                "handedness": entity.get("handedness", "clockwise"),
                "control_points": entity.get("control_points", [])
            })

        elif tipo == "SPLINE":
            params.update({
                "degree":entity.get("degree", []),
                "control_points": entity.get("control_points", []),
                "fit_points": entity.get("fit_points", []),
                "knots": entity.get("knots", [])
            })
        
        elif tipo == "ELLIPSE":
            params.update({
                "center": entity.get("center", (0, 0, 0)),
                "major_axis": entity.get("major_axis", (0, 0, 0)),
                "minor_axis": entity.get("minor_axis", (0, 0, 0)),
                "start_point": entity.get("start_point",  (0,0,0)),
                "end_point": entity.get("end_point",  (0,0,0))
            })
        
        elif tipo in ("LWPOLYLINE", "POLYLINE"):
            params.update({
                "points": entity.get("points", []),
                "closed": entity.get("is_closed", False)
            })
        
        parametros[tipo].append(params)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for entity_type, entities in parametros.items():
            if not entities:
                continue
            f.write(f"===== {entity_type} =====\n")
            for idx, entity in enumerate(entities, 1):
                f.write(f"Entidad {idx}:\n")
                for key, value in entity.items():
                    if key == "type":
                        continue
                    if isinstance(value, (list, tuple)):
                        value = [round(x, precision) if isinstance(x, Real) else x for x in value]
                    f.write(f"  - {key}: {value}\n")    
                f.write("\n")
            f.write("\n")
        print(f"Datos extraídos y guardados en {output_file}")


process_trayectorias(
    input_file="RegHelix_Raw_2.txt",
    output_file="params_RegHelix_2.txt",
    precision=6  # Adjust tolerance of rounding (0-10)
)
