import argparse
from glob import glob
from os.path import basename
from pathlib import Path

import yaml

from parse_sections_config import SmearMaskWorkflowConfig
from config import SmearMaskConfig

def main(wf_config: SmearMaskWorkflowConfig):
    section_id = lambda x: int(basename(x).split("_")[0][1:])

    section_paths = glob(str(Path(wf_config.section_dir) / "s*_g*"))
    section_paths = sorted(section_paths, key=section_id)
    section_paths = list(
        filter(lambda x: wf_config.start_section <= section_id(x) <= wf_config.end_section,
               section_paths))
    for i, chunk in enumerate(range(0, len(section_paths), wf_config.chunk_size)):
        config = SmearMaskConfig(
            section_paths=section_paths[chunk:chunk + wf_config.chunk_size],
            smear_extend=wf_config.smear_extend
        )
        with open(f"smear_mask_config_{i}.yaml", "w") as f:
            yaml.safe_dump(config.dict(), f, sort_keys=False)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=True)

    args = parser.parse_args()

    with open(args.config) as f:
        config = SmearMaskWorkflowConfig(**yaml.safe_load(f))

    main(config)