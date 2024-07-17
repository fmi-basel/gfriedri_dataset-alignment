from pathlib import Path

import questionary
import yaml
from pydantic import BaseModel, field_serializer


class SmearMaskWorkflowConfig(BaseModel):
    section_dir: Path
    start_section: int
    end_section: int
    smear_extend: int
    chunk_size: int

    @field_serializer("section_dir")
    def path_to_str(path: Path):
        return str(path)

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
    chunk_size = int(
        questionary.text(
            "Chunk size",
            default="10",
            validate=lambda v: v.isdigit(),
        ).ask()
    )

    config = SmearMaskWorkflowConfig(
        section_dir=section_dir,
        start_section=start_section,
        end_section=end_section,
        smear_extend=smear_extend,
        chunk_size=chunk_size
    )

    with open("smear_mask_workflow_config.yaml", "w") as f:
        yaml.safe_dump(config.dict(), f, sort_keys=False)

if __name__ == "__main__":
    build_config()
    