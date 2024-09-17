from pydantic import BaseModel


class AcquisitionConfig(BaseModel):
    sbem_root_dir: str = ""
    acquisition: str = "run_0"
    tile_grid: str = "g0001"
    grid_shape: tuple[int, int] = (32, 42)
    thickness: float = 25
    resolution_xy: float = 11
