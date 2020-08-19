import logging

import colorlog
import jsonschema

from .config import settings
from .utils.netcdf import (get_dimensions, get_global_attributes,
                           get_variables, open_dataset)


class File(object):

    def __init__(self, file_path):
        self.path = file_path.relative_to(settings.UNCHECKED_PATH)
        self.abs_path = file_path

        self.has_warnings = False
        self.has_errors = False
        self.logger = None
        self.handler = None
        self.dataset = None
        self.specifiers = {}

    @property
    def json(self):
        return {
            'dimensions': get_dimensions(self.dataset),
            'variables': get_variables(self.dataset),
            'global_attributes': get_global_attributes(self.dataset),
            'specifiers': self.specifiers
        }

    def open(self):
        self.dataset = open_dataset(self.abs_path)
        self.logger = self.get_logger()
        self.debug('File opened.')

    def close(self):
        self.debug('File closed.')
        self.dataset.close()
        if self.handler:
            self.handler.close()

    def debug(self, *args, **kwargs):
        self.logger.debug(*args, **kwargs)

    def info(self, *args, **kwargs):
        self.logger.info(*args, **kwargs)

    def warn(self, *args, **kwargs):
        self.logger.warn(*args, **kwargs)
        self.has_warnings = True

    def error(self, *args, **kwargs):
        self.logger.error(*args, **kwargs)
        self.has_errors = True

    def critical(self, *args, **kwargs):
        self.logger.critical(*args, **kwargs)

    def is_clean(self):
        return not (self.has_warnings or self.has_errors)

    def get_logger(self):
        # setup a log handler for the command line and one for the file
        logger_name = str(self.path)
        logger = colorlog.getLogger(logger_name)

        # do not propagate messages to the root logger,
        # which is configured in settings.setup()
        logger.propagate = False

        # add handlers
        logger.addHandler(self.get_stream_handler())
        if settings.LOG_PATH:
            logger.addHandler(self.get_file_handler())

        return logger

    def get_stream_handler(self):
        formatter = colorlog.ColoredFormatter(' %(log_color)s%(levelname)-9s: %(message)s%(reset)s')

        handler = colorlog.StreamHandler()
        handler.setLevel(settings.LOG_LEVEL)
        handler.setFormatter(formatter)

        return handler

    def get_file_handler(self):
        log_path = settings.LOG_PATH / self.path.with_suffix('.log')
        log_path.parent.mkdir(parents=True, exist_ok=True)

        formatter = logging.Formatter(' %(levelname)-9s: %(message)s')

        self.handler = logging.FileHandler(log_path, 'w+')
        self.handler.setLevel(logging.INFO)
        self.handler.setFormatter(formatter)

        return self.handler

    def match(self):
        match = settings.PATTERN['file'].match(self.path.name)
        if match:
            for key, value in match.groupdict().items():
                if value is not None:
                    if value.isdigit():
                        self.specifiers[key] = int(value)
                    else:
                        self.specifiers[key] = value

            self.info('File matched: %s.', self.specifiers)
        else:
            self.error('File did not match.')

    def validate(self):
        try:
            jsonschema.validate(schema=settings.SCHEMA, instance=self.json)
        except jsonschema.exceptions.ValidationError as e:
            self.error('Failed to validate with JSON schema: %s\n%s', self.json, e)
