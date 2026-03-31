import logging
import os
from datetime import datetime

LOG_DIR = "logs"

def init_logger():
    os.makedirs(LOG_DIR, exist_ok=True)
    filename = datetime.now().strftime("agent_%Y%m%d_%H%M%S.log")

    logging.basicConfig(
        filename=os.path.join(LOG_DIR, filename),
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

def log(msg):
    logging.info(msg)