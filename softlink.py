import os
import time
import shutil
import logging
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler
import configparser

# 设置日志
def setup_logging(log_path):
    if os.path.isdir(log_path):
        log_file = os.path.join(log_path, "softlink.log")
    else:
        log_file = log_path

    logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def log_info(message):
    logging.info(message)
    print(f"INFO: {message}")

def log_error(message):
    logging.error(message)
    print(f"ERROR: {message}")

# 读取配置文件
config = configparser.ConfigParser()
config.read('config.ini')
compatibility_mode = config.getboolean('settings', 'compatibility_mode')
SOURCE_DIR = os.path.abspath(config['paths']['SOURCE_DIR'])
DEST_DIR = os.path.abspath(config['paths']['DEST_DIR'])
LOG_PATH = os.path.abspath(config['paths']['LOG_PATH'])

LINK_FILE_EXTENSIONS = config['settings']['LINK_FILE_EXTENSIONS'].split(',')
COPY_FILE_EXTENSIONS = config['settings']['COPY_FILE_EXTENSIONS'].split(',')

setup_logging(LOG_PATH)

# 检查路径
for path in [SOURCE_DIR, DEST_DIR, LOG_PATH]:
    if not os.path.exists(path):
        log_error(f"路径 {path} 不存在")

def create_symlink_and_copy(event_path: str):
    relative_path = os.path.relpath(event_path, SOURCE_DIR)
    dest_folder = os.path.dirname(os.path.join(DEST_DIR, relative_path))
    dest_file = os.path.join(DEST_DIR, relative_path)

    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)

    file_ext = os.path.splitext(event_path)[1].lower()

    if os.path.exists(dest_file):
        log_info(f"{event_path} 已存在，跳过")
        return

    if file_ext in LINK_FILE_EXTENSIONS:
        try:
            os.symlink(event_path, dest_file)
            log_info(f"{event_path} 创建软链完成")
        except OSError as e:
            log_error(f"从 {event_path} 到 {dest_file} 创建软链接时出错: {str(e)}")
    elif file_ext in COPY_FILE_EXTENSIONS:
        try:
            shutil.copy(event_path, dest_file)
            log_info(f"{event_path} 复制完成")
        except OSError as e:
            log_error(f"从 {event_path} 到 {dest_file} 复制时出错: {str(e)}")
    else:
        log_info(f"{event_path} 的文件类型不在预期的范围内，跳过")

class FileMonitorHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            create_symlink_and_copy(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            create_symlink_and_copy(event.dest_path)

    def on_deleted(self, event):
        if not event.is_directory:
            relative_path = os.path.relpath(event.src_path, SOURCE_DIR)
            dest_file = os.path.join(DEST_DIR, relative_path)
            if os.path.exists(dest_file):
                os.remove(dest_file)
                log_info(f"{dest_file} 由于源文件删除而被删除")

if __name__ == "__main__":
    event_handler = FileMonitorHandler()

    if compatibility_mode:
        observer = PollingObserver(timeout=10)
    else:
        observer = Observer()

    observer.schedule(event_handler, path=SOURCE_DIR, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()