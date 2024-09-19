import argparse
import multiprocessing
from typing import Optional, Iterable
import yaml

from inspection import Inspection
from inspection_utils import plot_trace_from_backup, get_tile_ids_set


def main_plot_traces(
    exp_path: str, trace_ids: Optional[Iterable[int]] = None, in_parallel: bool = False
):
    # Init experiment
    exp = Inspection(exp_path)

    traces_out_dir = exp.dir_inspect / "traces"
    if not traces_out_dir.exists():
        try:
            traces_out_dir.mkdir(parents=True, exist_ok=True)
            print(f"Directory created at: {traces_out_dir}")
        except Exception as e:
            print(f"Error creating directory: {e}")

    # Determine traces to be plotted
    ids_to_plot = sorted(list(get_tile_ids_set(str(exp.path_id_maps))))
    if trace_ids is not None:
        ids_to_plot = trace_ids

    # Create args list for trace plotting
    args_list = []
    for tile_id in ids_to_plot:
        print(f"Plotting trace of tile nr.: {tile_id}")
        plot_name = "t" + str(tile_id).zfill(4) + "_trace.png"
        args = (
            str(exp.path_cxyz),
            str(exp.path_id_maps),
            str(traces_out_dir / plot_name),
            tile_id,
            (None, None),
            0,
        )
        args_list.append(args)

    if in_parallel:
        num_proc = min(40, len(ids_to_plot))
        with multiprocessing.Pool(processes=num_proc) as pool:
            pool.starmap(plot_trace_from_backup, args_list)
    else:
        for i_args in args_list:
            plot_trace_from_backup(*i_args)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="parsing_config.yaml")
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

    main_plot_traces(exp_path=config["output_dir"], trace_ids=args.trace_ids)
