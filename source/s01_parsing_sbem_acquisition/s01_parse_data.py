import argparse
from glob import glob
from os import scandir
from os.path import exists, join
from pathlib import Path
from typing import Optional

import yaml
from parameter_config import AcquisitionConfig
from sbem.experiment.parse_utils import get_tile_metadata
from sbem.record.Section import Section
from sbem.record.Tile import Tile


def section_in_range(name: str, start: int, end: int) -> bool:
    s, _ = name.split("_")
    z = int(s[1:])
    return start <= z <= end


def get_missing_sections(tile_specs, start_section, end_section) -> set[int]:
    existing_sec_nums = set()
    for spec in tile_specs:
        sec_num = spec["z"]
        assert isinstance(sec_num, int)
        existing_sec_nums.add(sec_num)
    all_sec_nums = set(range(start_section, end_section + 1))
    return all_sec_nums - existing_sec_nums


def get_raw_tile_prefix(directory: Path) -> Optional[str]:
    """
    Get the prefix of raw SBEMimage project .tif files without listing all files.

    Example:
        raw_filename: directory/20230523_RoLi_IV_130558_run2_g0001_t0902_s00299.tif
        returns: 20230523_RoLi_IV_130558_run2_

    Parameters:
    directory (str): parent directory to the directories for searching the .tif file.

    Returns:
    str: Path to the first .tif file, or None if no .tif files are found.
    """
    for entry in scandir(directory):
        if entry.is_file() and entry.name.endswith(".tif"):
            p = entry.name
            assert (
                p[-22] == "g"
            ), 'Error extracting tile filename (expected suffix pattern form: "g0001_t0902_s00296.tif")'
            assert (
                p[-16] == "t"
            ), 'Error extracting tile filename (expected suffix pattern form: "g0001_t0902_s00296.tif")'
            assert (
                p[-10] == "s"
            ), 'Error extracting tile filename (expected suffix pattern form: "g0001_t0902_s00296.tif")'
            return entry.name[:-22]


def get_missing_tile_specs(
    missing_section_nums: set[int],
    sbem_root_dir: str,
    tile_grid: str,
    tile_height: int,
    tile_width: int,
    overlap: int,
) -> list[dict]:

    if not missing_section_nums:
        return []

    dir_tiles = Path(sbem_root_dir) / "tiles" / tile_grid
    tile_folders = [Path(d) for d in dir_tiles.glob("*") if d.is_dir()]
    prefix = get_raw_tile_prefix(tile_folders[0])
    new_tile_specs = []

    for num in missing_section_nums:
        paths_tiles = []
        for tf in tile_folders:
            tile_path = tf / f"{prefix}{tile_grid}_{tf.name}_s{str(num).zfill(5)}.tif"
            if tile_path.is_file():
                paths_tiles.append(tile_path)

        for tp in paths_tiles:
            tile_spec = {
                "tile_id": int(tp.name[-15:-11]),
                "grid_num": int(tp.name[-21:-17]),
                "tile_file": str(tp),
                "x": 0,
                "y": 0,
                "z": int(tp.name[-9:-4]),
                "overlap": overlap,
                "tile_height": tile_height,
                "tile_width": tile_width,
            }
            new_tile_specs.append(tile_spec)

    return new_tile_specs


def parse_data(
    output_dir: str,
    sbem_root_dir: str,
    acquisition: str,
    tile_grid: str,
    grid_shape: tuple[int, int],
    thickness: float,
    resolution_xy: float,
    start_section: int,
    end_section: int,
):
    tile_grid_num = int(tile_grid[1:])

    metadata_files = sorted(glob(join(sbem_root_dir, "meta", "logs", "metadata_*")))

    tile_specs = get_tile_metadata(
        sbem_root_dir, metadata_files, tile_grid_num, resolution_xy
    )

    missing_sec_nums = get_missing_sections(tile_specs, start_section, end_section)
    first_spec = tile_specs[0]
    tile_specs.extend(
        get_missing_tile_specs(
            missing_sec_nums,
            sbem_root_dir,
            tile_grid,
            first_spec["tile_height"],
            first_spec["tile_width"],
            first_spec["overlap"],
        )
    )

    sections = {}
    existing_sections = glob(join(output_dir, "*", "section.yaml"))
    for es in existing_sections:
        section = Section.load_from_yaml(es)
        if section_in_range(section.get_name(), start_section, end_section):
            sections[section.get_name()] = section

    for tile_spec in tile_specs:
        section_name = f"s{tile_spec['z']}_g{tile_grid_num}"
        if section_in_range(section_name, start_section, end_section):
            if section_name in sections.keys():
                section = sections[section_name]
            else:
                section = Section(
                    acquisition=acquisition,
                    section_num=tile_spec["z"],
                    tile_grid_num=tile_grid_num,
                    grid_shape=grid_shape,
                    thickness=thickness,
                    tile_height=tile_spec["tile_height"],
                    tile_width=tile_spec["tile_width"],
                    tile_overlap=tile_spec["overlap"],
                )
                sections[section_name] = section

            assert (
                tile_spec["tile_height"] == section.get_tile_height()
            ), f"Tile height is off in section {section.get_name()}."
            assert (
                tile_spec["tile_width"] == section.get_tile_width()
            ), f"Tile width is off in section {section.get_name()}."
            assert (
                tile_spec["overlap"] == section.get_tile_overlap()
            ), f"Tile overlap is off in section {section.get_name()}."
            Tile(
                section,
                tile_id=tile_spec["tile_id"],
                path=tile_spec["tile_file"],
                stage_x=tile_spec["x"],
                stage_y=tile_spec["y"],
                resolution_xy=resolution_xy,
                unit="nm",
            )

    section_paths = []
    for section in sections.values():
        section.save(path=output_dir, overwrite=True)
        tile_id_map_path = join(output_dir, section.get_name(), "tile_id_map.json")
        if not exists(tile_id_map_path):
            section.get_tile_id_map(path=tile_id_map_path)

        section_paths.append(join(output_dir, section.get_name(), "section.yaml"))

    return section_paths


def main(
    output_dir: str,
    acquisition_conf: AcquisitionConfig = AcquisitionConfig(),
    start_section: int = 0,
    end_section: int = 10,
    chunk_size: int = 10,
):
    parse_data(
        output_dir=output_dir,
        sbem_root_dir=acquisition_conf.sbem_root_dir,
        acquisition=acquisition_conf.acquisition,
        tile_grid=acquisition_conf.tile_grid,
        grid_shape=acquisition_conf.grid_shape,
        thickness=acquisition_conf.thickness,
        resolution_xy=acquisition_conf.resolution_xy,
        start_section=start_section,
        end_section=end_section,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="tile-stitching.config")
    args = parser.parse_args()

    with open(args.config) as f:
        config = yaml.safe_load(f)

    main(
        output_dir=join(config["output_dir"], "sections"),
        acquisition_conf=AcquisitionConfig(**config["acquisition_config"]),
        start_section=config["start_section"],
        end_section=config["end_section"],
    )

    from inspection import cross_platform_path, Inspection

    root = cross_platform_path(config["output_dir"])
    first = config["start_section"]
    last = config["end_section"]

    exp = Inspection(root, first, last)
    exp.validate_parsed_sbem_acquisition()
    exp.validate_tile_id_maps()
