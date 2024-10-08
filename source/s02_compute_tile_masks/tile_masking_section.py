import hashlib
import platform
from pathlib import Path

import numpy as np
import yaml
from sbem.record.Section import Section
from scipy import ndimage
from skimage.morphology import binary_erosion


def win_to_ux_path(win_path: str, remove_substring=None) -> str:
    if remove_substring:
        win_path = win_path.replace(remove_substring, "/tungstenfs")

    linux_path = win_path.replace("\\", "/")

    linux_path = linux_path.replace("//", "", 1)

    return linux_path


def ux_to_win_path(ux_path: str, remove_substring=None) -> str:
    if remove_substring:
        ux_path = ux_path.replace(remove_substring, r"\\tungsten-nas.fmi.ch\tungsten")

    win_path = ux_path.replace("/", "\\")

    return win_path


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


class TileMaskingSection(Section):
    _section_path: str
    _tile_smearing_masks = None
    _tile_resin_masks = None
    _tile_smearing_masks_cache = {}

    def __init__(
        self,
        acquisition: str,
        section_num: int,
        tile_grid_num: int,
        grid_shape: tuple[int, int],
        thickness: float,
        tile_height: int,
        tile_width: int,
        tile_overlap: int,
    ):
        super().__init__(
            acquisition=acquisition,
            section_num=section_num,
            tile_grid_num=tile_grid_num,
            grid_shape=grid_shape,
            thickness=thickness,
            tile_width=tile_width,
            tile_height=tile_height,
            tile_overlap=tile_overlap,
        )

    def get_tile_shape(self) -> tuple[int, int]:
        return self.get_tile_height(), self.get_tile_width()

    def _add_smearing_mask_to_cache(self, mask: np.ndarray):
        checksum = hashlib.sha256(mask.tobytes()).hexdigest()
        self._tile_smearing_masks_cache[checksum] = mask
        return checksum

    def _get_smearing_mask_from_cache(self, checksum: str):
        return self._tile_smearing_masks_cache[checksum]

    def create_simple_smearing_masks(self, smear_extend: int) -> None:
        """
        Careful, this cleans the existing tile smearing masks!
        """
        assert smear_extend >= 0, "smr_extend for tile masks can not be negative!"
        assert (
            smear_extend < self._tile_overlap * 1.2
        ), "smr_extend must be smaller than 120% over tile-overlap."
        self._tile_smearing_masks = {}
        smr_mask = np.zeros(shape=self.get_tile_shape(), dtype=bool)
        smr_mask[:smear_extend] = True
        smr_mask_checksum = self._add_smearing_mask_to_cache(smr_mask)

        for tile_id in self.tiles.keys():
            self._tile_smearing_masks[tile_id] = smr_mask_checksum

    def create_dynamic_smearing_masks(self) -> None:
        raise NotImplementedError("Dynamic smearing masks are not implemented yet.")
        # smr_mask_checksum = self._add_smearing_mask_to_cache(smr_mask)
        # self._tile_smearing_masks[tile_id] = smr_mask_checksum

    def set_smearing_mask(self, tile_id: int, mask: np.ndarray):
        checksum = self._add_smearing_mask_to_cache(mask)
        self._tile_smearing_masks[tile_id] = checksum

    def get_smearing_mask(self, tile_id: int) -> np.ndarray:
        assert (
            self._tile_smearing_masks is not None
        ), "Tile smearing masks have not been initialized."
        return self._get_smearing_mask_from_cache(self._tile_smearing_masks[tile_id])

    def get_resin_mask(self, tile_id: int) -> np.ndarray:
        assert (
            self._tile_resin_masks is not None
        ), "Tile resin masks have not been initialized."
        if tile_id not in self._tile_resin_masks:
            return np.zeros(self.get_tile_shape(), dtype=bool)
        return self._tile_resin_masks[tile_id]

    def set_resin_mask(self, tile_id: int, mask: np.ndarray) -> None:
        self._tile_resin_masks[tile_id] = mask

    def save(self, path: str, overwrite: bool = False):
        with open(Path(path) / self.get_name() / "tile_smearing_masks.yaml", "w") as f:
            yaml.safe_dump(self._tile_smearing_masks, f)

        output_dir = Path(path) / self.get_name()

        tile_smearing_masks_npz = output_dir / "tile_smearing_masks.npz"
        np.savez_compressed(tile_smearing_masks_npz, **self._tile_smearing_masks_cache)

        tile_resin_masks_output_npz = output_dir / "tile_resin_masks.npz"
        keys_as_strings = {str(k): v for k, v in self._tile_resin_masks.items()}
        np.savez_compressed(tile_resin_masks_output_npz, **keys_as_strings)

    def compute_resin_mask(
        self,
        tile_id,
        thresh: int = 20,
        filter_size: int = 10,
        range_limit: int = 20,
    ) -> np.ndarray:
        def detect_resin(a: np.ndarray) -> np.ndarray[bool]:
            # Identify silver particles
            binary_image = ((a <= thresh) * 255).astype(np.uint8)

            # Blur particles and perform thresholding again
            binary_image = ndimage.gaussian_filter(binary_image, sigma=125)
            binary_image = binary_image > (thresh + 1)

            return ndimage.binary_fill_holes(binary_image)

        def mask_low_dynamic_range(a: np.ndarray):
            # Masks areas with insufficient dynamic range.
            a_mask = (
                ndimage.maximum_filter(a, filter_size)
                - ndimage.minimum_filter(a, filter_size)
            ) < range_limit
            return ndimage.binary_fill_holes(a_mask)

        img_data = self.get_tile(tile_id).get_tile_data()
        # Compute mask
        mask = detect_resin(img_data)
        # mask_resin = mutils.detect_resin(self.img_data, thresh)
        if range_limit != 0:
            mask_void = mask_low_dynamic_range(img_data)
            mask = mask | mask_void

        return mask

    def create_resin_masks(
        self, threshold: int, filter_size: int, range_limit: int
    ) -> None:
        self._tile_resin_masks = {}
        for tile_id in self.outer_tile_ids():
            self._tile_resin_masks[tile_id] = self.compute_resin_mask(
                tile_id, threshold, filter_size, range_limit
            )

    def outer_tile_ids(self):
        path_tile_id_map = str(Path(self._section_path).parent / "tile_id_map.json")
        tile_id_map = self.get_tile_id_map(path_tile_id_map)

        mask = tile_id_map > -1
        mask_eroded = binary_erosion(mask, footprint=np.ones((3, 3)), mode="min")
        boundary_tiles = mask ^ mask_eroded
        return tile_id_map[boundary_tiles]

    @classmethod
    def load_from_yaml(cls, path: str) -> "TileMaskingSection":
        with open(path) as f:
            dict = yaml.safe_load(f)

        section = cls(
            section_num=dict["section_num"],
            tile_grid_num=dict["tile_grid_num"],
            grid_shape=dict["grid_shape"],
            acquisition=dict["acquisition"],
            thickness=dict["thickness"],
            tile_height=dict["tile_height"],
            tile_width=dict["tile_width"],
            tile_overlap=dict["tile_overlap"],
        )

        for t_dict in dict["tiles"]:
            from sbem.record.Tile import Tile

            tile = Tile(
                section=section,
                tile_id=t_dict["tile_id"],
                path=t_dict["path"],
                stage_x=t_dict["stage_x"],
                stage_y=t_dict["stage_y"],
                resolution_xy=t_dict["resolution_xy"],
            )
            tile._path = cross_platform_path(tile._path)
            section.tiles[tile.get_tile_id()] = tile

        tile_smearing_masks_path = Path(path).parent / "tile_smearing_masks.yaml"
        if tile_smearing_masks_path.exists():
            with open(tile_smearing_masks_path) as f:
                tile_smearing_masks = yaml.safe_load(f)

            tile_smearing_masks_cache_path = (
                Path(path).parent / "tile_smearing_masks.npz"
            )
            with np.load(tile_smearing_masks_cache_path) as npz:
                tile_smearing_masks_cache = {k: npz[k] for k in npz.files}

            section._tile_smearing_masks = tile_smearing_masks
            section._tile_smearing_masks_cache = tile_smearing_masks_cache

        tile_resin_masks_path = Path(path).parent / "tile_resin_masks.npz"
        if tile_resin_masks_path.exists():
            with np.load(tile_resin_masks_path) as npz:
                tile_resin_masks = {int(k): npz[k] for k in npz.files}
            section._tile_resin_masks = tile_resin_masks

        section._section_path = path
        return section
