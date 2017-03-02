"""
Optional metricz
This module only works if metricz is installed
"""

from urllib.parse import urlparse

try:
    import metricz
except ImportError:
    metricz = None

from .configuration import Configuration
from .version import VERSION

METRICZ_AVAILABLE = bool(metricz)


def report_metric(metric_name: str, value: int, fail_silently: bool=True):
    """
    Tries to report a metric, ignoring all errors
    """
    if metricz is None:
        return

    configuration = Configuration()

    try:
        lizzy_domain = urlparse(configuration.lizzy_url).netloc
        lizzy_name, _ = lizzy_domain.split('.', 1)
    except:
        lizzy_name = 'UNKNOWN'

    tags = {
        'version': VERSION,
        'lizzy': lizzy_name
    }

    # noinspection PyBroadException
    try:
        writer = metricz.MetricWriter(url=configuration.token_url,
                                      directory=configuration.credentials_dir,
                                      fail_silently=False)
        writer.write_metric(metric_name, value, tags, timeout=10)
    except Exception:
        if not fail_silently:
            raise
