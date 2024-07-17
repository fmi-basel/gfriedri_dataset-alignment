from pathlib import Path

from source.s03_compute_tile_masks.tile_masking_section import TileMaskingSection


def compute_masks(section_path: Path):
    section = TileMaskingSection.load_from_yaml(str(section_path / "section.yaml"))
    print(section)


def main(section_paths: list[Path]):
    for section_path in section_paths:
        compute_masks(section_path)


if __name__ == "__main__":
    section_path = r"\\tungsten-nas.fmi.ch\tungsten\scratch\gmicro_sem\gfriedri\gitrepos\gfriedri_dataset-alignment\processed_data\mont-3\sections\s1000_g0"
    sections = [Path(section_path)]
    main(sections)
