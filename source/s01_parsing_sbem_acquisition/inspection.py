import json
import logging
import os
import re
import platform
from pathlib import Path
from typing import List, Union, Dict, Iterable, Optional
import glob

import numpy as np
import yaml
from tqdm import tqdm

UniPath = Union[Path, str]


class Inspection:
    def __init__(self, root, first_sec, last_sec):
        self.root = Path(root)
        self.first_sec = first_sec
        self.last_sec = last_sec

        self.dir_sections = self.root / "sections"
        assert self.dir_sections.exists(), "{self.dir_sections} does not exist!"
        self.section_dirs = [
            Path(p) for p in self.filter_and_sort_sections(self.dir_sections)
        ]

    def validate_parsed_sbem_acquisition(self) -> None:
        section_nums = [
            int(Path(d).name.split("_")[0].strip("s")) for d in self.section_dirs
        ]
        missing_sections = self.get_missing_sections(section_nums)

        print(f"len sections: {len(section_nums)}")
        print(f"first, last {self.first_sec, self.last_sec}")
        print(f"len missing folders: {len(missing_sections)}")
        self.write_dict_to_yaml(
            str(self.root / "missing_sections.yaml"), missing_sections
        )

    def write_dict_to_yaml(
        self, file_path: str, data: Union[Dict[int, float], Iterable[int]]
    ):
        """
        Write a dictionary with integer keys and float values, or an iterable of integers, to a YAML file.

        :param file_path: Path to the YAML file.
        :param data: Dictionary or iterable to be written to the file.
        """

        if isinstance(data, dict):
            # Convert NumPy types to native Python types, if any
            converted_data = {int(k): float(v) for k, v in data.items()}
        elif isinstance(data, Iterable):
            converted_data = [int(item) for item in data]
        else:
            raise ValueError(
                "The 'data' parameter must be a dictionary with integer keys and float values, or an iterable of integers."
            )

        try:
            with open(file_path, "w") as file:
                yaml.dump(converted_data, file, default_flow_style=False)
        except Exception as e:
            print(f"An error occurred while writing to the file: {e}")

    def get_missing_sections(self, section_nums: List[int]) -> List[int]:
        """Identify section numbers discontinuities in section folder"""

        section_range = set(range(self.first_sec, self.last_sec + 1))
        missing_nums = sorted(list(section_range - set(section_nums)))

        if len(missing_nums) > 0:
            fp = str(Path(self.dir_sections) / "missing_section_folders.yaml")
            self.write_dict_to_yaml(fp, missing_nums)
            is_are = "is" if len(missing_nums) == 1 else "are"
            logging.warning(
                f"There {is_are} {len(missing_nums)} missing sections in 'sections' folder!"
            )

        return missing_nums

    def filter_and_sort_sections(self, sections_dir: Path) -> Optional[List[str]]:
        """
        Filter and sort section directories within a parent directory.

        Only section names in form 's0xxxx_gy' where x and y are numeric will be returned.
        Sorting according to the section number from smallest to largest.
        :param sections_dir: Path to the parent directory containing section directories.
        :return: List of sorted and filtered section directory names.
        """

        # Define a regex pattern to filter section directory names
        pattern = r"s\d+_g\d+"
        regex_pattern = re.compile(pattern)

        # Use glob to filter the section directory names
        dirs = glob.glob(str(sections_dir / "*"))

        # Filter and sort the matching section directory names
        return sorted(
            [
                dir_name
                for dir_name in dirs
                if os.path.isdir(dir_name) and regex_pattern.match(Path(dir_name).name)
            ],
            key=lambda name: int(Path(name).name.split("_")[0].strip("s")),
        )

    def validate_tile_id_maps(self) -> None:
        invalid_tile_id_maps = []
        for section in tqdm(self.section_dirs):
            if not self.valid_tile_id_map(section):
                invalid_tile_id_maps.append(section.name)

        output_path = self.root / "invalid_tile_id_maps.yaml"
        with open(output_path, "w") as f:
            yaml.safe_dump(invalid_tile_id_maps, f)

        logging.warning(
            f"There are {len(invalid_tile_id_maps)} invalid tile-id maps!\n"
            f"Check {output_path}."
        )

    def valid_tile_id_map(self, section: Path) -> bool:
        section_yaml = section / "section.yaml"
        assert section_yaml.exists(), f"{section_yaml} does not exist!"

        tile_id_map_json = section / "tile_id_map.json"
        assert tile_id_map_json.exists(), f"{tile_id_map_json} does not exist!"

        with open(section_yaml, "r") as f:
            section_yaml_data = yaml.safe_load(f)

        section_tile_ids = set([t["tile_id"] for t in section_yaml_data["tiles"]])

        with open(tile_id_map_json, "r") as f:
            tile_id_map = np.array(json.load(f))

        tile_ids = set(tile_id_map.flatten())
        if -1 in tile_ids:
            tile_ids.remove(-1)

        return section_tile_ids == tile_ids


def cross_platform_path(path: str) -> str:
    """
    Normalize the given filepath to use forward slashes on all platforms.
    Additionally, remove Windows UNC prefix "\\tungsten-nas.fmi.ch\" if present

    Parameters:
        :rtype: object
        :param path: The input filepath.

    Returns:
        str: The normalized filepath.
    """

    def win_to_ux_path(win_path: str, remove_substring=None) -> str:
        if remove_substring:
            win_path = win_path.replace(remove_substring, "/tungstenfs")
        linux_path = win_path.replace("\\", "/")
        linux_path = linux_path.replace("//", "", 1)
        return linux_path

    def ux_to_win_path(ux_path: str, remove_substring=None) -> str:
        if remove_substring:
            ux_path = ux_path.replace(
                remove_substring, r"\\tungsten-nas.fmi.ch\tungsten"
            )
        win_path = ux_path.replace("/", "\\")
        return win_path

    # Get the operating system name
    os_name = platform.system()

    if os_name == "Windows" and "/" in path:
        # Running on Windows but path in UX style
        path = ux_to_win_path(path, remove_substring="/tungstenfs")

    elif os_name == "Windows" and r"\\tungsten-nas.fmi.ch\tungsten" in path:
        path = path.replace(r"\\tungsten-nas.fmi.ch\tungsten", "W:")
        path = path.replace("\\", "/")

    elif os_name == "Linux" and "\\" in path:
        # Running on UX but path in Win style
        rs = r"\\tungsten-nas.fmi.ch\tungsten"
        path = win_to_ux_path(path, remove_substring=rs)

    return path
