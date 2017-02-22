from .cli import main
from .metrics import report_metric

try:
    main()
except (Exception, SystemExit):
    report_metric("bus.lizzy-client.failed", 1)
    raise
else:
    report_metric("bus.lizzy-client.success", 1)
