from pathlib import Path
from typing import Optional

import questionary
import yaml
from faim_ipa.utils import IPAConfig
from pydantic import field_serializer
from config import CoarseOffsetsConfig

CONFIG_NAME = "s03_estimate_coarse_offsets_workflow_config.yaml"

class EstimateCoarseOffsetsWorkflowConfig(IPAConfig):
    section_dir: Path
    start_section: int
    end_section: int
    chunk_size: int
    coarse_offsets_config: CoarseOffsetsConfig

    @field_serializer("section_dir")
    def path_to_str(path: Path):
        return str(path)

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
    def ask_user(cls, config: Optional["EstimateCoarseOffsetsWorkflowConfig"] = None):
        section_dir = Path(
            questionary.path(
                "Path to the section directory:",
                default=str(config.section_dir) if config else "",
            ).ask()
        )
        start_section = int(
            questionary.text(
                "Start section",
                default=str(config.start_section) if config else "0",
                validate=lambda v: v.isdigit(),
            ).ask()
        )
        end_section = int(
            questionary.text(
                "End section",
                default=str(config.end_section) if config else "10",
                validate=lambda v: v.isdigit(),
            ).ask()
        )
        chunk_size = int(
            questionary.text(
                "Chunk size",
                default=str(config.chunk_size) if config else "10",
                validate=lambda v: v.isdigit(),
            ).ask()
        )
        coarse_offsets_config = CoarseOffsetsConfig.ask_user(
            config.coarse_offsets_config if config else None
        )

        return cls(
            section_dir=section_dir,
            start_section=start_section,
            end_section=end_section,
            chunk_size=chunk_size,
            coarse_offsets_config=coarse_offsets_config,
        )


if __name__ == "__main__":
    config = EstimateCoarseOffsetsWorkflowConfig.ask_user()
    config.save()
