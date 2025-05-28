# -*- coding: utf-8 -*-
"""
Created on Tue Jan 21 11:51:37 2025
@author: Daniel
"""

from collections import defaultdict
import ast
import os
import numpy as np

def read_sections(file_path):
    """Lee y separa las secciones del archivo manteniendo formato original"""
    sections = {
        'TRAYECTORIAS': [],
        'PLANOS': [],
        'current': None
    }
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            stripped = line.strip()
            
            if stripped == "TRAYECTORIAS:":
                sections['current'] = 'TRAYECTORIAS'
                sections['TRAYECTORIAS'].append(line)
            elif stripped == "PLANOS:":
                sections['current'] = 'PLANOS'
                sections['PLANOS'].append(line)
            elif sections['current']:
                sections[sections['current']].append(line)
    
    return sections['TRAYECTORIAS'], sections['PLANOS']

def compute_plane_normal(points):
    """Calcula el vector normal de un plano usando 3 puntos no colineales."""
    if len(points) < 3:
        return None
    
    # Convertir a arrays de numpy para cálculos vectoriales
    np_points = [np.array(p) for p in points]
    
    # Buscar 3 puntos no colineales
    for i in range(len(np_points)-2):
        p1, p2, p3 = np_points[i], np_points[i+1], np_points[i+2]
        v1 = p2 - p1
        v2 = p3 - p1
        cross_product = np.cross(v1, v2)
        
        if np.linalg.norm(cross_product) > 1e-6:  # Evitar colinealidad
            normal = cross_product / np.linalg.norm(cross_product)
            return tuple(np.round(normal, 5))
    
    return None

def get_unique_points_from_edges(edges):
    """Extrae puntos únicos de todas las aristas de un plano."""
    points = set()
    for edge in edges:
        points.add(edge['start'])
        points.add(edge['end'])
    return [np.array(p) for p in points]

def process_planes_section(planos_lines):
    """Procesa la sección PLANOS extrayendo entidades válidas"""
    direct_planes = []
    edges = []
    vertices = defaultdict(set)
    edge_id_map = {}  # Maps edge index to edge data (optional, if needed elsewhere)

    for line in planos_lines:
        line = line.strip()
        if not line.startswith('{') or not line.endswith('}'):
            continue

        try:
            data = ast.literal_eval(line.replace("'", "\""))
            if data.get('weight', 0) < 0:
                continue

            entity_type = data['type']
            color = data.get('color', 'N/A')

            if entity_type in ['CIRCLE', 'ELLIPSE']:
                # Existing extrusion adjustment code remains the same
                extrusion = np.array(data.get('extrusion', (0, 0, 1)))
                if np.linalg.norm(extrusion) < 1e-6:
                    extrusion = np.array([0.0, 0.0, 1.0])
                else:
                    extrusion = extrusion / np.linalg.norm(extrusion)

                max_idx = np.argmax(np.abs(extrusion))
                if extrusion[max_idx] < 0:
                    extrusion = -extrusion

                direct_planes.append({
                    'type': entity_type,
                    'data': data,
                    'original': line,
                    'extrusion': tuple(np.round(extrusion, 5))
                })
                continue

            # Process edges and track their indices
            edge = None
            if entity_type == 'LINE':
                edge = {
                    'type': 'LINE',
                    'start': tuple(data['start_point'][:3]),
                    'end': tuple(data['end_point'][:3]),
                    'color': color,
                    'original': line,
                    'extra': {}
                }
            elif entity_type == 'ARC':
                edge = {
                    'type': 'ARC',
                    'start': tuple(data['start_point'][:3]),
                    'end': tuple(data['end_point'][:3]),
                    'color': color,
                    'radius': data['radius'],
                    'start_angle': data['start_angle'],
                    'end_angle': data['end_angle'],
                    'center': tuple(data['center'][:3]),
                    'original': line,
                    'extra': {}
                }
            elif entity_type == 'LWPOLYLINE':
                points = [tuple(p[:3]) for p in data['points']]
                for i in range(len(points)-1):
                    edge = {
                        'type': 'LWPOLYLINE_SEGMENT',
                        'start': points[i],
                        'end': points[i+1],
                        'color': color,
                        'original': line,
                        'extra': {
                            'polyline_closed': data.get('is_closed', False),
                            'segment_index': i
                        }
                    }
                    edges.append(edge)
                    edge_idx = len(edges) - 1
                    vertices[edge['start']].add(edge_idx)
                    vertices[edge['end']].add(edge_idx)

            if edge and entity_type != 'LWPOLYLINE':  # LWPOLYLINE already handled
                edges.append(edge)
                edge_idx = len(edges) - 1
                vertices[edge['start']].add(edge_idx)
                vertices[edge['end']].add(edge_idx)

        except Exception as e:
            print(f"Error procesando línea: {line}\nError: {str(e)}")

    return direct_planes, edges, vertices, edge_id_map

def group_connected_edges(edges, vertices, edge_id_map):
    """Agrupa aristas conectadas usando BFS y calcula vector normal"""
    visited = set()
    planes = []

    for edge_idx, edge in enumerate(edges):
        if edge_idx not in visited:
            current_plane = []
            stack = [edge_idx]

            while stack:
                current_edge_idx = stack.pop()
                if current_edge_idx not in visited:
                    visited.add(current_edge_idx)  # Track by index (integer)
                    current_edge = edges[current_edge_idx]
                    current_plane.append(current_edge)

                    # Get connection points from the current edge
                    connection_points = []
                    if current_edge['type'] in ['LINE', 'ARC', 'LWPOLYLINE_SEGMENT']:
                        connection_points = [current_edge['start'], current_edge['end']]

                    # Find all edges connected to these points
                    for point in connection_points:
                        for neighbor_idx in vertices.get(point, []):
                            if neighbor_idx not in visited:
                                stack.append(neighbor_idx)

            if current_plane:
                points = get_unique_points_from_edges(current_plane)
                extrusion_vector = compute_plane_normal(points)
                planes.append({
                    'edges': current_plane,
                    'extrusion': extrusion_vector
                })

    return planes


def format_edge(edge):
    """Formatea una arista para su visualización"""
    details = []
    details.append(f"Tipo: {edge['type']}")
    details.append(f"Color: {edge['color']}")
    
    if edge['type'] == 'LINE':
        details.append(f"Desde: {edge['start']}")
        details.append(f"Hasta: {edge['end']}")
        
    elif edge['type'] == 'ARC':
        details.append(f"Desde: {edge['start']}")
        details.append(f"Hasta: {edge['end']}")
        details.append(f"Radio: {edge['radius']:.5f}")
        details.append(f"Ángulos: {edge['start_angle']:.5f}° - {edge['end_angle']:.5f}°")
        details.append(f"Centro: {edge['center']}")
        
    elif edge['type'] == 'LWPOLYLINE_SEGMENT':
        details.append(f"Segmento: {edge['extra']['segment_index'] + 1}")
        details.append(f"Desde: {edge['start']}")
        details.append(f"Hasta: {edge['end']}")
        details.append(f"Polilínea cerrada: {'Sí' if edge['extra']['polyline_closed'] else 'No'}")
    
    return "\n    ".join(details)

def write_output(output_path, trayectorias, direct_planes, grouped_planes):
    """Escribe el archivo de salida incluyendo vectores de extrusión"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(trayectorias)
        f.write("\nPLANOS PROCESADOS:\n")
        plano_counter = 1
        
        # Planos directos (Círculos/Elipses)
        for plano in direct_planes:
            f.write(f"\nPlano {plano_counter} ({plano['type']}):\n")
            f.write(plano['original'] + "\n")
            f.write(f"Detalles:\n")
            f.write(f"  Vector de extrusión: {plano['extrusion']}\n")
            if plano['type'] == 'CIRCLE':
                f.write(f"  Centro: {tuple(plano['data']['center'][:3])}\n")
                f.write(f"  Radio: {plano['data']['radius']:.5f}\n")
            elif plano['type'] == 'ELLIPSE':
                f.write(f"  Centro: {tuple(plano['data']['center'][:3])}\n")
                f.write(f"  Eje Mayor: {tuple(plano['data']['major_axis'][:3])}\n")
                f.write(f"  Eje Menor: {tuple(plano['data']['minor_axis'][:3])}\n")
            plano_counter += 1
        
        # Planos agrupados
        for plane in grouped_planes:
            f.write(f"\nPlano {plano_counter} (Agrupado):\n")
            f.write(f"Total de aristas: {len(plane['edges'])}\n")
            f.write(f"Vector de extrusión calculado: {plane['extrusion']}\n")
            
            for idx, edge in enumerate(plane['edges'], 1):
                f.write(f"\n  Arista {idx}:\n")
                f.write(f"    {format_edge(edge)}\n")
                f.write(f"    Entidad original:\n    {edge['original']}\n")
            
            plano_counter += 1

def main():
    directory = r'C:\Users\Daniel\Desktop\Uni\Python\TFG\GetPlanes\DiagPlane'
    os.chdir(directory)
    input_file = 'DiagPlane_Raw.txt'
    output_file = 'planos_procesadosDiagPlane.txt'
    
    trayectorias, planos = read_sections(input_file)
    direct_planes, edges, vertices, edge_id_map = process_planes_section(planos)
    grouped_planes = group_connected_edges(edges, vertices, edge_id_map)
    
    write_output(output_file, trayectorias, direct_planes, grouped_planes)
    
    print(f"Proceso completado exitosamente!")
    print(f"- Planos directos: {len(direct_planes)}")
    print(f"- Planos agrupados: {len(grouped_planes)}")
    print(f"- Total de aristas procesadas: {sum(len(p['edges']) for p in grouped_planes)}")

if __name__ == "__main__":
    main()