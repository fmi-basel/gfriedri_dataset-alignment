import sys
from faim_ipa.utils import get_git_root
sys.path.append(str(get_git_root()))

from source.s01_parsing_sbem_acquisition.s01_parse_data import section_in_range

def test_section_in_range():
    in_range = section_in_range("s100_g0", 100, 200)
    assert in_range

    in_range = section_in_range("s100_g0", 101, 200)
    assert not in_range

    in_range = section_in_range("s100_g0", 99, 100)
    assert in_range

    in_range = section_in_range("s100_g0", 90, 99)
    assert not in_range
