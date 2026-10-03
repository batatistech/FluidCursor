"""Disposable Fluent control panel process; the cursor/tray process stays lightweight."""
import json
import os
import sys
from dataclasses import asdict

from PyQt6.QtCore import QTimer
from PyQt6.QtNetwork import QLocalSocket
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from core.config import CursorConfig


def run_settings(server_name):
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    icon = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'icon.png')
    if os.path.isfile(icon):
        app.setWindowIcon(QIcon(icon))
    socket = QLocalSocket()
    socket.connectToServer(server_name)
    if not socket.waitForConnected(3000):
        print('FluidCursor is not running. Open the main app first.', file=sys.stderr)
        return 1
    from ui.settings_window import SettingsWindow
    config = CursorConfig.load()
    incoming = bytearray()
    def send(message):
        if socket.state() == QLocalSocket.LocalSocketState.ConnectedState:
            socket.write((json.dumps(message) + '\n').encode('utf-8'))
            socket.flush()

    def changed():
        send({'type': 'config', 'settings': asdict(config)})

    def exit_main():
        send({'type': 'exit'})
        socket.waitForBytesWritten(500)

    def request_language_change():
        QTimer.singleShot(0, rebuild_window)

    def rebuild_window():
        nonlocal win
        old = win
        page_name = old.stackedWidget.currentWidget().objectName()
        geometry = old.geometry()
        old._save_timer.stop()
        old._appearance_timer.stop()
        old.on_destroy_callback = None
        old.hide()
        old.deleteLater()
        win = SettingsWindow(config, changed, None,
                             on_destroy_callback=app.quit,
                             on_language_changed=request_language_change)
        win.on_exit_callback = exit_main
        pages = (win.basic_interface, win.app_interface, win.motion_interface,
                 win.click_interface, win.tilt_interface, win.fun_interface, win.sys_interface)
        page = next((item for item in pages if item.objectName() == page_name), win.sys_interface)
        win.stackedWidget.setCurrentWidget(page)
        win.setGeometry(geometry)
        win.show()
        win.raise_()
        win.activateWindow()

    win = SettingsWindow(config, changed, None,
                         on_destroy_callback=app.quit,
                         on_language_changed=request_language_change)
    win.on_exit_callback = exit_main

    def read_updates():
        incoming.extend(bytes(socket.readAll()))
        while b'\n' in incoming:
            line, _, tail = incoming.partition(b'\n')
            incoming[:] = tail
            try:
                message = json.loads(line)
            except (ValueError, UnicodeDecodeError):
                continue
            if message.get('type') == 'state':
                win.update_enabled_state(bool(message['enabled']))
                config.save()
            elif message.get('type') == 'show':
                win.showNormal()
                win.raise_()
                win.activateWindow()
            elif message.get('type') == 'close':
                win.close()
            elif message.get('type') == 'quit':
                app.quit()

    socket.readyRead.connect(read_updates)
    socket.disconnected.connect(app.quit)
    win.show()
    win.raise_()
    win.activateWindow()
    send({'type': 'ready'})
    # Data can arrive while the large GUI is still constructing; readyRead
    # might have fired before its callback was installed.
    QTimer.singleShot(0, read_updates)
    result = app.exec()
    config.save()
    send({'type': 'config', 'settings': asdict(config)})
    socket.waitForBytesWritten(500)
    socket.disconnectFromServer()
    return result
