import torch


def RasterizeCudaContext(device=None):
    return None


def rasterize(ctx, vertices, faces, resolution, ranges=None):
    return None, None


def interpolate(attr, rast, tri_idx, rast_db=None, diff_attrs=None):
    return torch.zeros(1, 1, 1, attr.shape[-1])
