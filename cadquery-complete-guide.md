# CadQuery: Complete Reference Guide for LLMs

## Table of Contents
1. [Introduction and Overview](#introduction-and-overview)
2. [Installation and Setup](#installation-and-setup)
3. [Core Architecture and Concepts](#core-architecture-and-concepts)
4. [API Structure and Layers](#api-structure-and-layers)
5. [Topological Concepts (BREP)](#topological-concepts-brep)
6. [Workplane Class](#workplane-class)
7. [2D Operations](#2d-operations)
8. [3D Operations](#3d-operations)
9. [Sketch System](#sketch-system)
10. [Selectors](#selectors)
11. [Assembly System](#assembly-system)
12. [Import and Export](#import-and-export)
13. [Vector, Location, and Transformations](#vector-location-and-transformations)
14. [Shape Classes and Operations](#shape-classes-and-operations)
15. [OCP Bindings](#ocp-bindings)
16. [Extending CadQuery](#extending-cadquery)
17. [Common Patterns and Best Practices](#common-patterns-and-best-practices)
18. [Debugging and Development](#debugging-and-development)
19. [GUI Tools](#gui-tools)
20. [Community and Resources](#community-and-resources)

---

## Introduction and Overview

### What is CadQuery?

CadQuery is an intuitive, easy-to-use Python library for building parametric 3D CAD models. It was designed to address several key goals:

- Build models with scripts that are as close as possible to how you'd describe the object to a human, using Python
- Create parametric models that can be very easily customized by end users
- Output high quality CAD formats like STEP, AMF, and 3MF in addition to traditional STL
- Provide a non-proprietary, plain text model format that can be edited and executed with only a web browser

**Source**: [1][10][16]

### Key Features

- Build 3D models with scripts that are as close as possible to how you would describe the object to a human
- Create parametric models that can be very easily customized by end users
- Output high quality (loss-less) CAD formats like STEP and DXF in addition to STL, VRML, AMF and 3MF
- Provide a non-proprietary, plain text model format
- Offer advanced modeling capabilities such as fillets, curvilinear extrudes, parametric curves and lofts
- Build nested assemblies out of individual parts and other assemblies

**Source**: [1][10]

### History and Architecture

The original version of CadQuery was built on the FreeCAD API. CadQuery 2.0+ is based directly on a Python wrapper of the OpenCASCADE Technology (OCCT) kernel called OCP (OpenCASCADE Python bindings). This gives greater control and flexibility at the expense of some simplicity. The OCCT kernel uses Boundary Representation (BREP) for objects.

**Source**: [1][10][55]

### CadQuery vs OpenSCAD

CadQuery is often compared to OpenSCAD. Key advantages of CadQuery:

1. **Standard programming language**: Scripts use Python, benefiting from the associated infrastructure including standard libraries and IDEs
2. **More powerful CAD kernel**: OpenCascade (OCCT) is more powerful than CGAL used by OpenSCAD. Features supported natively by OCCT include NURBS, splines, surface sewing, STL repair, STEP import/export, and other complex operations
3. **STEP import/export**: Ability to begin with a STEP model created in a CAD package and add parametric features. OpenSCAD uses STL which is a lossy format
4. **Less code**: CadQuery scripts require less code to create most objects because it's possible to locate features based on the position of other features, workplanes, vertices, etc.
5. **Better performance**: CadQuery scripts can build STL, STEP, AMF and 3MF faster than OpenSCAD

**Source**: [1][10][26]

### Design Philosophy

CadQuery is **design-intent focused**. The idea is to have Python scripts read more like a human description of an object's form, as opposed to a bunch of algorithms constructing an object from boolean operations relative to the global coordinate system. CadQuery uses a **relative association model** where things are defined relative to other things, preserving design intent like a human would when creating a drawing.

**Source**: [118]

---

## Installation and Setup

### Installation via Conda (Recommended)

Conda/mamba is the better supported installation method.

```bash
# Install Conda package manager first (see Miniforge for minimal installer)
# Create a new environment
conda create -n cadquery

# Activate the new environment
conda activate cadquery

# Install the latest released version (mamba is faster than conda)
mamba install -c conda-forge cadquery

# Or install the dev version to get the latest changes
mamba install -c conda-forge -c cadquery cadquery=master
```

**Source**: [1][5]

### Installation via Pip

CadQuery has complex dependencies including OCP (OpenCASCADE bindings). OCP is distributed as binary wheels for Linux, MacOS and Windows. Limitations:
- Only Python 3.9 through 3.12 are currently supported
- Some older Linux distributions (e.g., Ubuntu 18.04) are not supported

```bash
# Upgrade pip first
python3 -m pip install --upgrade pip

# Install CadQuery
pip install cadquery

# Install from git repository (latest changes, may have breaking changes)
pip install git+https://github.com/CadQuery/cadquery.git

# For IPython/Jupyter support
pip install cadquery[ipython]

# For development
pip install cadquery[dev]
```

**Source**: [1][5]

### Python Version Support

- Python versions: 3.9 through 3.12 supported
- Python 3.x is required (Python 2.x is NOT supported in older versions)

**Source**: [1][13]

### Dependencies

Core dependencies include:
- **OCP**: Python bindings to OpenCASCADE Technology (OCCT) kernel
- **cadquery-ocp**: The OpenCASCADE wrapper (available on conda-forge and PyPI)
- Various other Python libraries specified in setup.py

**Source**: [1][19][83]

---

## Core Architecture and Concepts

### 3D BREP Topology Concepts

CadQuery is based on the OpenCascade kernel, which uses **Boundary Representations (BREP)** for objects. This means objects are defined by their enclosing surfaces.

**Fundamental constructs** (working up the hierarchy):

1. **Vertex**: A single point in space
2. **Edge**: A connection between two or more vertices along a particular path (called a curve)
3. **Wire**: A collection of edges that are connected together
4. **Face**: A set of edges or wires that enclose a surface
5. **Shell**: A collection of faces that are connected together along some of their edges
6. **Solid**: A shell that has a closed interior
7. **Compound**: A collection of solids

**Source**: [55][86]

### Underlying Geometry

In the CAD kernel, there is another set of geometrical constructs:
- An arc-shaped edge holds a reference to an underlying curve that is a full circle
- Each linear edge holds the equation for a line
- CadQuery shields you from these constructs in most cases

**Source**: [55]

---

## API Structure and Layers

CadQuery is composed of 4 different API layers, implemented on top of each other:

### 1. The Fluent API

The **Fluent API** is what you work with when first starting CadQuery. The `Workplane` class and all its methods define the Fluent API.

**Example**:
```python
part = cq.Workplane("XY").box(1, 2, 3).faces(">Z").vertices().circle(0.5).cutThruAll()
```

The `Workplane` is your part object, and its methods are operations that affect your part. Often you start with an empty `Workplane`, then add features by calling methods.

**Code style**: Typically uses method chaining:
```python
part = (
    cq.Workplane("XY")
    .box(1, 2, 3)
    .faces(">Z")
    .vertices()
    .circle(0.5)
    .cutThruAll()
)
```

Or broken down for debugging:
```python
part = cq.Workplane("XY")
part = part.box(1, 2, 3)
part = part.faces(">Z")
part = part.vertices()
part = part.circle(0.5)
part = part.cutThruAll()
```

**Source**: [55][86]

### 2. The Direct API

The **Direct API** is called by the Fluent API under the hood. The 9 topological classes and their methods compose the Direct API:
- `Vertex`
- `Edge`
- `Wire`
- `Face`
- `Shell`
- `Solid`
- `CompSolid`
- `Compound`
- `Shape` (base class)

These classes wrap the equivalent OpenCASCADE Technology (OCCT) classes. You can create geometry from the bottom up with full control.

**Example**:
```python
circle_wire = Wire.makeCircle(10, Vector(0, 0, 0), Vector(0, 0, 1))
circular_face = Face.makeFromWires(circle_wire, [])
```

All topological classes are shapes. The `Shape` class is the most abstract topological class.

**Source**: [55][85]

### 3. The Geometry API

Provides classes for geometric operations:
- `Vector`: 3D vectors
- `Matrix`: 4x4 transformation matrices
- `Plane`: 2D coordinate systems in space
- `Location`: Locations and transformations in 3D space

**Source**: [55]

### 4. The OCCT API

The **OCCT API** is the lowest level of CadQuery. The Direct API is built upon the OCCT API, where the OCCT API in CadQuery is available through **OCP** (Python bindings of the OCCT C++ libraries).

Working with the OCCT API gives maximum flexibility and control but is very verbose and difficult to use.

**Importing OCCT classes**:
```python
from OCP.thePackageName import theClassName

# Example:
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
```

The package name is often written as a prefix in the class name itself.

**Source**: [55][85]

### Going Between API Layers

#### Fluent API ↔ Direct API

**Fluent → Direct**:
```python
# Get last object on stack
box = cq.Workplane().box(10, 5, 5).val()
print(type(box))  # <class 'cadquery.occ_impl.shapes.Solid'>

# Get all objects
boxes = cq.Workplane().box(10, 5, 5).vals()

# Get context solid
part = cq.Workplane().box(10,5,5).circle(3).findSolid()
# Returns either a Solid or Compound object
```

**Direct → Fluent**:
```python
# Pass topological object as base object
solid_box = Solid.makeBox(10, 10, 10)
part = cq.Workplane(obj=solid_box)
part = part.faces(">Z").circle(1).extrude(10)

# Add topological object to call chain
circle_wire = Wire.makeCircle(1, Vector(0, 0, 0), Vector(0, 0, 1))
box = cq.Workplane().box(10, 10, 10).newObject([circle_wire])
box = box.toPending().cutThruAll()
```

**Source**: [55]

#### Direct API ↔ OCCT API

**Direct → OCCT**: Every Direct API object stores its OCCT equivalent in its `wrapped` attribute:
```python
box = Solid.makeBox(10,5,5)
print(type(box))  # <class 'cadquery.occ_impl.shapes.Solid'>

box = Solid.makeBox(10,5,5).wrapped
print(type(box))  # <class 'OCP.TopoDS.TopoDS_Solid'>
```

**OCCT → Direct**: Pass OCCT object as parameter:
```python
occt_box = BRepPrimAPI_MakeBox(5,5,5).Solid()
direct_api_box = Solid(occt_box)
```

**Source**: [55][85]

---

## Topological Concepts (BREP)

### Shape Hierarchy

All topological objects in CadQuery inherit from the `Shape` class:

```
Shape (base)
├── Vertex
├── Edge
├── Wire
├── Face
├── Shell
├── Solid
├── CompSolid
└── Compound
```

**Source**: [22][55]

### Vertex

A **Vertex** represents a single point in space.

**Source**: [22][55]

### Edge

An **Edge** is a trimmed curve that represents the border of a face. Edges can be:
- Linear
- Arcs
- Bezier curves
- Splines

**Key methods**:
- `Edge.makeLine(v1, v2)`: Create a line between two points
- `Edge.makeCircle(radius, pnt, dir)`: Make a circular edge
- `Edge.makeEllipse(x_radius, y_radius, pnt, dir)`: Make an elliptical edge
- `Edge.makeBezier(points)`: Create a cubic Bézier curve
- `Edge.makeSpline(listOfVector, tangents, periodic, parameters, scale, tol)`: Interpolate a spline
- `Edge.makeSplineApprox(listOfVector, tol, smoothing, minDeg, maxDeg)`: Approximate a spline
- `Edge.makeThreePointArc(v1, v2, v3)`: Make arc through three points
- `Edge.makeTangentArc(v1, v2, v3)`: Make tangent arc
- `Edge.arcCenter()`: Center of underlying circle/ellipse
- `Edge.trim(u0, u1)`: Trim edge in parametric space
- `Edge.close()`: Close an edge

**Source**: [22]

### Wire

A **Wire** is a series of connected, ordered edges that typically bounds a face.

**Key methods**:
- `Wire.makeCircle(radius, pnt, dir)`: Make circular wire
- `Wire.makePolygon(listOfVertices)`: Make polygon wire
- `Wire.assembleEdges(listOfEdges)`: Assemble edges into wire
- `Wire.fillet2D(radius, vertices)`: Apply 2D fillet
- `Wire.chamfer2D(d, vertices)`: Apply 2D chamfer
- `Wire.offset2D(d)`: Offset wire in 2D

**Source**: [22]

### Face

A **Face** is a bounded surface that represents part of the boundary of a solid.

**Key methods**:
- `Face.makeFromWires(outerWire, innerWires)`: Make planar face from wires
- `Face.makeNSidedSurface(edges, constraints, ...)`: N-sided surface
- `Face.makeRuledSurface(edgeOrWire1, edgeOrWire2)`: Ruled surface between two edges/wires
- `Face.makeSplineApprox(points, tol, smoothing, minDeg, maxDeg)`: Approximate spline surface
- `Face.normalAt(u, v)` or `Face.normalAt(locationVector)`: Compute normal vector
- `Face.positionAt(u, v)`: Position at u,v parameters
- `Face.paramAt(pt)`: Compute (u,v) pair closest to point
- `Face.thicken(thickness)`: Return thickened face
- `Face.fillet2D(radius, vertices)`: Apply 2D fillet
- `Face.chamfer2D(d, vertices)`: Apply 2D chamfer
- `Face.addHole(*inner)`: Add holes to face
- `Face.trim(...)`: Trim face in various ways
- `Face.toArcs(tolerance)`: Approximate with arcs

**Source**: [22]

### Shell

A **Shell** is the outer boundary of a surface, a collection of faces connected along edges.

**Source**: [22]

### Solid

A **Solid** is a single solid object with closed interior.

**Key methods**:
- `Solid.makeBox(length, width, height)`: Create box
- `Solid.makeCone(radius1, radius2, height)`: Create cone
- `Solid.makeCylinder(radius, height)`: Create cylinder
- `Solid.makeSphere(radius)`: Create sphere
- `Solid.makeTorus(radius1, radius2)`: Create torus
- `Solid.makeWedge(dx, dy, dz, xmin, xmax, ymin, ymax, zmin, zmax)`: Create wedge
- `Solid.makeLoft(listOfWires, ruled)`: Loft through wires
- `Solid.extrudeLinear(face, vector)`: Extrude face linearly
- `Solid.revolve(face, angleDegrees, axisStart, axisEnd)`: Revolve face
- `Solid.sweep(wire, path)`: Sweep wire along path

**Boolean operations**:
- `fuse(*toFuse, glue, tol)`: Union
- `cut(*toCut, tol)`: Difference
- `intersect(*toIntersect, tol)`: Intersection

**Modification operations**:
- `fillet(radius, edgeList)`: Fillet edges
- `chamfer(length, length2, edgeList)`: Chamfer edges
- `shell(faceList, thickness, tolerance)`: Shell faces

**Source**: [22]

### Compound

A **Compound** is a collection of disconnected solids.

**Key methods**:
- `Compound.makeCompound(listOfShapes)`: Create compound
- `Compound.makeText(text, size, height, font, fontPath, kind, halign, valign, position)`: Create 3D text
- Boolean operations: `fuse()`, `cut()`, `intersect()`
- `remove(*shape)`: Remove shapes

**Source**: [22]

---

## Workplane Class

The `Workplane` class is the main class for the Fluent API. It contains:
- **objects**: Currently selected objects (list of Shapes, Vectors, or Locations)
- **ctx**: Modelling context (CQContext object)
- **plane**: The 2D coordinate system (Plane object)
- **parent**: Reference to parent Workplane in the chain

**Source**: [27][55]

### Workplane Initialization

```python
# Create workplane on named plane
wp = cq.Workplane("XY")  # or "YZ", "ZX", "XZ", "YX", "ZY"
# Named planes: front, back, left, right, top, bottom

# Create with custom plane
plane = Plane(origin=(0, 0, 10), normal=(0, 0, 1))
wp = cq.Workplane(plane)

# Create with existing object
solid = Solid.makeBox(10, 10, 10)
wp = cq.Workplane(obj=solid)
```

**Source**: [22][24][27]

### The Stack

As you work in CadQuery, each operation returns a new Workplane object with the result of that operation. Each Workplane has a list of objects and a reference to its parent.

You can always go backwards to older operations:
```python
# Get all vertices on highest face
cq.Workplane(someObject).faces(">Z").first().vertices()

# Go back to get the face
cq.Workplane(someObject).faces(">Z").first().vertices().end()
```

**Stack access methods**: Allow browsing the parent chain.

**Source**: [27]

### Chaining

All Workplane methods return another Workplane object for method chaining. Each Workplane has a `parent` attribute pointing to the Workplane that created it.

**Tagging**: You can give a Workplane object a tag and refer back to it later:
```python
part = (
    cq.Workplane()
    .box(1, 1, 1)
    .tag("base")
    .faces(">Z")
    .workplane()
    .circle(0.5)
    .extrude(1)
)

# Later reference the tag
part.faces(">>X", tag="base").workplane()
```

**Source**: [27][33]

### Named Planes

Available named planes for `Workplane()`:

| Name | xDir | yDir | zDir |
|------|------|------|------|
| XY / front | +x | +y | +z |
| YZ | +y | +z | +x |
| ZX | +z | +x | +y |
| XZ | +x | +z | -y |
| YX | +y | +x | -z |
| ZY | +z | +y | -x |
| back | -x | +y | -z |
| left | +z | +y | -x |
| right | -z | +y | +x |
| top | +x | -z | +y |
| bottom | +x | +z | -y |

**Source**: [22]

---

## 2D Operations

All 2D operations require a **Workplane** object to be created. These operations create 2D constructs that can later be used to create 3D features.

### Point Movement

```python
# Move to absolute coordinates
.center(x, y)

# Move to coordinates
.moveTo(x, y, forConstruction=False)

# Move relative to current point
.move(xDist, yDist, forConstruction=False)
```

**Source**: [24]

### Line Drawing

```python
# Line to absolute point
.lineTo(x, y, forConstruction=False)

# Line relative to current point
.line(xDist, yDist, forConstruction=False)

# Vertical line (absolute y)
.vLineTo(yCoord, forConstruction=False)

# Vertical line (relative)
.vLine(distance, forConstruction=False)

# Horizontal line (absolute x)
.hLineTo(xCoord, forConstruction=False)

# Horizontal line (relative)
.hLine(distance, forConstruction=False)

# Line at angle from current point
.polarLine(distance, angle, forConstruction=False)

# Line to polar coordinates
.polarLineTo(distance, angle, forConstruction=False)

# Polyline through points
.polyline(listOfXYTuple, forConstruction=False)
```

**Source**: [24]

### Arc Drawing

```python
# Three-point arc
.threePointArc(point1, point2, forConstruction=False)

# Arc with sagitta
.sagittaArc(endPoint, sag, forConstruction=False)

# Arc with radius
.radiusArc(endPoint, radius, forConstruction=False)

# Tangent arc
.tangentArcPoint(endpoint, forConstruction=False)

# Elliptical arc
.ellipseArc(x_radius, y_radius, ...)
```

**Source**: [24]

### Splines

```python
# Interpolated spline through points
.spline(listOfXYTuple, tangents=None, periodic=False, ...)

# Parametric curve
.parametricCurve(func, N=400, start=0, stop=1, ...)

# Parametric surface
.parametricSurface(func, N=20, ...)
```

**Source**: [24]

### 2D Shapes

```python
# Rectangle
.rect(xLen, yLen, centered=True, forConstruction=False)

# Circle
.circle(radius, forConstruction=False)

# Ellipse
.ellipse(x_radius, y_radius, rotation=0, forConstruction=False)

# Slot (rounded rectangle)
.slot2D(length, diameter, angle=0, forConstruction=False)

# Wire completion
.close(forConstruction=False)  # Close current wire
.wire(forConstruction=False)   # Connect pending edges into wire
```

**Source**: [24]

### Arrays

```python
# Rectangular array
.rarray(xSpacing, ySpacing, xCount, yCount)

# Polar array
.polarArray(radius, startAngle, angle, count)
```

**Source**: [24]

### Mirroring

```python
# Mirror around y-axis
.mirrorY()

# Mirror around x-axis
.mirrorX()
```

**Source**: [24]

### 2D Offset

```python
# Create 2D offset wire
.offset2D(d, kind='arc', forConstruction=False)
```

**Source**: [24]

### Placing Sketches

```python
# Place sketches at current locations
.placeSketch(*sketches)
```

**Source**: [24]

---

## 3D Operations

### 3D Operations Requiring 2D Workplane

#### Holes

```python
# Simple hole
.hole(diameter, depth=None, clean=True)

# Counterbored hole
.cboreHole(diameter, cboreDiameter, cboreDepth, clean=True)

# Countersunk hole
.cskHole(diameter, cskDiameter, cskAngle=82, clean=True)
```

**Source**: [24]

#### Extrusion

```python
# Extrude until distance or face
.extrude(until, combine=True, clean=True, both=False, taper=0)

# Cut through all
.cutThruAll(clean=True, taper=0)

# Cut blind (to depth)
.cutBlind(until, clean=True, both=False, taper=0)
```

**Source**: [24][92]

#### Revolve

```python
# Revolve around axis
.revolve(angleDegrees=360, axisStart=None, axisEnd=None, combine=True, clean=True)
```

**Source**: [24][92]

#### Loft

```python
# Loft through wires
.loft(ruled=False, combine=True, clean=True)
```

**Source**: [24][92]

#### Sweep

```python
# Sweep along path
.sweep(path, multisection=False, isFrenet=False, combine=True, clean=True, transition='right')
```

**Source**: [24][92]

#### Twist Extrude

```python
# Extrude with twist
.twistExtrude(distance, angleDegrees)
```

**Source**: [24]

#### Primitives

```python
# Box
.box(length, width, height, centered=(True, True, True), combine=True, clean=True)

# Sphere
.sphere(radius, direct=(0, 0, 1), angle1=-90, angle2=90, angle3=360, centered=(True, True, True), combine=True, clean=True)

# Cylinder
.cylinder(height, radius, direct=(0, 0, 1), angle=360, centered=(True, True, True), combine=True, clean=True)

# Wedge
.wedge(dx, dy, dz, xmin, zmin, xmax, zmax, centered=(True, True, True), combine=True, clean=True)
```

**Source**: [24]

#### Text

```python
# 3D text
.text(txt, fontsize, distance, cut=True, combine=False, clean=True, font='Arial', fontPath=None, kind='regular', halign='center', valign='center')
```

**Source**: [24]

### 3D Operations Not Requiring 2D Workplane

#### Boolean Operations

```python
# Union
.union(toUnion=None, clean=True, glue=False, tol=None)

# Combine all
.combine(clean=True, glue=False, tol=None)

# Intersect
.intersect(toIntersect, clean=True, tol=None)

# Cut/Subtract
.cut(toCut, clean=True, tol=None)
```

**Tips**:
- Boolean operations are relatively slow
- For union with no intersections, use `glue=True` for significant speed boost (up to 90%)
- Avoid boolean operations in loops if possible
- Can union multiple solids at once by first combining them into a compound

**Source**: [24][92][99]

#### Shell

```python
# Shell faces to create hollow
.shell(thickness, kind='intersection')
```

**Source**: [24]

#### Fillet and Chamfer

```python
# Fillet selected edges
.fillet(radius)

# Chamfer selected edges
.chamfer(length, length2=None)
```

**Important notes**:
- Boolean operations frequently fail if coplanar faces are involved
- Filleting and chamfering can fail if edges are too complex or constraints conflict
- The chamfer needs to be slightly smaller than adjacent fillets
- Order of operations matters - switching fillet and chamfer order may work or fail differently

**Source**: [24][52][53][54]

#### Split

```python
# Split solid
.split(keepTop=False, keepBottom=False)
```

**Source**: [24]

#### Transformations

```python
# Rotate
.rotate(axisStartPoint, axisEndPoint, angleDegrees)
.rotateAboutCenter(axisEndPoint, angleDegrees)

# Translate
.translate(vec)

# Mirror
.mirror(mirrorPlane='XY', basePointVector=(0, 0, 0))
```

**Source**: [24]

---

## Sketch System

The **Sketch** class provides 2D sketching capabilities with constraints (added in CadQuery 2.1). It brings CadQuery more in line with traditional CAD packages.

**Source**: [40][126]

### Sketch Initialization

```python
# Initialize sketch
s = cq.Sketch()

# From DXF file
s = cq.Sketch().importDXF(filename, tol=1e-6, exclude=[], include=[], ...)

# Within workplane
result = (
    cq.Workplane()
    .box(5, 5, 1)
    .faces(">Z")
    .sketch()  # Start sketch mode
    .circle(2)
    .finalize()  # End sketch mode
    .extrude(0.5)
)
```

**Source**: [24][40]

### Face-Based Sketching

The main approach for constructing sketches is based on constructing faces and combining them using boolean operations.

#### Basic Shapes

```python
# Rectangle
.rect(w, h, angle=0, mode='a', tag=None)

# Circle
.circle(r, mode='a', tag=None)

# Ellipse
.ellipse(a1, a2, angle=0, mode='a', tag=None)

# Trapezoid
.trapezoid(w, h, a1, a2=None, angle=0, mode='a', tag=None)

# Slot
.slot(w, h, angle=0, mode='a', tag=None)

# Regular polygon
.regularPolygon(r, n, angle=0, mode='a', tag=None)

# Polygon from points
.polygon(pts, angle=0, mode='a', tag=None)

# Face from wire/edges
.face(b, angle=0, mode='a', tag=None, ignore_selection=False)
```

**Modes**:
- `'a'` or `'fuse'`: Add/union (default)
- `'s'` or `'cut'`: Subtract
- `'i'` or `'intersect'`: Intersection
- `'c'` or `'construction'`: Construction geometry (guides)

**Source**: [24][40]

#### Arrays

```python
# Rectangular array
.rarray(xs, ys, nx, ny)

# Polar array
.push(locs, tag=None)  # Set locations

# Distribute along edges
.distribute(n, start=0, stop=1, rotate=True)

# Apply callback on entities
.each(callback, mode='a', tag=None, clean=True)

# Convex hull
.hull(mode='a', tag=None)
```

**Source**: [24][40]

#### Modifications

```python
# Offset
.offset(d, mode='a', tag=None)

# Fillet
.fillet(d)

# Chamfer
.chamfer(d)

# Clean internal wires
.clean()
```

**Source**: [24][40]

### Edge-Based Sketching

Construct sketches by placing individual edges, then assemble into faces.

```python
# Segment
.segment(p1, p2, tag=None, forConstruction=False)

# Arc
.arc(p1, p2, p3, tag=None, forConstruction=False)

# Spline
.spline(pts, tangents=[], tag=None, forConstruction=False)

# Close sketch
.close(tag=None)

# Assemble edges into faces
.assemble(mode='a', tag=None)
```

**Source**: [24][40]

### Constraints

CadQuery supports constraint-based sketching (similar to traditional CAD). After defining edges, add constraints and solve.

```python
# Add constraint
.constrain(tag1, tag2, kind, param=None)
# Or
.constrain(id1, s1, id2, s2, kind, param=None)

# Solve constraints
.solve()
```

**Constraint types**:
- `'Fixed'`: Fix entity in place
- `'FixedPoint'`: Fix point
- `'FixedAxis'`: Fix axis
- `'FixedRotation'`: Fix rotation
- `'Point'`: Two points coincident or at distance
- `'Axis'`: Two axes aligned
- `'Plane'`: Combination of Axis and Point
- `'Coincident'`: Points/endpoints coincident
- `'Angle'`: Angle between entities
- `'PointInPlane'`: Point lies in plane
- `'PointOnLine'`: Point lies on line

**Example**:
```python
result = (
    cq.Sketch()
    .segment((0, 0), (0, 3.0), "s1")
    .arc((0.0, 3.0), (1.5, 1.5), (0.0, 0.0), "a1")
    .constrain("s1", "Fixed", None)
    .constrain("s1", "a1", "Coincident", None)
    .constrain("a1", "s1", "Coincident", None)
    .constrain("s1", "a1", "Angle", 45)
    .solve()
    .assemble()
)
```

**Source**: [24][40][124][128]

### Selection and Tagging

```python
# Tag current selection
.tag(tag)

# Select based on tags
.select(*tags)

# Reset selection
.reset()

# Delete selected
.delete()

# Select faces/edges/vertices
.faces(s=None, tag=None)
.edges(s=None, tag=None)
.vertices(s=None, tag=None)
```

**Source**: [24][40]

### Sketch Integration

```python
# Reset and copies
.reset()  # Reset current selection
.copy()   # Create partial copy
.located(loc)  # Copy with new location
.moved()  # Copy with moved faces

# Finalize sketch in workplane
.finalize()  # Return to parent workplane
```

**Source**: [24][40]

---

## Selectors

Selectors allow you to select one or more features to define new features. They are the equivalent of your hand and mouse in a conventional CAD system.

### String Selectors

CadQuery provides convenient string shortcuts for common selectors.

#### Direction Operators

**Parallel to axis** (`|`):
```python
.edges("|Z")  # Edges parallel to Z axis
.faces("|X")  # Faces with normal parallel to X axis
```

**Aligned with axis** (`+` or `-`):
```python
.faces("+Z")  # Faces with normal in +Z direction
.edges("-X")  # Edges in -X direction
```

**Perpendicular to axis** (`#`):
```python
.edges("#Z")  # Edges perpendicular to Z axis
```

**Source**: [23][25][59]

#### Distance Operators

**Farthest in direction** (`>`):
```python
.faces(">Z")   # Face farthest in +Z direction
.faces(">Y[1]")  # 2nd farthest in +Y direction
.edges(">>Y[-2]")  # 2nd farthest edge in Y direction
```

**Closest in direction** (`<`):
```python
.faces("<Z")   # Face farthest in -Z direction (closest from bottom)
.edges("<<Y[0]")  # 1st closest edge in Y direction
```

**Source**: [23][25][34]

#### Type Selectors

```python
.edges("%Line")     # Linear edges
.edges("%Circle")   # Circular edges
.edges("%Ellipse")  # Elliptical edges
.faces("%Plane")    # Planar faces
.faces("%Cylinder") # Cylindrical faces
```

**Source**: [23][25]

#### User-Defined Directions

Use tuples for custom directions:
```python
.edges(">(-1, 1, 0)")  # Edges in custom direction
```

**Source**: [25]

### Combining Selectors

Selectors can be combined using logical operators:

```python
# AND
.edges("|Z and >Y")

# OR
.faces(">Z or <Z")

# NOT
.edges("not(<X or >X or <Y or >Y)")

# EXCEPT (set difference)
.faces(">Z except <X")

# Complex expression
result = (
    cq.Workplane("XY")
    .box(2, 2, 2)
    .faces(">Z")
    .shell(-0.2)
    .faces(">Z")
    .edges("not(<X or >X or <Y or >Y)")
    .chamfer(0.1)
)
```

**Source**: [23][25]

### Selector Classes

For more control, use selector classes directly:

```python
# Nearest to point
cq.NearestToPointSelector((0, 1, 0))

# Box selector
cq.BoxSelector(point0, point1, boundingbox=True)

# Direction selector
cq.DirectionSelector(vector, tolerance=0.0001)

# Parallel direction
cq.ParallelDirSelector(vector, tolerance=0.0001)

# Perpendicular direction
cq.PerpendicularDirSelector(vector, tolerance=0.0001)

# Type selector
cq.TypeSelector("Face")  # or "Edge", "Vertex", "Wire", "Solid", "Shell", "Compound"

# Direction min/max selector
cq.DirectionMinMaxSelector(vector, directionMax=True, tolerance=0.0001)

# Direction Nth selector
cq.DirectionNthSelector(vector, n, directionMax=True, tolerance=0.0001)

# Length Nth selector
cq.LengthNthSelector(n, directionMax=True, tolerance=0.0001)

# Area Nth selector
cq.AreaNthSelector(n, directionMax=True, tolerance=0.0001)

# Radius Nth selector
cq.RadiusNthSelector(n, directionMax=True, tolerance=0.0001)

# String syntax selector (used internally)
cq.StringSyntaxSelector(selectorString)
```

**Combining selector classes**:
```python
from cadquery import selectors as s

# Intersection
box.edges((s.DirectionSelector((0,0,1)) & s.DirectionSelector((0,1,0))))

# Union
box.edges(s.DirectionSelector((0,0,1)) | s.DirectionSelector((1,0,0)))

# Difference
box.edges(s.DirectionSelector((0,0,1)) - s.DirectionSelector((1,0,0)))

# Inverse
box.edges(-s.DirectionSelector((0,0,1)))
```

**Source**: [22][23][25][28]

### Custom Selectors

You can create custom selectors by subclassing `Selector`:

```python
class MySelector(cq.Selector):
    def filter(self, objectList):
        # Filter logic here
        return [obj for obj in objectList if <condition>]

# Use it
result.edges(MySelector())
```

**Source**: [23][28]

---

## Assembly System

Simple models can be combined into complex, possibly nested assemblies.

### Basic Assembly

```python
from cadquery import *

# Create parts
part1 = Workplane().box(20, 20, 10)
part2 = Workplane().box(10, 10, 20)
part3 = Workplane().box(10, 10, 30)

# Manual placement
assy = (
    Assembly(part1, loc=Location(Vector(-10, 0, 5)))
    .add(
        part2,
        loc=Location(Vector(15, -5, 5)),
        color=Color(0, 0, 1, 0.5)
    )
    .add(
        part3,
        loc=Location(Vector(-5, -5, 20)),
        color=Color("red")
    )
)
```

**Note**: Locations of children parts are defined relative to their parents.

**Source**: [42][43][55]

### Assembly with Constraints

For fully parametric assemblies, use constraints instead of explicit locations:

```python
# Create parts with tags
part1 = Workplane().box(20, 20, 10)
part2 = Workplane().box(10, 10, 20)
part3 = Workplane().box(10, 10, 30)

# Tag features for constraints
part1.faces(">Z").edges("<X").vertices("<Y").tag("pt1")
part1.faces(">X").edges("<Z").vertices("<Y").tag("pt2")
part3.faces("<Z").edges("<X").vertices("<Y").tag("pt1")
part2.faces("<X").edges("<Z").vertices("<Y").tag("pt2")

# Build assembly with constraints
assy = (
    Assembly(part1, name="part1")
    .add(part2, name="part2", color=Color(0, 0, 1, 0.5))
    .add(part3, name="part3", color=Color("red"))
    .constrain("part1@faces@>Z", "part3@faces@<Z", "Axis")
    .constrain("part1@faces@>Z", "part2@faces@<Z", "Axis")
    .constrain("part1@faces@>Y", "part3@faces@<Y", "Axis")
    .constrain("part1@faces@>Y", "part2@faces@<Y", "Axis")
    .constrain("part1?pt1", "part3?pt1", "Point")
    .constrain("part1?pt2", "part2?pt2", "Point")
    .solve()
)
```

**Constraint syntax**: `"<name>@<type>@<selector>"` or `"<name>?<tag>"`

**Source**: [42][43][55]

### Constraint Types

- **Axis**: Two normal vectors are anti-coincident or at specified angle. For planar faces, wires, and edges.
- **Point**: Two points are coincident or separated by specified distance. For all entities (uses center of mass for lines/faces/solids, vertex position for vertices).
- **Plane**: Combination of Axis and Point constraints.
- **FixedPoint**: Fix a point in space
- **FixedAxis**: Fix an axis orientation
- **FixedRotation**: Fix rotation
- **PointInPlane**: Point lies in plane
- **PointOnLine**: Point lies on line

**Source**: [22][42][55]

### Assembly Methods

```python
# Add sub-assembly or part
.add(obj, loc=None, name=None, color=None, metadata=None)

# Add constraint
.constrain(q1, q2, kind, param=None)
# or
.constrain(q1, kind, param=None)
# or
.constrain(id1, s1, id2, s2, kind, param=None)

# Solve constraints
.solve(verbosity=0)

# Remove part
.remove(name)

# Export/save assembly
.save(path, exportType=None, mode='default', tolerance=0.1, angularTolerance=0.1, **kwargs)
.export(path, exportType=None, mode='default', tolerance=0.1, angularTolerance=0.1, **kwargs)

# Convert to compound
.toCompound()

# Iterate over assembly
.__iter__(loc=None, name=None, color=None)

# Traverse bottom-up
.traverse()
```

**Export types**: 'STEP', 'XML', 'GLTF', 'VTKJS', 'VRML', 'STL'

**Source**: [22][42][43][46]

### Assembly Solver Performance

The assembly solver can be slow with many components. The solver is constraint-based using numerical methods. For better performance:
- Minimize number of constraints
- Structure constraints in a tree (A-B, B-C) rather than fully connected graph
- Consider manual placement for complex assemblies

**Source**: [94][95]

---

## Import and Export

### Import

#### STEP Import

```python
# Import STEP file
from cadquery import importers

result = importers.importStep("filename.step")

# Use in workplane
wp = cq.Workplane(obj=result)
```

**Source**: [38][46]

#### DXF Import

```python
# Import DXF in sketch
sketch = cq.Sketch().importDXF(
    filename,
    tol=1e-6,
    exclude=[],
    include=[],
    tol=1e-6
)

# Import DXF in workplane
wp = cq.Workplane().importDXF(
    filename,
    tol=1e-6,
    exclude=[],
    include=[],
    tol=1e-6
)
```

**Source**: [24][46]

#### STL Import

STL import is not well supported due to STL being a mesh-based, lossy format. BREP systems like OCCT are not mesh-based, making conversion difficult.

**Source**: [44]

### Export

#### Generic Export

```python
# Export to file
cq.exporters.export(shape, "filename.ext")

# Supported formats determined by extension:
# .step, .stp - STEP
# .stl - STL
# .amf - AMF
# .svg - SVG
# .dxf - DXF
# .vrml, .vml - VRML
# .3mf - 3MF
```

**Source**: [24][46]

#### STEP Export

```python
from cadquery import exporters

# Export shape
exporters.exportShape(
    shape,
    "STEP",
    "filename.step",
    mode='default',  # or 'fused'
    **kwargs
)

# With assembly
assy.save("assembly.step", exportType="STEP")
```

**Mode options**:
- `'default'`: Standard export
- `'fused'`: Fuse shapes before export

**Source**: [38][46][48]

#### STL Export

```python
from cadquery import exporters

# Export to STL
exporters.exportShape(
    shape,
    "STL",
    "filename.stl",
    tolerance=0.1,
    angularTolerance=0.1,
    ascii=False  # Binary by default
)
```

**Source**: [46]

#### SVG Export

```python
# To SVG string
svg_text = result.toSvg(opts=None)

# Export SVG file
result.exportSvg("filename.svg")
```

**Source**: [24]

#### DXF Export

```python
from cadquery import exporters

# Create DXF from objects
dxf = exporters.dxf.exportDXF(
    workplane,
    tolerance=0.1
)
dxf.saveas("filename.dxf")
```

**Source**: [24][46]

### Color Handling in Exports

STEP exports support color information when exporting assemblies. Individual shapes can be assigned colors using the Assembly system.

```python
assy.add(part, name="part1", color=Color("red"))
assy.add(part2, color=Color(0, 0, 1, 0.5))  # RGBA
```

**Source**: [42][48]

---

## Vector, Location, and Transformations

### Vector Class

The `Vector` class represents a 3D vector or point in space.

```python
# Create vector
v1 = Vector(1, 2, 3)
v2 = Vector((1, 2, 3))

# Vector operations
v3 = v1 + v2        # Addition
v3 = v1 - v2        # Subtraction
v3 = v1 * 2         # Scalar multiplication
v3 = v1.cross(v2)   # Cross product
dot = v1.dot(v2)    # Dot product

# Properties
length = v1.Length  # Magnitude
v_norm = v1.normalized()  # Unit vector

# Convert to tuple
tuple_v = v1.toTuple()
```

**Source**: [22][84]

### Location Class

The `Location` class represents a location/transformation in 3D space (position and orientation).

```python
# Translation only
loc1 = Location(Vector(10, 0, 0))
loc1 = Location((10, 0, 0))

# Translation with rotation (axis-angle)
loc2 = Location(
    Vector(10, 0, 0),      # translation
    Vector(0, 0, 1),        # axis
    45                      # angle in degrees
)

# Translation with Euler angles
loc3 = Location(
    Vector(10, 0, 0),       # translation
    (45, 30, 60)            # rx, ry, rz in degrees
)

# From plane
plane = Plane(origin=(0, 0, 10), normal=(0, 0, 1))
loc4 = Location(plane)

# From transformation matrix
from OCP.gp import gp_Trsf
trsf = gp_Trsf()
loc5 = Location(trsf)

# Coordinate specification
loc6 = Location(x=10, y=0, z=0, rx=0, ry=0, rz=45)

# Convert to tuple
translation, rotation = loc.toTuple()  # ((tx,ty,tz), (rx,ry,rz))
```

**Source**: [22]

### Matrix Class

The `Matrix` class represents a 4x4 transformation matrix.

```python
# Create matrix
from OCP.gp import gp_Trsf
trsf = gp_Trsf()
matrix = Matrix(trsf)

# From nested list
matrix = Matrix([
    [m11, m12, m13, m14],
    [m21, m22, m23, m24],
    [m31, m32, m33, m34]
])

# Access elements (0-indexed)
value = matrix[row, col]

# Convert to list
list_matrix = matrix.transposed_list()
```

**Source**: [22]

### Plane Class

The `Plane` class represents a 2D coordinate system in space (origin, x-direction, normal).

```python
# Create plane
plane = Plane(
    origin=(0, 0, 10),
    xDir=(1, 0, 0),
    normal=(0, 0, 1)
)

# Named planes
plane = Plane.named("XY", origin=(0, 0, 5))
# Available: XY, YZ, ZX, XZ, YX, ZY, front, back, left, right, top, bottom

# Rotate plane
rotated_plane = plane.rotated(rotate=(45, 0, 0))
```

**Source**: [22]

### Transformations on Shapes

```python
# Translate
shape.translate(Vector(10, 0, 0))

# Rotate
shape.rotate(
    Vector(0, 0, 0),   # axisStartPoint
    Vector(0, 0, 1),   # axisEndPoint
    45                  # angleDegrees
)

# Mirror
shape.mirror(
    mirrorPlane="XY",
    basePointVector=(0, 0, 0)
)

# Locate (apply location)
shape.locate(Location(Vector(10, 0, 0)))

# Transform with matrix
shape.transformShape(Matrix(...))
```

**Source**: [22][24]

---

## Shape Classes and Operations

### Common Shape Methods

All shape classes inherit from the `Shape` base class and share common methods:

#### Geometric Properties

```python
# Bounding box
bbox = shape.BoundingBox()

# Center of mass
center = shape.Center()

# Area (for faces, shells, solids)
area = shape.Area()

# Volume (for solids)
volume = shape.Volume()
```

**Source**: [22]

#### Queries

```python
# Get sub-shapes
vertices = shape.Vertices()
edges = shape.Edges()
wires = shape.Wires()
faces = shape.Faces()
shells = shape.Shells()
solids = shape.Solids()
compounds = shape.Compounds()

# Check shape type
is_valid = shape.isValid()
is_closed = shape.isClosed()
shape_type = shape.ShapeType()  # Returns string: "Vertex", "Edge", etc.
```

**Source**: [22]

#### Relationships

```python
# Find ancestors (shapes containing this shape)
ancestors = edge.ancestors(solid, kind='Face')

# Find siblings (shapes sharing subshapes)
siblings = face.siblings(solid, kind='Edge', level=1)
```

**Source**: [22]

#### Transformations

```python
# Copy
new_shape = shape.copy()

# Move/locate
new_shape = shape.moved(Location(...))
new_shape = shape.locate(Location(...))

# Rotate
new_shape = shape.rotate(startPoint, endPoint, angle)

# Mirror
new_shape = shape.mirror(mirrorPlane, basePoint)

# Translate
new_shape = shape.translate(vector)
```

**Source**: [22]

### Boolean Operations Details

Boolean operations work on solids and compounds:

```python
# Union (addition)
result = solid1.fuse(solid2, solid3, glue=False, tol=None)

# Difference (subtraction)
result = solid1.cut(solid2, solid3, tol=None)

# Intersection
result = solid1.intersect(solid2, solid3, tol=None)
```

**Fuzzy boolean operations**: Use `tol` parameter for tolerance in fuzzy mode. Useful when exact boolean operations fail due to numerical precision issues.

**Performance tips**:
- Boolean operations are slow
- Use `glue=True` for union when shapes don't intersect (up to 90% faster)
- Avoid boolean operations in loops
- Can union multiple shapes at once by combining into compound first

**Source**: [22][88][99][102]

### Fillet and Chamfer Operations

```python
# Fillet solid on edges
filleted = solid.fillet(radius, edgeList)

# Chamfer solid on edges
chamfered = solid.chamfer(length, length2, edgeList)

# 2D fillet on wire
filleted_wire = wire.fillet2D(radius, vertices)

# 2D chamfer on wire
chamfered_wire = wire.chamfer2D(d, vertices)

# 2D fillet on face
filleted_face = face.fillet2D(radius, vertices)

# 2D chamfer on face
chamfered_face = face.chamfer2D(d, vertices)
```

**Important notes**:
- Fillet/chamfer operations can fail with complex geometry
- Order matters - changing order of fillet/chamfer may produce different results
- Chamfers need to be smaller than adjacent fillets
- Can fail if edges are perpendicular to filleted edges

**Source**: [22][52][53][54][56]

### Shell Operation

```python
# Shell a solid by removing faces
shelled = solid.shell(faceList, thickness, tolerance=0.0001)
```

**Source**: [22]

---

## OCP Bindings

### What is OCP?

**OCP** (OpenCASCADE Python bindings) provides Python access to the OpenCASCADE Technology (OCCT) C++ libraries. It's generated using pywrap and provides thin bindings to OCCT.

**Source**: [55][83]

### Accessing OCP

```python
# Import specific class
from OCP.PackageName import ClassName

# Example: Import BRepPrimAPI_MakeBox
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox

# Create OCCT box
occt_box = BRepPrimAPI_MakeBox(5, 5, 5).Solid()
```

**Source**: [55][85]

### Converting Between CadQuery and OCP

#### CadQuery → OCP

Every CadQuery shape object has a `wrapped` attribute containing the underlying OCCT object:

```python
# CadQuery solid
cq_box = Solid.makeBox(10, 5, 5)

# Get underlying OCCT object
occt_box = cq_box.wrapped
# Type: OCP.TopoDS.TopoDS_Solid
```

**Source**: [55][85]

#### OCP → CadQuery

Pass OCCT object as parameter to CadQuery shape class:

```python
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox

# Create OCCT object
occt_box = BRepPrimAPI_MakeBox(5, 5, 5).Solid()

# Wrap in CadQuery
cq_box = Solid(occt_box)
```

**Source**: [55][85]

### Why Use OCP?

Using OCP directly provides:
- **Maximum flexibility and control** over designs
- **Access to all OCCT functionality** not exposed by CadQuery
- **Lower-level operations** for advanced use cases

However, it's:
- **Very verbose** and difficult to use
- **Requires strong knowledge** of OCCT C++ libraries
- **Less intuitive** than CadQuery's fluent API

**When to use OCP**:
- Advanced operations not available in CadQuery
- Performance-critical code
- Accessing specific OCCT features

**Source**: [55][85]

### Learning OCP

Resources:
- Read CadQuery's direct API source code (full of OCP usage examples)
- OCCT documentation: https://dev.opencascade.org
- OCP typing stubs for better IDE support

**Source**: [55][63]

---

## Extending CadQuery

CadQuery can be extended through plugins or by using OCP directly.

### Plugin Architecture

Plugins are methods attached to the `Workplane` or `CQ` objects. Your plugin method's first parameter is `self`, providing access to base class functionality.

**Source**: [106]

### Creating a Simple Plugin

```python
import cadquery as cq
from cadquery.occ_impl.shapes import box

# Define plugin function
def makeCubes(self, length):
    """Make cubes at each point on the stack"""
    
    def _singleCube(loc):
        # loc is a location in local coordinates
        return box(length, length, length).locate(loc)
    
    # Use CQ utility to iterate over stack
    return self.eachpoint(_singleCube, True)

# Link plugin into CadQuery
cq.Workplane.makeCubes = makeCubes

# Use the plugin
result = (
    cq.Workplane("XY")
    .box(6.0, 8.0, 0.5)
    .faces(">Z")
    .rect(4.0, 4.0, forConstruction=True)
    .vertices()
    .makeCubes(1.0)
)
```

**Source**: [106]

### Functional Style Plugins

Alternative approach using special methods (avoids monkey-patching):

```python
import cadquery as cq
from cadquery.occ_impl.shapes import box

def makeCubes(length):
    """Functional style plugin"""
    
    def callback(wp):
        return wp.eachpoint(box(length, length, length), True)
    
    return callback

# Use the plugin
result = (
    cq.Workplane("XY")
    .box(6.0, 8.0, 0.5)
    .faces(">Z")
    .rect(4.0, 4.0, forConstruction=True)
    .vertices()
    .invoke(makeCubes(1.0))
    .combineSolids()
)
```

This approach is more friendly for auto-completion and static analysis tools.

**Source**: [106]

### Helper Methods for Plugins

When implementing plugins, you can call:

- **Any CadQuery or Workplane methods** from inside your extension
- `cadquery.Workplane._makeWireAtPoints()`: Invoke factory function for all points on stack
- `cadquery.Workplane.newObject()`: Return new Workplane with provided stack and parent set to current object

**Source**: [106]

### Using OCP in Plugins

The easiest way to extend CadQuery is to use OCP scripting directly inside your plugin:

```python
def myCustomOperation(self, param):
    from OCP.BRepFilletAPI import BRepFilletAPI_MakeFillet
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_EDGE
    
    # Get underlying OCCT shape
    occt_shape = self.val().wrapped
    
    # Use OCCT operations
    fillet = BRepFilletAPI_MakeFillet(occt_shape)
    
    # Add edges to fillet
    explorer = TopExp_Explorer(occt_shape, TopAbs_EDGE)
    while explorer.More():
        edge = explorer.Current()
        fillet.Add(param, edge)
        explorer.Next()
    
    # Build result
    result_shape = fillet.Shape()
    
    # Wrap back in CadQuery
    from cadquery.occ_impl.shapes import Shape
    return self.newObject([Shape(result_shape)])

# Attach to Workplane
cq.Workplane.myCustomOperation = myCustomOperation
```

**Source**: [106]

### Example Core Code Written as Plugins

Some core CadQuery code is intentionally written like plugins for reference. Good examples to study:
- `Workplane.cboreHole()`
- `Workplane.slot2D()`
- Other methods in the CadQuery source

**Source**: [106]

---

## Common Patterns and Best Practices

### Design Patterns

#### 1. Fluent Chaining

Build complex models through method chaining:

```python
result = (
    cq.Workplane("XY")
    .box(10, 10, 5)
    .faces(">Z")
    .workplane()
    .hole(2)
    .faces(">Z")
    .workplane()
    .rect(8, 8, forConstruction=True)
    .vertices()
    .cboreHole(1.5, 3, 2)
    .edges("|Z")
    .fillet(0.5)
)
```

**Source**: [10][118]

#### 2. Relative Positioning

Define features relative to other features, not global coordinates:

```python
result = (
    cq.Workplane("XY")
    .box(10, 10, 5)
    .faces(">Z")        # Select top face
    .workplane()        # New workplane on that face
    .hole(2)            # Hole relative to face center
)
```

**Source**: [118]

#### 3. Parametric Design

Use variables to make designs easily customizable:

```python
# Parameters
height = 60.0
width = 80.0
thickness = 10.0
diameter = 22.0
padding = 12.0

# Model
result = (
    cq.Workplane("XY")
    .box(height, width, thickness)
    .faces(">Z")
    .workplane()
    .hole(diameter)
    .faces(">Z")
    .workplane()
    .rect(height - padding, width - padding, forConstruction=True)
    .vertices()
    .cboreHole(2.4, 4.4, 2.1)
)
```

**Source**: [10][26]

#### 4. Tagging for Complex Chains

Use tags to refer back to specific points in the chain:

```python
result = (
    cq.Workplane("XY")
    .box(10, 10, 10)
    .tag("base")
    .faces(">Z")
    .workplane()
    .circle(3)
    .extrude(5)
    .faces(">>X", tag="base")  # Reference base
    .workplane()
    .hole(2)
)
```

**Source**: [27][33]

### Performance Optimization

#### 1. Boolean Operations

- **Avoid in loops**: Boolean operations are slow
- **Use glue for non-intersecting unions**: `glue=True` can provide up to 90% speedup
- **Batch operations**: Union multiple solids at once using compounds

```python
# Bad: Multiple separate unions
result = solid1
for s in [solid2, solid3, solid4]:
    result = result.union(s)

# Better: Union all at once
result = solid1.union(solid2, solid3, solid4)

# Best: Use glue if no intersections
result = solid1.union(solid2, solid3, solid4, glue=True)
```

**Source**: [99]

#### 2. Avoid Unnecessary Operations

- Skip intermediate boolean operations when possible
- Use construction geometry (`forConstruction=True`) for reference features
- Minimize face/edge selections in hot paths

**Source**: [99]

#### 3. Parallelization Limitations

CadQuery/OCP does not release the Python GIL (Global Interpreter Lock). Some operations (especially boolean operations) are parallelized internally by OCCT, but Python-level parallelization is limited.

**Source**: [76][120]

### Debugging Strategies

#### 1. Break Up Chains

Instead of:
```python
result = cq.Workplane("XY").box(10, 10, 10).faces(">Z").hole(2)
```

Use:
```python
result = cq.Workplane("XY")
result = result.box(10, 10, 10)
result = result.faces(">Z")
result = result.hole(2)
```

This allows inspection at each step.

**Source**: [55]

#### 2. Use show_object Liberally

In CQ-editor:
```python
show_object(intermediate_result, name="step1")
show_object(final_result, name="final")
```

**Source**: [67]

#### 3. Inspect the Stack

CQ-editor provides a stack inspector to visualize objects at each step.

**Source**: [110][129]

#### 4. Use debug()

In CQ-editor:
```python
debug(some_shape)  # Shows semi-transparent red
```

**Source**: [67][127]

### Common Pitfalls

#### 1. Coplanar Faces in Boolean Operations

Boolean operations frequently fail if coplanar faces are involved. Solution: Make cutting objects slightly larger/smaller to avoid exact coplanarity.

**Source**: [102]

#### 2. Fillet/Chamfer Order

The order of fillet and chamfer operations matters. Switching order may work or fail differently.

**Source**: [53]

#### 3. Selector Reset in Sketches

In sketches, selections must be explicitly reset with `.reset()`. Unlike Workplane, Sketch does not implement automatic history.

**Source**: [40][128]

#### 4. Multimethods and Keyword Arguments

CadQuery uses multimethods for method dispatch based on argument types. Avoid using keyword arguments for positional parameters as it can break dispatch:

```python
# Bad
sketch.arc(p1=(1, 2), p2=(2, 3), p3=(3, 4))

# Good
sketch.arc((1, 2), (2, 3), (3, 4))
```

**Source**: [55]

---

## Debugging and Development

### CQ-Editor Debugging Tools

CQ-editor provides several tools for debugging:

#### 1. Graphical Debugger

Step through script line by line and watch model changes.

**Source**: [110]

#### 2. Stack Inspector

Visual inspection of current workplane and selected items, providing insight into model evolution.

**Source**: [110][129]

#### 3. Console Logging

Use `log()` instead of `print()`:

```python
log("Debug message")  # Outputs to Log viewer panel
```

If started from command line, `print()` works and outputs to terminal.

**Source**: [123]

#### 4. Show Object

Display intermediate results:

```python
show_object(obj, name="name", options={'alpha': 0.5, 'color': 'red'})
```

**Source**: [67]

### Development Environment Setup

#### 1. Clone Repository

```bash
git clone https://github.com/CadQuery/cadquery.git
cd cadquery
```

**Source**: [1]

#### 2. Create Conda Development Environment

```bash
mamba env create -n cq-dev -f environment.yml
conda activate cq-dev
```

**Source**: [1]

#### 3. Install in Development Mode

```bash
pip install -e .

# For development dependencies
pip install -e .[dev]
```

**Source**: [1]

#### 4. Run Tests

```bash
pytest
```

Expected output: `======= 215 passed, 57 warnings in 13.95s =======`

**Source**: [1]

#### 5. Code Formatting

Use the project's black fork:

```bash
black .
```

**Source**: [1]

### Testing Best Practices

- Start with tests first (TDD approach)
- Add assertions checking all expected results
- Add descriptive docstrings to tests
- Split complex tests into multiple simpler tests
- Run full test suite before submitting PR

**Source**: [1]

### Contributing Guidelines

1. Consider opening an issue first to discuss changes
2. Keep PRs short and simple
3. Fork repository and create feature branch
4. Write tests before implementing
5. Add docstrings to functions/methods/classes
6. Update documentation if public API changes
7. Run pytest to ensure nothing breaks
8. Run black for code formatting
9. Push changes and open PR
10. Be prepared for constructive feedback

**Source**: [1]

---

## GUI Tools

### CQ-Editor

CQ-editor is the primary IDE for CadQuery, providing:
- **Code editor** for Python scripts
- **3D viewport** for visualization
- **Graphical debugger** to step through scripts
- **Stack inspector** for CadQuery object inspection
- **Export** to STEP, STL, and other formats directly from menu

**Source**: [1][107][110]

#### Installation

**Pre-built releases** (recommended for beginners):
- Download from: https://github.com/jmwright/CQ-editor/actions (nightly builds)
- Includes both CQ-editor and CadQuery library
- No need for Anaconda/MiniConda

**From source** (via pip):
```bash
# Create virtual environment
mkvirtualenv cqeditor
workon cqeditor

# Clone repository
git clone https://github.com/CadQuery/CQ-editor

# Install (after editing setup.py to include requirements)
pip install ./

# Run
python run.py
```

**Via conda**:
```bash
conda create -n cq-editor
conda activate cq-editor
mamba install -c conda-forge -c cadquery cq-editor=master
```

**Source**: [107][109][110][113]

#### Features

- **Auto-reload**: Use your favorite editor, CQ-editor reloads automatically
- **OCCT-based**: Uses same kernel as CadQuery
- **Step-through debugging**: Watch model changes step by step
- **Object stack inspector**: Visual inspection of workplane and selections
- **Multiple exports**: STL, STEP, and more

**Source**: [110]

### Jupyter/JupyterLab

CadQuery supports Jupyter out-of-the-box:

```python
import cadquery as cq

result = cq.Workplane("XY").box(10, 10, 10)

# Visualize
display(result)
```

Install with Jupyter support:
```bash
pip install cadquery[ipython]
```

**Source**: [1][5]

### VSCode + OCP CAD Viewer

Alternative to CQ-editor:
- Better code suggestions and inline documentation
- Linting support
- More general-purpose IDE features

Requires OCP CAD Viewer extension for visualization.

**Source**: [123]

### Web-based Options

#### CadQuery Server

A web server for rendering 3D models from CadQuery code:

```python
import cadquery as cq
from cq_server.ui import ui, show_object

show_object(cq.Workplane('XY').box(1, 2, 3))
```

Provides browser-based rendering without local installation.

**Source**: [67]

---

## Community and Resources

### Official Resources

- **Documentation**: https://cadquery.readthedocs.io
- **GitHub Repository**: https://github.com/CadQuery/cadquery
- **Cheat Sheet**: https://cadquery.readthedocs.io/en/latest/_static/cadquery_cheatsheet.html

**Source**: [1][12][16]

### Community Forums

- **GitHub Discussions**: https://github.com/CadQuery/cadquery/discussions - Good for general questions
- **Google Group**: https://groups.google.com/forum/#!forum/cadquery - Help from other users
- **Discord Server**: Available but other methods preferred for newcomers

**Source**: [1][66][69]

### Learning Resources

- **Examples**: https://cadquery.readthedocs.io/en/latest/examples.html
- **CadQuery Contrib**: https://github.com/CadQuery/cadquery-contrib - Community scripts and tutorials
- **Awesome CadQuery**: https://github.com/CadQuery/awesome-cadquery - Curated list of resources

**Source**: [6][8][75]

### Related Projects

- **CQ-Kit**: Utility library extending CadQuery capabilities (https://github.com/michaelgale/cq-kit)
- **cq_warehouse**: Parametric parts collection (https://github.com/gumyr/cq_warehouse)
- **CadQuery Plugins**: https://github.com/CadQuery/cadquery-plugins
- **MAssembly**: Manual assembly system for CadQuery (https://github.com/bernhard-42/cadquery-massembly)

**Source**: [2][7][11][39]

### Video Tutorials

- Installation videos available for Linux and Windows
- Community-created tutorials on YouTube
- CadQuery Video Tutorials thread in Google Group

**Source**: [1][69][105]

### Key Community Members

Active contributors and maintainers (as of documentation):
- dcowden (original creator)
- jmwright
- adam-urbanczyk (OCCT wrapper/OCP maintainer)
- marcus7070 (core developer)

**Source**: [1][66]

### Getting Help

When asking for help:
1. Specify CadQuery version
2. Specify operating system
3. Describe how CadQuery was installed
4. Provide Python version
5. Include steps to reproduce issue
6. Provide minimum reproducible example (MRE)

**Source**: [1][68]

### Contributing

Ways to contribute without coding:
- Writing and improving documentation
- Triaging bugs
- Submitting bug reports and feature requests
- Creating tutorial videos and blog posts
- Helping other users
- Telling others about the project
- Translations and internationalization
- Improving accessibility

**Source**: [1]

### Citation

For scientific research, use the Zenodo DOI: https://doi.org/10.5281/zenodo.3955118

**Source**: [1]

### License

CadQuery is licensed under the **Apache License, version 2.0**.

**Source**: [1]

---

## Appendix: Common Issues and Solutions

### Installation Issues

**Issue**: pip install fails with dependency errors
**Solution**: Try conda/mamba installation method, or use virtual environment

**Issue**: Python version not supported
**Solution**: Use Python 3.9-3.12 (check with `python --version`)

**Source**: [1][5][68]

### Boolean Operation Failures

**Issue**: Boolean operations fail with coplanar faces
**Solution**: Make cutting object slightly larger/smaller to avoid exact coplanarity

**Issue**: Boolean operations very slow
**Solution**: Use `glue=True` for union when shapes don't intersect, avoid boolean operations in loops

**Source**: [99][102]

### Fillet/Chamfer Issues

**Issue**: Fillet fails on complex edges
**Solution**: Try reducing fillet radius, change order of operations, or split into multiple smaller fillets

**Issue**: Chamfer fails after fillet
**Solution**: Ensure chamfer is smaller than adjacent fillet, or swap operation order

**Source**: [52][53][54]

### Selector Issues

**Issue**: Selector returns no results
**Solution**: Check selector syntax, visualize intermediate results, use `show_object` to inspect

**Issue**: Selector returns wrong faces/edges
**Solution**: Understand normal directions for faces, edge directions, use numerical indexing `>Z[0]` for specific faces

**Source**: [23][25][34]

### Import/Export Issues

**Issue**: STEP import has no color
**Solution**: In FreeCAD, disable "Enable STEP Compound merge" in preferences

**Issue**: STL import doesn't work
**Solution**: STL import is not well supported in CadQuery; use STEP format instead

**Source**: [44]

### Performance Issues

**Issue**: Script very slow
**Solution**: Minimize boolean operations, use `glue=True`, avoid operations in loops, batch operations where possible

**Issue**: Parallel processing doesn't speed up
**Solution**: OCP doesn't release GIL; some operations are internally parallelized by OCCT but Python-level parallelization is limited

**Source**: [76][99][120]

---

## Index of Key Concepts

- **BREP (Boundary Representation)**: Core topology model used by OpenCASCADE
- **Fluent API**: Main CadQuery interface using method chaining
- **Direct API**: Lower-level shape manipulation using topological classes
- **OCP**: OpenCASCADE Python bindings providing access to OCCT C++ libraries
- **Workplane**: Main class for fluent API, represents 2D coordinate system in 3D space
- **Sketch**: 2D sketching with constraints (similar to traditional CAD)
- **Stack**: List of objects in current Workplane
- **Selector**: Object for filtering and selecting geometric entities
- **Assembly**: System for combining parts with constraints
- **Location**: Represents position and orientation in 3D space
- **Vector**: 3D vector or point
- **Shape**: Base class for all topological objects
- **Tags**: Named references to specific Workplanes in chain

---

## References

All information in this document was gathered from the following sources:

1. CadQuery GitHub Repository: https://github.com/CadQuery/cadquery
2. CadQuery Documentation: https://cadquery.readthedocs.io
3. CadQuery API Reference: https://cadquery.readthedocs.io/en/latest/classreference.html
4. CadQuery Examples: https://cadquery.readthedocs.io/en/latest/examples.html
5. CadQuery Installation: https://cadquery.readthedocs.io/en/latest/installation.html
6. CadQuery Intro: https://cadquery.readthedocs.io/en/latest/intro.html
7. CadQuery Primer: https://cadquery.readthedocs.io/en/latest/primer.html
8. CadQuery Selectors: https://cadquery.readthedocs.io/en/latest/selectors.html
9. CadQuery Sketch: https://cadquery.readthedocs.io/en/latest/sketch.html
10. CadQuery Workplane: https://cadquery.readthedocs.io/en/latest/workplane.html
11. CadQuery Assembly: https://cadquery.readthedocs.io/en/latest/assy.html
12. CadQuery Cheat Sheet: https://cadquery.readthedocs.io/en/latest/_static/cadquery_cheatsheet.html
13. PyPI CadQuery: https://pypi.org/project/cadquery/
14. CadQuery OCP: https://github.com/CadQuery/OCP
15. CadQuery Contrib: https://github.com/CadQuery/cadquery-contrib
16. CadQuery Plugins: https://github.com/CadQuery/cadquery-plugins
17. CQ-Editor: https://github.com/CadQuery/CQ-editor
18. CadQuery Google Group: https://groups.google.com/g/cadquery
19. CadQuery GitHub Issues: https://github.com/CadQuery/cadquery/issues
20. CadQuery GitHub Discussions: https://github.com/CadQuery/cadquery/discussions
21. Community blog posts, forum discussions, and Stack Overflow questions
22. OCCT Documentation: https://dev.opencascade.org

This guide was compiled from publicly available documentation, source code, community forums, and issue trackers as of October 2025.