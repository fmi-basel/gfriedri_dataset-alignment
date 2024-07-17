#!/usr/bin/env nextflow

params.parse_sections_config = "smear_mask_workflow_config.yaml"

process PARSESECTIONS {
    label 'cpu'

    input:
    path config

    output:
    path "smear_mask_config_*.yaml"

    script:
    """
    pixi run --frozen python $baseDir/parse_sections.py --config $config
    """
}

process COMPUTESMEARMASKS {
    label 'cpu'

    input:
    path config

    output:
    path "sections_with_smear_masks.yaml"

    script:
    """
    pixi run --frozen python $baseDir/create_simple_smear_masks.py --config $config
    """
}

workflow {
    section_chunks = PARSESECTIONS(params.parse_sections_config)
    smear_masks = COMPUTESMEARMASKS(section_chunks.flatten())
}