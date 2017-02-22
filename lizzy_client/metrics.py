"""
Optional metricz
This module only works if metriz is installed
"""

try:
    import metricz
except ImportError:
    metricz = None


def report_metric(metric_name: str, value: int):
    """
    Tries to report a metric, ignoring all errors
    """
    if metricz is None:
        return

    writer = metricz.MetricWriter()
    try:
        writer.write_metric(metric_name, value, {}, timeout=10)
    except:
        pass
