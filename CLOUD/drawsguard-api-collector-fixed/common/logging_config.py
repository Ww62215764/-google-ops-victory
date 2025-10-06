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

# Example usage:
if __name__ == '__main__':
    # Configure logging for a hypothetical service
    setup_dual_logging("my-test-service")

    # Get a logger for the current module
    logger = logging.getLogger(__name__)

    # Log messages with different severity levels
    logger.debug("This is a debug message. It won't be shown if level is INFO.")
    logger.info("This is an informational message.")
    logger.warning("This is a warning message.")
    logger.error("This is an error message.")

    # This is a placeholder for demonstrating logging levels.
    # In a real application, you would have actual logic here.
    try:
        pass  # Removed the useless expression '1 / 0'
    except ZeroDivisionError:
        logger.critical("A critical error occurred.", exc_info=True)
