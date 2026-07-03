import tempfile
import uuid
from pathlib import Path

import trimesh

from flask import (
    Flask, render_template, request, jsonify, send_file, session
)

from . import generator

_ai_mesh_cache: dict[str, str] = {}

puck_designer_app = Flask(__name__)
puck_designer_app.config["SECRET_KEY"] = "puck-designer-secret-change-in-production"
puck_designer_app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

UPLOAD_DIR = Path(tempfile.mkdtemp(prefix="puck_uploads_"))
OUTPUT_DIR = Path(tempfile.mkdtemp(prefix="puck_outputs_"))


@puck_designer_app.route("/")
def index():
    """Render the main puck designer page.

    Returns:
        Rendered HTML template.
    """
    return render_template("designer.html")


@puck_designer_app.route("/api/generate", methods=["POST"])
def api_generate():
    """Generate a puck mesh and return download URLs for the output files.

    Expects a JSON body with puck parameters.  Returns STL and 3MF download
    URLs, plus bounds and optionally an AI-model-only download URL.

    Returns:
        JSON response with 'stl_url', '3mf_url', 'bounds', and optionally
        'ai_stl_url'.  Returns 400 on missing data and 500 on error.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400

    base_diameter = float(data.get("base_diameter", generator.DEFAULT_BASE_DIAMETER))
    base_thickness = float(data.get("base_thickness", generator.DEFAULT_BASE_THICKNESS))
    hole_diameter = float(data.get("hole_diameter", generator.DEFAULT_HOLE_DIAMETER))
    hole_height = float(data.get("hole_height", generator.DEFAULT_HOLE_HEIGHT))
    hole_bottom_offset = float(data.get("hole_bottom_offset", generator.DEFAULT_HOLE_BOTTOM_OFFSET))
    top_type = data.get("top_type", "none")
    text_content = data.get("text_content", "")
    font_size = int(data.get("font_size", 48))
    text_height = float(data.get("text_height", 5))
    shape_type = data.get("shape_type", "cube")
    shape_params = data.get("shape_params", {})
    ai_image_path = data.get("ai_image_path")
    base_fillet = float(data.get("base_fillet", 2.0))
    ai_offset_x = float(data.get("ai_offset_x", 0))
    ai_offset_y = float(data.get("ai_offset_y", 0))
    ai_offset_z = float(data.get("ai_offset_z", 0))
    ai_rotation_z = float(data.get("ai_rotation_z", 0))
    ai_flip_x = data.get("ai_flip_x", False)
    ai_flip_y = data.get("ai_flip_y", False)
    ai_flip_z = data.get("ai_flip_z", False)
    ai_scale = float(data.get("ai_scale", 10.0))

    shape_params["shape_type"] = shape_type

    job_dir = Path(tempfile.mkdtemp(prefix="puck_job_"))

    try:
        result = generator.generate_and_export(
            base_diameter=base_diameter,
            base_thickness=base_thickness,
            hole_diameter=hole_diameter,
            hole_height=hole_height,
            hole_bottom_offset=hole_bottom_offset,
            top_type=top_type,
            top_params=shape_params,
            text_content=text_content,
            font_size=font_size,
            text_height=text_height,
            base_fillet=base_fillet,
            ai_image_path=ai_image_path,
            ai_offset_x=ai_offset_x,
            ai_offset_y=ai_offset_y,
            ai_offset_z=ai_offset_z,
            ai_rotation_z=ai_rotation_z,
            ai_flip_x=ai_flip_x,
            ai_flip_y=ai_flip_y,
            ai_flip_z=ai_flip_z,
            ai_scale=ai_scale,
            output_dir=job_dir,
        )
        mesh, stl_path, _3mf_path, ai_stl_path = result

        session_id = str(hash(str(job_dir)))
        session["last_job_dir"] = str(job_dir)

        resp = {
            "stl_url": f"/api/download/{job_dir.name}/puck.stl",
            "3mf_url": f"/api/download/{job_dir.name}/puck.3mf",
            "bounds": {
                "min": mesh.bounds[0].tolist(),
                "max": mesh.bounds[1].tolist(),
            },
        }
        if ai_stl_path:
            resp["ai_stl_url"] = f"/api/download/{job_dir.name}/ai_model.stl"
        return jsonify(resp)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@puck_designer_app.route("/api/generate_ai_mesh", methods=["POST"])
def api_generate_ai_mesh():
    """Generate only the AI mesh (no merging or export) and cache it.

    Expects JSON with ``ai_image_path``.  The raw mesh is saved to a temp
    directory, its path is cached in ``_ai_mesh_cache``, and a download URL
    for the raw mesh is returned so the frontend can load it for preview.

    Returns:
        JSON with ``mesh_id``, ``ai_stl_url``, and ``bounds``.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400

    ai_image_path = data.get("ai_image_path")
    if not ai_image_path:
        return jsonify({"error": "No ai_image_path provided"}), 400

    from .inference_instant_mesh import generate_mesh_from_image

    ai_mesh_path = generate_mesh_from_image(ai_image_path, diffusion_steps=64)
    mesh_id = str(uuid.uuid4())
    _ai_mesh_cache[mesh_id] = str(ai_mesh_path)

    # Export raw mesh to a temp dir so the frontend can download it for preview
    output_dir = Path(tempfile.mkdtemp(prefix="puck_ai_"))
    raw_mesh = trimesh.load(str(ai_mesh_path), force="mesh")
    raw_mesh.export(str(output_dir / "ai_model.stl"), file_type="stl")

    return jsonify({
        "mesh_id": mesh_id,
        "ai_stl_url": f"/api/download/{output_dir.name}/ai_model.stl",
        "bounds": {
            "min": raw_mesh.bounds[0].tolist(),
            "max": raw_mesh.bounds[1].tolist(),
        },
    })


@puck_designer_app.route("/api/export_puck", methods=["POST"])
def api_export_puck():
    """Generate a puck with AI transforms applied and return the file.

    Uses a previously cached AI mesh (by ``mesh_id``) so the AI model is not
    regenerated.  The caller specifies the desired format (``format``:
    ``"stl"`` or ``"3mf"``).

    Returns:
        The puck file as an attachment download.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400

    mesh_id = data.get("mesh_id")
    if not mesh_id or mesh_id not in _ai_mesh_cache:
        return jsonify({"error": "AI mesh not found"}), 400

    fmt = data.get("format", "stl")
    if fmt not in ("stl", "3mf"):
        return jsonify({"error": f"Unsupported format: {fmt}"}), 400

    ai_mesh_path = _ai_mesh_cache[mesh_id]

    base_diameter = float(data.get("base_diameter", generator.DEFAULT_BASE_DIAMETER))
    base_thickness = float(data.get("base_thickness", generator.DEFAULT_BASE_THICKNESS))
    hole_diameter = float(data.get("hole_diameter", generator.DEFAULT_HOLE_DIAMETER))
    hole_height = float(data.get("hole_height", generator.DEFAULT_HOLE_HEIGHT))
    hole_bottom_offset = float(data.get("hole_bottom_offset", generator.DEFAULT_HOLE_BOTTOM_OFFSET))
    base_fillet = float(data.get("base_fillet", 2.0))
    ai_offset_x = float(data.get("ai_offset_x", 0))
    ai_offset_y = float(data.get("ai_offset_y", 0))
    ai_offset_z = float(data.get("ai_offset_z", 0))
    ai_rotation_z = float(data.get("ai_rotation_z", 0))
    ai_flip_x = data.get("ai_flip_x", False)
    ai_flip_y = data.get("ai_flip_y", False)
    ai_flip_z = data.get("ai_flip_z", False)
    ai_scale = float(data.get("ai_scale", 10.0))

    job_dir = Path(tempfile.mkdtemp(prefix="puck_export_"))

    try:
        result = generator.generate_and_export(
            base_diameter=base_diameter,
            base_thickness=base_thickness,
            hole_diameter=hole_diameter,
            hole_height=hole_height,
            hole_bottom_offset=hole_bottom_offset,
            top_type="ai_model",
            base_fillet=base_fillet,
            ai_pregen_mesh_path=ai_mesh_path,
            ai_offset_x=ai_offset_x,
            ai_offset_y=ai_offset_y,
            ai_offset_z=ai_offset_z,
            ai_rotation_z=ai_rotation_z,
            ai_flip_x=ai_flip_x,
            ai_flip_y=ai_flip_y,
            ai_flip_z=ai_flip_z,
            ai_scale=ai_scale,
            output_dir=job_dir,
        )
        mesh, stl_path, _3mf_path, ai_stl_path = result

        file_path = stl_path if fmt == "stl" else _3mf_path
        mimetype = "model/stl" if fmt == "stl" else "application/vnd.ms-package.3dmanufacturing-3dmodel+xml"
        return send_file(str(file_path), as_attachment=True, download_name=f"puck.{fmt}", mimetype=mimetype)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@puck_designer_app.route("/api/download/<job_id>/<filename>")
def api_download(job_id: str, filename: str):
    """Serve a generated file for download.

    Args:
        job_id: Directory name of the job output.
        filename: Name of the file to serve.

    Returns:
        The file as an attachment, or JSON 404 if not found.
    """
    job_dir = Path(tempfile.gettempdir()) / job_id
    file_path = job_dir / filename
    if not file_path.exists():
        return jsonify({"error": "File not found"}), 404
    return send_file(str(file_path), as_attachment=True, download_name=filename)


@puck_designer_app.route("/api/upload_stl", methods=["POST"])
def api_upload_stl():
    """Upload a 3D mesh file (STL/3MF/OBJ) for use as a top feature.

    Expects a multipart/form-data upload with field name 'stl_file'.

    Returns:
        JSON with 'upload_path' on success, or error with appropriate status.
    """
    if "stl_file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["stl_file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    suffix = Path(file.filename).suffix
    if suffix.lower() not in (".stl", ".stla", ".stlb", ".3mf", ".obj"):
        return jsonify({"error": f"Unsupported format: {suffix}"}), 400

    temp_path = UPLOAD_DIR / file.filename
    file.save(str(temp_path))

    return jsonify({"upload_path": str(temp_path)})


@puck_designer_app.route("/api/upload_image", methods=["POST"])
def api_upload_image():
    """Upload an image file for AI model generation.

    Accepts PNG, JPG, JPEG, WebP, and BMP via multipart/form-data with
    field name 'image_file'.

    Returns:
        JSON with 'upload_path' on success, or error with appropriate status.
    """
    if "image_file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["image_file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    suffix = Path(file.filename).suffix
    if suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
        return jsonify({"error": f"Unsupported format: {suffix}"}), 400

    temp_path = UPLOAD_DIR / file.filename
    file.save(str(temp_path))

    return jsonify({"upload_path": str(temp_path)})


@puck_designer_app.route("/api/preview_mesh", methods=["POST"])
def api_preview_mesh():
    """Generate a preview mesh (non-AI types) and return vertices and faces.

    For AI models a 400 error is returned because the generation is too slow
    for real-time preview.

    Returns:
        JSON with 'vertices', 'faces', and 'bounds', or error with status.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400

    if data.get("top_type") == "ai_model":
        return jsonify({"error": "Preview not available for AI-generated models"}), 400

    base_diameter = float(data.get("base_diameter", generator.DEFAULT_BASE_DIAMETER))
    base_thickness = float(data.get("base_thickness", generator.DEFAULT_BASE_THICKNESS))
    hole_diameter = float(data.get("hole_diameter", generator.DEFAULT_HOLE_DIAMETER))
    hole_height = float(data.get("hole_height", generator.DEFAULT_HOLE_HEIGHT))
    hole_bottom_offset = float(data.get("hole_bottom_offset", generator.DEFAULT_HOLE_BOTTOM_OFFSET))
    top_type = data.get("top_type", "none")
    text_content = data.get("text_content", "")
    font_size = int(data.get("font_size", 48))
    text_height = float(data.get("text_height", 5))
    shape_type = data.get("shape_type", "cube")
    shape_params = data.get("shape_params", {})
    shape_params["shape_type"] = shape_type

    try:
        mesh = generator.generate_puck(
            base_diameter=base_diameter,
            base_thickness=base_thickness,
            hole_diameter=hole_diameter,
            hole_height=hole_height,
            hole_bottom_offset=hole_bottom_offset,
            top_type=top_type,
            top_params=shape_params,
            text_content=text_content,
            font_size=font_size,
            text_height=text_height,
        )

        verts = mesh.vertices.tolist()
        faces = mesh.faces.tolist()

        return jsonify({
            "vertices": verts,
            "faces": faces,
            "bounds": {
                "min": mesh.bounds[0].tolist(),
                "max": mesh.bounds[1].tolist(),
            },
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
