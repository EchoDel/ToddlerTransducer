import math
import tempfile
from pathlib import Path
from typing import Any, Optional

import freetype
import numpy as np
import trimesh
from shapely.geometry import Polygon as ShapelyPolygon
from shapely.ops import unary_union
from trimesh.creation import extrude_polygon

from ..config import AI_MODEL_BACKEND

FONT_PATH = Path("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf")
DEFAULT_BASE_DIAMETER = 50
DEFAULT_BASE_THICKNESS = 3
DEFAULT_HOLE_DIAMETER = 30
DEFAULT_HOLE_HEIGHT = 0.6
DEFAULT_HOLE_BOTTOM_OFFSET = 0.5


def _quadratic_bezier(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    num_segments: int = 8,
) -> list[tuple[float, float]]:
    """Sample points along a quadratic Bézier curve.

    Args:
        p0: Start point (x, y).
        p1: Control point (x, y).
        p2: End point (x, y).
        num_segments: Number of segments to sample (default 8).

    Returns:
        List of (x, y) points along the curve, excluding the start point.
    """
    points = []
    for i in range(num_segments + 1):
        t = i / num_segments
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
        points.append((x, y))
    return points[1:]


def _cubic_bezier(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    num_segments: int = 10,
) -> list[tuple[float, float]]:
    """Sample points along a cubic Bézier curve.

    Args:
        p0: Start point (x, y).
        p1: First control point (x, y).
        p2: Second control point (x, y).
        p3: End point (x, y).
        num_segments: Number of segments to sample (default 10).

    Returns:
        List of (x, y) points along the curve, excluding the start point.
    """
    points = []
    for i in range(num_segments + 1):
        t = i / num_segments
        x = (1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * p1[0] + 3 * (1 - t) * t ** 2 * p2[0] + t ** 3 * p3[0]
        y = (1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * p1[1] + 3 * (1 - t) * t ** 2 * p2[1] + t ** 3 * p3[1]
        points.append((x, y))
    return points[1:]


def _glyph_to_polygon(face: freetype.Face, char: str) -> Optional[ShapelyPolygon]:
    """Convert a single glyph from a FreeType face into a shapely Polygon.

    Handles quadratic and cubic Bézier curves via the outline decomposer.

    Args:
        face: An already-loaded FreeType face object.
        char: The character to render (only used for load_char).

    Returns:
        A Shapely Polygon representing the glyph outline, or None on failure.
    """
    face.load_char(char, freetype.FT_LOAD_DEFAULT | freetype.FT_LOAD_NO_BITMAP)
    outline = face.glyph.outline

    if not outline.points:
        return None

    raw_contours: list[list[tuple[float, float]]] = []
    current_contour: list[tuple[float, float]] = []

    def move_to(v: freetype.Vector, ctx: Any) -> None:
        if current_contour and len(current_contour) >= 3:
            raw_contours.append(current_contour[:])
        current_contour.clear()
        current_contour.append((float(v.x), float(v.y)))

    def line_to(v: freetype.Vector, ctx: Any) -> None:
        current_contour.append((float(v.x), float(v.y)))

    def conic_to(v1: freetype.Vector, v2: freetype.Vector, ctx: Any) -> None:
        p0 = current_contour[-1]
        p1 = (float(v1.x), float(v1.y))
        p2 = (float(v2.x), float(v2.y))
        current_contour.extend(_quadratic_bezier(p0, p1, p2))

    def cubic_to(v1: freetype.Vector, v2: freetype.Vector, v3: freetype.Vector, ctx: Any) -> None:
        p0 = current_contour[-1]
        p1 = (float(v1.x), float(v1.y))
        p2 = (float(v2.x), float(v2.y))
        p3 = (float(v3.x), float(v3.y))
        current_contour.extend(_cubic_bezier(p0, p1, p2, p3))

    outline.decompose(
        move_to=move_to, line_to=line_to,
        conic_to=conic_to, cubic_to=cubic_to,
    )

    if current_contour and len(current_contour) >= 3:
        raw_contours.append(current_contour[:])

    if not raw_contours:
        return None

    polygons = []
    for contour in raw_contours:
        poly = ShapelyPolygon(contour)
        if poly.is_valid and poly.area > 0.1:
            polygons.append(poly)

    if not polygons:
        return None

    outer = max(polygons, key=lambda p: abs(p.area))
    holes = [p for p in polygons if p is not outer and abs(p.area) < abs(outer.area)]

    result = ShapelyPolygon(outer.exterior.coords, [hole.exterior.coords for hole in holes])
    if result.is_valid:
        return result
    return outer


def _polygon_to_mesh(
    polygon: Optional[ShapelyPolygon],
    height: float,
    scale: float = 1.0 / 64.0,
) -> Optional[trimesh.Trimesh]:
    """Extrude a shapely Polygon into a 3D trimesh.

    Args:
        polygon: The 2D polygon to extrude, or None.
        height: Extrusion height.
        scale: Scale factor applied before extrusion (default 1/64).

    Returns:
        Trimesh of the extruded polygon, or None if polygon is empty.
    """
    if polygon is None or polygon.is_empty:
        return None

    scaled = polygon
    if scale != 1.0:
        scaled = ShapelyPolygon(
            [(x * scale, y * scale) for x, y in polygon.exterior.coords],
            [[(x * scale, y * scale) for x, y in hole.coords] for hole in polygon.interiors]
        )

    path = trimesh.path.Path2D(scaled)
    mesh = path.extrude(height)
    return mesh


def create_text_mesh(
    text: str,
    font_path: Path = FONT_PATH,
    font_size: int = 48,
    height: float = 5,
) -> Optional[trimesh.Trimesh]:
    """Create a 3D text mesh by extruding each character glyph.

    Args:
        text: The string to render.
        font_path: Path to a TrueType font file.
        font_size: Font size in FreeType units.
        height: Extrusion depth for the text.

    Returns:
        A centered 3D Trimesh of the extruded text, or None if text is empty.
    """
    if not text:
        return None

    face = freetype.Face(str(font_path))
    face.set_char_size(font_size << 6)

    char_polygons: list[ShapelyPolygon] = []
    x_offset = 0.0

    for char in text:
        polygon = _glyph_to_polygon(face, char)
        if polygon is not None:
            scale = 1.0 / 64.0
            translated = ShapelyPolygon(
                [(x * scale + x_offset, y * scale) for x, y in polygon.exterior.coords],
                [[(x * scale + x_offset, y * scale) for x, y in hole.coords] for hole in polygon.interiors]
            )
            char_polygons.append(translated)

            advance = face.glyph.advance.x
            x_offset += advance * scale
        else:
            advance = face.glyph.advance.x
            x_offset += advance * scale

    if not char_polygons:
        return None

    merged = unary_union(char_polygons)
    if merged.is_empty:
        return None

    polygons = [merged] if isinstance(merged, ShapelyPolygon) else [p for p in merged.geoms if isinstance(p, ShapelyPolygon)]
    text_mesh = trimesh.creation.extrude_polygon(polygons[0], height=height)
    for p in polygons[1:]:
        extra = trimesh.creation.extrude_polygon(p, height=height)
        text_mesh = _combine_meshes(text_mesh, extra)

    if text_mesh is not None:
        bounds = text_mesh.bounds
        center_x = (bounds[0][0] + bounds[1][0]) / 2
        center_y = (bounds[0][1] + bounds[1][1]) / 2
        text_mesh.apply_translation([-center_x, -center_y, 0])

    return text_mesh


def _filleted_cylinder_profile(
    radius: float,
    height: float,
    fillet: float,
    arc_segments: int = 8,
) -> np.ndarray:
    """Build a 2D revolve profile for a cylinder with rounded top/bottom edges.

    The profile lies in the XZ plane (X = radius, Z = height).  A fillet arc
    is placed at each outer corner so the resulting revolved mesh has smooth
    edges.

    Args:
        radius: Outer radius of the cylinder.
        height: Total height of the cylinder.
        fillet: Radius of the edge fillet.
        arc_segments: Number of segments per fillet arc (default 8).

    Returns:
        (N, 2) array of profile vertices.
    """
    profile = []
    h = height
    r = radius
    f = min(fillet, r * 0.4, h * 0.4)

    profile.append((0, -h / 2))
    profile.append((r - f, -h / 2))

    cx, cy = r - f, -h / 2 + f
    for i in range(1, arc_segments + 1):
        a = -math.pi / 2 + (math.pi / 2) * (i / arc_segments)
        profile.append((cx + f * math.cos(a), cy + f * math.sin(a)))

    profile.append((r, h / 2 - f))

    cx, cy = r - f, h / 2 - f
    for i in range(1, arc_segments + 1):
        a = 0 + (math.pi / 2) * (i / arc_segments)
        profile.append((cx + f * math.cos(a), cy + f * math.sin(a)))

    profile.append((0, h / 2))

    return np.array(profile)


def create_base(
    diameter: float = DEFAULT_BASE_DIAMETER,
    thickness: float = DEFAULT_BASE_THICKNESS,
    hole_diameter: float = DEFAULT_HOLE_DIAMETER,
    hole_height: float = DEFAULT_HOLE_HEIGHT,
    hole_bottom_offset: float = DEFAULT_HOLE_BOTTOM_OFFSET,
    segments: int = 64,
    fillet_radius: float = 2.0,
) -> trimesh.Trimesh:
    """Create the puck base — a filleted cylinder with an optional central cavity.

    The base is revolved from a filleted profile, then a cylindrical cavity
    is subtracted from the bottom.  The result is centered at the origin.

    Args:
        diameter: Outer diameter of the puck in mm (default 50).
        thickness: Overall thickness in mm (default 3).
        hole_diameter: Diameter of the bottom cavity in mm (default 25).
        hole_height: Height of the cavity in mm (default 2).
        hole_bottom_offset: Offset of the cavity bottom from the base bottom (default 0.5).
        segments: Circumferential subdivision count (default 64).
        fillet_radius: Radius of the edge fillet in mm (default 2).

    Returns:
        A watertight Trimesh of the puck base, centered at origin.
    """
    outer_radius = diameter / 2

    profile = _filleted_cylinder_profile(outer_radius, thickness, fillet_radius, arc_segments=6)
    base = trimesh.creation.revolve(profile, sections=segments)

    hole_radius = min(hole_diameter / 2, outer_radius - 0.5)
    cavity_height = max(0, hole_height)
    cavity_bottom = max(0, hole_bottom_offset)
    cavity_top = cavity_bottom + cavity_height
    if cavity_top > thickness:
        cavity_height = max(0, thickness - cavity_bottom)
        cavity_top = thickness

    if cavity_height > 0.1 and hole_radius > 0:
        bottom_z = -thickness / 2 + cavity_bottom
        cavity_center_z = bottom_z + cavity_height / 2
        cavity = trimesh.creation.cylinder(radius=hole_radius, height=cavity_height, sections=segments)
        cavity.apply_translation([0, 0, cavity_center_z])
        base = base.difference(cavity)

    center = (base.bounds[0] + base.bounds[1]) / 2
    base.vertices -= center
    return base


def add_shape(
    base_mesh: trimesh.Trimesh,
    shape_type: str,
    params: Optional[dict[str, Any]] = None,
) -> trimesh.Trimesh:
    """Add a 3D primitive (cube, sphere, cylinder, etc.) on top of the base mesh.

    The shape is placed flush with the top of the base and merged via CSG union.

    Args:
        base_mesh: The puck base Trimesh.
        shape_type: One of 'cube', 'sphere', 'cylinder', 'cone', 'torus',
                    'heart', or 'star'.
        params: Dict with keys 'size', 'radius', 'height' etc.

    Returns:
        The combined Trimesh.
    """
    if params is None:
        params = {}

    base_thickness = base_mesh.bounds[1][2] - base_mesh.bounds[0][2]

    if shape_type == "cube":
        size = params.get("size", 20)
        height = params.get("height", 10)
        mesh = trimesh.creation.box(extents=[size, size, height])
    elif shape_type == "sphere":
        radius = params.get("radius", 10)
        mesh = trimesh.creation.icosphere(subdivisions=2, radius=radius)
    elif shape_type == "cylinder":
        radius = params.get("radius", 10)
        height = params.get("height", 15)
        mesh = trimesh.creation.cylinder(radius=radius, height=height, sections=32)
    elif shape_type == "cone":
        radius = params.get("radius", 10)
        height = params.get("height", 15)
        mesh = trimesh.creation.cone(radius=radius, height=height, sections=32)
    elif shape_type == "torus":
        major_radius = params.get("size", 15) * 0.6
        minor_radius = params.get("height", 8) * 0.4
        mesh = trimesh.creation.torus(
            major_radius=major_radius,
            minor_radius=minor_radius,
        )
    elif shape_type == "heart":
        height = params.get("height", 10)
        mesh = _create_heart_mesh(params.get("size", 15), height=height)
    elif shape_type == "star":
        height = params.get("height", 10)
        mesh = _create_star_mesh(params.get("size", 15), height=height)
    else:
        return base_mesh

    mesh.vertices -= mesh.center_mass

    z_offset = base_thickness / 2 + mesh.bounds[1][2] - mesh.bounds[0][2]
    mesh.apply_translation([0, 0, z_offset - (mesh.bounds[1][2] - mesh.bounds[0][2]) / 2])

    return _combine_meshes(base_mesh, mesh)


def _create_heart_mesh(
    size: float,
    height: float,
    num_points: int = 64,
) -> trimesh.Trimesh:
    """Create a heart-shaped extruded polygon.

    Uses the parametric heart curve: x = 16 sin³ t, y = 13 cos t - 5 cos 2t - ...

    Args:
        size: Overall scale factor.
        height: Extrusion depth.
        num_points: Number of samples for the parametric curve (default 64).

    Returns:
        A Trimesh of the extruded heart.
    """
    t = np.linspace(0, 2 * math.pi, num_points)
    x = size * (16 * np.sin(t) ** 3)
    y = size * (13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t))
    scale = size / 17
    x = x * scale
    y = y * scale

    polygon = ShapelyPolygon([(x[i], y[i]) for i in range(num_points)])
    mesh = extrude_polygon(polygon, height=height)
    return mesh


def _create_star_mesh(
    size: float,
    height: float,
    num_points: int = 5,
) -> trimesh.Trimesh:
    """Create a star-shaped extruded polygon.

    Alternates between outer and inner radii to form star points.

    Args:
        size: Outer radius of the star.
        height: Extrusion depth.
        num_points: Number of star points (default 5).

    Returns:
        A Trimesh of the extruded star.
    """
    outer_r = size
    inner_r = size * 0.4
    angles = []
    for i in range(num_points * 2):
        angle = i * math.pi / num_points - math.pi / 2
        r = outer_r if i % 2 == 0 else inner_r
        angles.append((r * math.cos(angle), r * math.sin(angle)))

    polygon = ShapelyPolygon(angles)
    mesh = extrude_polygon(polygon, height=height)
    return mesh


def _combine_meshes(
    mesh_a: trimesh.Trimesh,
    mesh_b: trimesh.Trimesh,
) -> trimesh.Trimesh:
    """Combine two meshes via CSG union, falling back to concatenation.

    Args:
        mesh_a: First mesh.
        mesh_b: Second mesh.

    Returns:
        The combined Trimesh.
    """
    try:
        combined = mesh_a.union(mesh_b)
        return combined
    except Exception:
        return trimesh.util.concatenate([mesh_a, mesh_b])


def merge_stl(
    base_mesh: trimesh.Trimesh,
    mesh_path: str,
    offset_x: float = 0.0,
    offset_y: float = 0.0,
    offset_z: float = 0.0,
    rotation_x: float = 0.0,
    rotation_y: float = 0.0,
    rotation_z: float = 0.0,
    flip_x: bool = False,
    flip_y: bool = False,
    flip_z: bool = False,
    scale: float = 1.0,
) -> trimesh.Trimesh:
    """Load an external mesh, apply transforms, and merge it with the base.

    Transform order: scale → flip X/Y/Z → rotate X/Y/Z → center → XY offset →
    Z lift + offset_z → CSG union.

    Args:
        base_mesh: The puck base Trimesh.
        mesh_path: Path to the external mesh file (STL/OBJ/3MF).
        offset_x: X offset after centering.
        offset_y: Y offset after centering.
        offset_z: Additional Z offset on top of the automatic Z lift.
        rotation_x: X-axis rotation in degrees.
        rotation_y: Y-axis rotation in degrees.
        rotation_z: Z-axis rotation in degrees.
        flip_x: Mirror along X axis.
        flip_y: Mirror along Y axis.
        flip_z: Mirror along Z axis.
        scale: Uniform scale factor.

    Returns:
        The combined Trimesh.
    """
    uploaded = trimesh.load(str(mesh_path), force="mesh")
    if uploaded.is_watertight is False:
        uploaded.fix_normals()

    if scale != 1.0:
        uploaded.vertices *= scale

    if flip_x:
        uploaded.vertices[:, 0] *= -1
    if flip_y:
        uploaded.vertices[:, 1] *= -1
    if flip_z:
        uploaded.vertices[:, 2] *= -1

    if rotation_x != 0.0 or rotation_y != 0.0 or rotation_z != 0.0:
        # Frontend (Three.js) converts the mesh from Z-up to Y-up via
        # geo.rotateX(-PI/2) before applying rotations from the sliders.
        # This means slider rotations operate in Y-up space there, but the
        # backend operates in Z-up space.  Remap the rotation axes so the
        # exported result matches the preview:
        #   Frontend Y → Backend Z
        #   Frontend Z → Backend -Y
        rot = (
            trimesh.transformations.rotation_matrix(math.radians(-rotation_z), [0, 1, 0])
            @ trimesh.transformations.rotation_matrix(math.radians(rotation_y), [0, 0, 1])
            @ trimesh.transformations.rotation_matrix(math.radians(rotation_x), [1, 0, 0])
        )
        uploaded.apply_transform(rot)

    uploaded.vertices -= uploaded.center_mass
    uploaded.apply_translation([offset_x, offset_y, 0])

    base_thickness = base_mesh.bounds[1][2] - base_mesh.bounds[0][2]
    uploaded.apply_translation([0, 0, base_thickness / 2 + uploaded.bounds[1][2] + offset_z])

    return _combine_meshes(base_mesh, uploaded)


def add_text(
    base_mesh: trimesh.Trimesh,
    text: str,
    font_path: Path = FONT_PATH,
    font_size: int = 48,
    text_height: float = 5,
) -> trimesh.Trimesh:
    """Emboss text on top of the puck base.

    Args:
        base_mesh: The puck base Trimesh.
        text: String to emboss.
        font_path: Path to a TrueType font file.
        font_size: Font size in FreeType units.
        text_height: Extrusion depth of the text.

    Returns:
        The combined Trimesh.
    """
    text_mesh = create_text_mesh(text, font_path, font_size, text_height)
    if text_mesh is None:
        return base_mesh

    base_thickness = base_mesh.bounds[1][2] - base_mesh.bounds[0][2]
    text_mesh.apply_translation([0, 0, base_thickness / 2 + text_height / 2])

    return _combine_meshes(base_mesh, text_mesh)


def generate_puck(
    base_diameter: float = DEFAULT_BASE_DIAMETER,
    base_thickness: float = DEFAULT_BASE_THICKNESS,
    hole_diameter: float = DEFAULT_HOLE_DIAMETER,
    hole_height: float = DEFAULT_HOLE_HEIGHT,
    hole_bottom_offset: float = DEFAULT_HOLE_BOTTOM_OFFSET,
    base_fillet: float = 2.0,
    top_type: str = "none",
    top_params: Optional[dict[str, Any]] = None,
    text_content: str = "",
    font_size: int = 48,
    text_height: float = 5,
    uploaded_stl_path: Optional[str] = None,
    uploaded_offset_x: float = 0.0,
    uploaded_offset_y: float = 0.0,
    uploaded_offset_z: float = 0.0,
    uploaded_rotation_x: float = 0.0,
    uploaded_rotation_y: float = 0.0,
    uploaded_rotation_z: float = 0.0,
    uploaded_flip_x: bool = False,
    uploaded_flip_y: bool = False,
    uploaded_flip_z: bool = False,
    uploaded_scale: float = 1.0,
    ai_image_path: Optional[str] = None,
    ai_pregen_mesh_path: Optional[str] = None,
    ai_offset_x: float = 0.0,
    ai_offset_y: float = 0.0,
    ai_offset_z: float = 0.0,
    ai_rotation_x: float = 0.0,
    ai_rotation_y: float = 0.0,
    ai_rotation_z: float = 0.0,
    ai_flip_x: bool = False,
    ai_flip_y: bool = False,
    ai_flip_z: bool = False,
    ai_scale: float = 10.0,
) -> tuple[trimesh.Trimesh, Optional[str]]:
    """Assemble a complete puck by creating the base and adding the top feature.

    Top feature is chosen by *top_type*: 'text' embosses text, 'shape' adds a
    primitive, 'upload' merges an external mesh, 'ai_model' generates a 3D
    mesh from an image via the configured AI backend and merges the result.

    Args:
        base_diameter: Puck outer diameter in mm.
        base_thickness: Puck thickness in mm.
        hole_diameter: Bottom cavity diameter in mm.
        hole_height: Bottom cavity height in mm.
        hole_bottom_offset: Cavity bottom offset from base bottom.
        base_fillet: Edge fillet radius in mm.
        top_type: 'none', 'text', 'shape', 'upload', or 'ai_model'.
        top_params: Additional params forwarded to add_shape().
        text_content: Text to emboss (for top_type='text').
        font_size: Font size for text.
        text_height: Text extrusion depth.
        uploaded_stl_path: Path to uploaded mesh file.
        ai_image_path: Path to input image for AI model generation.
        ai_pregen_mesh_path: Path to a pre-generated AI mesh (skips generation).
        ai_offset_x: X offset for the AI model on the puck.
        ai_offset_y: Y offset for the AI model on the puck.
        ai_offset_z: Additional Z offset for the AI model.
        ai_rotation_x: X rotation for the AI model in degrees.
        ai_rotation_y: Y rotation for the AI model in degrees.
        ai_rotation_z: Z rotation for the AI model in degrees.
        ai_flip_x: Mirror AI model along X.
        ai_flip_y: Mirror AI model along Y.
        ai_flip_z: Mirror AI model along Z.
        ai_scale: Scale factor for the AI model.

    Returns:
        Tuple of (puck mesh, ai_mesh_path or None).
    """
    if top_params is None:
        top_params = {}

    ai_mesh_path: Optional[str] = None
    mesh = create_base(diameter=base_diameter, thickness=base_thickness, hole_diameter=hole_diameter,
                       hole_height=hole_height,
                       hole_bottom_offset=hole_bottom_offset,
                       fillet_radius=base_fillet)

    if top_type == "text" and text_content:
        mesh = add_text(mesh, text_content, font_size=font_size, text_height=text_height)
    elif top_type == "shape":
        mesh = add_shape(mesh, top_params.get("shape_type", "cube"), top_params)
    elif top_type == "upload" and uploaded_stl_path:
        mesh = merge_stl(mesh, uploaded_stl_path,
                         offset_x=uploaded_offset_x,
                         offset_y=-uploaded_offset_y,
                         offset_z=uploaded_offset_z,
                         rotation_x=uploaded_rotation_x,
                         rotation_y=uploaded_rotation_y,
                         rotation_z=uploaded_rotation_z,
                         flip_x=uploaded_flip_x,
                         flip_y=uploaded_flip_z,
                         flip_z=uploaded_flip_y,
                         scale=uploaded_scale)
    elif top_type == "ai_model" and (ai_image_path or ai_pregen_mesh_path):
        if ai_pregen_mesh_path:
            ai_mesh_path = ai_pregen_mesh_path
        else:
            if AI_MODEL_BACKEND == "hunyuan3d":
                from .inference_hunyuan3d import generate_mesh_from_image
            else:
                from .inference_instant_mesh import generate_mesh_from_image
            ai_mesh_path = generate_mesh_from_image(ai_image_path, diffusion_steps=64)
        mesh = merge_stl(mesh, str(ai_mesh_path), offset_x=ai_offset_x, offset_y=-ai_offset_y,
                         offset_z=ai_offset_z, rotation_x=ai_rotation_x, rotation_y=ai_rotation_y,
                         rotation_z=ai_rotation_z, flip_x=ai_flip_x,
                         flip_y=ai_flip_z, flip_z=ai_flip_y, scale=ai_scale)

    return mesh, ai_mesh_path


def export_stl(mesh: trimesh.Trimesh, filepath: Path) -> None:
    """Export a mesh to an STL file.

    Args:
        mesh: The Trimesh to export.
        filepath: Destination path for the .stl file.
    """
    mesh.export(str(filepath), file_type="stl")


def export_3mf(mesh: trimesh.Trimesh, filepath: Path) -> None:
    """Export a mesh to a 3MF file.

    Args:
        mesh: The Trimesh to export.
        filepath: Destination path for the .3mf file.
    """
    mesh.export(str(filepath), file_type="3mf")


def generate_and_export(
    base_diameter: float = DEFAULT_BASE_DIAMETER,
    base_thickness: float = DEFAULT_BASE_THICKNESS,
    hole_diameter: float = DEFAULT_HOLE_DIAMETER,
    hole_height: float = DEFAULT_HOLE_HEIGHT,
    hole_bottom_offset: float = DEFAULT_HOLE_BOTTOM_OFFSET,
    base_fillet: float = 2.0,
    top_type: str = "none",
    top_params: Optional[dict[str, Any]] = None,
    text_content: str = "",
    font_size: int = 48,
    text_height: float = 5,
    uploaded_stl_path: Optional[str] = None,
    uploaded_offset_x: float = 0.0,
    uploaded_offset_y: float = 0.0,
    uploaded_offset_z: float = 0.0,
    uploaded_rotation_x: float = 0.0,
    uploaded_rotation_y: float = 0.0,
    uploaded_rotation_z: float = 0.0,
    uploaded_flip_x: bool = False,
    uploaded_flip_y: bool = False,
    uploaded_flip_z: bool = False,
    uploaded_scale: float = 1.0,
    ai_image_path: Optional[str] = None,
    ai_pregen_mesh_path: Optional[str] = None,
    ai_offset_x: float = 0.0,
    ai_offset_y: float = 0.0,
    ai_offset_z: float = 0.0,
    ai_rotation_x: float = 0.0,
    ai_rotation_y: float = 0.0,
    ai_rotation_z: float = 0.0,
    ai_flip_x: bool = False,
    ai_flip_y: bool = False,
    ai_flip_z: bool = False,
    ai_scale: float = 10.0,
    output_dir: Optional[Path] = None,
) -> tuple[trimesh.Trimesh, Path, Path, Optional[Path]]:
    """Generate a puck and export STL + 3MF files to a directory.

    This is the top-level entry-point used by the Flask API.  It creates the
    puck, writes STL and 3MF to *output_dir*, and optionally exports the raw
    AI mesh.

    Args:
        base_diameter: Puck outer diameter in mm.
        base_thickness: Puck thickness in mm.
        hole_diameter: Bottom cavity diameter in mm.
        hole_height: Bottom cavity height in mm.
        hole_bottom_offset: Cavity bottom offset from base bottom.
        base_fillet: Edge fillet radius in mm.
        top_type: 'none', 'text', 'shape', 'upload', or 'ai_model'.
        top_params: Additional params forwarded to add_shape().
        text_content: Text to emboss (for top_type='text').
        font_size: Font size for text.
        text_height: Text extrusion depth.
        uploaded_stl_path: Path to uploaded mesh file.
        ai_image_path: Path to input image for AI model generation.
        ai_pregen_mesh_path: Path to a pre-generated AI mesh (skips generation).
        ai_offset_x: X offset for the AI model on the puck.
        ai_offset_y: Y offset for the AI model on the puck.
        ai_offset_z: Additional Z offset for the AI model.
        ai_rotation_x: X rotation for the AI model in degrees.
        ai_rotation_y: Y rotation for the AI model in degrees.
        ai_rotation_z: Z rotation for the AI model in degrees.
        ai_flip_x: Mirror AI model along X.
        ai_flip_y: Mirror AI model along Y.
        ai_flip_z: Mirror AI model along Z.
        ai_scale: Scale factor for the AI model.
        output_dir: Directory to write output files into.  A temp dir is used
                    when None.

    Returns:
        Tuple of (puck mesh, stl_path, _3mf_path, ai_stl_path).
        ai_stl_path is None when top_type != 'ai_model'.
    """
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix="puck_creator_"))

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    mesh, ai_mesh_path = generate_puck(
        base_diameter=base_diameter,
        base_thickness=base_thickness,
        hole_diameter=hole_diameter,
        hole_height=hole_height,
        hole_bottom_offset=hole_bottom_offset,
        base_fillet=base_fillet,
        top_type=top_type,
        top_params=top_params,
        text_content=text_content,
        font_size=font_size,
        text_height=text_height,
        uploaded_stl_path=uploaded_stl_path,
        uploaded_offset_x=uploaded_offset_x,
        uploaded_offset_y=uploaded_offset_y,
        uploaded_offset_z=uploaded_offset_z,
        uploaded_rotation_x=uploaded_rotation_x,
        uploaded_rotation_y=uploaded_rotation_y,
        uploaded_rotation_z=uploaded_rotation_z,
        uploaded_flip_x=uploaded_flip_x,
        uploaded_flip_y=uploaded_flip_y,
        uploaded_flip_z=uploaded_flip_z,
        uploaded_scale=uploaded_scale,
        ai_image_path=ai_image_path,
        ai_pregen_mesh_path=ai_pregen_mesh_path,
        ai_offset_x=ai_offset_x,
        ai_offset_y=ai_offset_y,
        ai_offset_z=ai_offset_z,
        ai_rotation_x=ai_rotation_x,
        ai_rotation_y=ai_rotation_y,
        ai_rotation_z=ai_rotation_z,
        ai_flip_x=ai_flip_x,
        ai_flip_y=ai_flip_y,
        ai_flip_z=ai_flip_z,
        ai_scale=ai_scale,
    )

    stl_path = output_dir / "puck.stl"
    _3mf_path = output_dir / "puck.3mf"
    ai_stl_path: Optional[Path] = None

    export_stl(mesh, stl_path)
    export_3mf(mesh, _3mf_path)

    if top_type == "ai_model" and ai_mesh_path:
        ai_stl_path = output_dir / "ai_model.stl"
        ai_mesh = trimesh.load(str(ai_mesh_path), force="mesh")
        export_stl(ai_mesh, ai_stl_path)

    return mesh, stl_path, _3mf_path, ai_stl_path
