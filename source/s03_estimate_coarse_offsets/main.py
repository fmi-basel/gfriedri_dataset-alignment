import argparse
from os.path import basename
from pathlib import Path

import cv2
import numpy as np
import yaml
from faim_ipa.utils import create_logger, get_git_root
from sofima import stitch_rigid

import sys
root = get_git_root()
sys.path.append(str(root))

from source.s02_compute_tile_masks.tile_masking_section import TileMaskingSection

from config import CoarseOffsetsConfig

def get_mask_map(section: TileMaskingSection, tile_id_map_path: str):
    mask_map = {}
    tile_id_map = section.get_tile_id_map(tile_id_map_path)
    for y in range(tile_id_map.shape[0]):
        for x in range(tile_id_map.shape[1]):
            tile_id = tile_id_map[y, x]
            if tile_id != -1:
                smearing_mask = section.get_smearing_mask(tile_id)
                resin_mask = section.get_resin_mask(tile_id)
                mask_map[(x, y)] = np.logical_or(smearing_mask, resin_mask)

    return mask_map

def load_tile_map(section, tile_id_map_path, apply_clahe_to_tiles):
    tile_map = section.get_tile_data_map(tile_id_map_path, indexing="xy")
    if apply_clahe_to_tiles:
        clahe_op = cv2.createCLAHE(clipLimit=2., tileGridSize=(8, 8))
        for key, data in tile_map.items():
            tile_map[key] = clahe_op.apply(data)

    return tile_map

def compute_coarse_offset(
    section_dir: str,
    apply_clahe_to_tiles: bool,
    overlaps_xy,
    min_range,
    min_overlap,
    filter_size,
    max_valid_offset,
):
    section = TileMaskingSection.load_from_yaml(str(Path(section_dir) / "section.yaml"))
    tile_id_map_path = str(Path(section_dir) / 'tile_id_map.json')
    mask_map = get_mask_map(section, tile_id_map_path)
    tile_space = section.get_tile_id_map(tile_id_map_path).shape
    tile_map = load_tile_map(section, tile_id_map_path, apply_clahe_to_tiles)
    cx, cy = stitch_rigid.compute_coarse_offsets(
        yx_shape=tile_space,
        tile_map=tile_map,
        mask_map=mask_map,
        co=None,
        overlaps_xy=overlaps_xy,
        min_range=min_range,
        min_overlap=min_overlap,
        filter_size=filter_size,
        max_valid_offset=max_valid_offset,
    )
    coarse_offset_path = str(Path(section_dir) / 'cx_cy.json')
    section.set_coarse_offsets(cx, cy, coarse_offset_path)
    return coarse_offset_path

def main(
    section_dirs: list[str],
    config: CoarseOffsetsConfig,
):
    logger = create_logger("estimate-coarse-offset")
    logger.info(f"section_dirs: {section_dirs}")
    logger.info(f"config: {config.dict()}")

    coarse_offset_paths = []
    for section_dir in section_dirs:
        logger.info(f"Processing section {basename(section_dir)}")
        coarse_offset_paths.append(
            compute_coarse_offset(
                section_dir,
                apply_clahe_to_tiles=config.apply_clahe_to_tiles,
                overlaps_xy=config.overlaps_xy,
                min_range=config.min_range,
                min_overlap=config.min_overlap,
                filter_size=config.filter_size,
                max_valid_offset=config.max_valid_offset,
            )
        )

    with open("coarse_offset_paths.yaml", "w") as f:
        yaml.safe_dump(coarse_offset_paths, f, sort_keys=False)

    logger.info("Done.")




if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=True)
    parser.add_argument("--chunk", type=str, required=True)

    args = parser.parse_args()

    config = CoarseOffsetsConfig.load(Path(args.config))

    with open(args.chunk, 'r') as f:
        section_dirs = yaml.safe_load(f)

    main(
        section_dirs=section_dirs,
        config=config
    )