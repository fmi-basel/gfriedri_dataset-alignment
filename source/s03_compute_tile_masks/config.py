from glob import glob
from os.path import basename
from pathlib import Path

import questionary
import yaml
from pydantic import BaseModel, field_serializer


class MaskConfig(BaseModel):
    section_paths: list[Path]
    smear_extend: int
    threshold: int = 20
    filter_size: int = 10
    range_limit: int = 20

    @field_serializer("section_paths")
    def path_to_str(paths: list[Path]):
        return [str(path) for path in paths]


def build_config():
    section_dir = questionary.path("Path to the section directory:").ask()
    start_section = int(
        questionary.text(
            "Start section",
            default="0",
            validate=lambda v: v.isdigit(),
        ).ask()
    )
    end_section = int(
        questionary.text(
            "End section",
            default="10",
            validate=lambda v: v.isdigit(),
        ).ask()
    )
    smear_extend = int(
        questionary.text(
            "Smear extend",
            default="20",
            validate=lambda v: v.isdigit(),
        ).ask()
    )
    threshold = int(
        questionary.text(
            "Threshold for silver particle detection",
            default="20",
            validate=lambda v: v.isdigit(),
        ).ask()
    )
    filter_size = int(
        questionary.text(
            "Sensitivity parameter for dynamic range of image region",
            default="10",
            validate=lambda v: v.isdigit(),
        ).ask()
    )
    range_limit = int(
        questionary.text(
            "Threshold for masking based on dynamic range",
            default="10",
            validate=lambda v: v.isdigit(),
        ).ask()
    )
    chunk_size = int(
        questionary.text(
            "Chunk size",
            default="10",
            validate=lambda v: v.isdigit(),
        ).ask()
    )

    def section_id(x):
        return int(basename(x).split("_")[0][1:])

    section_paths = glob(str(Path(section_dir) / "s*_g*"))
    section_paths = sorted(section_paths, key=section_id)
    section_paths = list(
        filter(lambda x: start_section <= section_id(x) <= end_section, section_paths)
    )
    for i, chunk in enumerate(range(0, len(section_paths), chunk_size)):
        config = MaskConfig(
            section_paths=section_paths[chunk : chunk + chunk_size],
            smear_extend=smear_extend,
            threshold=threshold,
            filter_size=filter_size,
            range_limit=range_limit,
        )
        with open(f"mask_config_{i}.yaml", "w") as f:
            yaml.safe_dump(config.dict(), f, sort_keys=False)


if __name__ == "__main__":
    build_config()
