import os
import sys

from aiprovider import AIProvider
from PySide6 import QtCore, QtWidgets
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QHBoxLayout, QRadioButton, QScrollArea

from ui.AutostartManager import AutostartManager
from ui.UIUtils import UIUtils, colorMode

_ = lambda x: x

class SettingsWindow(QtWidgets.QWidget):
    """
    A janela de configurações do aplicativo.
    Agora com suporte a rolagem para melhor usabilidade em telas menores.
    """
    close_signal = QtCore.Signal()

    def __init__(self, app, providers_only=False):
        super().__init__()
        self.app = app
        self.current_provider_layout = None
        self.providers_only = providers_only
        self.gradient_radio = None
        self.plain_radio = None
        self.provider_dropdown = None
        self.provider_container = None
        self.autostart_checkbox = None
        self.shortcut_input = None
        self.init_ui()
        self.retranslate_ui()

    def retranslate_ui(self):
        self.setWindowTitle(_("Configurações"))

    def init_provider_ui(self, provider: AIProvider, layout):
        """
        Inicializa a interface do provedor, incluindo logotipo, nome, descrição e todas as configurações.
        """
        if self.current_provider_layout:
            self.current_provider_layout.setParent(None)
            UIUtils.clear_layout(self.current_provider_layout)
            self.current_provider_layout.deleteLater()

        self.current_provider_layout = QtWidgets.QVBoxLayout()

        # Cria um layout horizontal para o logotipo e o nome do provedor
        provider_header_layout = QtWidgets.QHBoxLayout()
        provider_header_layout.setSpacing(10)
        provider_header_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        if provider.logo:
            logo_path = os.path.join(os.path.dirname(sys.argv[0]), 'icons', f"provider_{provider.logo}.png")
            if os.path.exists(logo_path):
                targetPixmap = UIUtils.resize_and_round_image(QImage(logo_path), 30, 15)
                logo_label = QtWidgets.QLabel()
                logo_label.setPixmap(targetPixmap)
                logo_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter)
                provider_header_layout.addWidget(logo_label)

        provider_name_label = QtWidgets.QLabel(provider.provider_name)
        provider_name_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {'#ffffff' if colorMode == 'dark' else '#333333'};")
        provider_name_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter)
        provider_header_layout.addWidget(provider_name_label)

        self.current_provider_layout.addLayout(provider_header_layout)

        if provider.description:
            description_label = QtWidgets.QLabel(provider.description)
            description_label.setStyleSheet(f"font-size: 16px; color: {'#ffffff' if colorMode == 'dark' else '#333333'}; text-align: center;")
            description_label.setWordWrap(True)
            self.current_provider_layout.addWidget(description_label)

        if hasattr(provider, 'ollama_button_text'):
            # Cria um contêiner para os botões
            button_layout = QtWidgets.QHBoxLayout()
            
            # Adiciona o botão de configuração do Ollama
            ollama_button = QtWidgets.QPushButton(provider.ollama_button_text)
            ollama_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {'#4CAF50' if colorMode == 'dark' else '#008CBA'};
                    color: white;
                    padding: 10px;
                    font-size: 16px;
                    border: none;
                    border-radius: 5px;
                }}
                QPushButton:hover {{
                    background-color: {'#45a049' if colorMode == 'dark' else '#007095'};
                }}
            """)
            ollama_button.clicked.connect(provider.ollama_button_action)
            button_layout.addWidget(ollama_button)
            
            # Adiciona o botão original
            main_button = QtWidgets.QPushButton(provider.button_text)
            main_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {'#4CAF50' if colorMode == 'dark' else '#008CBA'};
                    color: white;
                    padding: 10px;
                    font-size: 16px;
                    border: none;
                    border-radius: 5px;
                }}
                QPushButton:hover {{
                    background-color: {'#45a049' if colorMode == 'dark' else '#007095'};
                }}
            """)
            main_button.clicked.connect(provider.button_action)
            button_layout.addWidget(main_button)
            
            self.current_provider_layout.addLayout(button_layout)
        else:
            # Lógica original para botão único
            if provider.button_text:
                button = QtWidgets.QPushButton(provider.button_text)
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {'#4CAF50' if colorMode == 'dark' else '#008CBA'};
                        color: white;
                        padding: 10px;
                        font-size: 16px;
                        border: none;
                        border-radius: 5px;
                    }}
                    QPushButton:hover {{
                        background-color: {'#45a049' if colorMode == 'dark' else '#007095'};
                    }}
                """)
                button.clicked.connect(provider.button_action)
                self.current_provider_layout.addWidget(button, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

        # Inicializa a configuração se necessário
        if "providers" not in self.app.config:
            self.app.config["providers"] = {}
        if provider.provider_name not in self.app.config["providers"]:
            self.app.config["providers"][provider.provider_name] = {}

        # Adiciona as configurações do provedor
        for setting in provider.settings:
            setting.set_value(self.app.config["providers"][provider.provider_name].get(setting.name, setting.default_value))
            setting.render_to_layout(self.current_provider_layout)

        layout.addLayout(self.current_provider_layout)

    def init_ui(self):
        """
        Inicializa a interface da janela de configurações.
        Agora inclui uma área rolável para melhor exibição do conteúdo em telas menores.
        """
        self.setWindowTitle(_("Configurações"))
        # Define a largura exata desejada (592px) como mínima e fixa
        self.setMinimumWidth(592)
        self.setFixedWidth(592)  # Torna a largura não redimensionável

        # Configura o layout principal da janela com espaçamento para os elementos inferiores
        UIUtils.setup_window_and_layout(self)
        main_layout = QtWidgets.QVBoxLayout(self.background)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)  # Adiciona espaçamento entre a área rolável e os elementos inferiores

        # Cria a área de rolagem
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Cria o widget para o conteúdo rolável
        scroll_content = QtWidgets.QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        
        # Estiliza a área de rolagem para transparência
        scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
            QScrollBar:vertical {
                background-color: transparent;
                width: 12px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(128, 128, 128, 0.5);
                min-height: 20px;
                border-radius: 6px;
                margin: 2px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        # Cria um widget para conter o conteúdo rolável
        scroll_content = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(20)

        if not self.providers_only:
            title_label = QtWidgets.QLabel(_("Configurações"))
            title_label.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {'#ffffff' if colorMode == 'dark' else '#333333'};")
            content_layout.addWidget(title_label, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

            # Adiciona a caixa de seleção de inicialização automática para a versão compilada no Windows
            if AutostartManager.get_startup_path():
                self.autostart_checkbox = QtWidgets.QCheckBox(_("Iniciar com o Sistema"))
                self.autostart_checkbox.setStyleSheet(f"font-size: 16px; color: {'#ffffff' if colorMode == 'dark' else '#333333'};")
                self.autostart_checkbox.setChecked(AutostartManager.check_autostart())
                self.autostart_checkbox.stateChanged.connect(self.toggle_autostart)
                content_layout.addWidget(self.autostart_checkbox)

            # Adiciona o campo de entrada para a tecla de atalho
            shortcut_label = QtWidgets.QLabel(_("Tecla de Atalho:"))
            shortcut_label.setStyleSheet(f"font-size: 16px; color: {'#ffffff' if colorMode == 'dark' else '#333333'};")
            content_layout.addWidget(shortcut_label)

            self.shortcut_input = QtWidgets.QLineEdit(self.app.config.get('shortcut', 'ctrl+space'))
            self.shortcut_input.setStyleSheet(f"""
                font-size: 16px;
                padding: 5px;
                background-color: {'#444' if colorMode == 'dark' else 'white'};
                color: {'#ffffff' if colorMode == 'dark' else '#000000'};
                border: 1px solid {'#666' if colorMode == 'dark' else '#ccc'};
            """)
            content_layout.addWidget(self.shortcut_input)

            # Adiciona a seleção de tema de fundo
            theme_label = QtWidgets.QLabel(_("Tema de Fundo:"))
            theme_label.setStyleSheet(f"font-size: 16px; color: {'#ffffff' if colorMode == 'dark' else '#333333'};")
            content_layout.addWidget(theme_label)

            theme_layout = QHBoxLayout()
            self.gradient_radio = QRadioButton(_("Gradiente Difuso"))
            self.plain_radio = QRadioButton(_("Simples"))
            self.gradient_radio.setStyleSheet(f"color: {'#ffffff' if colorMode == 'dark' else '#333333'};")
            self.plain_radio.setStyleSheet(f"color: {'#ffffff' if colorMode == 'dark' else '#333333'};")
            current_theme = self.app.config.get('theme', 'gradient')
            self.gradient_radio.setChecked(current_theme == 'gradient')
            self.plain_radio.setChecked(current_theme == 'plain')
            theme_layout.addWidget(self.gradient_radio)
            theme_layout.addWidget(self.plain_radio)
            content_layout.addLayout(theme_layout)

        # Adiciona a seleção de provedor de IA
        provider_label = QtWidgets.QLabel(_("Escolha o Provedor de IA:"))
        provider_label.setStyleSheet(f"font-size: 16px; color: {'#ffffff' if colorMode == 'dark' else '#333333'};")
        content_layout.addWidget(provider_label)

        self.provider_dropdown = QtWidgets.QComboBox()
        self.provider_dropdown.setStyleSheet(f"""
            font-size: 16px;
            padding: 5px;
            background-color: {'#444' if colorMode == 'dark' else 'white'};
            color: {'#ffffff' if colorMode == 'dark' else '#000000'};
            border: 1px solid {'#666' if colorMode == 'dark' else '#ccc'};
        """)
        self.provider_dropdown.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)

        current_provider = self.app.config.get('provider', self.app.providers[0].provider_name)
        for provider in self.app.providers:
            self.provider_dropdown.addItem(provider.provider_name)
        self.provider_dropdown.setCurrentIndex(self.provider_dropdown.findText(current_provider))
        content_layout.addWidget(self.provider_dropdown)

        # Adiciona um separador horizontal
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        content_layout.addWidget(line)

        # Cria o contêiner para a interface do provedor
        self.provider_container = QtWidgets.QVBoxLayout()
        content_layout.addLayout(self.provider_container)

        # Inicializa a interface do provedor
        provider_instance = self.app.providers[self.provider_dropdown.currentIndex()]
        self.init_provider_ui(provider_instance, self.provider_container)

        # Conecta a alteração do provedor na lista
        self.provider_dropdown.currentIndexChanged.connect(
            lambda: self.init_provider_ui(self.app.providers[self.provider_dropdown.currentIndex()], self.provider_container)
        )

        # Adiciona outro separador horizontal
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        content_layout.addWidget(line)

        # Configura a área rolável com o conteúdo
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        # Cria o contêiner inferior para o botão de salvar e o aviso de reinicialização
        bottom_container = QtWidgets.QWidget()
        bottom_container.setStyleSheet("background: transparent;")
        bottom_layout = QtWidgets.QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(30, 0, 30, 30)
        bottom_layout.setSpacing(10)

        # Adiciona o botão de salvar ao contêiner inferior
        save_button = QtWidgets.QPushButton((_('Concluir Configuração da IA') if self.providers_only else _('Salvar')))
        save_button.setStyleSheet("""
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
        save_button.clicked.connect(self.save_settings)
        bottom_layout.addWidget(save_button)

        if not self.providers_only:
            restart_text = "<p style='text-align: center;'>" + \
            (_("Por favor, reinicie o Writing Tools para que as alterações tenham efeito.")) + \
            "</p>"

            restart_notice = QtWidgets.QLabel(restart_text)
            restart_notice.setStyleSheet(f"font-size: 15px; color: {'#cccccc' if colorMode == 'dark' else '#555555'}; font-style: italic;")
            restart_notice.setWordWrap(True)
            bottom_layout.addWidget(restart_notice)

        main_layout.addWidget(bottom_container)

        # Define a altura adequada da janela com base no tamanho da tela
        screen = QtWidgets.QApplication.primaryScreen().geometry()
        max_height = int(screen.height() * 0.85)  # 85% da altura da tela
        desired_height = min(720, max_height)  # Limita a 720px ou 85% da altura da tela
        self.resize(592, desired_height)  # Usa uma largura exata de 592px para uma boa apresentação

    @staticmethod
    def toggle_autostart(state):
        """Alterna a configuração de inicialização automática."""
        AutostartManager.set_autostart(state == 2)

    def save_settings(self):
        """Salva as configurações atuais."""
        self.app.config['locale'] = 'pt_BR'

        if not self.providers_only:
            self.app.config['shortcut'] = self.shortcut_input.text()
            self.app.config['theme'] = 'gradient' if self.gradient_radio.isChecked() else 'plain'
        else:
            self.app.create_tray_icon()

        self.app.config['streaming'] = False
        self.app.config['provider'] = self.provider_dropdown.currentText()

        self.app.providers[self.provider_dropdown.currentIndex()].save_config()

        provider_name = self.app.config.get('provider', 'Gemini')
        self.app.current_provider = next(
            (provider for provider in self.app.providers if provider.provider_name == provider_name),
            self.app.providers[0]
        )

        self.app.current_provider.load_config(
            self.app.config.get("providers", {}).get(provider_name, {})
        )

        self.app.register_hotkey()
        self.providers_only = False
        self.close()

    def closeEvent(self, event):
        """Trata o evento de fechamento da janela."""
        if self.providers_only:
            self.close_signal.emit()
        super().closeEvent(event)
