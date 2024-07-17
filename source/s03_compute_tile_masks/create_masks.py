import argparse
from pathlib import Path

import yaml

from config import MaskConfig
from tile_masking_section import TileMaskingSection


def compute_masks(
    section_path: Path,
    smear_extend: int,
    threshold: int,
    filter_size: int,
    range_limit: int,
):
    section = TileMaskingSection.load_from_yaml(str(section_path / "section.yaml"))
    section.create_simple_smearing_masks(smear_extend=smear_extend)
    section.create_resin_masks(threshold, filter_size, range_limit)
    section.save(str(section_path.parent), overwrite=False)


def main(config: MaskConfig):
    done_sections = []
    for section_path in config.section_paths:
        compute_masks(
            section_path,
            smear_extend=config.smear_extend,
            threshold=config.threshold,
            filter_size=config.filter_size,
            range_limit=config.range_limit,
        )
        done_sections.append(str(section_path))

    with open("sections_with_masks.yaml", "w") as f:
        yaml.safe_dump(done_sections, f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=True)

    args = parser.parse_args()

    with open(args.config) as f:
        config = MaskConfig(**yaml.safe_load(f))

    main(config)
