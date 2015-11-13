import logging

def debug1(self, message, *args, **kwargs):
    if self.isEnabledFor(logging.DEBUG-1):
        self._log(logging.DEBUG-1, message, args, kwargs)

def debug2(self, message, *args, **kwargs):
    if self.isEnabledFor(logging.DEBUG-2):
        self._log(logging.DEBUG-2, message, args, kwargs)

def debug3(self, message, *args, **kwargs):
    if self.isEnabledFor(logging.DEBUG-3):
        self._log(logging.DEBUG-3, message, args, kwargs)

def debug4(self, message, *args, **kwargs):
    if self.isEnabledFor(logging.DEBUG-4):
        self._log(logging.DEBUG-4, message, args, kwargs)


def setup_logging(debug=None, noop=False):
    logger = logging.getLogger()
    if debug is not None:
        logging_level = logging.DEBUG-debug
    else:
        logging_level = logging.INFO
    #print logging_level
    if noop:
        logging_format = '[%(asctime)s] %(levelname)s: %(message)s [NOOP]'
    else:
        logging_format = '[%(asctime)s] %(levelname)s: %(message)s'
    logging_datefmt = '%Y-%m-%dT%H:%M:%S'
    logger.setLevel(logging_level)
    ch = logging.StreamHandler()
    formatter = logging.Formatter(logging_format)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("paramiko").setLevel(logging.WARNING)
    logging.addLevelName(logging.DEBUG-1, 'DEBUG1')
    logging.Logger.debug1 = debug1
    logging.addLevelName(logging.DEBUG-2, 'DEBUG2')
    logging.Logger.debug2 = debug2
    logging.addLevelName(logging.DEBUG-3, 'DEBUG3')
    logging.Logger.debug3 = debug3
    logging.addLevelName(logging.DEBUG-4, 'DEBUG4')
    logging.Logger.debug4 = debug4
    #logger.debug("DEBUG")
    #logger.debug1("DEBUG1")
    #logger.debug2("DEBUG2")
    #logger.debug3("DEBUG3")
    #logger.debug4("DEBUG4")
