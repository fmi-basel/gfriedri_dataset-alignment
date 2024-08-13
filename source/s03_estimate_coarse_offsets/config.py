from pathlib import Path
from typing import Optional

import questionary
import yaml
from faim_ipa.utils import IPAConfig

CONFIG_NAME = "s03_estimate_coarse_offsets_config.yaml"

class CoarseOffsetsConfig(IPAConfig):
    apply_clahe_to_tiles: bool
    overlaps_xy: tuple[tuple[int, int], tuple[int, int]]
    min_range: tuple[tuple[int, int, int], tuple[int, int, int]]
    min_overlap: int
    filter_size: int
    max_valid_offset: int

    def save(self):
        self.make_paths_relative()
        with open(CONFIG_NAME, "w") as f:
            yaml.safe_dump(self.dict(), f, sort_keys=False)

        self.make_paths_absolute()

    @classmethod
    def load(cls, path: Optional[Path] = None):
        if path is None:
            path = Path(CONFIG_NAME)
        if path.exists():
            with open(path, "r") as f:
                config = cls(**yaml.safe_load(f))
                config.make_paths_absolute()
                return config
        else:
            return None

    @classmethod
    def ask_user(cls, config: Optional["CoarseOffsetsConfig"] = None):
        apply_clahe_to_tiles = bool(
            questionary.confirm(
                "Apply CLAHE to tiles",
                default=config.apply_clahe_to_tiles if config else False,
            ).ask()
        )
        overlaps_xy = (
            tuple(
                int(x) for x in questionary.text(
                    "Overlaps X",
                    default=str(config.overlaps_xy[0]) if config else "200,300",
                    validate=lambda x: x.replace(",", "").isdigit(),
                ).ask().split(",")
            ),
            tuple(
                int(y) for y in questionary.text(
                    "Overlaps Y",
                    default=str(config.overlaps_xy[1]) if config else "200,300",
                    validate=lambda x: x.replace(",", "").isdigit(),
                ).ask().split(",")
            ),
        )
        min_range = (
            tuple(
                int(x) for x in questionary.text(
                    "Min range X",
                    default=str(config.min_range[0]) if config else "0,10,100",
                    validate=lambda x: x.replace(",", "").isdigit(),
                ).ask().split(",")
            ),
            tuple(
                int(y) for y in questionary.text(
                    "Min range Y",
                    default=str(config.min_range[1]) if config else "0,10,100",
                    validate=lambda x: x.replace(",", "").isdigit(),
                ).ask().split(",")
            ),
        )
        min_overlap = int(
            questionary.text(
                "Min overlap",
                default=str(config.min_overlap) if config else "20",
                validate=lambda x: x.isdigit(),
            ).ask()
        )
        filter_size = int(
            questionary.text(
                "Filter size",
                default=str(config.filter_size) if config else "10",
                validate=lambda x: x.isdigit(),
            ).ask()
        )
        max_valid_offset = int(
            questionary.text(
                "Max valid offset",
                default=str(config.max_valid_offset) if config else "500",
                validate=lambda x: x.isdigit(),
            ).ask()
        )

        return cls(
            apply_clahe_to_tiles=apply_clahe_to_tiles,
            overlaps_xy=overlaps_xy,
            min_range=min_range,
            min_overlap=min_overlap,
            filter_size=filter_size,
            max_valid_offset=max_valid_offset,
        )

if __name__ == "__main__":
    config = CoarseOffsetsConfig.ask_user()
    config.save()
