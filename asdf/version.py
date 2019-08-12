from pkg_resources import get_distribution, DistributionNotFound

try:
    version = get_distribution('asdf').version
except DistributionNotFound:
    # package is not installed
    version = "unknown"

__all__ = ['version']
