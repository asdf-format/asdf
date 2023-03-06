import numpy as np

ASDF_MAGIC = b"#ASDF"
BLOCK_MAGIC = b"\xd3BLK"
FITS_MAGIC = b"SIMPLE"

BLOCK_HEADER_BOILERPLATE_SIZE = 6

ASDF_STANDARD_COMMENT = b"ASDF_STANDARD"

INDEX_HEADER = b"#ASDF BLOCK INDEX"

# The maximum number of blocks supported
MAX_BLOCKS = 2**16
MAX_BLOCKS_DIGITS = int(np.ceil(np.log10(MAX_BLOCKS) + 1))

YAML_TAG_PREFIX = "tag:yaml.org,2002:"
YAML_END_MARKER_REGEX = rb"\r?\n\.\.\.((\r?\n)|$)"


STSCI_SCHEMA_URI_BASE = "http://stsci.edu/schemas/"
STSCI_SCHEMA_TAG_BASE = "tag:stsci.edu:asdf"


BLOCK_FLAG_STREAMED = 0x1


# ASDF max number size
MAX_BITS = 63
MAX_NUMBER = (1 << MAX_BITS) - 1
MIN_NUMBER = -((1 << MAX_BITS) - 2)
