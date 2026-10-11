"""Keep each X11 clipboard block until the target requests its text."""

import ctypes

from PySide6.QtCore import QAbstractNativeEventFilter, QMimeData, QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication


class _SelectionRequest(ctypes.Structure):
    # xcb_selection_request_event_t, in the native byte order of Qt's connection.
    _fields_ = [
        ("response_type", ctypes.c_uint8),
        ("pad", ctypes.c_uint8),
        ("sequence", ctypes.c_uint16),
        ("time", ctypes.c_uint32),
        ("owner", ctypes.c_uint32),
        ("requestor", ctypes.c_uint32),
        ("selection", ctypes.c_uint32),
        ("target", ctypes.c_uint32),
        ("property", ctypes.c_uint32),
    ]


class _RequestFilter(QAbstractNativeEventFilter):
    def __init__(self, transfer):
        super().__init__()
        self.transfer = transfer

    def nativeEventFilter(self, event_type, message):
        transfer = self.transfer
        transfer.target_request = False
        if bytes(event_type) == b"xcb_generic_event_t":
            event = _SelectionRequest.from_address(int(message))
            if event.response_type & 0x7F == 30:  # XCB_SELECTION_REQUEST
                transfer.target_request = (
                    event.owner == transfer.owner
                    and event.selection == transfer.selection
                    and transfer.belongs_to_target(event.requestor)
                    and (event.time == 0 or (event.time - transfer.sent_after) & 0xFFFFFFFF < 0x80000000)
                )
        return False


class _TextData(QMimeData):
    def __init__(self, text, on_read):
        super().__init__()
        self.setText(text)
        self.on_read = on_read

    def retrieveData(self, mime_type, preferred_type):
        result = super().retrieveData(mime_type, preferred_type)
        if mime_type.startswith("text/plain") and self.on_read is not None:
            self.on_read()
        return result


class X11ClipboardTransfer(QObject):
    delivered = Signal()
    failed = Signal(str)

    def __init__(self, target: str):
        super().__init__()
        if QApplication.platformName() != "xcb":
            raise RuntimeError("Для вставки X11 требуется платформа Qt xcb")
        from Xlib import display
        from Xlib.ext import res

        connection = display.Display()
        try:
            if not connection.has_extension(res.extname):
                raise RuntimeError("Для проверки получателя буфера требуется расширение X11 X-Resource")
            connection.res_query_version()
            clients = connection.res_query_clients().clients
            client = next(
                (item for item in clients if int(target) & ~item.resource_mask == item.resource_base), None
            )
            if client is None:
                raise RuntimeError("Не удалось определить получателя буфера X11")
            self.base, self.mask = client.resource_base, client.resource_mask
            self.selection = connection.intern_atom("CLIPBOARD")
        finally:
            connection.close()
        self.owner = 0
        self.data = None
        self.sent = False
        self.sent_after = 0
        self.closed = False
        self.ack_pending = False
        self.target_request = False
        self.local_target = False
        self.filter = _RequestFilter(self)
        QApplication.instance().installNativeEventFilter(self.filter)
        QApplication.clipboard().dataChanged.connect(self._clipboard_changed)

    def belongs_to_target(self, window: int) -> bool:
        return window & ~self.mask == self.base

    def publish(self, text: str):
        from Xlib import display

        self.data = _TextData(text, self._text_requested)
        QApplication.clipboard().setMimeData(self.data)
        connection = display.Display()
        try:
            owner = connection.get_selection_owner(self.selection)
            self.owner = owner.id if owner else 0
        finally:
            connection.close()
        if not self.owns_clipboard():
            raise RuntimeError("Не удалось сохранить текст диктовки в буфере X11")
        self.local_target = self.belongs_to_target(self.owner)

    def owns_clipboard(self) -> bool:
        clipboard = QApplication.clipboard()
        return clipboard.ownsClipboard() and clipboard.mimeData() is self.data

    def _clipboard_changed(self):
        if self.data is not None and not self.closed and not self.owns_clipboard():
            self.failed.emit("Буфер обмена изменился. Вставка остановлена, текст сохранён для копирования")

    def _text_requested(self):
        if self.sent and (self.local_target or self.target_request) and not self.ack_pending:
            self.ack_pending = True
            # Qt finishes this request before the queue may replace its QMimeData.
            # External requests get their own property / INCR transaction payload.
            QTimer.singleShot(0, self._delivered)

    def _delivered(self):
        if not self.closed:
            self.delivered.emit()

    def close(self):
        if self.closed:
            return
        self.closed = True
        if self.data is not None:
            self.data.on_read = None
        QApplication.clipboard().dataChanged.disconnect(self._clipboard_changed)
        QApplication.instance().removeNativeEventFilter(self.filter)
