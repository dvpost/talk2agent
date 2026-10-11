"""Ordered system insertion, focus checks and clipboard ownership."""

import sys
import time
from collections import deque

from PySide6.QtCore import QObject, QTimer, Signal

from .input import ModifiersHeld, check_focus, is_wayland, modifiers_pressed, paste, windows_unicode


class InsertionQueue(QObject):
    failed = Signal(str, str)
    idle = Signal()

    def __init__(self, target: str, portal=None, mode: str = "auto"):
        super().__init__()
        self.target = target
        self.portal = portal
        self.mode = mode
        self.queue = deque()
        self.busy = False
        self.suspended = False
        self.current = ""
        self.paste_started = 0.0
        self.clipboard_written = False
        self.last_clipboard_text = ""
        self.transfer = None
        self.delivery_uncertain = False

    def add(self, text: str):
        if self.suspended:
            self.failed.emit("Вставка приостановлена", text)
            return
        self.queue.append(text)
        if not self.busy:
            self._next()

    def _fail(self, error):
        self._close_transfer()
        rest = self.current + "".join(self.queue)
        self.queue.clear()
        self.current = ""
        self.busy = False
        self.suspended = True
        self.failed.emit(str(error), rest)
        self.idle.emit()

    def suspend(self) -> str:
        if self.transfer is not None and self.transfer.sent:
            rest = "".join(self.queue)
            self.queue.clear()
            self.suspended = True
            return rest
        self._close_transfer()
        rest = self.current + "".join(self.queue)
        self.queue.clear()
        self.current = ""
        self.busy = False
        self.suspended = True
        self.idle.emit()
        return rest

    def _close_transfer(self):
        if self.transfer is not None:
            self.delivery_uncertain = self.transfer.sent
            self.transfer.close()
            self.transfer = None

    def _delivered(self):
        self.transfer.sent = False
        self._close_transfer()
        self.current = ""
        if self.suspended:
            self.busy = False
            self.idle.emit()
        else:
            QTimer.singleShot(150, self._next)

    def _delivery_timeout(self, transfer):
        if self.transfer is transfer:
            self._fail(
                "Окно не запросило текст за 5 секунд. Вставка остановлена, текст сохранён для копирования"
            )

    def _next(self):
        if self.suspended:
            return
        if not self.queue:
            self.busy = False
            self.current = ""
            self.idle.emit()
            return
        self.busy = True
        self.current = self.queue.popleft()
        try:
            check_focus(self.target)
            if sys.platform == "win32":
                windows_unicode(self.current)
                self.current = ""
                QTimer.singleShot(20, self._next)
                return
            if is_wayland():
                if self.portal is None:
                    raise RuntimeError("В настройках сначала разрешите ввод через портал Wayland")
                self.portal.set_text(self.current)
            else:
                from .x11_clipboard import X11ClipboardTransfer

                self.transfer = X11ClipboardTransfer(self.target)
                self.transfer.delivered.connect(self._delivered)
                self.transfer.failed.connect(self._fail)
                self.transfer.publish(self.current)
            self.clipboard_written = True
            self.last_clipboard_text = self.current
            # Let Qt serve clipboard requests before the next delta changes ownership.
            self.paste_started = time.monotonic()
            QTimer.singleShot(30, self._paste)
        except Exception as error:
            self._fail(error)

    def _paste(self):
        if self.suspended or not self.current:
            return
        # EXC-0002: approved pre-input modifier wait; see docs/exceptional_execution_paths.md.
        try:
            check_focus(self.target)
            if self.transfer is not None and not self.transfer.owns_clipboard():
                raise RuntimeError(
                    "Буфер обмена изменился. Вставка остановлена, текст сохранён для копирования"
                )
            if modifiers_pressed():
                if time.monotonic() - self.paste_started > 5:
                    raise RuntimeError("Отпустите Ctrl/Alt/Shift: текст сохранён для копирования")
                QTimer.singleShot(30, self._paste)
                return
            if self.transfer is not None:
                self.transfer.sent = True
                self.transfer.sent_after = paste(
                    self.target, self.portal, self.mode, clipboard_owner=self.transfer.owner
                )
                transfer = self.transfer
                QTimer.singleShot(5000, lambda: self._delivery_timeout(transfer))
            else:
                paste(self.target, self.portal, self.mode)
                self.current = ""
                QTimer.singleShot(150, self._next)
        except ModifiersHeld as error:
            if self.transfer is not None:
                self.transfer.sent = False
            if time.monotonic() - self.paste_started > 5:
                self._fail(error)
            else:
                QTimer.singleShot(30, self._paste)
        except Exception as error:
            self._fail(error)
