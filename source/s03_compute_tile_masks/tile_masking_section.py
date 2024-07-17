import numpy as np
from sbem.record.Section import Section


class TileMaskingSection(Section):
    tile_smearing_masks = {}

    def set_smearing_mask(self, tile_id: int, mask: np.ndarray):
        self.tile_smearing_masks[tile_id] = mask

    def get_tile_shape(self) -> tuple[int, int]:
        return self.get_tile_height(), self.get_tile_width()

    def create_simple_smearing_masks(self, smr_extend: int):

        assert smr_extend >= 0, "smr_extend for tile masks can no tbe negative!"
        smr_mask = np.zeros(shape=self.get_tile_shape(), dtype=bool)
        smr_mask[:smr_extend] = True

        for tile_id in self.tiles.keys():
            self.tile_smearing_masks[tile_id] = smr_mask
