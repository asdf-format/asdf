import numpy as np

RNG = np.random.default_rng(619)


def create_small_tree():
    x = np.arange(0, 10, dtype=float)
    return {
        "science_data": x,
        "subset": x[3:-3],
        "skipping": x[::2],
        "not_shared": np.arange(10, 0, -1, dtype=np.uint8),
    }


def create_large_tree():
    # These are designed to be big enough so they don't fit in a
    # single block, but not so big that RAM/disk space for the tests
    # is enormous.
    x = RNG.normal(size=(256, 256))
    y = RNG.normal(size=(16, 16, 16))
    return {
        "science_data": x,
        "more": y,
    }
