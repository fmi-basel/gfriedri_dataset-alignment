import json
import logging
from pathlib import Path
from typing import Tuple, List, Union, Optional, Dict

import numpy as np
from numpy import ndarray
from tqdm import tqdm

UniPath = Union[str, Path]
TileCoord = Union[Tuple[int, int, int, int], Tuple[int, int]]  # (c, z, y, x)


def get_section_num(section_path: UniPath) -> Optional[int]:
    try:
        num = int(Path(section_path).name.split("_")[0].strip("s"))
        return num
    except (ValueError, IndexError):
        return None


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
