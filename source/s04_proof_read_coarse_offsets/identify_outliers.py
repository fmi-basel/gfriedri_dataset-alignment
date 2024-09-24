import argparse
import logging
from typing import Optional, Dict, Tuple, Iterable

import yaml
from pathlib import Path
import numpy as np
from inspection_utils import cross_platform_path, find_outliers, get_vert_tile_id


class TraceOutlierDetector:
    def __init__(self, exp_path: str):
        self.root = Path(cross_platform_path(exp_path))
        self.cxyz_obj = None
        self.tile_id_maps_obj = None
        self.dir_inspect = self.root / "_inspect"
        self.path_cxyz = Path(self.dir_inspect / "all_offsets.npz")
        self.path_id_maps = Path(self.dir_inspect / "all_tile_id_maps.npz")

    def load_data(self):
        if not self.path_cxyz.exists() or not self.path_id_maps.exists():
            raise FileNotFoundError("Data files do not exist!")
        self.cxyz_obj = np.load(self.path_cxyz)
        self.tile_id_maps_obj = np.load(self.path_id_maps)

    def process_tile_id(
        self, tile_id: int, n_before: int, n_after: int, thresh: float
    ) -> None:
        win_size = n_before + n_after
        mapped_outliers = {}

        for axis in range(2):
            trace_dict = self.get_trace(tile_id, axis)
            if trace_dict is None:
                continue

            for vec_component in range(2):
                trace = {
                    sec_num: v[0][vec_component] for sec_num, v in trace_dict.items()
                }
                out_sec_nums = find_outliers(trace, win_size, thresh)

                for num in out_sec_nums:
                    y, x = trace_dict[num][1]
                    tid_map = self.tile_id_maps_obj[str(num)]
                    tid_a = int(tid_map[y][x])
                    tid_b = (
                        get_vert_tile_id(tid_map, tid_a)
                        if axis == 1
                        else int(tid_map[y][x + 1])
                    )
                    mapped_outliers[num] = (axis, vec_component, y, x, tid_a, tid_b)

        # Store into a .txt file
        if mapped_outliers:
            self.store_outliers(mapped_outliers)

        return

    def get_trace(
        self, tile_id: int, axis: int
    ) -> Optional[Dict[int, Tuple[np.ndarray, Tuple[int, int]]]]:
        trace_dict = {}
        for sec_num, tile_map in self.tile_id_maps_obj.items():
            try:
                y, x = np.where(tile_map == tile_id)
                if y.size == 0 or x.size == 0:
                    continue
                yx = (int(y[0]), int(x[0]))
                vec = self.cxyz_obj[sec_num][axis, :, yx[0], yx[1]]
                trace_dict[int(sec_num)] = (tuple(vec), yx)
            except (IndexError, KeyError):
                continue
        return trace_dict if trace_dict else None

    def store_outliers(self, mapped_outliers: dict) -> None:
        path_out = str(self.dir_inspect / "coarse_offset_outliers.txt")

        logging.info(f"Storing outliers to: {path_out}")

        fmt_outs = [np.array((k,) + v) for k, v in mapped_outliers.items()]

        file_exists = Path(path_out).exists()
        with open(path_out, "a") as f:
            if not file_exists:
                f.write("# Slice\tC\tZ\tY\tX\tTileID\tTileID_nn\n")
            np.savetxt(f, fmt_outs, fmt="%s", delimiter="\t")
        return

    def process_all_tile_ids(self, n_before, n_after, thresh):
        self.load_data()
        unique_tile_ids = self.get_unique_tile_ids()
        for tile_id in unique_tile_ids:
            self.process_tile_id(tile_id, n_before, n_after, thresh)

    def get_unique_tile_ids(self) -> set:
        unique_ids = set()
        for arr in self.tile_id_maps_obj.values():
            unique_ids.update(arr.flatten())
        unique_ids.discard(-1)
        return unique_ids


def main_get_cxyz_outliers(
    exp_path: str,
    n_before: int,
    n_after: int,
    thresh: float,
    trace_ids: Optional[Iterable[int]] = None,
):

    td = TraceOutlierDetector(exp_path)
    td.load_data()

    # Process specific or all tile-IDs
    if trace_ids:
        for tile_id in trace_ids:
            td.process_tile_id(tile_id, n_before, n_after, thresh)
    else:
        td.process_all_tile_ids(n_before, n_after, thresh)
    return


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="parsing_config.yaml")
    parser.add_argument(
        "--n_before",
        type=int,
        nargs=1,
        default=9,
        help="Number of coarse offsets from previous sections to compute mean.",
    )
    parser.add_argument(
        "--n_after",
        type=int,
        nargs=1,
        default=9,
        help="Number of coarse offsets from following sections to compute mean.",
    )
    parser.add_argument(
        "--thresh",
        type=float,
        nargs=1,
        default=5.0,
        help="Stddev multiplication factor to determine outlier from mean.",
    )
    parser.add_argument(
        "--trace-ids",
        type=int,
        nargs="*",
        default=None,
        help="Optional list of trace IDs (space-separated).",
    )

    args = parser.parse_args()

    with open(args.config) as f:
        config = yaml.safe_load(f)

    main_get_cxyz_outliers(
        exp_path=config["output_dir"],
        n_before=args.n_before,
        n_after=args.n_after,
        thresh=args.thresh,
        trace_ids=args.trace_ids,
    )
