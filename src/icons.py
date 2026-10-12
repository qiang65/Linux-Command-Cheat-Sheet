#!/usr/bin/env python3
"""自绘矢量图标。

不使用 emoji 字符：本机只有位图版 Noto Color Emoji，Qt5 渲染不出彩色字形，
在窗口角上会显示成残缺方框。这里全部用 QPainter 画，颜色跟随主题。
"""
from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import (QBrush, QColor, QIcon, QLinearGradient, QPainter,
                         QPainterPath, QPen, QPixmap)


def _canvas(size):
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    return pm, p


def chevron(left=False, color="#4b5563", size=18, weight=None):
    """左右箭头 ‹ ›"""
    pm, p = _canvas(size)
    pen = QPen(QColor(color))
    pen.setWidthF(weight or max(1.8, size * 0.13))
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    path = QPainterPath()
    if left:
        path.moveTo(size * 0.63, size * 0.20)
        path.lineTo(size * 0.35, size * 0.50)
        path.lineTo(size * 0.63, size * 0.80)
    else:
        path.moveTo(size * 0.37, size * 0.20)
        path.lineTo(size * 0.65, size * 0.50)
        path.lineTo(size * 0.37, size * 0.80)
    p.drawPath(path)
    p.end()
    return QIcon(pm)


def gear(color="#4b5563", size=18):
    """齿轮（设置）"""
    pm, p = _canvas(size)
    s = size
    c = QPointF(s / 2, s / 2)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))
    p.save()
    p.translate(c)
    for i in range(8):
        p.save()
        p.rotate(i * 45)
        p.drawRoundedRect(QRectF(-s * 0.10, -s * 0.47, s * 0.20, s * 0.22),
                          s * 0.05, s * 0.05)
        p.restore()
    p.drawEllipse(c, s * 0.31, s * 0.31)
    p.restore()
    # 中心孔
    p.setCompositionMode(QPainter.CompositionMode_Clear)
    p.setBrush(QColor(0, 0, 0, 0))
    p.drawEllipse(c, s * 0.13, s * 0.13)
    p.end()
    return QIcon(pm)


def moon(color="#4b5563", size=18):
    """月牙（切到深色）"""
    pm, p = _canvas(size)
    s = size
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))
    full = QPainterPath()
    full.addEllipse(QRectF(s * 0.10, s * 0.10, s * 0.80, s * 0.80))
    cut = QPainterPath()
    cut.addEllipse(QRectF(s * 0.30, s * 0.04, s * 0.74, s * 0.74))
    p.drawPath(full.subtracted(cut))
    p.end()
    return QIcon(pm)


def sun(color="#4b5563", size=18):
    """太阳（切到浅色）"""
    pm, p = _canvas(size)
    s = size
    c = QPointF(s / 2, s / 2)
    pen = QPen(QColor(color))
    pen.setWidthF(max(1.6, s * 0.10))
    pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(c, s * 0.19, s * 0.19)
    p.save()
    p.translate(c)
    for i in range(8):
        p.save()
        p.rotate(i * 45)
        p.drawLine(QPointF(0, -s * 0.30), QPointF(0, -s * 0.44))
        p.restore()
    p.restore()
    p.end()
    return QIcon(pm)


def plus(color="#ffffff", size=16):
    """加号（新增）"""
    pm, p = _canvas(size)
    pen = QPen(QColor(color))
    pen.setWidthF(max(1.8, size * 0.14))
    pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)
    s = size
    p.drawLine(QPointF(s * 0.5, s * 0.20), QPointF(s * 0.5, s * 0.80))
    p.drawLine(QPointF(s * 0.20, s * 0.5), QPointF(s * 0.80, s * 0.5))
    p.end()
    return QIcon(pm)


def search(color="#98a1ae", size=18):
    """放大镜"""
    pm, p = _canvas(size)
    pen = QPen(QColor(color))
    pen.setWidthF(max(1.6, size * 0.10))
    pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    s = size
    c = QPointF(s * 0.42, s * 0.42)
    p.drawEllipse(c, s * 0.26, s * 0.26)
    p.drawLine(QPointF(s * 0.62, s * 0.62), QPointF(s * 0.86, s * 0.86))
    p.end()
    return QIcon(pm)


def logo(size=30):
    """应用图标：绿色圆角方块 + 终端提示符 >_"""
    pm, p = _canvas(size)
    s = size
    g = QLinearGradient(0, 0, s, s)
    g.setColorAt(0, QColor("#22c55e"))
    g.setColorAt(1, QColor("#15803d"))
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(g))
    p.drawRoundedRect(QRectF(0.5, 0.5, s - 1, s - 1), s * 0.24, s * 0.24)

    pen = QPen(QColor("#0b1220"))
    pen.setWidthF(max(1.6, s * 0.075))
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    path = QPainterPath()
    path.moveTo(s * 0.30, s * 0.33)
    path.lineTo(s * 0.52, s * 0.50)
    path.lineTo(s * 0.30, s * 0.67)
    p.drawPath(path)
    p.drawLine(QPointF(s * 0.58, s * 0.69), QPointF(s * 0.76, s * 0.69))
    p.end()
    return QIcon(pm)


def grip(color="#98a1ae", size=14):
    """拖动手柄：两列圆点"""
    pm, p = _canvas(size)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))
    r = max(1.4, size * 0.10)
    for cx in (0.34, 0.66):
        for cy in (0.22, 0.50, 0.78):
            p.drawEllipse(QPointF(size * cx, size * cy), r, r)
    p.end()
    return QIcon(pm)


def chevrons(down=True, color="#4b5563", size=18):
    """双箭头：向下=展开全部，向上=收起全部"""
    pm, p = _canvas(size)
    pen = QPen(QColor(color))
    pen.setWidthF(max(1.7, size * 0.11))
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    s = size
    for k, base in ((0, 0.20), (1, 0.55)):
        path = QPainterPath()
        if down:
            path.moveTo(s * 0.24, s * base)
            path.lineTo(s * 0.50, s * (base + 0.26))
            path.lineTo(s * 0.76, s * base)
        else:
            path.moveTo(s * 0.24, s * (base + 0.26))
            path.lineTo(s * 0.50, s * base)
            path.lineTo(s * 0.76, s * (base + 0.26))
        p.drawPath(path)
    p.end()
    return QIcon(pm)


def star(filled=True, color="#16a34a", size=16):
    """五角星（收藏）"""
    import math
    pm, p = _canvas(size)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color) if filled else Qt.NoBrush)
    if not filled:
        pen = QPen(QColor(color))
        pen.setWidthF(max(1.2, size * 0.08))
        p.setPen(pen)
    pts = []
    cx = cy = size / 2.0
    r_out, r_in = size * 0.46, size * 0.20
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        r = r_out if i % 2 == 0 else r_in
        pts.append(QPointF(cx + r * math.cos(ang), cy + r * math.sin(ang)))
    path = QPainterPath(pts[0])
    for pt in pts[1:]:
        path.lineTo(pt)
    path.closeSubpath()
    p.drawPath(path)
    p.end()
    return QIcon(pm)
