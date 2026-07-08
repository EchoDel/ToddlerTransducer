import tempfile
from pathlib import Path
from typing import Any, Optional

import numpy as np
import torch
from hy3dgen.rembg import BackgroundRemover
from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline

BACKEND_NAME = "hunyuan3d"


def _process_input_image(
    image_path: str,
    no_rembg: bool = False,
) -> "Image.Image":
    from PIL import Image

    image = Image.open(image_path)
    if image.mode == "RGBA":
        bg = Image.new("RGBA", image.size, (255, 255, 255, 255))
        bg.paste(image, mask=image.split()[-1])
        image = bg
    image = image.convert("RGBA")
    if not no_rembg:
        remover = BackgroundRemover()
        image = remover(image)
    return image


def generate_mesh_from_image(
    image_path: str,
    output_dir: Optional[str] = None,
    diffusion_steps: int = 30,
    seed: int = 42,
    scale: float = 1.0,
    view: int = 6,
    no_rembg: bool = False,
    save_multiview: bool = True,
    multiview_resolution: int = 320,
    config_name: str = "hunyuan3d-mini",
) -> Path:
    """Generate a watertight 3D mesh from a 2D image using Hunyuan3D-2mini.

    Pipeline: optional background removal → Hunyuan3D-2mini shape generation →
    export to .obj.

    Args:
        image_path: Path to the input 2D image.
        output_dir: Directory for output files.  A temp dir is created when
                    None.
        diffusion_steps: Number of denoising steps (default 30).
        seed: Random seed for reproducibility (default 42).
        scale: No-op, kept for interface compatibility.
        view: No-op, kept for interface compatibility.
        no_rembg: Skip background removal when True (default False).
        save_multiview: No-op, kept for interface compatibility.
        multiview_resolution: No-op, kept for interface compatibility.
        config_name: No-op, kept for interface compatibility.

    Returns:
        Path to the exported .obj file.
    """
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="hunyuan3d_")
    output_dir = Path(output_dir)
    meshes_dir = output_dir / "meshes"
    meshes_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

    name = Path(image_path).stem

    print(f"Loading Hunyuan3D-2mini pipeline ...")
    pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
        "tencent/Hunyuan3D-2mini",
        subfolder="hunyuan3d-dit-v2-mini",
        use_safetensors=True,
        device=device,
    )

    print(f"Processing {name} ...")
    image = _process_input_image(image_path, no_rembg)

    print("Running shape generation ...")
    results = pipeline(
        image=image,
        num_inference_steps=diffusion_steps,
        octree_resolution=380,
        num_chunks=20000,
        generator=torch.manual_seed(seed),
        output_type="trimesh",
    )
    mesh = results[0]

    mesh_path = meshes_dir / f"{name}.obj"
    mesh.export(str(mesh_path))
    print(
        f"Mesh saved to {mesh_path} "
        f"({len(mesh.vertices)} verts, {len(mesh.faces)} faces)"
    )
    return mesh_path
