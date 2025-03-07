import logging

from PySide6 import QtCore, QtWidgets
from PySide6.QtWidgets import QHBoxLayout, QRadioButton

from ui.UIUtils import UIUtils, colorMode

_ = lambda x: x

class OnboardingWindow(QtWidgets.QWidget):
    # Sinal de fechamento
    close_signal = QtCore.Signal()

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.shortcut = 'ctrl+space'
        self.theme = 'gradient'
        self.content_layout = None
        self.shortcut_input = None
        self.init_ui()
        self.self_close = False

    def init_ui(self):
        logging.debug('Inicializando a interface de onboarding')
        self.setWindowTitle(_('Bem-vindo ao Writing Tools'))
        self.resize(600, 500)

        UIUtils.setup_window_and_layout(self)

        self.content_layout = QtWidgets.QVBoxLayout()
        self.content_layout.setContentsMargins(30, 30, 30, 30)
        self.content_layout.setSpacing(20)

        self.background.setLayout(self.content_layout)

        self.show_welcome_screen()

    def show_welcome_screen(self):
        UIUtils.clear_layout(self.content_layout)

        title_label = QtWidgets.QLabel(_("Bem-vindo ao Writing Tools") + "!")
        title_label.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {'#ffffff' if colorMode == 'dark' else '#333333'};")
        self.content_layout.addWidget(title_label, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

        features_text = f"""
        • {_('Otimize instantaneamente sua escrita com IA selecionando seu texto e invocando o Writing Tools com "ctrl+space", em qualquer lugar.')} 

        • {_('Obtenha um resumo com o qual você pode conversar de artigos, vídeos do YouTube ou documentos selecionando todo o texto com "ctrl+a"')}
          {_('(ou selecione a transcrição do YouTube a partir da descrição), invocando o Writing Tools e escolhendo Resumo.')}

        • {_('Converse com a IA a qualquer momento invocando o Writing Tools sem selecionar nenhum texto.')}

        • {_('Suporta uma ampla gama de modelos de IA:')}
            - {_('Gemini 2.0')}
            - {_('QUALQUER API compatível com OpenAI — incluindo LLMs locais!')}
        """
        features_label = QtWidgets.QLabel(features_text)
        features_label.setStyleSheet(f"font-size: 16px; color: {'#ffffff' if colorMode == 'dark' else '#333333'};")
        features_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self.content_layout.addWidget(features_label)

        shortcut_label = QtWidgets.QLabel("Personalize sua tecla de atalho (padrão: \"ctrl+space\"):")
        shortcut_label.setStyleSheet(f"font-size: 16px; color: {'#ffffff' if colorMode == 'dark' else '#333333'};")
        self.content_layout.addWidget(shortcut_label)

        self.shortcut_input = QtWidgets.QLineEdit(self.shortcut)
        self.shortcut_input.setStyleSheet(f"""
            font-size: 16px;
            padding: 5px;
            background-color: {'#444' if colorMode == 'dark' else 'white'};
            color: {'#ffffff' if colorMode == 'dark' else '#000000'};
            border: 1px solid {'#666' if colorMode == 'dark' else '#ccc'};
        """)
        self.content_layout.addWidget(self.shortcut_input)

        theme_label = QtWidgets.QLabel(_("Escolha seu tema:"))
        theme_label.setStyleSheet(f"font-size: 16px; color: {'#ffffff' if colorMode == 'dark' else '#333333'};")
        self.content_layout.addWidget(theme_label)

        theme_layout = QHBoxLayout()
        gradient_radio = QRadioButton(_("Gradiente"))
        plain_radio = QRadioButton(_("Simples"))
        gradient_radio.setStyleSheet(f"color: {'#ffffff' if colorMode == 'dark' else '#333333'};")
        plain_radio.setStyleSheet(f"color: {'#ffffff' if colorMode == 'dark' else '#333333'};")
        gradient_radio.setChecked(self.theme == 'gradient')
        plain_radio.setChecked(self.theme == 'plain')
        theme_layout.addWidget(gradient_radio)
        theme_layout.addWidget(plain_radio)
        self.content_layout.addLayout(theme_layout)

        next_button = QtWidgets.QPushButton(_('Próximo'))
        next_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px;
                font-size: 16px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        next_button.clicked.connect(lambda: self.on_next_clicked(gradient_radio.isChecked()))
        self.content_layout.addWidget(next_button)

    def on_next_clicked(self, is_gradient):
        self.shortcut = self.shortcut_input.text()
        self.theme = 'gradient' if is_gradient else 'plain'
        logging.debug(f'Atalho selecionado: {self.shortcut}, tema: {self.theme}')
        self.app.config = {
            'shortcut': self.shortcut,
            'theme': self.theme
        }
        self.show_api_key_input()

    def show_api_key_input(self):
        self.app.show_settings(providers_only=True)
        self.self_close = True
        self.close()

    def closeEvent(self, event):
        # Emite o sinal de fechamento
        if not self.self_close:
            self.close_signal.emit()
        super().closeEvent(event)
