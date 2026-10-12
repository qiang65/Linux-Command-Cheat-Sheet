#!/usr/bin/env python3
"""Linux 手册 · 启动入口

用法：
    python3 app.py                # 正常启动
    python3 app.py --rebuild      # 重建数据库并重新灌入种子数据
    python3 app.py --db <路径>     # 使用指定数据库文件
"""
import hashlib
import os
import sys

APP_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(APP_DIR, "src"))

import PyQt5

QT_PLATFORM_PLUGIN_DIR = os.path.join(
    os.path.dirname(PyQt5.__file__), "Qt5", "plugins", "platforms")
if os.path.isdir(QT_PLATFORM_PLUGIN_DIR):
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = QT_PLATFORM_PLUGIN_DIR

from PyQt5.QtCore import Qt                                        # noqa: E402
from PyQt5.QtNetwork import QLocalServer, QLocalSocket            # noqa: E402
from PyQt5.QtWidgets import QApplication, QMessageBox             # noqa: E402

from db import Store                                          # noqa: E402
from main_window import MainWindow                            # noqa: E402


def user_data_dir():
    if not getattr(sys, "frozen", False):
        return os.path.join(APP_DIR, "data")
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    elif sys.platform == "darwin":
        base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME", os.path.join(
            os.path.expanduser("~"), ".local", "share"))
    path = os.path.join(base, "LinuxHandbook")
    os.makedirs(path, exist_ok=True)
    return path


def parse_args(argv):
    db_path = os.path.join(user_data_dir(), "linux.db")
    rebuild = "--rebuild" in argv
    if "--db" in argv:
        try:
            db_path = os.path.abspath(argv[argv.index("--db") + 1])
        except IndexError:
            print("--db 需要一个路径参数")
            sys.exit(2)
    return db_path, rebuild


def instance_id(db_path):
    return "linuxHandbook-" + hashlib.sha1(db_path.encode()).hexdigest()[:12]


def try_connect_existing(app_id):
    """已有实例在运行则唤醒它并返回 True。"""
    sock = QLocalSocket()
    sock.connectToServer(app_id)
    if sock.waitForConnected(400):
        sock.write(b"raise")
        sock.waitForBytesWritten(400)
        sock.disconnectFromServer()
        return True
    return False


def main():
    db_path, rebuild = parse_args(sys.argv)
    app = QApplication(sys.argv)
    app.setApplicationName("Linux 手册")
    app.setApplicationDisplayName("Linux 手册")
    app.setOrganizationName("LinuxHandbook")

    app_id = instance_id(db_path)
    if try_connect_existing(app_id):
        print("已有实例在运行，已唤醒其窗口。")
        return 0

    server = QLocalServer()
    server.removeServer(app_id)
    if not server.listen(app_id):
        server = None

    store = Store(db_path)
    store.ensure_categories()
    seed = os.path.join(APP_DIR, "data", "seed.json")
    if rebuild:
        if os.path.exists(seed):
            store.seed_from_json(seed, replace=True)
        else:
            print(f"种子文件不存在：{seed}")
    elif store.is_empty() and os.path.exists(seed):
        store.seed_from_json(seed, replace=False)
        print("首次运行：已创建数据库并灌入初始数据。")

    win = MainWindow(store, APP_DIR)
    if server is not None:
        server.newConnection.connect(win.wake_up)
        win.local_server = server
    win.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
