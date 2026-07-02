import os
import sys
import argparse
import tempfile
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
import trimesh
import rembg
from PIL import Image
from shapely.geometry import Polygon as ShapelyPolygon
from torchvision.transforms import v2
from torchvision.utils import save_image
from pytorch_lightning import seed_everything
from omegaconf import OmegaConf
from einops import rearrange
from huggingface_hub import hf_hub_download
from diffusers import DiffusionPipeline, EulerAncestralDiscreteScheduler

INSTANT_MESH_DIR = Path(__file__).resolve().parents[3] / "vendor" / "InstantMesh"
sys.path.insert(0, str(INSTANT_MESH_DIR))

from src.utils.train_util import instantiate_from_config
from src.utils.camera_util import get_zero123plus_input_cameras
from src.utils.mesh_util import save_obj
from src.utils.infer_util import remove_background, resize_foreground


REPO_ID = "TencentARC/InstantMesh"


def make_watertight(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    edge_counts = defaultdict(int)
    for face in mesh.faces:
        for i in range(3):
            e = tuple(sorted([face[i], face[(i + 1) % 3]]))
            edge_counts[e] += 1

    boundary_edges = [e for e, c in edge_counts.items() if c < 2]
    if not boundary_edges:
        return mesh

    boundary_adj = defaultdict(set)
    for e in boundary_edges:
        boundary_adj[e[0]].add(e[1])
        boundary_adj[e[1]].add(e[0])

    visited = set()
    loops = []
    for start in boundary_adj:
        if start in visited:
            continue
        loop = []
        current = start
        prev = None
        while True:
            loop.append(current)
            visited.add(current)
            neighbors = [v for v in boundary_adj[current] if v != prev]
            if not neighbors:
                break
            nxt = neighbors[0]
            if nxt == start:
                break
            if nxt in visited:
                break
            prev, current = current, nxt
        if len(loop) >= 3:
            loops.append(loop)

    new_vertices = list(mesh.vertices)
    new_faces = list(mesh.faces)

    for loop in loops:
        verts = mesh.vertices[loop]
        z_vals = verts[:, 2]
        if not np.allclose(z_vals, z_vals[0]):
            continue
        z = float(z_vals[0])

        verts_2d = verts[:, :2]
        sa = 0.0
        for i in range(len(loop)):
            x1, y1 = verts_2d[i]
            x2, y2 = verts_2d[(i + 1) % len(loop)]
            sa += x1 * y2 - x2 * y1
        sa /= 2

        if sa < 0:
            loop = list(reversed(loop))
            verts_2d = verts_2d[::-1]

        poly = ShapelyPolygon([(p[0], p[1]) for p in verts_2d])
        if not poly.is_valid:
            poly = poly.buffer(0)

        tri_verts_2d, tri_faces = trimesh.creation.triangulate_polygon(poly)

        vert_map = {}
        for i, tv in enumerate(tri_verts_2d):
            found = None
            for j, lv in enumerate(loop):
                if np.allclose(tv, mesh.vertices[lv, :2], atol=1e-6):
                    found = lv
                    break
            if found is None:
                vert_map[i] = len(new_vertices)
                new_vertices.append(np.array([tv[0], tv[1], z]))
            else:
                vert_map[i] = found

        for face in tri_faces:
            new_faces.append([vert_map[f] for f in face])

    result = trimesh.Trimesh(vertices=np.array(new_vertices), faces=np.array(new_faces))
    result.fix_normals()

    comps = result.split()
    if len(comps) > 1:
        main = max(comps, key=lambda c: len(c.vertices))
        result = main

    return result


def ensure_model_weights(config_name="instant-nerf-base"):
    base_ckpt = f"{config_name.replace('-', '_')}.ckpt"
    ckpt_path = hf_hub_download(repo_id=REPO_ID, filename=base_ckpt, repo_type="model")
    unet_path = hf_hub_download(
        repo_id=REPO_ID, filename="diffusion_pytorch_model.bin", repo_type="model"
    )
    return ckpt_path, unet_path


def generate_mesh_from_image(
    image_path: str,
    output_dir: str = None,
    diffusion_steps: int = 75,
    seed: int = 42,
    scale: float = 1.0,
    view: int = 6,
    no_rembg: bool = False,
    save_multiview: bool = True,
    multiview_resolution: int = 320,
    config_name: str = "instant-mesh-base",
) -> Path:
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="instantmesh_")
    output_dir = Path(output_dir)
    images_dir = output_dir / "images"
    meshes_dir = output_dir / "meshes"
    images_dir.mkdir(parents=True, exist_ok=True)
    meshes_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    seed_everything(seed)

    config_path = INSTANT_MESH_DIR / "configs" / f"{config_name}.yaml"
    config = OmegaConf.load(config_path)
    model_config = config.model_config
    infer_config = config.infer_config

    print("Loading diffusion model (Zero123++) ...")
    pipeline = DiffusionPipeline.from_pretrained(
        "sudo-ai/zero123plus-v1.2",
        custom_pipeline=str(INSTANT_MESH_DIR / "zero123plus" / "pipeline.py"),
        torch_dtype=torch.float32,
    )
    pipeline.scheduler = EulerAncestralDiscreteScheduler.from_config(
        pipeline.scheduler.config, timestep_spacing="trailing"
    )

    _, unet_ckpt_path = ensure_model_weights(config_name)
    state_dict = torch.load(unet_ckpt_path, map_location="cpu")
    pipeline.unet.load_state_dict(state_dict, strict=True)
    pipeline = pipeline.to(device)

    print("Loading reconstruction model ...")
    model = instantiate_from_config(model_config)
    model_ckpt_path, _ = ensure_model_weights(config_name)
    state_dict = torch.load(model_ckpt_path, map_location="cpu")["state_dict"]
    state_dict = {k[14:]: v for k, v in state_dict.items() if k.startswith("lrm_generator.")}
    model.load_state_dict(state_dict, strict=True)
    model = model.to(device)
    model = model.eval()
    if hasattr(model, "init_flexicubes_geometry"):
        model.init_flexicubes_geometry(device)

    name = Path(image_path).stem
    print(f"Processing {name} ...")

    input_image = Image.open(image_path).convert("RGB")
    if not no_rembg:
        rembg_session = rembg.new_session()
        input_image = remove_background(input_image, rembg_session)
        input_image = resize_foreground(input_image, 0.85)

    output_image = pipeline(
        input_image,
        num_inference_steps=diffusion_steps,
        width=multiview_resolution * 2,
        height=multiview_resolution * 3,
    ).images[0]

    if save_multiview:
        output_image.save(str(images_dir / f"{name}.png"))

    images = np.asarray(output_image, dtype=np.float32) / 255.0
    images = torch.from_numpy(images).permute(2, 0, 1).contiguous().float()
    images = rearrange(images, "c (n h) (m w) -> (n m) c h w", n=3, m=2)

    for n, x in enumerate(images):
        save_image(x, images_dir / f'viewpoint_{n}.png')

    del pipeline

    input_cameras = get_zero123plus_input_cameras(batch_size=1, radius=4.0 * scale, fov=30).to(device)

    images = images.unsqueeze(0).to(device)
    images = v2.functional.resize(images, 320, interpolation=3, antialias=True).clamp(0, 1)

    for n, x in enumerate(images):
        save_image(x, images_dir / f'viewpoint_rescaled_{n}.png')

    if view == 4:
        indices = torch.tensor([0, 2, 4, 5]).long().to(device)
        images = images[:, indices]
        input_cameras = input_cameras[:, indices]

    with torch.no_grad():
        planes = model.forward_planes(images, input_cameras)

        mesh_out = model.extract_mesh(
            planes,
            use_texture_map=False,
            **infer_config,
        )
        vertices, faces, vertex_colors = mesh_out
        raw_path = meshes_dir / f"{name}_raw.obj"
        save_obj(vertices, faces, vertex_colors, str(raw_path))
        print(f"Raw mesh saved to {raw_path}")

    raw_mesh = trimesh.load(str(raw_path), force="mesh")
    watertight_mesh = make_watertight(raw_mesh)
    mesh_path = meshes_dir / f"{name}.obj"
    watertight_mesh.export(str(mesh_path))
    print(f"Watertight mesh saved to {mesh_path} ({len(watertight_mesh.vertices)} verts, {len(watertight_mesh.faces)} faces)")

    return mesh_path
