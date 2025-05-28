# -*- coding: utf-8 -*-
"""
Created on Wed Jan 23 16:26:17 2025
@author: Daniel
Integrated script that:
  1. Reads a single input file (e.g., 'planos_procesadosRdA.txt') containing plane information (edges, color, extrusion vector, etc.).
  2. Detects the parent-child relationship among planes (using Shapely for polygon inclusion).
  3. Based on the detected information, generates an allowed polygon:
       - The parent plane is used as the outer boundary.
       - The child plane is used as a void.
  4. Generates a scanline-based trajectory over the allowed area.
  5. Assigns the "shutter" state to each trajectory segment depending on its zone.
  6. Simplifies the trajectory and saves it in a text file ("trajectory.txt"),
     including header information such as the parent plane's color and the constant Z coordinate.
  7. Plots the trajectory along with the contours of the planes.
"""

import re
import math
import numpy as np
import matplotlib.pyplot as plt
import os
from shapely.geometry import Polygon, LineString, Point, MultiLineString 
from shapely.validation import explain_validity

# ======================================================================
# MODULE 1: Extraction of Plane Information and Hierarchy Detection
# ======================================================================

def read_planes(input_filename):
    """
    Reads the input file and groups the content of each plane into blocks.
    General headers are ignored.
    """
    with open(input_filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    planes = []
    current_block = []
    for line in lines:
        stripped = line.rstrip('\n')
        # Assumes each plane block starts with "Plano"
        if re.match(r'^Plano\s+\d+', stripped):
            if current_block:
                planes.append(current_block)
            current_block = [stripped]
        elif current_block:
            current_block.append(stripped)
    if current_block:
        planes.append(current_block)
    return planes

def extract_vertices(plane_block):
    """
    Extracts the vertices of the plane by searching for lines starting with "Desde:".
    It is assumed that the 'Desde' points are representative of the contour.
    """
    vertices = []
    for line in plane_block:
        if line.strip().startswith("Desde:"):
            match = re.search(r'\(([^)]+)\)', line)
            if match:
                point = tuple(map(float, match.group(1).split(',')))
                vertices.append(point)
    if vertices:
        # To ensure polygon closure, use the last coordinate "Hasta:" if needed.
        hasta = None
        for line in reversed(plane_block):
            if line.strip().startswith("Hasta:"):
                m = re.search(r'\(([^)]+)\)', line)
                if m:
                    hasta = tuple(map(float, m.group(1).split(',')))
                    break
        if hasta and vertices[0] != hasta:
            vertices.append(hasta)
    return vertices

def build_polygon_from_vertices(vertices):
    """
    Constructs a polygon from a list of vertices.
    """
    if not vertices or len(vertices) < 3:
        return None
    poly = Polygon(vertices)
    if not poly.is_valid:
        print("Invalid polygon:", explain_validity(poly))
    return poly

def extract_plane_info(plane_block):
    """
    From a block of text for a plane, extracts:
      - The vertices (for the contour)
      - The color
      - The extrusion vector (if exists)
      - The complete block (for reconstructing output if needed)
    Returns a dictionary with these data.
    """
    vertices = extract_vertices(plane_block)
    poly = build_polygon_from_vertices(vertices)
    
    color = None
    vector_extrusion = None
    for line in plane_block:
        if line.strip().startswith("Color:") and color is None:
            try:
                color = int(line.split(":",1)[1].strip())
            except ValueError:
                color = line.split(":",1)[1].strip()
        if line.strip().startswith("Vector de extrusión calculado:") and vector_extrusion is None:
            m = re.search(r'\(([^)]+)\)', line)
            if m:
                vector_extrusion = tuple(map(float, m.group(1).split(',')))
    return {"block": plane_block, "vertices": vertices, "polygon": poly,
            "color": color, "vector_extrusion": vector_extrusion}

def detect_hierarchy(planes_info):
    """
    Detects the parent-child relationship among planes.
    Returns a list of tuples (parent_index, child_index).
    """
    hierarchy = []
    n = len(planes_info)
    for i in range(n):
        poly1 = planes_info[i]["polygon"]
        if poly1 is None:
            continue
        for j in range(n):
            if i == j:
                continue
            poly2 = planes_info[j]["polygon"]
            if poly2 is None:
                continue
            if poly2.within(poly1):
                hierarchy.append((i, j))
    return hierarchy

# ===========================================================
# MODULE 2: Trajectory Generation and Shutter Assignment
# ===========================================================

def parse_point(line):
    """Extracts a point (x,y,z) from a line containing numbers in parentheses."""
    match = re.search(r'\(([^)]+)\)', line)
    if match:
        coords = match.group(1).split(',')
        try:
            coords = [float(coord.strip()) for coord in coords]
        except ValueError:
            return None
        return tuple(coords)
    return None

def interpolate_arc(segment, resolution):
    """
    Given an arc segment (with 'radio', 'centro', and 'angulos'),
    returns a list of points approximating the arc.
    """
    if "angulos" not in segment or segment["angulos"] is None:
        return [segment["desde"], segment["hasta"]]
    start_angle, end_angle = segment["angulos"]
    if end_angle <= start_angle:
        end_angle += 360
    angles = np.linspace(start_angle, end_angle, num=resolution + 1)
    points = []
    center = segment["centro"]
    radius = segment["radio"]
    for angle in angles:
        rad = math.radians(angle)
        x = center[0] + radius * math.cos(rad)
        y = center[1] + radius * math.sin(rad)
        z = center[2] if len(center) > 2 else 0.0
        points.append((x, y, z))
    return points

def points_equal(p1, p2, tol=1e-5):
    """Returns True if the two 3D points are equal within a tolerance."""
    return all(abs(a - b) < tol for a, b in zip(p1, p2))

def get_segment_points(segment, resolution):
    """
    Returns a list of points for a segment.
    If it is an arc, interpolation is performed; for a line, 'desde' and 'hasta' are used.
    """
    tipo = segment.get("tipo", "").upper()
    if "ARC" in tipo:
        pts = interpolate_arc(segment, resolution)
    else:
        pts = []
        if "desde" in segment:
            pts.append(segment["desde"])
        if "hasta" in segment:
            pts.append(segment["hasta"])
    return pts

def build_polygon_segments(segments, resolution):
    """
    Joins the segments to form the contour of the plane.
    Assumes that the segments are connected.
    """
    polygon_points = []
    for seg in segments:
        seg_points = get_segment_points(seg, resolution)
        if not seg_points:
            continue
        if not polygon_points:
            polygon_points.extend(seg_points)
        else:
            if points_equal(polygon_points[-1], seg_points[0]):
                polygon_points.extend(seg_points[1:])
            elif points_equal(polygon_points[-1], seg_points[-1]):
                seg_points.reverse()
                polygon_points.extend(seg_points[1:])
            else:
                print("Warning: segment does not connect. Last point: {}, points: {}".format(polygon_points[-1], seg_points))
                polygon_points.extend(seg_points)
    if not points_equal(polygon_points[0], polygon_points[-1]):
        polygon_points.append(polygon_points[0])
    return polygon_points

def get_polygon_coords_from_segments(segments, resolution):
    """
    From the list of segments of a plane, returns a list of 2D coordinates.
    """
    poly3d = build_polygon_segments(segments, resolution)
    return [(pt[0], pt[1]) for pt in poly3d]

def generate_scanlines(poly, spacing):
    """
    Generates horizontal scanlines covering the area of polygon 'poly'
    with spacing 'spacing'.
    """
    minx, miny, maxx, maxy = poly.bounds
    lines = []
    y = miny
    while y <= maxy:
        line = LineString([(minx, y), (maxx, y)])
        lines.append(line)
        y += spacing
    return lines

def create_trajectory_points(plane_poly, spacing):
    """
    Generates a raster-based scanline trajectory over the contour of polygon 'plane_poly'.
    """
    scanlines = generate_scanlines(plane_poly, spacing)
    trajectory = []
    for i, line in enumerate(scanlines):
        inter = plane_poly.intersection(line)
        segments = []
        if inter.is_empty:
            continue
        if isinstance(inter, LineString):
            segments = [inter]
        elif isinstance(inter, MultiLineString):
            segments = list(inter)
        line_points = []
        for seg in segments:
            num_samples = max(2, int(np.ceil(seg.length / spacing)))
            samples = [seg.interpolate(t, normalized=True) for t in np.linspace(0, 1, num_samples)]
            if i % 2 == 1:
                samples = list(reversed(samples))
            line_points.extend([(pt.x, pt.y) for pt in samples])
        if i == 0 and line_points and line_points[0][0] > line_points[-1][0]:
            line_points.reverse()
        if trajectory:
            trajectory.append(trajectory[-1])
        trajectory.extend(line_points)
    return trajectory

def is_on_border(point, allowed_area, tol=1e-3):
    """Returns True if the point is on the boundary of the allowed area."""
    pt = Point(point)
    return allowed_area.boundary.distance(pt) < tol

def point_zone(point, allowed_area, hole_poly):
    """
    Determines the zone in which a point is located:
      - Zone 1: inside the allowed area (parent plane)
      - Zone 2: inside the forbidden area (child plane)
      - 0 in other cases.
    """
    pt = Point(point)
    if allowed_area.contains(pt):
        return 1
    elif hole_poly.contains(pt):
        return 2
    else:
        return 0

def assign_shutter_to_trajectory(trajectory, allowed_area, hole_poly):
    """
    Assigns a shutter state to each segment of the trajectory:
      - If both endpoints are in Zone 1: "open"
      - Otherwise: "closed"
      - If any endpoint is on the border, the shutter is forced "open".
    Returns a list of tuples: (start_point, end_point, shutter_state).
    """
    traj_with_shutter = []
    for i in range(len(trajectory)-1):
        pt1 = trajectory[i]
        pt2 = trajectory[i+1]
        zone1 = point_zone(pt1, allowed_area, hole_poly)
        zone2 = point_zone(pt2, allowed_area, hole_poly)
        shutter = "open" if zone1 == 1 and zone2 == 1 else "closed"
        if is_on_border(pt1, allowed_area) or is_on_border(pt2, allowed_area):
            shutter = "open"
        traj_with_shutter.append((pt1, pt2, shutter))
    return traj_with_shutter

def are_collinear(p, q, r, tol=1e-5):
    """Determines if three points are collinear within a tolerance."""
    v1 = (q[0]-p[0], q[1]-p[1])
    v2 = (r[0]-q[0], r[1]-q[1])
    cross = v1[0]*v2[1] - v1[1]*v2[0]
    return abs(cross) < tol

def simplify_trajectory(traj_with_shutter, tol=1e-5):
    """
    Simplifies the trajectory by concatenating consecutive segments that are collinear
    and have the same shutter state.
    Returns a list of simplified segments.
    """
    if not traj_with_shutter:
        return []
    simplified = []
    current_start, current_end, current_shutter = traj_with_shutter[0]
    for seg in traj_with_shutter[1:]:
        p_start, p_end, shutter = seg
        if shutter == current_shutter and are_collinear(current_start, current_end, p_end, tol):
            current_end = p_end
        else:
            simplified.append((current_start, current_end, current_shutter))
            current_start, current_end, current_shutter = seg
    simplified.append((current_start, current_end, current_shutter))
    return simplified

def save_trajectory_to_txt(traj_simplified, filename, trajectory_color, constant_z, decimals=6):
    """
    Saves the simplified trajectory to a text file.
    A header with the parent's color and the Z constant is added.
    """
    fmt = "{{:.{0}f}}".format(decimals)
    with open(filename, "w", encoding="utf-8") as f:
        f.write("Color extraido del Plano padre: {}\n".format(trajectory_color))
        f.write("Constante Z: {}\n".format(constant_z))
        f.write("\n")
        for seg in traj_simplified:
            p1, p2, shutter = seg
            line = ("De (" + fmt + ", " + fmt + ") a (" + fmt + ", " + fmt + "): shutter {}"
                    ).format(p1[0], p1[1], p2[0], p2[1], shutter)
            f.write(line + "\n")
    print("La trayectoria se ha guardado en '{}'".format(filename))

def plot_trajectory(traj_simplified, plane1_coords, plane2_coords, trajectory_color, constant_z):
    """
    Plots the simplified trajectory and the contours:
      - The parent plane contour (blue).
      - The child plane contour (red) if present.
      - The trajectory with shutter state labels on each segment.
    """
    plt.figure(figsize=(8,10),dpi=120)

    # Extract points for trajectory plotting
    xs = []
    ys = []
    for seg in traj_simplified:
        p1, p2, shutter = seg
        xs.extend([p1[0], p2[0]])
        ys.extend([p1[1], p2[1]])
    plt.plot(xs, ys, '.-', color='C1', label="Trajectory")
    
    # Plot parent plane contour
    if plane1_coords:
        plane1_x, plane1_y = zip(*plane1_coords)
        plt.plot(list(plane1_x)+[plane1_x[0]], list(plane1_y)+[plane1_y[0]], 'C0', label="Parent")
    
    # Plot child plane contour if available
    if plane2_coords:
        plane2_x, plane2_y = zip(*plane2_coords)
        plt.plot(list(plane2_x)+[plane2_x[0]], list(plane2_y)+[plane2_y[0]], 'C2', label="Child (Void)")
    
    # Annotate shutter state at the midpoint of each segment
    for seg in traj_simplified:
        mid_x = (seg[0][0] + seg[1][0]) / 2.0
        mid_y = (seg[0][1] + seg[1][1]) / 2.0
        plt.text(mid_x, mid_y, seg[2], fontsize=8, color='purple')
    

    plt.title(f"Shutter Actuated Trajectory")
    plt.xlabel("X [µm]")
    plt.ylabel("Y [µm]")
    plt.legend(loc='lower right', fontsize=8)
    plt.gca().set_aspect('equal', adjustable='box')
    plt.grid(True)
    plt.show()

# ======================================================
# MAIN FUNCTION
# ======================================================

def main():
    # ----- Parameters and paths -----
    base_directory = r'C:\Users\Daniel\Desktop\Uni\Python\TFG\GetPlanes\RdA'
    os.chdir(base_directory)
    input_filename = r'C:\Users\Daniel\Desktop\Uni\Python\TFG\GetPlanes\RdA\testhiercode.txt'
    trajectory_output = r'C:\Users\Daniel\Desktop\Uni\Python\TFG\GetPlanes\RdA\trajectorytesting.txt'
    resolution = 30           # Resolution for arc interpolation
    VOXEL_DIAMETER = 2      # Voxel diameter (for trajectory spacing)
    OVERLAP = 0.5
    spacing = VOXEL_DIAMETER * (1 - OVERLAP)
    # ------------------------------
    
    # 1. Read the input file and extract plane information
    plane_blocks = read_planes(input_filename)
    planes_info = []
    for block in plane_blocks:
        info = extract_plane_info(block)
        planes_info.append(info)
    
    if not planes_info:
        print("No plane information detected in the file.")
        return
    
    # 2. Detect the parent-child relationship between planes
    hierarchy = detect_hierarchy(planes_info)
    if hierarchy:
        father_idx, son_idx = hierarchy[0]
        print(f"Detected hierarchy: Plane {father_idx+1} (parent) contains Plane {son_idx+1} (child)")
    else:
        print("No parent-child hierarchy detected. The first plane will be used as parent.")
        father_idx = 0
        son_idx = None

    # 3. Extract contours from the edges of the parent (and child if exists)
    def extract_segments(plane_block):
        segments = []
        current_segment = {}
        for line in plane_block:
            stripped = line.strip()
            if re.match(r'^Arista\s+\d+:', stripped):
                if current_segment:
                    segments.append(current_segment)
                current_segment = {}
            else:
                if stripped.startswith("Tipo:"):
                    current_segment["tipo"] = stripped.split(":",1)[1].strip()
                elif stripped.startswith("Color:"):
                    try:
                        current_segment["color"] = int(stripped.split(":",1)[1].strip())
                    except ValueError:
                        current_segment["color"] = stripped.split(":",1)[1].strip()
                elif stripped.startswith("Desde:"):
                    current_segment["desde"] = parse_point(stripped)
                elif stripped.startswith("Hasta:"):
                    current_segment["hasta"] = parse_point(stripped)
                elif stripped.startswith("Radio:"):
                    try:
                        current_segment["radio"] = float(stripped.split(":",1)[1].strip())
                    except ValueError:
                        current_segment["radio"] = None
                elif stripped.startswith("Ángulos:"):
                    parts = stripped.split(":",1)[1].strip().replace("°", "")
                    angle_parts = parts.split("-")
                    if len(angle_parts) >= 2:
                        try:
                            current_segment["angulos"] = (float(angle_parts[0].strip()), float(angle_parts[1].strip()))
                        except ValueError:
                            current_segment["angulos"] = None
                elif stripped.startswith("Centro:"):
                    current_segment["centro"] = parse_point(stripped)
        if current_segment:
            segments.append(current_segment)
        return segments

    father_segments = extract_segments(planes_info[father_idx]["block"])
    father_coords = get_polygon_coords_from_segments(father_segments, resolution)
    
    if son_idx is not None:
        son_segments = extract_segments(planes_info[son_idx]["block"])
        son_coords = get_polygon_coords_from_segments(son_segments, resolution)
    else:
        son_coords = []
    
    # 4. Determine the Z constant from the first point of the parent's vertices
    constant_z = 0.0
    if father_coords and len(planes_info[father_idx]["vertices"][0]) >= 3:
        constant_z = planes_info[father_idx]["vertices"][0][2]
    
    # 5. Extract the parent's color
    father_color = planes_info[father_idx]["color"]
    
    # 6. Create the allowed polygon: external contour (parent) and void (child) if exists
    if son_coords:
        allowed_area = Polygon(father_coords, [son_coords])
        hole_poly = Polygon(son_coords)
    else:
        allowed_area = Polygon(father_coords)
        hole_poly = Polygon()
    
    father_poly = Polygon(father_coords)
    
    # 7. Generate the scanline-based trajectory over the parent's area
    trajectory = create_trajectory_points(father_poly, spacing)
    traj_with_shutter = assign_shutter_to_trajectory(trajectory, allowed_area, hole_poly)
    # Simplify the trajectory to avoid duplicate segments with the same shutter state
    traj_simplified = simplify_trajectory(traj_with_shutter)
    
    # 8. Save the simplified trajectory to a text file
    save_trajectory_to_txt(traj_simplified, trajectory_output, trajectory_color=father_color, constant_z=constant_z)
    
    # 9. Plot the simplified trajectory and the plane contours
    plot_trajectory(traj_simplified, father_coords, son_coords, trajectory_color=father_color, constant_z=constant_z)

if __name__ == '__main__':
    main()
