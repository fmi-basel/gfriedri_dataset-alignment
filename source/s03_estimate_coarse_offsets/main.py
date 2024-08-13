from typing import Optional, Dict, Tuple, Union, Any

Vector = Union[
    Tuple[int, int], Tuple[int, int, int], Union[Tuple[int], Tuple[Any, ...]]
]  # [z]yx order


def compute_coarse_offset_section(
    self,
    co: Optional[Vector],
    store=bool,
    overlaps_xy=((200, 300), (200, 300)),
    min_range=((10, 100, 0), (10, 100, 0)),
    min_overlap=160,
    filter_size=10,
    max_valid_offset=400,
    sigma_horiz_pair=1.0,
    clahe: bool = True,
    masking: bool = False,
    overwrite_cxcy: bool = False,
    rewrite_masks: bool = False,
    kwargs_masks: Optional[Dict] = None,
) -> None:
    """
    Computes coarse offsets for entire section.

    :param co: Optional vector
    :param store: Boolean flag to store results
    :param overlaps_xy: Tuple for overlaps in x and y directions
    :param min_range: Tuple for minimum range values
    :param min_overlap: Minimum overlap
    :param filter_size: Filter size
    :param max_valid_offset: Maximum valid offset
    :param sigma_horiz_pair: Sigma for horizontal pair
    :param clahe: Boolean flag for CLAHE
    :param masking: Boolean flag for masking
    :param overwrite_cxcy: Boolean flag to overwrite cx_cy.json
    :param rewrite_masks: Boolean flag to write masks
    :param kwargs_masks: Optional dictionary for mask parameters
    :return: None
    """

    if kwargs_masks is None:
        kwargs_masks = dict(
            roi_thresh=20,
            max_vert_ext=200,
            edge_only=True,
            n_lines=20,
            store=True,
            filter_size=50,
            range_limit=0,
        )

    def process_masks():
        if not masking:
            self.mask_map = None
            # self.mask_map = self.roi_mask_map  # Disable smearing masks
        else:
            self.load_masks()
            if not self.mask_map or rewrite_masks:
                self.create_masks(**kwargs_masks)
        return

    if (self.path / "cx_cy.json").exists() and not overwrite_cxcy:
        sec_num = utils.get_section_num(self.path)
        msg = f"s{sec_num} cx_cy.json already exists. Skipping coarse offsets computation."
        logging.info(msg)
        return

    if self.tile_id_map is None:
        self.feed_section_data()

    if self.tile_map is None:
        self.load_tile_map(clahe=clahe)

    if self.tile_map is None:
        logging.warning(f"Computing coarse offsets s{self.section_num} failed.")
        return

    # Load or compute tile masks
    process_masks()

    cx, cy = stitch_rigid.compute_coarse_offsets(
        yx_shape=np.shape(self.tile_id_map),
        tile_map=self.tile_map,
        mask_map=self.mask_map,
        co=co,
        overlaps_xy=overlaps_xy,
        min_range=min_range,
        min_overlap=min_overlap,
        filter_size=filter_size,
        max_valid_offset=max_valid_offset,
        sigma_horiz_pair=sigma_horiz_pair,
    )

    # Save coarse offsets
    if store:
        cx = np.squeeze(cx)
        cy = np.squeeze(cy)
        cx_cy = np.array((cx, cy))
        self.cxy = cx_cy
        self.save_coarse_mat(cx_cy)

    self.clear_section()
    return
