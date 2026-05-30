import sys
import os
import logging
import platform
from logging.handlers import RotatingFileHandler

os.makedirs("logs", exist_ok=True)

# --- ZMIANA NAZWY ---
logger = logging.getLogger("KuzenBot")
logger.setLevel(logging.DEBUG)

if logger.hasHandlers():
    logger.handlers.clear()

# Zapisywanie logów do pliku logs/KuzenBot.log (rotacja do 5 plików po 5MB)
file_formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - [%(threadName)s] - %(filename)s:%(lineno)d - %(message)s'
)
# --- ZMIANA NAZWY PLIKU ORAZ ROZMIARU (5 MB) ---
file_handler = RotatingFileHandler(
    "logs/KuzenBot.log", 
    maxBytes=5*1024*1024, 
    backupCount=5, 
    encoding="utf-8"
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

original_stdout = sys.stdout
original_stderr = sys.stderr

class StreamToLogger:
    def __init__(self, logger, log_level, stream):
        self.logger = logger
        self.log_level = log_level
        self.stream = stream

    def write(self, buf):
        # Wypisujemy na oryginalną konsolę
        try:
            self.stream.write(buf)
        except Exception:
            pass
            
        # Zapisujemy do logu w pliku
        try:
            lines = buf.rstrip().splitlines()
            for line in lines:
                cleaned = line.rstrip()
                if cleaned:
                    self.logger.log(self.log_level, cleaned)
        except Exception:
            pass

    def flush(self):
        try:
            self.stream.flush()
        except:
            pass

def setup_logging():
    # Przekierowanie standardowych strumieni
    sys.stdout = StreamToLogger(logger, logging.INFO, original_stdout)
    sys.stderr = StreamToLogger(logger, logging.ERROR, original_stderr)
    
    # Nagłówek systemowy
    logger.info("==================================================")
    # --- ZMIANA W POWITANIU ---
    logger.info("KuzenBot - Rozpoczęcie działania aplikacji")
    logger.info(f"System: {platform.system()} {platform.release()} ({platform.version()})")
    logger.info(f"Architektura: {platform.machine()}")
    logger.info(f"Python: {sys.version}")
    logger.info(f"Katalog roboczy: {os.getcwd()}")
    logger.info("==================================================")