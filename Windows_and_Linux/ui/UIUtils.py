import os
import sys

from PySide6 import QtGui, QtCore, QtWidgets
from PySide6.QtGui import QImage, QPixmap

import darkdetect
colorMode = 'dark' if darkdetect.isDark() else 'light'

class UIUtils:
    @classmethod
    def clear_layout(cls, layout):
        """
        Limpa o layout de todos os widgets.
        """
        while ((child := layout.takeAt(0)) != None):
            # Se o filho for um layout, deleta-o
            if child.layout():
                cls.clear_layout(child.layout())
                child.layout().deleteLater()
            else:
                child.widget().deleteLater()

    @classmethod
    def resize_and_round_image(cls, image, image_size=100, rounding_amount=50):
        image = image.scaledToWidth(image_size)
        clipPath = QtGui.QPainterPath()
        clipPath.addRoundedRect(0, 0, image_size, image_size, rounding_amount, rounding_amount)
        target = QImage(image_size, image_size, QImage.Format_ARGB32)
        target.fill(QtCore.Qt.GlobalColor.transparent)
        painter = QtGui.QPainter(target)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setClipPath(clipPath)
        painter.drawImage(0, 0, image)
        painter.end()
        targetPixmap = QPixmap.fromImage(target)
        return targetPixmap

    @classmethod
    def setup_window_and_layout(cls, base: QtWidgets.QWidget):
        # Define o ícone da janela
        icon_path = os.path.join(os.path.dirname(sys.argv[0]), 'icons', 'app_icon.png')
        if os.path.exists(icon_path):
            base.setWindowIcon(QtGui.QIcon(icon_path))
        main_layout = QtWidgets.QVBoxLayout(base)
        main_layout.setContentsMargins(0, 0, 0, 0)
        base.background = ThemeBackground(base, 'gradient')
        main_layout.addWidget(base.background)


class ThemeBackground(QtWidgets.QWidget):
    """
    Um widget personalizado que cria um fundo para o aplicativo com base no tema selecionado.
    """
    def __init__(self, parent=None, theme='gradient', is_popup=False, border_radius=0):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.theme = theme
        self.is_popup = is_popup
        self.border_radius = border_radius

    def paintEvent(self, event):
        """
        Sobrescreve o evento de pintura para desenhar o fundo com base no tema selecionado.
        """
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform, True)
        if self.theme == 'gradient':
            if self.is_popup:
                background_image = QtGui.QPixmap(os.path.join(os.path.dirname(sys.argv[0]),
                                                               'background_popup_dark.png' if colorMode == 'dark' else 'background_popup.png'))
            else:
                background_image = QtGui.QPixmap(os.path.join(os.path.dirname(sys.argv[0]),
                                                               'background_dark.png' if colorMode == 'dark' else 'background.png'))
            # Adiciona um caminho/borda utilizando o qual o raio da borda será desenhado
            path = QtGui.QPainterPath()
            path.addRoundedRect(0, 0, self.width(), self.height(), self.border_radius, self.border_radius)
            painter.setClipPath(path)
            painter.drawPixmap(self.rect(), background_image)
        else:
            if colorMode == 'dark':
                color = QtGui.QColor(35, 35, 35)  # Cor para modo escuro
            else:
                color = QtGui.QColor(222, 222, 222)  # Cor para modo claro
            brush = QtGui.QBrush(color)
            painter.setBrush(brush)
            pen = QtGui.QPen(QtGui.QColor(0, 0, 0, 0))
            pen.setWidth(0)
            painter.setPen(pen)
            painter.drawRoundedRect(QtCore.QRect(0, 0, self.width(), self.height()), self.border_radius, self.border_radius)
