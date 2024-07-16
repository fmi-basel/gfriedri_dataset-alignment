import os
from os.path import join

import questionary
import yaml
from parameter_config import AcquisitionConfig

def get_acquistion_config():
    sbem_root_dir = questionary.path("Path to the SBEM root directory:").ask()
    acquisition = questionary.text("Acquisition name:", default="run_0").ask()
    tile_grid = questionary.text("Tile Grid ID:", default="g0001").ask()
    grid_shape = tuple(
        map(
            int,
            questionary.text(
                "sbem_config.Grid Shape (rows, cols):",
                default="32, 42",
                validate=lambda v: all([x.replace(" ", "").isdigit() for x in v.split(",")]),
            ).ask().split(",")
        )
    )
    thickness = float(
        questionary.text(
            "sbem_config.Thickness:",
            default="25",
            validate=lambda v: v.replace(".", "").isdigit(),
        ).ask()
    )
    resolution_xy = float(
        questionary.text(
            "sbem_config.Resolution [XY]:",
            default="11",
            validate=lambda v: v.replace(".", "").isdigit(),
        ).ask()
    )

    return AcquisitionConfig(
        sbem_root_dir=sbem_root_dir,
        acquisition=acquisition,
        tile_grid=tile_grid,
        grid_shape=grid_shape,
        thickness=thickness,
        resolution_xy=resolution_xy,
    )


def build_config():
    output_dir = questionary.path("Path to the output directory:").ask()
    acquisition_config = get_acquistion_config()

    start_section = int(
        questionary.text(
            "start_section:",
            default="0",
            validate=lambda v: v.isdigit(),
        ).ask()
    )
    end_section = int(
        questionary.text(
            "end_section:",
            default="10",
            validate=lambda v: v.isdigit(),
        ).ask()
    )

    section_dir = join(output_dir, "sections")

    os.makedirs(section_dir, exist_ok=True)

    config = dict(
        output_dir=output_dir,
        acquisition_config=dict(acquisition_config),
        start_section=start_section,
        end_section=end_section,
    )

    with open("parsing_config.yaml", "w") as f:
        yaml.safe_dump(config, f, sort_keys=False)


if __name__ == "__main__":
    build_config()
