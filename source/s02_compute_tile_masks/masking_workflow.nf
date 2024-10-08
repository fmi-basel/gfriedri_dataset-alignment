#!/usr/bin/env nextflow

params.parse_sections_config = "mask_workflow_config.yaml"

process PARSESECTIONS {
    label 'cpu'

    input:
    path config

    output:
    path "mask_config_*.yaml"

    script:
    """
    pixi run --frozen python $baseDir/parse_sections.py --config $config
    """
}

process COMPUTEMASKS {
    label 'cpu'

    input:
    path config

    output:
    path "sections_with_masks.yaml"

    script:
    """
    pixi run --frozen python $baseDir/create_masks.py --config $config
    """
}

workflow {
    section_chunks = PARSESECTIONS(params.parse_sections_config)
    smear_masks = COMPUTEMASKS(section_chunks.flatten())
}
