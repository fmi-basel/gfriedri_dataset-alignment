import json
import logging
import platform
from pathlib import Path
from typing import Tuple, List, Union, Optional, Dict, Set

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.ticker import MaxNLocator
from numpy import ndarray
from tqdm import tqdm

UniPath = Union[str, Path]
TileCoord = Union[Tuple[int, int, int, int], Tuple[int, int]]  # (c, z, y, x)


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

    if path is None:
        return ""

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


def get_section_num(section_path: UniPath) -> Optional[int]:
    try:
        num = int(Path(section_path).name.split("_")[0].strip("s"))
        return num
    except (ValueError, IndexError):
        return None


def get_vert_tile_id(tile_id_map: np.ndarray, tile_id: int) -> Optional[int]:
    """
    Retrieves the tile ID located directly below the specified tile ID in the given tile ID map.

    Example:
        tile_id_map = np.array([[1, 2, 3],
                                [4, 5, 6],
                                [7, 8, 9]])
        get_vert_tile_id(tile_id_map, 5) returns:  8
        get_vert_tile_id(tile_id_map, 9) returns: None
    """
    tile_id = int(tile_id)
    if not isinstance(tile_id, int):
        raise ValueError(
            f"Invalid tile_id '{tile_id}' specification: must be an integer."
        )

    if tile_id < 0:
        logging.warning("Invalid tile_id specification (must be non-negative)!")
        return None

    if tile_id not in tile_id_map:
        # logging.debug(f"Invalid tile_id specification ({tile_id} not in tile_id_map)!")
        return None

    y, x = np.where(tile_id == tile_id_map)
    y, x = y[0], x[0]
    try:
        return int(tile_id_map[y + 1][x])
    except IndexError as _:
        # logging.debug(f"tile_id {tile_id} not found in tile_id_map.")
        return None


def get_tid_idx(tile_id_map, tile_id) -> Optional[Tuple[int, int]]:
    # Extract y, x coordinate of tile_id in tile_id_map
    if tile_id not in tile_id_map:
        # logging.info(f'Tile_ID: {tile_id} not present in section!')
        return None

    if tile_id == -1:
        logging.info(f"Tile_ID: {tile_id} has undefined mask!")
        return None

    coords = np.where(tile_id == tile_id_map)
    y, x = int(coords[0][0]), int(coords[1][0])
    return y, x


def get_tile_id_map(path_tid_map: UniPath) -> np.ndarray:
    """Loads a JSON file containing a tile ID map and return it as a NumPy array.

    Args:
        path_tid_map (UniPath): Path to the JSON file.

    Returns:
        np.ndarray: Tile ID map as a NumPy array.
    """
    try:
        with open(path_tid_map, "r") as file:
            mp = np.array(json.load(file))
        return mp
    except (FileNotFoundError, json.JSONDecodeError) as e:
        # Handle file not found or JSON decoding errors gracefully.
        raise ValueError(f"Error loading tile ID map from {path_tid_map}: {str(e)}")


def get_tile_ids_set(path_all_tid_maps: str) -> Set[int]:
    try:
        path_tid_maps = Path(path_all_tid_maps).parent / "all_tile_id_maps.npz"
        tid_maps = np.load(str(path_tid_maps), allow_pickle=True)
    except FileNotFoundError as _:
        tid_maps = None
        logging.warning("Error reading all_tile_id_maps.npz")

    tile_ids = set()
    for tid in tid_maps.values():
        tile_ids |= set(tid.flatten())

    tile_ids.remove(-1)

    return tile_ids


def aggregate_tile_id_maps(
    section_dirs: List[UniPath],
) -> Tuple[Dict[str, ndarray], List[str]]:
    """
    Load tile_id_maps arrays from input folder and return them
    as a dictionary with section numbers as keys

    :param section_dirs:
    :return: dictionary mapping tile_id array to section number
    """
    maps: dict = {}
    failed_paths = []
    fn_map = "tile_id_map.json"
    for section_path in tqdm(section_dirs):
        fp_map = Path(section_path) / fn_map
        if not fp_map.exists():
            logging.debug(
                f"s{get_section_num(section_path)} tile_id_map.json file does not exist"
            )
            failed_paths.append(f"s{get_section_num(section_path)}\n")
            continue

        key = str(get_section_num(section_path))
        maps[key] = get_tile_id_map(fp_map)

    return maps, failed_paths


def read_coarse_mat(path: UniPath) -> Tuple[Optional[ndarray], ndarray, ndarray]:
    """Returns contents of a coarse data file (either npz or json).

    :param path: path to the data file (coarse.npz or cx_cy.json)
    :return:
        coarse_mesh: contents of coarse_mesh (only if .npz file is read) or None
        cx: coarse shifts between horizontal neighbors
        cy: coarse shifts between vertical neighbors
    """

    path = Path(path)
    try:
        if path.suffix == ".npz":
            arr = np.load(str(path))
            coarse_mesh, cx, cy = arr["coarse_mesh"], arr["cx"], arr["cy"]
            logging.debug(f"cx npz shape: {np.shape(cx)}")
            return coarse_mesh, cx, cy
        elif path.suffix == ".json":
            # Load the JSON data from the file
            with open(path, "r") as file:
                data = json.load(file)

            # Convert the loaded data back to NumPy arrays
            cx = np.asarray(data.get("cx", {}))
            cy = np.asarray(data.get("cy", {}))
            if cx.ndim == 4:
                cx = cx[:, 0, ...]
                cy = cy[:, 0, ...]
            if cx.ndim == 5:
                cx = cx[:, 0, 0, ...]
                cy = cy[:, 0, 0, ...]

            coarse_mesh = None
            return coarse_mesh, cx, cy
        else:
            print(
                f"Error: Unsupported file format for '{path}'. Supported formats are '.npz' and '.json'."
            )

    except FileNotFoundError:
        print(f"Error: The file '{path}' does not exist.")
    except json.JSONDecodeError as e:
        print(f"Error: Failed to decode JSON data in '{path}': {e}")
    except Exception as e:
        print(f"Error during read_coarse_mat: {e}")


def aggregate_coarse_offsets(
    section_dirs: List[UniPath],
) -> Tuple[Dict[str, ndarray], List[str]]:
    """
    Load coarse offset arrays from input folder and return them
    as a dictionary with section numbers as keys

    Coarse offsets can be read either from coarse.npz or from cx_cy.json file.
    :param section_dirs:
    :return:
    """
    offsets: dict = {}
    failed_paths = []
    for section_path in tqdm(section_dirs):
        cxy_path = None
        cxy_names = ("cx_cy.json",)
        for name in cxy_names:
            path_to_check = Path(section_path) / name
            if path_to_check.exists():
                cxy_path = path_to_check
                break

        if cxy_path is None:
            logging.debug(
                f"s{get_section_num(section_path)} coarse-offsets file does not exist"
            )
            failed_paths.append(f"s{get_section_num(section_path)}\n")
            continue

        _, cx, cy = read_coarse_mat(cxy_path)
        key = str(get_section_num(section_path))
        offsets[key] = np.array((cx, cy))

    return offsets, failed_paths


def tile_id_from_coord(coord: TileCoord, tile_id_map: np.ndarray) -> Optional[int]:
    """Determines tile ID from tile coordinates.

    Args:
        coord (TileCoord): Tile coordinates, either (c, z, y, x) or (y, x).
        tile_id_map (np.ndarray): Array containing tile IDs.
    Returns:
        Optional[int]: The tile ID if found, None otherwise.
    """
    if len(coord) in (2, 4):
        # Unpack the last two elements of the tuple as y, x
        y, x = coord[-2:]
    else:
        return None

    try:
        return int(tile_id_map[int(y), int(x)])
    except (ValueError, IndexError):
        return None


def locate_inf_vals(
    path_cxyz: Union[str, Path], dir_out: Union[str, Path], store: bool
) -> Optional[List[Tuple[int]]]:
    """
    Find all Inf values in a backed-up coarse shift tensor.

    :param path_cxyz: Path to the backed-up coarse shift .npz file
    :param dir_out: Directory where to store results
    :param store: Activates storing the results to a text file
    :return: List containing tuples of section numbers, all Inf
            coordinates and corresponding tile IDs
    """

    try:
        cxyz = np.load(str(path_cxyz), allow_pickle=True)
    except FileNotFoundError:
        print("Error reading coarse tensor file.")
        return

    try:
        path_tid_maps = Path(path_cxyz).parent / "all_tile_id_maps.npz"
        tid_maps = np.load(str(path_tid_maps), allow_pickle=True)
    except FileNotFoundError as _:
        tid_maps = None
        logging.warning("Error reading all_tile_id_maps.npz")

    all_coords = []
    all_tids = []
    tids_list = ()

    for section_num in cxyz:
        inf_coords = np.where(np.isinf(cxyz[section_num]))
        coords_list = list(zip(*inf_coords))

        # Get TileIDs of a corrupted tile-pair
        if tid_maps is not None:
            tile_id_map = tid_maps[section_num]
            tids_list = []
            for crd in coords_list:
                tile_id_a = tile_id_from_coord(crd, tile_id_map)

                # Determine the direction of the tile neighbor
                dx = 1 if crd[0] == 0 else 0
                dy = 1 if crd[0] != 0 else 0

                # Compute the neighbor's coordinates
                nn_dxdy = np.zeros_like(crd)
                nn_dxdy[-2:] = (dy, dx)  # Assign dy and dx directly
                nn_crd = crd + nn_dxdy

                # Get the tile ID of the neighboring coordinate
                tile_id_b = tile_id_from_coord(nn_crd, tile_id_map)

                tids_list.append((tile_id_a, tile_id_b))

        if len(tids_list) > 0:
            coords_w_key = [
                (int(section_num),) + c + tids
                for c, tids in zip(coords_list, tids_list)
            ]
        else:
            coords_w_key = [(int(section_num),) + c for c in coords_list]

        all_coords.extend(coords_w_key)
        all_tids.append(tids_list)

    if store:
        path_out = str(Path(dir_out) / "inf_vals.txt")
        logging.info(f"Storing Inf values to: {path_out}")
        np.savetxt(
            fname=path_out,
            X=all_coords,
            fmt="%s",
            delimiter="\t",
            header="Slice\tC\tZ\tY\tX\tTileID\tTileID_nn",
        )

    return all_coords


def plot_trace_from_backup(
    path_cxyz: str,
    path_id_maps: str,
    path_plot: str,
    tile_id: int,
    sec_range: Tuple[Optional[int], Optional[int]],
    show_plot: bool,
):
    """Plots traces from input cxyz tensor

    Args:
        path_cxyz: str -  path to aggregated file containing all coarse offsets
        path_id_map: str - path to aggregated file containing all tile_id_maps
        path_plot: str - path where to store resulting graph
        tile_id: int - ID of the tile trace to be plotted
        sec_range: Optional[tuple(int, int)] - range of section numbers to be plotted

    :return:
    """

    def plot_traces(
        x_axis: np.ndarray,
        traces: np.ndarray,
        _path_plot: str,
        _tile_id: int,
        _vert_nn_tile_id: Optional[int],
        _show_plot: bool,
    ) -> None:
        """Plots array of both coarse offset vectors' values"""

        fig, ax = plt.subplots(figsize=(15, 9))
        labels = ("c0x", "c0y", "c1x", "c1y")
        for j in range(traces.shape[0]):
            ax.plot(x_axis, traces[j, :], "-", label=f"{labels[j]}")

        # Add labels, title, and legend
        ax.set_xlabel("Section number")
        ax.set_ylabel("Shift [pix]")
        nn_tile_id = "" if _vert_nn_tile_id is None else f" ({str(_vert_nn_tile_id)})"
        ax.set_title(f"Coarse Offsets for Tile ID {_tile_id} {nn_tile_id}")
        ax.legend(loc="upper right")
        ax.grid(True)

        # Adjust x-axis and y-axis ticks density
        ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=30))
        ax.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=20))

        plt.savefig(_path_plot)
        if _show_plot:
            plt.show()

        plt.close(fig)
        return

    path_cxyz = Path(cross_platform_path(path_cxyz))
    path_id_maps = Path(cross_platform_path(path_id_maps))
    path_plot = cross_platform_path(path_plot)

    if path_cxyz.exists() and path_id_maps.exists():
        # Load coarse offsets
        cxyz_obj = np.load(path_cxyz)
        cxyz_keys = list(cxyz_obj.files)
        sec_nums = set(map(int, cxyz_keys))

        # Load tile_id_maps
        tile_id_maps = np.load(path_id_maps)
        tile_id_maps_keys = list(tile_id_maps.files)
        sec_nums_id_maps = set(map(int, tile_id_maps_keys))

        # Compatible section numbers
        sec_nums = sec_nums.intersection(sec_nums_id_maps)

        if len(sec_nums) == 0:
            # Not possible to map tile_id_map files to the coarse offset files
            print("Available offsets maps and tile_id_maps do not match.")
            return

        # Select range of sections to be processed
        first, last = sec_range
        if first is None:
            first = min(sec_nums)

        if last is None:
            last = max(sec_nums)

        if first > last:
            logging.warning("Plot traces: wrong section range definition.")
            return

        sec_nums_plot = set(np.arange(first, last, step=1))
        sec_nums_plot = sec_nums.intersection(sec_nums_plot)
        logging.info(
            f"Trace plotting: {len(sec_nums_plot)} sections will be processed."
        )

        if len(sec_nums_plot) > 1:

            arr = np.full(shape=(4, last - first), fill_value=np.nan)
            x_axis_sec_nums = np.arange(first, last)
            vert_nn_tile_id = None
            for i, num in enumerate(x_axis_sec_nums):
                if num in sec_nums_plot:
                    tile_id_map = tile_id_maps[str(num)]
                    if vert_nn_tile_id is None:
                        vert_nn_tile_id = get_vert_tile_id(tile_id_map, tile_id)
                    coord = get_tid_idx(tile_id_map, tile_id)
                    if coord is not None:
                        y, x = coord
                        try:
                            shifts = cxyz_obj[str(num)][:, :, y, x]
                            arr[:, i] = shifts.flatten().transpose()
                        except IndexError as _:
                            logging.warning(
                                f"Trace plotting: unable to determine shifts of s{num} t{tile_id}"
                            )
                    else:
                        continue

            if not np.all(np.isnan(arr)):
                plot_traces(
                    x_axis_sec_nums, arr, path_plot, tile_id, vert_nn_tile_id, show_plot
                )
        else:
            print(
                f"Nothing to plot. Sections {first} : {last} not in available"
                f"range: [{min(sec_nums)} : {max(sec_nums)}]."
            )
            return
    else:
        print(f"Input files are missing. Check path_cxyz: {path_cxyz}")
    return
