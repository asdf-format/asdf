from pkg_resources import get_distribution, DistributionNotFound

try:
    version = get_distribution(__package__).version
except DistributionNotFound:
    # package is not installed
    version = "unknown"
