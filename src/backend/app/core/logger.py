from app.core.config import settings
import logging
import threading
import queue

# logging.basicConfig()
# logging.getLogger('sqlalchemy.engine.Engine').disabled = True


class AsyncLoggingHandler(logging.Handler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log_queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self._process_log_queue)
        self.worker_thread.daemon = True
        self.worker_thread.start()

    def _process_log_queue(self):
        while True:
            try:
                record = self.log_queue.get()
                if record is None:  # Signal to exit the worker thread
                    break
                # Here we implement the actual logging behavior
                self._log_to_destination(record)
            except Exception:
                self.handleError(record)

    def _log_to_destination(self, record):
        """Define where and how you want to log. Here it's to the console."""
        try:
            # Get the formatted message
            msg = self.format(record)
            # You can replace this with any logging destination (file, etc.)
            print(msg)
        except Exception:
            self.handleError(record)

    def emit(self, record):
        """Puts the record in the queue to be processed by the worker thread."""
        self.log_queue.put(record)

    def close(self):
        """Gracefully shuts down the logging handler and joins the worker thread."""
        self.log_queue.put(None)
        self.worker_thread.join()
        super().close()


# Define your log level from settings
log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

# Set up the async handler
async_handler = AsyncLoggingHandler()

# Obtain the root logger
logger = logging.getLogger(__name__)
logger.setLevel(log_level)

# Remove any existing handlers
if logger.hasHandlers():
    logger.handlers.clear()

# Add the async handler
logger.addHandler(async_handler)

# Optional: Add a console handler as well
console_handler = logging.StreamHandler()
console_handler.setLevel(log_level)
logger.addHandler(console_handler)
