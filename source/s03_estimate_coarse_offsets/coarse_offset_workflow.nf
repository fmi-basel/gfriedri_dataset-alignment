#!/usr/bin/env nextflow

params.config = "s03_estimate_coarse_offsets_workflow_config.yaml"

process PARSESECTIONS {
    label 'cpu'

    input:
    path config

    output:
    path "chunk_*.yaml"
    path "s03_estimate_coarse_offsets_config.yaml"

    script:
    """
    pixi run --frozen python $baseDir/parse_sections.py --config $config
    """
}

process ESTIMATECOARSEOFFSETS {
    label 'cpu'

    input:
    path chunk
    path config

    output:
    path "coarse_offset_paths.yaml"

    script:
    """
    pixi run --frozen python $baseDir/main.py --config $config --chunk $chunk
    """
}

workflow {
    (section_chunks, config) = PARSESECTIONS(params.config)
    coarse_offsets = ESTIMATECOARSEOFFSETS(section_chunks.flatten(), config)
}
