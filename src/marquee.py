#!/usr/bin/env python3
"""跑马灯标签：文字超出可用宽度时，鼠标停留自动滚动显示全文，移开即复位。"""
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFontMetrics
from PyQt5.QtWidgets import QLabel, QSizePolicy


class MarqueeLabel(QLabel):
    def __init__(self, text="", parent=None, interval=110, step=2):
        super().__init__(text, parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.full = text
        self._off = 0
        self._step = step
        self._rolling = False
        self._timer = QTimer(self)
        self._timer.setInterval(interval)
        self._timer.timeout.connect(self._tick)
        self.setMouseTracking(True)

    def set_full(self, text):
        self.full = text
        self._off = 0
        self._apply()

    def _apply(self):
        """静止状态：用省略号收尾，绝不把最后一个字切掉半截。"""
        if self._rolling:
            return
        fm = QFontMetrics(self.font())
        text = fm.elidedText(self.full, Qt.ElideRight, max(1, self.width()))
        if self.text() != text:
            self.setText(text)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        if not self._rolling:
            QTimer.singleShot(0, self._apply)

    def overflow(self):
        if not self.full:
            return False
        fm = QFontMetrics(self.font())
        return fm.horizontalAdvance(self.full) > self.width() + 2

    def enterEvent(self, ev):
        if self.overflow():
            self._off = 0
            self._rolling = True
            self._timer.start()
        super().enterEvent(ev)

    def leaveEvent(self, ev):
        self._timer.stop()
        self._off = 0
        self._rolling = False
        QTimer.singleShot(0, self._apply)
        super().leaveEvent(ev)

    def _tick(self):
        self._off += self._step
        if self._off > len(self.full):
            self._timer.stop()
            self._off = 0
            self._rolling = False
            self._apply()
            return
        self.setText(self.full[self._off:])
