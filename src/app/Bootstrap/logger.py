import logging

# logging conf
logger = logging.getLogger()
for handler in logger.handlers:
    logger.removeHandler(handler)

log_format = "%(asctime)s delegator-api %(levelname)s %(message)s"
logging.basicConfig(format=log_format, level=logging.INFO)
