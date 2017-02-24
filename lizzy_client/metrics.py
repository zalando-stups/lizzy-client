"""
Optional metricz
This module only works if metricz is installed
"""

try:
    import metricz
except ImportError:
    metricz = None

from .configuration import Configuration

METRICZ_AVAILABLE = bool(metricz)


def report_metric(metric_name: str, value: int, fail_silently: bool=True):
    """
    Tries to report a metric, ignoring all errors
    """
    if metricz is None:
        return

    configuration = Configuration()

    try:
        writer = metricz.MetricWriter(url=configuration.token_url,
                                      directory=configuration.credentials_dir,
                                      fail_silently=False)
        writer.write_metric(metric_name, value, {}, timeout=10)
    except Exception:
        if not fail_silently:
            raise
