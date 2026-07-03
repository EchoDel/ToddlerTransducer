import tempfile
from pathlib import Path

from flask import (
    Flask, render_template, request, jsonify, send_file, session
)

from . import generator

puck_designer_app = Flask(__name__)
puck_designer_app.config["SECRET_KEY"] = "puck-designer-secret-change-in-production"
puck_designer_app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

UPLOAD_DIR = Path(tempfile.mkdtemp(prefix="puck_uploads_"))
OUTPUT_DIR = Path(tempfile.mkdtemp(prefix="puck_outputs_"))


@puck_designer_app.route("/")
def index():
    return render_template("designer.html")


@puck_designer_app.route("/api/generate", methods=["POST"])
def api_generate():
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


@puck_designer_app.route("/api/download/<job_id>/<filename>")
def api_download(job_id, filename):
    job_dir = Path(tempfile.gettempdir()) / job_id
    file_path = job_dir / filename
    if not file_path.exists():
        return jsonify({"error": "File not found"}), 404
    return send_file(str(file_path), as_attachment=True, download_name=filename)


@puck_designer_app.route("/api/upload_stl", methods=["POST"])
def api_upload_stl():
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
