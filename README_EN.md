# CAD2AeroBasic Converter

This repository contains Python scripts for CAD to AeroBasic conversion.

---
## Requirements

- Python 3.x
To install libraries:

```bash
pip install ezdxf numpy matplotlib shapely
# Or, using Anaconda
conda install -c conda-forge ezdxf numpy matplotlib shapely
```

---

## Notes

Units in the DXF file are expected to be in micrometers.

The origin in the generated AeroBasic code is set relative to the point with the smallest X and Y, and the largest Z value.

Margins of 10 µm (XY) and 100 µm (Z) are added for safe motion planning.

To automatically detect whether each entity belongs to a linear trajectory or a planar fill, use any positive value of lineweight for the closed entity to represent a plane.

---

## Usage of all scripts:
1. **Set the working directory** where input file is located (this is where output file will land).
2. **Run the script:**
    ```bash
    python file_name.py
    ``` 
3. **Output:** Usually a .txt file or a print in console.

---

## Script: `dxftotxt.py`

### Overview

- **Purpose:** Extracts geometry data from a DXF file and writes it to a text file.
- **Entities Supported:** LINE, ARC, SPLINE, HELIX, CIRCLE, ELLIPSE, POLYLINE, LWPOLYLINE.
- **Classification:** Entities are categorized into `trayectorias` (trajectories) and `planos` (planes) based on line weight.

### Main Features

- Uses the [`ezdxf`](https://github.com/mozman/ezdxf) library for DXF parsing.
- Rounds coordinates for consistency.
- Extracts and organizes entity attributes such as type, color, weight, and geometry-specific data.
- Outputs results in a human-readable text format.

### Example

```python
directory = r'C:\Users\Daniel\Desktop\Uni\Python\TFG\GetTrayec\Helix'
os.chdir(directory)

dxf_file_name = 'RegHelix.dxf'
output_file_name = "RegHelix_Raw_2.txt"

extract_geometry_from_dxf(dxf_file_name, output_file_name)
```

---

## GetTrajectories

This folder contains the scripts for processing and generating trajectories in AeroBasic from CAD data:

---


### Script: `process_trayec.py`

#### Overview

- **Purpose:** Processes the output from `dxftotxt.py` (`RegHelix_Raw_2.txt`), cleans and rounds the data, and organizes it by entity type into a more structured text file.
- **Features:** 
  - Cleans and parses lines using `ast` and regular expressions.
  - Rounds all numeric values to a configurable precision.
  - Groups entities by type and outputs them in a readable format.

#### Main Features

- Uses Python standard libraries: `os`, `ast`, `re`, `collections`, and `typing`.
- Calculates additional parameters (e.g., `radio_base` for HELIX entities).
- Handles all supported entity types and their relevant parameters.

#### Example

```python
process_trayectorias(
    input_file="RegHelix_Raw_2.txt",
    output_file="params_RegHelix_2.txt",
    precision=6  # Adjust tolerance of rounding (0-10)
)
```

---

### Script: `CADTrajectory2AB.py`

#### Overview

- **Purpose:** Reads processed geometry parameter files (e.g., from `process_trayec.py`), generates parametric trajectories (HELIX, LINE), visualizes them in 3D, and outputs AeroBasic code for laser control.
- **Features:**
    - Parses structured parameter files.
    - Generates parametric points for HELIX and LINE entities.
    - Calculates voxel centers along trajectories for laser path planning.
    - Maps entity color to laser speed.
    - Visualizes trajectories in 3D using Matplotlib.
    - Outputs AeroBasic code for Aerotech A3200 systems.

#### Main Features

- Uses `numpy`, `matplotlib`, `scipy.interpolate`, and Python standard libraries.
- Supports both HELIX and LINE entities.
- Flexible voxel diameter and overlap configuration.
- Generates ready-to-use AeroBasic scripts for laser systems.

#### Example

```python
directory = r'C:\Users\Daniel\Desktop\Uni\Python\TFG\GetTrayec\Helix'
os.chdir(directory)
Input_File = "params_helixpore_wg.txt"
VOXEL_DIAMETER = 0.2
OVERLAP = 0.5

# Reads parameter file, generates trajectories, visualizes, and outputs AeroBasic code
# (See script for full details)
```

---



## GetPlanes
This folder contains the scripts for processing and generating planes in AeroBasic from CAD data.

### Script: `process_planes.py`

#### Overview

- **Purpose:** Processes the raw output file containing plane entities (e.g., `PlanoXZ_Raw.txt`), extracts and groups plane edges, computes extrusion (normal) vectors, and outputs a structured file for use in AeroBasic code generation.
- **Features:**
    - Reads and separates `TRAYECTORIAS` and `PLANOS` sections from the input file.
    - Identifies direct planes (CIRCLE, ELLIPSE) and computes/adjusts their extrusion vectors.
    - Extracts and groups connected edges (LINE, ARC, LWPOLYLINE) into planar groups using graph traversal.
    - Calculates the normal vector for each grouped plane using non-collinear points.
    - Outputs a detailed, human-readable summary of each plane, including extrusion vectors and edge details.

#### Main Features

- Uses Python standard libraries: `os`, `ast`, `collections`, and `numpy` for vector math.
- Handles both direct (CIRCLE/ELLIPSE) and grouped planes (arbitrary edge loops).
- Robust to collinear points and degenerate cases.
- Outputs a processed planes file with all relevant geometric and topological information.

#### Example

```python
directory = r'C:\Users\Daniel\Desktop\Uni\Python\TFG\GetPlanes\DiagPlane'
os.chdir(directory)
input_file = 'DiagPlane_Raw.txt'
output_file = 'planos_procesadosDiagPlane.txt'
```

---


### Script: `Planes2AB_Raster.py`

#### Overview

- **Purpose:** Generates raster-fill AeroBasic code for arbitrarily oriented planes from processed CAD data.
- **Features:**
    - Reads processed plane files containing edges and extrusion vectors.
    - Constructs an orthonormal frame for each plane based on its extrusion vector.
    - Projects 3D plane edges into a 2D plane for polygonization and rasterization.
    - Generates back-and-forth raster lines within the polygonized plane area.
    - Lifts raster points back into 3D world coordinates.
    - Maps edge color to laser feedrate.
    - Outputs AeroBasic code for Aerotech A3200.

#### Main Features

- Uses `numpy` for vector math and coordinate transforms.
- Employs `shapely` for geometric operations (polygonization, intersections).
- Handles any plane orientation and complex edge arrangements.
- Configurable voxel diameter and overlap for raster fill.
- Automatically computes global origin and margins for safe motion.

#### Example

```python
directory = r'C:\Users\Daniel\Desktop\Uni\Python\TFG\GetPlanes\DiagPlane'
os.chdir(directory)
planes = parse_planos("planos_procesadosDiagPlane.txt")
generate_aerobasic_plane_fill_code(planes, filename="DiagPlane_Raster_CAD2AB.txt")
```

---


### Script: `Planes2AB_Spiral.py`

#### Overview

- **Purpose:** Generates spiral-fill AeroBasic code for arbitrarily oriented planes with curved (arc) and straight edges, based on processed CAD data.
- **Features:**
    - Reads processed plane files with support for both straight and arc edges.
    - Reconstructs plane boundaries in 2D, including arc interpolation.
    - Generates a spiral fill pattern that adapts to the polygonal shape of each plane.
    - Lifts spiral points back into 3D world coordinates using the plane's extrusion vector.
    - Maps edge color to laser feedrate.
    - Outputs AeroBasic code for Aerotech A3200 with spiral motion blocks for each plane.

#### Main Features

- Uses `numpy` for vector math and coordinate transforms.
- Employs `shapely` for geometric operations (polygonization, arc handling).
- Handles arbitrary plane orientations and complex edge arrangements (including arcs).
- Configurable voxel diameter, overlap, and arc resolution.
- Automatically computes global origin and margins for safe motion.
- Robust to degenerate or invalid polygons.

#### Example

```python
directory = r'C:\Users\Daniel\Desktop\Uni\Python\TFG\GetPlanes\PlanoXZ'
os.chdir(directory)
planes = parse_planos("planos_procesadosXZ.txt")
generate_aerobasic_plane_fill_code(planes, filename="TEST.txt")
```

---
### Script: `Establish_Hierarchy.py`

#### Overview

- **Purpose:** Reads a processed planes file, detects parent-child (hierarchical) relationships among planes, constructs a polygon with holes (voids), generates a scanline-based trajectory over the allowed area, assigns "shutter" states to trajectory segments, simplifies the trajectory, saves it to a text file, and visualizes the result.
- **Features:**
    - Parses plane blocks and extracts contours, color, and extrusion vectors.
    - Uses Shapely to detect polygon inclusion (hierarchy) and perform geometric operations.
    - Generates scanline (raster) trajectories, respecting inner voids (child planes).
    - Assigns "shutter" (open/closed) state to each trajectory segment based on its location.
    - Simplifies the trajectory by merging collinear segments with the same shutter state.
    - Outputs a text file with trajectory data and a plot showing the trajectory and plane contours.

#### Main Features

- Uses `shapely` for polygon operations and hierarchy detection.
- Handles both straight and arc edges (with configurable interpolation resolution).
- Configurable voxel diameter and overlap for scanline spacing.
- Outputs trajectory with parent plane color and constant Z value.
- Visualizes the trajectory and plane contours with shutter state annotations.

#### Example

```python
base_directory = r'C:\Users\Daniel\Desktop\Uni\Python\TFG\GetPlanes\RdA'
os.chdir(base_directory)
input_filename = r'C:\Users\Daniel\Desktop\Uni\Python\TFG\GetPlanes\RdA\testhiercode.txt'
trajectory_output = r'C:\Users\Daniel\Desktop\Uni\Python\TFG\GetPlanes\RdA\trajectorytesting.txt'
resolution = 30           # Resolution for arc interpolation
VOXEL_DIAMETER = 0.2      # Voxel diameter (for trajectory spacing)
OVERLAP = 0.5
# Run main() to process and visualize
```

---


### Script: `Planes2AB_ShutterTrajec.py`

#### Overview

- **Purpose:** Converts a trajectory file (with shutter open/closed states) into AeroBasic code for Aerotech A3200, enabling laser control with shutter modulation along the path.
- **Features:**
    - Parses trajectory segments with explicit shutter states.
    - Extracts color and Z-value from the trajectory file header.
    - Maps color index to laser speed.
    - Generates AeroBasic code with correct shutter open/close commands.
    - Computes global origin and applies safety margins.
    - Outputs a ready-to-use AeroBasic script.

#### Main Features

- Uses `numpy` for coordinate calculations.
- Handles trajectory files with lines like:  
  `De (x1, y1) a (x2, y2): shutter open/closed`
- Automatically sets initial position and coordinate offsets.
- Supports configurable Z and speed via file header or defaults.

#### Example

```python
directory = r'C:\Users\Daniel\Desktop\Uni\Python\TFG\GetPlanes\RdA'
os.chdir(directory)
# Ensure 'trajectory.txt' exists with header:
# Color extraído del Plano 1: 6
# Constante Z: 0.0
# De (x1, y1) a (x2, y2): shutter open/closed
# ...
# Then run:
python Planes2AB_ShutterTrajec.py
```

---

## Script: `time_estimate.py`

### Overview

- **Purpose:** Estimates the total execution time of an AeroBasic code file by parsing movement commands and dwell (pause) instructions.
- **Features:**
    - Reads AeroBasic files and extracts all `LINEAR` motion commands and their associated speeds.
    - Detects and sums up all `dwell` (pause) commands.
    - Calculates the total distance traveled and divides by the corresponding speed for each segment.
    - Outputs the total estimated time in seconds and minutes.

### Main Features

- Uses Python standard libraries: `re`, `math`, `os`, and `sys`.
- Handles changes in speed (`$SPEED`) and ensures correct speed is used for each segment.
- Reports if insufficient data is present for estimation.

### Example

```python
directory = r"C:\Users\Daniel\Desktop\Uni\Python\TFG\GetPlanes\PlanoXZ"
os.chdir(directory)
filename = "PlanoXZ_Spiralv2_CAD2AB (3).txt"
estimate_time(filename)
```
--- 
