from .cli import main
from .metrics import report_metric

try:
    main()
except Exception:
    report_metric("bus.lizzy-client.failed", 1)
    raise
except SystemExit as sys_exit:
    if sys_exit.code == 0:
        report_metric("bus.lizzy-client.success", 1)
    else:
        report_metric("bus.lizzy-client.failed", 1)
    raise
else:
    report_metric("bus.lizzy-client.success", 1)
