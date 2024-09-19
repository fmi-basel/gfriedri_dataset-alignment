import argparse
import yaml

from inspection import Inspection
from inspection_utils import locate_inf_vals


def main(exp_path: str):
    exp = Inspection(exp_path)
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

    main(exp_path=config["output_dir"])
