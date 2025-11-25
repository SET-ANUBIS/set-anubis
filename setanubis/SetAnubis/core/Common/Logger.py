"""
Module CustomLogger

This module provides a class for logging management.

Classes:
    CustomLogger -- Manages the creation and configuration of loggers with file and stream handlers.

Usage:
    logger = CustomLogger("example_logger", "path/to/logfile.log").get_logger()
    logger.info("This is an info message")
"""

import logging
import os

class CustomLogger:
    """
    A class to create and configure custom loggers with file and stream handlers.

    Attributes:
        _instances (dict): A dictionary to maintain singleton logger instances.

    Methods:
        __new__(cls, name: str, log_file: str, level: int = logging.DEBUG) -- Creates a new instance of CustomLogger if it does not already exist.
        __init__(self, name: str, log_file: str, level: int = logging.DEBUG) -- Initializes the logger with the specified name and log file.
        get_logger(self) -- Returns the logger instance.
    """
    _instances = {}

    def __new__(cls, name: str, log_file: str, level: int = logging.DEBUG):
        """
        Creates a new instance of CustomLogger if it does not already exist.

        Parameters:
            name (str): The name of the logger.
            log_file (str): The path to the log file.
            level (int): The logging level. Default is logging.DEBUG.

        Returns:
            CustomLogger: The logger instance.
        """
        if name not in cls._instances:
            instance = super(CustomLogger, cls).__new__(cls)
            instance._initialized = False
            cls._instances[name] = instance
        return cls._instances[name]

    def __init__(self, name: str, log_file: str, level: int = logging.DEBUG):
        """
        Initializes the logger with the specified name and log file.

        Parameters:
            name (str): The name of the logger.
            log_file (str): The path to the log file.
            level (int): The logging level. Default is logging.DEBUG.
        """
        if self._initialized:
            return
        self._initialized = True
        
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        fh = logging.FileHandler(log_file)
        fh.setLevel(level)
        
        ch = logging.StreamHandler()
        ch.setLevel(level)
        
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        if not self.logger.handlers:
            self.logger.addHandler(fh)
            self.logger.addHandler(ch)
    
    def get_logger(self):
        """
        Returns the logger instance.

        Returns:
            logging.Logger: The logger instance.
        """
        return self.logger
