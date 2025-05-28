# -*- coding: utf-8 -*-
"""
Created on Mon Jan 20 11:50:48 2025

@author: Daniel
"""

import ezdxf
import os

def extract_geometry_from_dxf(file_path, output_file):
    doc = ezdxf.readfile(file_path)
    modelspace = doc.modelspace()
    
    geometry_data = {
        "trayectorias": [],
        "planos": []
    }

    def round_coordinates(coords):
        if isinstance(coords, (float, int)):
            return round(coords, 8)
        if coords is None:
            return None
        return tuple(round(coord, 8) for coord in coords)

    for entity in modelspace:
        entity_data = str(entity)
        weight = entity.dxf.lineweight if entity.dxf.hasattr("lineweight") else -1

        base_data = {
            "type": entity.dxftype(),
            "weight": weight,
            "color": entity.dxf.color,
            "entity": entity_data
        }

        # --- LÍNEA ---
        if entity.dxftype() == "LINE":
            base_data.update({
                "start_point": round_coordinates(entity.dxf.start),
                "end_point": round_coordinates(entity.dxf.end),
            })

        # --- ARCO ---
        elif entity.dxftype() == "ARC":
            base_data.update({
                "center": round_coordinates(entity.dxf.center),
                "radius": round_coordinates(entity.dxf.radius),
                "start_point": round_coordinates(entity.start_point),
                "end_point": round_coordinates(entity.end_point),
                "start_angle": round_coordinates(entity.dxf.start_angle),
                "end_angle": round_coordinates(entity.dxf.end_angle),
                "extrusion": round_coordinates(entity.dxf.extrusion), 
            })

        # --- SPLINE ---
        elif entity.dxftype() == "SPLINE":
            control_points = entity.control_points if hasattr(entity, 'control_points') else []
            fit_points = entity.fit_points if hasattr(entity, 'fit_points') else []
            
            base_data.update({
                "degree": entity.dxf.degree,
                "flag": entity.dxf.flags,
                "control_points": [round_coordinates(point) for point in control_points],
                "fit_points": [round_coordinates(point) for point in fit_points],
                "knots": round_coordinates(entity.knots)if hasattr(entity, 'knots') else [],
                "weights": round_coordinates(entity.weights)if hasattr(entity, 'weights')else [],
                "start_tangent": round_coordinates(entity.dxf.start_tangent) if hasattr(entity.dxf, 'start_tangent') else None,
                "end_tangent": round_coordinates(entity.dxf.end_tangent) if hasattr(entity.dxf, 'end_tangent') else None,
            })

        # --- HÉLICE ---
        elif entity.dxftype() == "HELIX":
            base_data.update({
                "axis_base_point": round_coordinates(entity.dxf.axis_base_point),
                "start_point": round_coordinates(entity.dxf.start_point),
                "axis_vector": round_coordinates(entity.dxf.axis_vector),
                "radius": round_coordinates(entity.dxf.radius),
                "turn_height": entity.dxf.turn_height,
                "turns": entity.dxf.turns,
                "handedness": "counter clockwise" if entity.dxf.handedness == 1 else "clockwise",
                "control_points": [round_coordinates(point) for point in entity.control_points] if hasattr(entity, 'control_points') else [],
            })

        # --- CÍRCULO ---
        elif entity.dxftype() == "CIRCLE":
            base_data.update({
                "center": round_coordinates(entity.dxf.center),
                "radius": entity.dxf.radius,
                "extrusion": round_coordinates(entity.dxf.extrusion), 
            })

        # --- ELIPSE ---
        elif entity.dxftype() == "ELLIPSE":
            base_data.update({
                "center": round_coordinates(entity.dxf.center),
                "major_axis": round_coordinates(entity.dxf.major_axis),
                "minor_axis": round_coordinates(entity.minor_axis) if hasattr(entity, 'minor_axis') else None,
                "ratio": entity.dxf.ratio,  # Relación eje menor/mayor
                "start_point": round_coordinates(entity.start_point),
                "end_point": round_coordinates(entity.end_point),
                "extrusion": round_coordinates(entity.dxf.extrusion),  
            })

        # --- POLILÍNEA ---
        elif entity.dxftype() == "POLYLINE":
            points = [round_coordinates(vertex.dxf.location) for vertex in entity.vertices] if hasattr(entity, 'vertices') else []
            base_data.update({
                "points": points,
                "is_closed": entity.is_closed,
            })

        # --- POLILÍNEA LIGERA ---
        elif entity.dxftype() == "LWPOLYLINE":
            base_data.update({
                "points": [round_coordinates(vertex) for vertex in entity],
                "is_closed": entity.is_closed,
            })

        # Clasificación por peso de línea
        if weight < 0:
            geometry_data["trayectorias"].append(base_data)
        else:
            geometry_data["planos"].append(base_data)

    with open(output_file, 'w') as file:
        for geom_type, data in geometry_data.items():
            file.write(f"{geom_type.upper()}:\n")
            for item in data:
                file.write(f"{item}\n")

    print(f"Datos extraídos y guardados en {output_file}")

# --- Ejecución principal ---
directory = r'C:\Users\Daniel\Desktop\Uni\Python\TFG\GetTrayec\Helix'
os.chdir(directory)

dxf_file_name = 'RegHelix.dxf'
output_file_name = "RegHelix_Raw_2.txt"

extract_geometry_from_dxf(dxf_file_name, output_file_name)