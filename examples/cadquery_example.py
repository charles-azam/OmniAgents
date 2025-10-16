"""
Complex CadQuery example demonstrating various features.

This example creates a mechanical bracket with:
- Multiple primitives (box, cylinder, sphere)
- Boolean operations (union, cut)
- Edge modifications (fillet, chamfer)
- Holes and shell operations
- 2D sketching and extrusion
- Selectors for face/edge/vertex selection
- Workplane positioning
- Multiple export formats
"""

import cadquery as cq
from cadquery import exporters


def create_simple_box() -> cq.Workplane:
    """Create a simple box with fillets."""
    result = (
        cq.Workplane("XY")
        .box(50, 50, 10)
        .edges("|Z")
        .fillet(2)
    )
    return result


def create_cylinder_with_holes() -> cq.Workplane:
    """Create a cylinder with mounting holes."""
    result = (
        cq.Workplane("XY")
        .circle(20)
        .extrude(30)
        .faces(">Z")
        .workplane()
        .pushPoints([(-10, 0), (10, 0)])
        .hole(4)
        .faces(">Z")
        .chamfer(1)
    )
    return result


def create_bracket_with_operations() -> cq.Workplane:
    """Create a bracket demonstrating various operations."""

    # Main base plate
    result = (
        cq.Workplane("XY")
        .box(80, 60, 10, centered=(True, True, False))
        .edges("|Z")
        .fillet(2)
    )

    # Add four mounting posts
    result = (
        result
        .faces(">Z")
        .workplane()
        .pushPoints([(-30, -20), (30, -20), (-30, 20), (30, 20)])
        .circle(5)
        .extrude(15)
    )

    # Add mounting holes through posts
    result = (
        result
        .faces(">Z")
        .workplane()
        .pushPoints([(-30, -20), (30, -20), (-30, 20), (30, 20)])
        .hole(3.2)
    )

    # Chamfer the top of the posts
    result = (
        result
        .faces(">Z")
        .chamfer(1)
    )

    return result


def create_loft_example() -> cq.Workplane:
    """Create a lofted shape."""
    result = (
        cq.Workplane("XY")
        .rect(20, 20)
        .workplane(offset=20)
        .rect(10, 10)
        .workplane(offset=20)
        .circle(3)
        .loft()
    )
    return result


def create_revolve_example() -> cq.Workplane:
    """Create a revolved shape."""
    result = (
        cq.Workplane("XZ")
        .moveTo(0, 0)
        .lineTo(10, 0)
        .lineTo(10, 5)
        .lineTo(5, 10)
        .lineTo(0, 10)
        .close()
        .revolve(360)
    )
    return result


def create_sweep_example() -> cq.Workplane:
    """Create a swept shape along a path."""
    # Define the path
    path = (
        cq.Workplane("XY")
        .moveTo(-20, 0)
        .lineTo(-20, 10)
        .lineTo(-10, 20)
        .lineTo(0, 20)
        .lineTo(10, 10)
        .lineTo(10, 0)
    )

    # Create profile and sweep
    result = (
        cq.Workplane("YZ")
        .workplane(offset=-20)
        .circle(2)
        .sweep(path.val())
    )
    return result


def create_2d_sketching_example() -> cq.Workplane:
    """Demonstrate 2D construction methods."""
    result = (
        cq.Workplane("XY")
        # Rectangle
        .rect(30, 20)
        .extrude(5)
        # Add circle on top
        .faces(">Z")
        .workplane()
        .circle(8)
        .extrude(10)
        # Add ellipse
        .faces(">Z")
        .workplane()
        .ellipse(6, 4)
        .extrude(5)
        # Fillet edges
        .edges("|Z")
        .fillet(1)
    )
    return result


def create_boolean_operations_example() -> cq.Workplane:
    """Demonstrate boolean operations."""
    # Create main box
    box1 = cq.Workplane("XY").box(30, 30, 20)

    # Create cylinder to subtract
    cylinder = cq.Workplane("XY").circle(10).extrude(25)

    # Perform cut
    result = box1.cut(cylinder)

    # Add a sphere
    sphere = cq.Workplane("XY").sphere(8).translate((15, 0, 10))
    result = result.union(sphere)

    return result


def create_shell_example() -> cq.Workplane:
    """Create a hollow box using shell."""
    result = (
        cq.Workplane("XY")
        .box(40, 40, 30)
        .faces(">Z")
        .shell(-2)
    )
    return result


def create_polyline_example() -> cq.Workplane:
    """Create shape using polyline."""
    result = (
        cq.Workplane("XY")
        .polyline([(0, 0), (20, 0), (20, 10), (10, 15), (0, 10)])
        .close()
        .extrude(5)
        .edges("|Z")
        .fillet(1)
    )
    return result


def create_selector_examples() -> cq.Workplane:
    """Demonstrate various selectors."""
    result = (
        cq.Workplane("XY")
        .box(40, 40, 20)
    )

    # Fillet edges parallel to Z
    result = result.edges("|Z").fillet(2)

    # Add holes on top face
    result = (
        result
        .faces(">Z")
        .workplane()
        .pushPoints([(-10, -10), (10, 10)])
        .circle(3)
        .cutBlind(-5)
    )

    return result


def create_complex_bracket() -> cq.Workplane:
    """Create a complex mechanical bracket demonstrating CadQuery features."""

    # Main base
    result = (
        cq.Workplane("XY")
        .box(80, 60, 10, centered=(True, True, False))
        .edges("|Z")
        .fillet(2)
    )

    # Add vertical wall
    wall = (
        cq.Workplane("XZ")
        .workplane(offset=25)
        .rect(80, 40)
        .extrude(5)
        .edges("|Y")
        .fillet(2)
    )
    result = result.union(wall)

    # Add mounting holes in base
    result = (
        result
        .faces("<Z")
        .workplane()
        .pushPoints([(-30, 0), (30, 0)])
        .circle(4)
        .cutThruAll()
    )

    # Add slot in wall
    result = (
        result
        .faces(">Y")
        .workplane()
        .center(0, 25)
        .rect(40, 8)
        .cutBlind(-3)
    )

    # Add reinforcement ribs
    for x_pos in [-25, -10, 10, 25]:
        rib = (
            cq.Workplane("XZ")
            .workplane(offset=25)
            .moveTo(x_pos, 0)
            .lineTo(x_pos, 20)
            .lineTo(x_pos + 3, 0)
            .close()
            .extrude(5)
        )
        result = result.union(rib)

    # Chamfer top edges of wall
    result = (
        result
        .faces(">Z")
        .edges("|Y")
        .chamfer(1.5)
    )

    return result


def export_model(model: cq.Workplane, base_path: str = "output") -> None:
    """Export model to various formats."""

    # Export to STEP
    exporters.export(w=model, fname=f"{base_path}.step")
    print(f"Exported: {base_path}.step")

    # Export to STL
    exporters.export(w=model, fname=f"{base_path}.stl")
    print(f"Exported: {base_path}.stl")


if __name__ == "__main__":
    print("Creating CadQuery examples...\n")

    # Create and export various examples
    examples = [
        ("simple_box", create_simple_box),
        ("cylinder_holes", create_cylinder_with_holes),
        ("bracket_operations", create_bracket_with_operations),
        ("loft", create_loft_example),
        ("revolve", create_revolve_example),
        ("sweep", create_sweep_example),
        ("2d_sketching", create_2d_sketching_example),
        ("boolean_ops", create_boolean_operations_example),
        ("shell", create_shell_example),
        ("polyline", create_polyline_example),
        ("selectors", create_selector_examples),
        ("complex_bracket", create_complex_bracket),
    ]

    for name, func in examples:
        try:
            print(f"Creating {name}...")
            model = func()
            export_model(model=model, base_path=name)
            print(f"✓ {name} created successfully\n")
        except Exception as e:
            print(f"✗ {name} failed: {e}\n")

    print("Done!")
