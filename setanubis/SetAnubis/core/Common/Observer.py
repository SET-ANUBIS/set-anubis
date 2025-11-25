import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class FileCreationHandler(FileSystemEventHandler):
    def __init__(self, observer):
        self.observer = observer

    def on_created(self, event):
        self.observer.file_created(event.src_path)

class FileObserver:
    _instance = None

    def __new__(cls, directory_to_watch=None):
        if cls._instance is None:
            cls._instance = super(FileObserver, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, directory_to_watch=None):
        if self._initialized:
            return
        self._initialized = True

        self.directory_to_watch = directory_to_watch
        self.observed_files = {}
        self.observer = Observer()
        self.event_handler = FileCreationHandler(self)

    def watch_file(self, file_path, callback):
        self.observed_files[file_path] = callback

    def start(self):
        if self.directory_to_watch is None:
            raise ValueError("Directory to watch is not set")
        self.observer.schedule(self.event_handler, self.directory_to_watch, recursive=False)
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()

    def file_created(self, file_path):
        if file_path in self.observed_files:
            self.observed_files[file_path](file_path)

# Usage example
def file_callback(file_path):
    logger.info(f"File created: {file_path}")