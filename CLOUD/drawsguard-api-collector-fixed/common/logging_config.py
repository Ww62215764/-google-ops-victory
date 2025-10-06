import logging
import sys
from google.cloud import logging as cloud_logging
from google.cloud.logging.handlers import CloudLoggingHandler

def setup_dual_logging(service_name: str, level: int = logging.INFO):
    """
    Configures logging to output to both console and Google Cloud Logging.

    This setup ensures that logs are available for local development (console)
    and for production monitoring, alerting, and analysis (Google Cloud).

    Args:
        service_name (str): The name of the service, used to identify logs
                            in Google Cloud Logging.
        level (int): The minimum logging level to capture (e.g., logging.INFO).
    """
    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove any existing handlers to avoid duplication
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 1. Console Handler (for local development and immediate feedback)
    console_handler = logging.StreamHandler(sys.stdout)

    # Create a formatter that adds severity, timestamp, and message
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)

    # Add the console handler to the root logger
    root_logger.addHandler(console_handler)

    # 2. Google Cloud Logging Handler (for production)
    try:
        # Instantiate a client
        client = cloud_logging.Client()

        # Create a handler that attaches to the root logger
        cloud_handler = CloudLoggingHandler(client, name=service_name)

        # The CloudLoggingHandler will automatically handle formatting for Cloud Logging.
        # It correctly sets severity and other structured log fields.
        root_logger.addHandler(cloud_handler)

        logging.info(f"Successfully configured dual logging for service '{service_name}'.")
        logging.info("Logs will now be sent to both Console and Google Cloud Logging.")

    except Exception as e:
        logging.error(f"Failed to configure Google Cloud Logging: {e}", exc_info=True)
        logging.warning("Continuing with console-only logging.")
