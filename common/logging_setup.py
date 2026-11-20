import logging
def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s'))
        logger.addHandler(h)
        logger.setLevel(logging.INFO)
    return logger
def log_step(logger, invoice_id, step, **extra):
    logger.info("invoice_id=%s step=%s %s", invoice_id, step, extra or "")