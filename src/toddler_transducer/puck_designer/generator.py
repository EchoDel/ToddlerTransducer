import math
import os
import sys
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np
import trimesh
from trimesh.creation import extrude_polygon
import freetype
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union


FONT_PATH = Path("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf")
DEFAULT_BASE_DIAMETER = 50
DEFAULT_BASE_THICKNESS = 3
DEFAULT_HOLE_DIAMETER = 25
DEFAULT_HOLE_HEIGHT = 2
DEFAULT_HOLE_BOTTOM_OFFSET = 0.5


def _quadratic_bezier(p0, p1, p2, num_segments=8):
    points = []
    for i in range(num_segments + 1):
        t = i / num_segments
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
        points.append((x, y))
    return points[1:]


def _cubic_bezier(p0, p1, p2, p3, num_segments=10):
    points = []
    for i in range(num_segments + 1):
        t = i / num_segments
        x = (1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * p1[0] + 3 * (1 - t) * t ** 2 * p2[0] + t ** 3 * p3[0]
        y = (1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * p1[1] + 3 * (1 - t) * t ** 2 * p2[1] + t ** 3 * p3[1]
        points.append((x, y))
    return points[1:]


def _glyph_to_polygon(face, char):
    face.load_char(char, freetype.FT_LOAD_DEFAULT | freetype.FT_LOAD_NO_BITMAP)
    outline = face.glyph.outline

    if not outline.points:
        return None

    raw_contours = []
    current_contour = []

    def move_to(v, ctx):
        if current_contour and len(current_contour) >= 3:
            raw_contours.append(current_contour[:])
        current_contour.clear()
        current_contour.append((float(v.x), float(v.y)))

    def line_to(v, ctx):
        current_contour.append((float(v.x), float(v.y)))

    def conic_to(v1, v2, ctx):
        p0 = current_contour[-1]
        p1 = (float(v1.x), float(v1.y))
        p2 = (float(v2.x), float(v2.y))
        current_contour.extend(_quadratic_bezier(p0, p1, p2))

    def cubic_to(v1, v2, v3, ctx):
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
        poly = Polygon(contour)
        if poly.is_valid and poly.area > 0.1:
            polygons.append(poly)

    if not polygons:
        return None

    outer = max(polygons, key=lambda p: abs(p.area))
    holes = [p for p in polygons if p is not outer and abs(p.area) < abs(outer.area)]

    result = Polygon(outer.exterior.coords, [hole.exterior.coords for hole in holes])
    if result.is_valid:
        return result
    return outer


def _polygon_to_mesh(polygon, height, scale=1.0 / 64.0):
    if polygon is None or polygon.is_empty:
        return None

    scaled = polygon
    if scale != 1.0:
        scaled = Polygon(
            [(x * scale, y * scale) for x, y in polygon.exterior.coords],
            [[(x * scale, y * scale) for x, y in hole.coords] for hole in polygon.interiors]
        )

    path = trimesh.path.Path2D(scaled)
    mesh = path.extrude(height)
    return mesh


def create_text_mesh(text, font_path=FONT_PATH, font_size=48, height=5):
    if not text:
        return None

    face = freetype.Face(str(font_path))
    face.set_char_size(font_size << 6)

    char_polygons = []
    x_offset = 0.0

    for char in text:
        polygon = _glyph_to_polygon(face, char)
        if polygon is not None:
            scale = 1.0 / 64.0
            translated = Polygon(
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

    polygons = [merged] if isinstance(merged, Polygon) else [p for p in merged.geoms if isinstance(p, Polygon)]
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


def create_base(diameter=DEFAULT_BASE_DIAMETER, thickness=DEFAULT_BASE_THICKNESS,
                hole_diameter=DEFAULT_HOLE_DIAMETER,
                hole_height=DEFAULT_HOLE_HEIGHT,
                hole_bottom_offset=DEFAULT_HOLE_BOTTOM_OFFSET, segments=64):
    outer_radius = diameter / 2

    base = trimesh.creation.cylinder(radius=outer_radius, height=thickness, sections=segments)

    hole_radius = min(hole_diameter / 2, outer_radius - 0.5)
    cavity_height = max(0, hole_height)
    cavity_bottom = max(0, hole_bottom_offset)
    # clamp so cavity fits within the base
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


def add_shape(base_mesh, shape_type, params=None):
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


def _create_heart_mesh(size, height, num_points=64):
    t = np.linspace(0, 2 * math.pi, num_points)
    x = size * (16 * np.sin(t) ** 3)
    y = size * (13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t))
    scale = size / 17
    x = x * scale
    y = y * scale

    polygon = Polygon([(x[i], y[i]) for i in range(num_points)])
    mesh = extrude_polygon(polygon, height=height)
    return mesh


def _create_star_mesh(size, height, num_points=5):
    outer_r = size
    inner_r = size * 0.4
    angles = []
    for i in range(num_points * 2):
        angle = i * math.pi / num_points - math.pi / 2
        r = outer_r if i % 2 == 0 else inner_r
        angles.append((r * math.cos(angle), r * math.sin(angle)))

    polygon = Polygon(angles)
    mesh = extrude_polygon(polygon, height=height)
    return mesh


def _combine_meshes(mesh_a, mesh_b):
    try:
        combined = mesh_a.union(mesh_b)
        return combined
    except Exception:
        return trimesh.util.concatenate([mesh_a, mesh_b])


def merge_stl(base_mesh, mesh_path, offset_x=0.0, offset_y=0.0, offset_z=0.0, rotation_z=0.0,
              flip_x=False, flip_y=False, flip_z=False, scale=1.0):
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

    if rotation_z != 0.0:
        angle = math.radians(rotation_z)
        rot = trimesh.transformations.rotation_matrix(angle, [0, 0, 1])
        uploaded.apply_transform(rot)

    uploaded.vertices -= uploaded.center_mass
    uploaded.apply_translation([offset_x, offset_y, 0])

    base_thickness = base_mesh.bounds[1][2] - base_mesh.bounds[0][2]
    uploaded.apply_translation([0, 0, base_thickness / 2 + uploaded.bounds[1][2] - uploaded.bounds[0][2] + offset_z])

    return _combine_meshes(base_mesh, uploaded)


def add_text(base_mesh, text, font_path=FONT_PATH, font_size=48, text_height=5):
    text_mesh = create_text_mesh(text, font_path, font_size, text_height)
    if text_mesh is None:
        return base_mesh

    base_thickness = base_mesh.bounds[1][2] - base_mesh.bounds[0][2]
    text_mesh.apply_translation([0, 0, base_thickness / 2 + text_height / 2])

    return _combine_meshes(base_mesh, text_mesh)


def generate_puck(base_diameter=DEFAULT_BASE_DIAMETER, base_thickness=DEFAULT_BASE_THICKNESS,
                  hole_diameter=DEFAULT_HOLE_DIAMETER,
                  hole_height=DEFAULT_HOLE_HEIGHT,
                  hole_bottom_offset=DEFAULT_HOLE_BOTTOM_OFFSET, top_type="none",
                  top_params=None, text_content="", font_size=48, text_height=5,
                  uploaded_stl_path=None, ai_image_path=None,
                        ai_offset_x=0.0, ai_offset_y=0.0, ai_offset_z=0.0, ai_rotation_z=0.0,
                  ai_flip_x=False, ai_flip_y=False, ai_flip_z=False,
                  ai_scale=10.0):
    if top_params is None:
        top_params = {}

    ai_mesh_path = None
    mesh = create_base(diameter=base_diameter, thickness=base_thickness, hole_diameter=hole_diameter,
                       hole_height=hole_height,
                       hole_bottom_offset=hole_bottom_offset)

    if top_type == "text" and text_content:
        mesh = add_text(mesh, text_content, font_size=font_size, text_height=text_height)
    elif top_type == "shape":
        mesh = add_shape(mesh, top_params.get("shape_type", "cube"), top_params)
    elif top_type == "upload" and uploaded_stl_path:
        mesh = merge_stl(mesh, uploaded_stl_path)
    elif top_type == "ai_model" and ai_image_path:
        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "vendor" / "nvdiffrast_stub"))
        from .inference_instant_mesh import generate_mesh_from_image
        ai_mesh_path = generate_mesh_from_image(ai_image_path, diffusion_steps=64)
        mesh = merge_stl(mesh, str(ai_mesh_path), offset_x=ai_offset_x, offset_y=ai_offset_y,
                         offset_z=ai_offset_z, rotation_z=ai_rotation_z, flip_x=ai_flip_x,
                         flip_y=ai_flip_y, flip_z=ai_flip_z, scale=ai_scale)

    return mesh, ai_mesh_path


def export_stl(mesh, filepath):
    mesh.export(str(filepath), file_type="stl")


def export_3mf(mesh, filepath):
    mesh.export(str(filepath), file_type="3mf")


def generate_and_export(base_diameter=DEFAULT_BASE_DIAMETER, base_thickness=DEFAULT_BASE_THICKNESS,
                        hole_diameter=DEFAULT_HOLE_DIAMETER,
                        hole_height=DEFAULT_HOLE_HEIGHT,
                        hole_bottom_offset=DEFAULT_HOLE_BOTTOM_OFFSET, top_type="none",
                        top_params=None, text_content="", font_size=48, text_height=5,
                        uploaded_stl_path=None, ai_image_path=None,
                  ai_offset_x=0.0, ai_offset_y=0.0, ai_offset_z=0.0, ai_rotation_z=0.0,
                        ai_flip_x=False, ai_flip_y=False, ai_flip_z=False,
                        ai_scale=10.0, output_dir=None):
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix="puck_designer_"))

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    mesh, ai_mesh_path = generate_puck(
        base_diameter=base_diameter,
        base_thickness=base_thickness,
        hole_diameter=hole_diameter,
        hole_height=hole_height,
        hole_bottom_offset=hole_bottom_offset,
        top_type=top_type,
        top_params=top_params,
        text_content=text_content,
        font_size=font_size,
        text_height=text_height,
        uploaded_stl_path=uploaded_stl_path,
        ai_image_path=ai_image_path,
        ai_offset_x=ai_offset_x,
        ai_offset_y=ai_offset_y,
        ai_offset_z=ai_offset_z,
        ai_rotation_z=ai_rotation_z,
        ai_flip_x=ai_flip_x,
        ai_flip_y=ai_flip_y,
        ai_flip_z=ai_flip_z,
        ai_scale=ai_scale,
    )

    stl_path = output_dir / "puck.stl"
    _3mf_path = output_dir / "puck.3mf"
    ai_stl_path = None

    export_stl(mesh, stl_path)
    export_3mf(mesh, _3mf_path)

    if top_type == "ai_model" and ai_mesh_path:
        ai_stl_path = output_dir / "ai_model.stl"
        ai_mesh = trimesh.load(str(ai_mesh_path), force="mesh")
        export_stl(ai_mesh, ai_stl_path)

    return mesh, stl_path, _3mf_path, ai_stl_path
