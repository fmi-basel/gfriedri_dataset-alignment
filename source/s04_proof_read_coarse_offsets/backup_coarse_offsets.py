import argparse
from glob import glob
import logging
from os.path import basename

import numpy as np
from pathlib import Path
from typing import Optional, List
import yaml

from parameter_config import AcquisitionConfig
from inspection_utils import (
    aggregate_coarse_offsets,
    aggregate_tile_id_maps,
    locate_inf_vals,
)


def section_id(x):
    return int(basename(x).split("_")[0][1:])


class Inspection:
    def __init__(self, config: AcquisitionConfig):
        self.root = Path(config.sbem_root_dir)
        self.dir_sections = self.root / "sections"
        self.dir_stitched = self.root / "stitched-sections"
        self.dir_inspect = self.root / "_inspect"
        self.path_cxyz = self.dir_inspect / "all_offsets.npz"
        self.path_id_maps = self.dir_inspect / "all_tile_id_maps.npz"
        self.section_dirs: Optional[List[Path]] = None

    def list_all_section_dirs(self) -> None:
        section_paths = glob(str(self.dir_sections / "s*_g*"))
        self.section_dirs = sorted(section_paths, key=section_id)

    def backup_coarse_offsets(self):
        """Stores all coarse offset arrays into a .npz file within an inspection directory"""

        # Collect all offsets
        offsets, missing_files = aggregate_coarse_offsets(self.section_dirs)
        logging.debug(f"len missing files {len(missing_files)}")
        for p in missing_files:
            logging.debug(p)

        fp_out = self.path_cxyz
        np.savez(fp_out, **offsets)
        logging.info(f"Coarse offsets saved to: {fp_out}")

        fp_out2 = fp_out.with_name("all_offsets_missing_files.txt")
        with open(fp_out2, "w") as f:
            f.writelines("\n".join(missing_files))
        logging.info(f"Missing offsets saved to: {fp_out2}")
        return

    def backup_tile_id_maps(self):
        # Collect all tile ID maps
        tile_id_maps, missing_files = aggregate_tile_id_maps(self.section_dirs)
        logging.debug(f"len missing files {len(missing_files)}")
        for p in missing_files:
            logging.debug(p)

        fp_out = self.path_id_maps
        np.savez(fp_out, **tile_id_maps)
        logging.info(f"Tile ID maps saved to: {fp_out}")

        fp_out2 = fp_out.with_name("all_missing_tile_id_maps.txt")
        with open(fp_out2, "w") as f:
            f.writelines("\n".join(missing_files))
        logging.info(f"Missing tile ID maps saved to: {fp_out2}")
        return


def main(config: AcquisitionConfig):
    exp = Inspection(config)
    exp.list_all_section_dirs()
    exp.backup_coarse_offsets()
    exp.backup_tile_id_maps()
    _ = locate_inf_vals(exp.path_cxyz, exp.dir_inspect, store=True)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="parsing_config.yaml")
    args = parser.parse_args()

    with open(args.config) as f:
        config = yaml.safe_load(f)

    main(config)
