from os import getenv
import logging.config

import structlog

app_env = getenv("APP_ENV", "Local")


# configure logging
def env_injector(_, __, event_dict):
    event_dict["environment"] = app_env.lower()
    return event_dict


class SetupLogging(object):
    handlers = ["console"] if app_env in ["Local", "Docker", "Ci"] else ["default"]
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processor": structlog.processors.JSONRenderer(),
                    "foreign_pre_chain": [
                        env_injector,
                        structlog.stdlib.add_log_level,
                        structlog.processors.TimeStamper(fmt="%Y-%m-%dT%H:%M:%S.%fZ", key="time"),
                    ],
                },
                "console": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processor": structlog.dev.ConsoleRenderer(),
                    "foreign_pre_chain": [
                        structlog.stdlib.add_log_level,
                        structlog.processors.TimeStamper(fmt="%H:%M:%S", key="time", utc=False),
                    ],
                },
            },
            "handlers": {
                "default": {"level": "INFO", "class": "logging.StreamHandler", "formatter": "default"},
                "console": {"level": "DEBUG", "class": "logging.StreamHandler", "formatter": "console"},
            },
            "loggers": {
                "": {"handlers": handlers, "level": "INFO", "propagate": True},
                "gunicorn.error": {"handlers": handlers, "level": "INFO", "propagate": False},
                "gunicorn.access": {"handlers": handlers, "level": "INFO", "propagate": False},
                "werkzeug": {"handlers": handlers, "level": "INFO", "propagate": False},
            },
        }
    )
    structlog.configure(
        processors=[
            env_injector,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
