import json
import logging
import os
import sys
from functools import partial

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from ui.UIUtils import ThemeBackground, colorMode

_ = lambda x: x

################################################################################
# Conteúdo padrão do arquivo `options.json` para restaurar quando o usuário pressionar "Reset"
################################################################################
DEFAULT_OPTIONS_JSON = r"""{
{
  "Revisão": {
    "prefix": "Revise este texto:\n\n",
    "instruction": "Você é um assistente de revisão gramatical. Produza APENAS o texto corrigido sem comentários adicionais. Mantenha a estrutura original do texto e o estilo de escrita. Responda no mesmo idioma do texto de entrada (ex.: Inglês dos EUA, Francês). Não responda ou comente o conteúdo do texto fornecido pelo usuário. Se o texto for absolutamente incompatível com essa tarefa (ex.: completo nonsense aleatório), produza \"ERROR_TEXT_INCOMPATIBLE_WITH_REQUEST\".",
    "icon": "icons/magnifying-glass",
    "open_in_window": false
  },
  "Reescrever": {
    "prefix": "Reescreva isto:\n\n",
    "instruction": "Você é um assistente de escrita. Reescreva o texto fornecido pelo usuário para melhorar a forma de expressão. Produza APENAS o texto reescrito sem comentários adicionais. Responda no mesmo idioma do texto de entrada (ex.: Inglês dos EUA, Francês). Não responda ou comente o conteúdo do texto fornecido pelo usuário. Se o texto for absolutamente incompatível com a tarefa de reescrita (ex.: completo nonsense aleatório), produza \"ERROR_TEXT_INCOMPATIBLE_WITH_REQUEST\".",
    "icon": "icons/rewrite",
    "open_in_window": false
  },
  "Amigável": {
    "prefix": "Torne isto mais amigável:\n\n",
    "instruction": "Você é um assistente de escrita. Reescreva o texto fornecido pelo usuário para que fique mais amigável. Produza APENAS o texto amigável sem comentários adicionais. Responda no mesmo idioma do texto de entrada (ex.: Inglês dos EUA, Francês). Não responda ou comente o conteúdo do texto fornecido pelo usuário. Se o texto for absolutamente incompatível com a tarefa de reescrita (ex.: completo nonsense aleatório), produza \"ERROR_TEXT_INCOMPATIBLE_WITH_REQUEST\".",
    "icon": "icons/smiley-face",
    "open_in_window": false
  },
  "Profissional": {
    "prefix": "Torne isto mais profissional:\n\n",
    "instruction": "Você é um assistente de escrita. Reescreva o texto fornecido pelo usuário para que fique mais profissional. Produza APENAS o texto profissional sem comentários adicionais. Responda no mesmo idioma do texto de entrada (ex.: Inglês dos EUA, Francês). Não responda ou comente o conteúdo do texto fornecido pelo usuário. Se o texto for absolutamente incompatível com a tarefa de reescrita (ex.: completo nonsense aleatório), produza \"ERROR_TEXT_INCOMPATIBLE_WITH_REQUEST\".",
    "icon": "icons/briefcase",
    "open_in_window": false
  },
  "Conciso": {
    "prefix": "Torne isto mais conciso:\n\n",
    "instruction": "Você é um assistente de escrita. Reescreva o texto fornecido pelo usuário para que fique mais conciso. Produza APENAS o texto conciso sem comentários adicionais. Responda no mesmo idioma do texto de entrada (ex.: Inglês dos EUA, Francês). Não responda ou comente o conteúdo do texto fornecido pelo usuário. Se o texto for absolutamente incompatível com a tarefa de reescrita (ex.: completo nonsense aleatório), produza \"ERROR_TEXT_INCOMPATIBLE_WITH_REQUEST\".",
    "icon": "icons/concise",
    "open_in_window": false
  },
  "Resumo": {
    "prefix": "Resuma isto:\n\n",
    "instruction": "Você é um assistente de resumo. Forneça um resumo sucinto do texto fornecido pelo usuário. O resumo deve ser breve, mas englobar todos os pontos-chave e insights. Para tornar o texto legível, utilize formatação Markdown (negrito, itálico, blocos de código, etc.) conforme apropriado. Você também pode adicionar um pequeno espaçamento entre os parágrafos, conforme necessário. E somente se apropriado, pode utilizar títulos (apenas os mais pequenos), listas, tabelas, etc. Não seja repetitivo ou excessivamente prolixo. Produza APENAS o resumo sem comentários adicionais. Responda no mesmo idioma do texto de entrada (ex.: Inglês dos EUA, Francês). Não responda ou comente o conteúdo do texto fornecido pelo usuário. Se o texto for absolutamente incompatível com a tarefa de sumarização (ex.: completo nonsense aleatório), produza \"ERROR_TEXT_INCOMPATIBLE_WITH_REQUEST\".",
    "icon": "icons/summary",
    "open_in_window": true
  },
  "Pontos-chave": {
    "prefix": "Extraia os pontos-chave disto:\n\n",
    "instruction": "Você é um assistente que extrai os pontos-chave do texto fornecido pelo usuário. Produza APENAS os pontos-chave sem comentários adicionais. Utilize formatação Markdown (listas, negrito, itálico, blocos de código, etc.) conforme apropriado para tornar o texto legível. Não seja repetitivo ou excessivamente prolixo. Responda no mesmo idioma do texto de entrada (ex.: Inglês dos EUA, Francês). Não responda ou comente o conteúdo do texto fornecido pelo usuário. Se o texto for absolutamente incompatível com a tarefa de extração de pontos-chave (ex.: completo nonsense aleatório), produza \"ERROR_TEXT_INCOMPATIBLE_WITH_REQUEST\".",
    "icon": "icons/keypoints",
    "open_in_window": true
  },
  "Tabela": {
    "prefix": "Converta isto em uma tabela:\n\n",
    "instruction": "Você é um assistente que converte o texto fornecido pelo usuário em uma tabela Markdown. Produza APENAS a tabela sem comentários adicionais. Responda no mesmo idioma do texto de entrada (ex.: Inglês dos EUA, Francês). Não responda ou comente o conteúdo do texto fornecido pelo usuário. Se o texto for completamente incompatível com essa conversão, produza \"ERROR_TEXT_INCOMPATIBLE_WITH_REQUEST\".",
    "icon": "icons/table",
    "open_in_window": true
  }
}"""

class ButtonEditDialog(QDialog):
    """
    Diálogo para editar ou criar as propriedades de um botão
    (nome/título, instrução do sistema, exibir em janela, etc.).
    """
    def __init__(self, parent=None, button_data=None, title="Editar Botão"):
        super().__init__(parent)
        self.button_data = button_data if button_data else {
            "prefix": "Faça esta alteração no seguinte texto:\n\n",
            "instruction": "",
            "icon": "icons/magnifying-glass",
            "open_in_window": False
        }
        self.setWindowTitle(title)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Nome do Botão
        name_label = QLabel("Nome do Botão:")
        name_label.setStyleSheet(f"color: {'#fff' if colorMode == 'dark' else '#333'}; font-weight: bold;")
        self.name_input = QLineEdit()
        self.name_input.setStyleSheet(f"""
            QLineEdit {{
                padding: 8px;
                border: 1px solid {'#777' if colorMode == 'dark' else '#ccc'};
                border-radius: 8px;
                background-color: {'#333' if colorMode == 'dark' else 'white'};
                color: {'#fff' if colorMode == 'dark' else '#000'};
            }}
        """)
        if "name" in self.button_data:
            self.name_input.setText(self.button_data["name"])
        layout.addWidget(name_label)
        layout.addWidget(self.name_input)
        
        # Instrução (alterada para um QPlainTextEdit multilinha)
        instruction_label = QLabel("O que sua IA deve fazer com o texto selecionado? (Instrução do Sistema)")
        instruction_label.setStyleSheet(f"color: {'#fff' if colorMode == 'dark' else '#333'}; font-weight: bold;")
        self.instruction_input = QPlainTextEdit()
        self.instruction_input.setStyleSheet(f"""
            QPlainTextEdit {{
                padding: 8px;
                border: 1px solid {'#777' if colorMode == 'dark' else '#ccc'};
                border-radius: 8px;
                background-color: {'#333' if colorMode == 'dark' else 'white'};
                color: {'#fff' if colorMode == 'dark' else '#000'};
            }}
        """)
        self.instruction_input.setPlainText(self.button_data.get("instruction", ""))
        self.instruction_input.setMinimumHeight(100)
        self.instruction_input.setPlaceholderText("""Exemplos:
    - Corrija / melhore / explique este código.
    - Torne-o engraçado.
    - Adicione emojis!
    - Tire sarro disso!
    - Traduza para o inglês.
    - Coloque o texto em formato de título.
    - Se estiver todo em maiúsculas, coloque tudo em minúsculas, e vice-versa.
    - Escreva uma resposta para isto.
    - Analise possíveis vieses neste artigo de notícias.""")
        layout.addWidget(instruction_label)
        layout.addWidget(self.instruction_input)
        
        # open_in_window
        display_label = QLabel("Como a resposta da sua IA deve ser exibida?")
        display_label.setStyleSheet(f"color: {'#fff' if colorMode == 'dark' else '#333'}; font-weight: bold;")
        layout.addWidget(display_label)
        
        radio_layout = QHBoxLayout()
        self.replace_radio = QRadioButton("Substituir o texto selecionado")
        self.window_radio = QRadioButton("Em uma janela pop-up (com suporte para acompanhamento)")
        for r in (self.replace_radio, self.window_radio):
            r.setStyleSheet(f"color: {'#fff' if colorMode == 'dark' else '#333'};")
        
        self.replace_radio.setChecked(not self.button_data.get("open_in_window", False))
        self.window_radio.setChecked(self.button_data.get("open_in_window", False))
        
        radio_layout.addWidget(self.replace_radio)
        radio_layout.addWidget(self.window_radio)
        layout.addLayout(radio_layout)
        
        # Botões OK & Cancelar
        btn_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancelar")
        for btn in (ok_button, cancel_button):
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {'#444' if colorMode == 'dark' else '#f0f0f0'};
                    color: {'#fff' if colorMode == 'dark' else '#000'};
                    border: 1px solid {'#666' if colorMode == 'dark' else '#ccc'};
                    border-radius: 5px;
                    padding: 8px;
                    min-width: 100px;
                }}
                QPushButton:hover {{
                    background-color: {'#555' if colorMode == 'dark' else '#e0e0e0'};
                }}
            """)
        btn_layout.addWidget(ok_button)
        btn_layout.addWidget(cancel_button)
        layout.addLayout(btn_layout)
        
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {'#222' if colorMode == 'dark' else '#f5f5f5'};
                border-radius: 10px;
            }}
        """)

    def get_button_data(self):
        return {
            "name": self.name_input.text(),
            "prefix": "Faça esta alteração no seguinte texto:\n\n",
            "instruction": self.instruction_input.toPlainText(),
            "icon": "icons/custom",
            "open_in_window": self.window_radio.isChecked()
        }

class DraggableButton(QtWidgets.QPushButton):
    def __init__(self, parent_popup, key, text):
        super().__init__(text, parent_popup)
        self.popup = parent_popup
        self.key = key
        self.drag_start_position = None
        self.setAcceptDrops(True)
        self.icon_container = None

        # Habilita o rastreamento do mouse e eventos de hover, e fundo estilizado
        self.setMouseTracking(True)
        self.setAttribute(QtCore.Qt.WA_Hover, True)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)

        # Define a propriedade dinâmica "hover" (padrão False)
        self.setProperty("hover", False)

        # Calcula a largura com base no texto, mantendo a altura fixa
        self.setFixedHeight(40)
        font_metrics = QtGui.QFontMetrics(self.font())
        text_width = font_metrics.horizontalAdvance(text)
        # Adiciona margem para o texto + ícone + padding
        self.setMinimumWidth(max(text_width + 40, 120))

        # Define o estilo base utilizando a propriedade dinâmica em vez da pseudo-classe :hover
        self.base_style = f"""
            QPushButton {{
                background-color: {"#444" if colorMode=="dark" else "white"};
                border: 1px solid {"#666" if colorMode=="dark" else "#ccc"};
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                text-align: left;
                color: {"#fff" if colorMode=="dark" else "#000"};
            }}
            QPushButton[hover="true"] {{
                background-color: {"#555" if colorMode=="dark" else "#f0f0f0"};
            }}
        """
        self.setStyleSheet(self.base_style)
        logging.debug("DraggableButton initialized")

    def enterEvent(self, event):
        if not self.popup.edit_mode:
            self.setProperty("hover", True)
            self.style().unpolish(self)
            self.style().polish(self)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.popup.edit_mode:
            self.setProperty("hover", False)
            self.style().unpolish(self)
            self.style().polish(self)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            if self.popup.edit_mode:
                self.drag_start_position = event.pos()
                event.accept()
                return
        super().mousePressEvent(event)
            
    def mouseMoveEvent(self, event):
        if not (event.buttons() & QtCore.Qt.LeftButton) or not self.drag_start_position:
            return

        distance = (event.pos() - self.drag_start_position).manhattanLength()
        if distance < QtWidgets.QApplication.startDragDistance():
            return

        if self.popup.edit_mode:
            drag = QtGui.QDrag(self)
            mime_data = QtCore.QMimeData()
            idx = self.popup.button_widgets.index(self)
            mime_data.setData("application/x-button-index", str(idx).encode())
            drag.setMimeData(mime_data)

            pixmap = self.grab()
            drag.setPixmap(pixmap)
            drag.setHotSpot(event.pos())

            self.drag_start_position = None
            drop_action = drag.exec_(QtCore.Qt.MoveAction)
            logging.debug(f"Drag completed with action: {drop_action}")

    def dragEnterEvent(self, event):
        if self.popup.edit_mode and event.mimeData().hasFormat("application/x-button-index"):
            event.acceptProposedAction()
            self.setStyleSheet(self.base_style + """
                QPushButton {
                    border: 2px dashed #666;
                }
            """)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet(self.base_style)
        event.accept()

    def dropEvent(self, event):
        if not self.popup.edit_mode or not event.mimeData().hasFormat("application/x-button-index"):
            event.ignore()
            return

        source_idx = int(event.mimeData().data("application/x-button-index").data().decode())
        target_idx = self.popup.button_widgets.index(self)

        if source_idx != target_idx:
            bw = self.popup.button_widgets
            bw[source_idx], bw[target_idx] = bw[target_idx], bw[source_idx]
            self.popup.rebuild_grid_layout()
            self.popup.update_json_from_grid()

        self.setStyleSheet(self.base_style)
        event.setDropAction(QtCore.Qt.MoveAction)
        event.acceptProposedAction()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.icon_container:
            self.icon_container.setGeometry(0, 0, self.width(), self.height())

class CustomPopupWindow(QtWidgets.QWidget):
    def __init__(self, app, selected_text):
        super().__init__()
        self.app = app
        self.selected_text = selected_text
        self.edit_mode = False
        self.has_text = bool(selected_text.strip())
        
        self.drag_label = None
        self.edit_button = None
        self.reset_button = None
        self.close_button = None
        self.custom_input = None
        self.input_area = None
        
        self.button_widgets = []

        logging.debug('Initializing CustomPopupWindow')
        self.init_ui()

    def init_ui(self):
        logging.debug('Setting up CustomPopupWindow UI')
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setWindowTitle("Writing Tools")
        
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0,0,0,0)
        
        self.background = ThemeBackground(
            self, 
            self.app.config.get('theme','gradient'),
            is_popup=True,
            border_radius=10
        )
        main_layout.addWidget(self.background)
        
        content_layout = QtWidgets.QVBoxLayout(self.background)
        content_layout.setContentsMargins(10, 4, 10, 10)
        content_layout.setSpacing(10)
        
        # TOPO - BARRA DE CONTROLE
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        top_bar.setSpacing(0)

        # Botão "Editar"/"Concluir" (à esquerda), do mesmo tamanho que o botão de fechar
        self.edit_button = QPushButton()
        pencil_icon = os.path.join(os.path.dirname(sys.argv[0]),
                                'icons',
                                'pencil' + ('_dark' if colorMode=='dark' else '_light') + '.png')
        if os.path.exists(pencil_icon):
            self.edit_button.setIcon(QtGui.QIcon(pencil_icon))
        self.edit_button.setFixedSize(24, 24)
        self.edit_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 6px;
                padding: 0px;
                margin-top: 3px;
            }}
            QPushButton:hover {{
                background-color: {'#333' if colorMode=='dark' else '#ebebeb'};
            }}
        """)
        self.edit_button.clicked.connect(self.toggle_edit_mode)
        top_bar.addWidget(self.edit_button, 0, Qt.AlignLeft)

        # Rótulo "Arraste para reorganizar" (em negrito)
        self.drag_label = QLabel("Arraste para reorganizar")
        self.drag_label.setStyleSheet(f"""
            color: {'#fff' if colorMode=='dark' else '#333'};
            font-size: 14px;
            font-weight: bold;
        """)
        self.drag_label.setAlignment(Qt.AlignCenter)
        self.drag_label.hide()
        top_bar.addWidget(self.drag_label, 1, Qt.AlignVCenter | Qt.AlignHCenter)

        # Botão "Reset" (somente no modo de edição) - também 24x24
        self.reset_button = QPushButton()
        reset_icon_path = os.path.join(os.path.dirname(sys.argv[0]), 'icons',
                                    'restore' + ('_dark' if colorMode=='dark' else '_light') + '.png')
        if os.path.exists(reset_icon_path):
            self.reset_button.setIcon(QtGui.QIcon(reset_icon_path))
        self.reset_button.setText("")
        self.reset_button.setFixedSize(24, 24)
        self.reset_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 6px;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: {'#333' if colorMode=='dark' else '#ebebeb'};
            }}
        """)
        self.reset_button.clicked.connect(self.on_reset_clicked)
        self.reset_button.hide()
        top_bar.addWidget(self.reset_button, 0, Qt.AlignRight)

        # Botão de fechar:
        self.close_button = QPushButton("×")
        self.close_button.setFixedSize(24, 24)
        self.close_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {'#fff' if colorMode=='dark' else '#333'};
                font-size: 20px;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: {'#333' if colorMode=='dark' else '#ebebeb'};
            }}
        """)
        self.close_button.clicked.connect(self.close)
        top_bar.addWidget(self.close_button, 0, Qt.AlignRight)
        content_layout.addLayout(top_bar)

        # Área de entrada (oculta no modo de edição)
        self.input_area = QWidget()
        input_layout = QHBoxLayout(self.input_area)
        input_layout.setContentsMargins(0,0,0,0)
        
        self.custom_input = QLineEdit()
        self.custom_input.setPlaceholderText(_("Descreva sua alteração...") if self.has_text else _("Pergunte à sua IA..."))
        self.custom_input.setStyleSheet(f"""
            QLineEdit {{
                padding: 8px;
                border: 1px solid {'#777' if colorMode=='dark' else '#ccc'};
                border-radius: 8px;
                background-color: {'#333' if colorMode=='dark' else 'white'};
                color: {'#fff' if colorMode=='dark' else '#000'};
            }}
        """)
        self.custom_input.returnPressed.connect(self.on_custom_change)
        input_layout.addWidget(self.custom_input)
        
        send_btn = QPushButton()
        send_icon = os.path.join(os.path.dirname(sys.argv[0]),
                                'icons',
                                'send' + ('_dark' if colorMode=='dark' else '_light') + '.png')
        if os.path.exists(send_icon):
            send_btn.setIcon(QtGui.QIcon(send_icon))
        send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {'#2e7d32' if colorMode=='dark' else '#4CAF50'};
                border: none;
                border-radius: 8px;
                padding: 5px;
            }}
            QPushButton:hover {{
                background-color: {'#1b5e20' if colorMode=='dark' else '#45a049'};
            }}
        """)
        send_btn.setFixedSize(self.custom_input.sizeHint().height(),
                            self.custom_input.sizeHint().height())
        send_btn.clicked.connect(self.on_custom_change)
        input_layout.addWidget(send_btn)
        
        content_layout.addWidget(self.input_area)
        
        if self.has_text:
            self.build_buttons_list()
            self.rebuild_grid_layout(content_layout)
        else:
            self.edit_button.hide()
            self.custom_input.setMinimumWidth(300)

        # Exibe aviso de atualização, se aplicável
        if self.app.config.get("update_available", False):
            update_label = QLabel()
            update_label.setOpenExternalLinks(True)
            update_label.setText('<a href="https://github.com/theJayTea/WritingTools/releases" style="color:rgb(255, 0, 0); text-decoration: underline; font-weight: bold;">Há uma atualização! :D Baixe agora.</a>')
            update_label.setStyleSheet("margin-top: 10px;")
            content_layout.addWidget(update_label, alignment=QtCore.Qt.AlignCenter)
        
        logging.debug('CustomPopupWindow UI setup complete')
        self.installEventFilter(self)
        QtCore.QTimer.singleShot(250, lambda: self.custom_input.setFocus())

    @staticmethod
    def load_options():
        options_path = os.path.join(os.path.dirname(sys.argv[0]), 'options.json')
        if os.path.exists(options_path):
            with open(options_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logging.debug('Opções carregadas com sucesso')
        else:
            logging.debug('Arquivo de opções não encontrado')
            data = {}
        return data

    @staticmethod
    def save_options(options):
        options_path = os.path.join(os.path.dirname(sys.argv[0]), 'options.json')
        with open(options_path, 'w', encoding='utf-8') as f:
            json.dump(options, f, indent=2, ensure_ascii=False)
            
    def build_buttons_list(self):
        """
        Lê o options.json, cria um DraggableButton para cada botão (exceto "Custom"),
        armazenando-os em self.button_widgets na mesma ordem do arquivo JSON.
        """
        self.button_widgets.clear()
        data = self.load_options()

        for k, v in data.items():
            if k == "Custom":
                continue
            b = DraggableButton(self, k, k)
            icon_path = os.path.join(os.path.dirname(sys.argv[0]),
                                    v["icon"] + ('_dark' if colorMode=='dark' else '_light') + '.png')
            if os.path.exists(icon_path):
                b.setIcon(QtGui.QIcon(icon_path))
                
            if not self.edit_mode:
                b.clicked.connect(partial(self.on_generic_instruction, k))
            self.button_widgets.append(b)

    def rebuild_grid_layout(self, parent_layout=None):
        """Reconstrói o layout em grade com tamanho consistente e posicionamento correto do botão 'Adicionar Novo'."""
        if not parent_layout:
            parent_layout = self.background.layout()

        for i in reversed(range(parent_layout.count())):
            item = parent_layout.itemAt(i)
            if isinstance(item, QtWidgets.QGridLayout):
                grid = item
                for j in reversed(range(grid.count())):
                    w = grid.itemAt(j).widget()
                    if w:
                        grid.removeWidget(w)
                parent_layout.removeItem(grid)
            elif (item.widget() and isinstance(item.widget(), QPushButton) 
                and item.widget().text() == "+ Add New"):
                item.widget().deleteLater()

        grid = QtWidgets.QGridLayout()
        grid.setSpacing(10)
        grid.setColumnMinimumWidth(0, 120)
        grid.setColumnMinimumWidth(1, 120)
        
        row = 0
        col = 0
        for b in self.button_widgets:
            grid.addWidget(b, row, col)
            col += 1
            if col > 1:
                col = 0
                row += 1
        
        parent_layout.addLayout(grid)
        
        if self.edit_mode and self.has_text:
            add_btn = QPushButton("+ Adicionar Novo")
            add_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {'#333' if colorMode=='dark' else '#e0e0e0'};
                    border: 1px solid {'#666' if colorMode=='dark' else '#ccc'};
                    border-radius: 8px;
                    padding: 10px;
                    font-size: 14px;
                    text-align: center;
                    color: {'#fff' if colorMode=='dark' else '#000'};
                    margin-top: 10px;
                }}
                QPushButton:hover {{
                    background-color: {'#444' if colorMode=='dark' else '#d0d0d0'};
                }}
            """)
            add_btn.clicked.connect(self.add_new_button_clicked)
            parent_layout.addWidget(add_btn)

    def add_edit_delete_icons(self, btn):
        """Adiciona ícones de edição/exclusão como sobreposições com espaçamento adequado."""
        if hasattr(btn, 'icon_container') and btn.icon_container:
            btn.icon_container.deleteLater()
        
        btn.icon_container = QtWidgets.QWidget(btn)
        btn.icon_container.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, False)
        
        btn.icon_container.setGeometry(0, 0, btn.width(), btn.height())
        
        circle_style = f"""
            QPushButton {{
                background-color: {'#666' if colorMode=='dark' else '#999'};
                border-radius: 10px;
                min-width: 16px;
                min-height: 16px;
                max-width: 16px;
                max-height: 16px;
                padding: 1px;
                margin: 0px;
            }}
            QPushButton:hover {{
                background-color: {'#888' if colorMode=='dark' else '#bbb'};
            }}
        """
        
        edit_btn = QPushButton(btn.icon_container)
        edit_btn.setGeometry(3, 3, 16, 16)
        pencil_icon = os.path.join(os.path.dirname(sys.argv[0]),
                        'icons', 'pencil' + ('_dark' if colorMode=='dark' else '_light') + '.png')
        if os.path.exists(pencil_icon):
            edit_btn.setIcon(QtGui.QIcon(pencil_icon))
        edit_btn.setStyleSheet(circle_style)
        edit_btn.clicked.connect(partial(self.edit_button_clicked, btn))
        edit_btn.show()
        
        delete_btn = QPushButton(btn.icon_container)
        delete_btn.setGeometry(btn.width() - 23, 3, 16, 16)
        del_icon = os.path.join(os.path.dirname(sys.argv[0]),
                                'icons', 'cross' + ('_dark' if colorMode=='dark' else '_light') + '.png')
        if os.path.exists(del_icon):
            delete_btn.setIcon(QtGui.QIcon(del_icon))
        delete_btn.setStyleSheet(circle_style)
        delete_btn.clicked.connect(partial(self.delete_button_clicked, btn))
        delete_btn.show()
        
        btn.icon_container.raise_()
        btn.icon_container.show()

    def toggle_edit_mode(self):
        """Alterna o modo de edição com rótulos de botão e estado aprimorados."""
        self.edit_mode = not self.edit_mode
        logging.debug(f'Modo de edição alterado: {self.edit_mode}')

        if self.edit_mode:
            icon_name = "check"
            self.edit_button.setText("")
            self.edit_button.setFixedSize(36, 36)
            self.edit_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: none;
                    border-radius: 6px;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    background-color: {'#333' if colorMode=='dark' else '#ebebeb'};
                }}
            """)
            self.close_button.hide()
            self.reset_button.show()
            self.drag_label.show()

        else:
            icon_name = "pencil"
            self.edit_button.setText("")
            self.edit_button.setFixedSize(24, 24)
            self.close_button.show()
            self.reset_button.hide()
            self.drag_label.hide()

            msg = QtWidgets.QMessageBox()
            msg.setWindowTitle("Encerrando para aplicar as mudanças...")
            msg.setText("O Writing Tools precisa ser reiniciado para aplicar suas mudanças e agora será encerrado.\nPor favor, reinicie o Writing Tools.exe para ver suas mudanças.")
            msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
            msg.exec_()

            self.app.load_options()
            self.close()
            QtCore.QTimer.singleShot(100, self.app.exit_app)
            return

        icon_path = os.path.join(
            os.path.dirname(sys.argv[0]),
            'icons',
            f"{icon_name}_{'dark' if colorMode=='dark' else 'light'}.png"
        )
        if os.path.exists(icon_path):
            self.edit_button.setIcon(QtGui.QIcon(icon_path))

        self.input_area.setVisible(not self.edit_mode)

        for btn in self.button_widgets:
            try:
                btn.clicked.disconnect()
            except:
                pass

            if not self.edit_mode:
                btn.clicked.connect(partial(self.on_generic_instruction, btn.key))
                if hasattr(btn, 'icon_container') and btn.icon_container:
                    btn.icon_container.deleteLater()
                    btn.icon_container = None
            else:
                self.add_edit_delete_icons(btn)

            btn.setStyleSheet(btn.base_style)

        self.rebuild_grid_layout()

    def on_reset_clicked(self):
        """
        Redefine o arquivo `options.json` para o DEFAULT_OPTIONS_JSON e, em seguida, exibe mensagem e reinicia.
        """
        confirm_box = QtWidgets.QMessageBox()
        confirm_box.setWindowTitle("Confirmar Redefinição para os Padrões e Encerramento?")
        confirm_box.setText("Para redefinir os botões para a configuração original, o Writing Tools precisará ser encerrado, então você precisará reiniciar o Writing Tools.exe.\nTem certeza de que deseja continuar?")
        confirm_box.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        confirm_box.setDefaultButton(QtWidgets.QMessageBox.No)
        
        if confirm_box.exec_() == QtWidgets.QMessageBox.Yes:
            try:
                logging.debug('Redefinindo para as opções padrão do options.json')
                default_data = json.loads(DEFAULT_OPTIONS_JSON)
                self.save_options(default_data)

                self.app.load_options()
                self.close()
                QtCore.QTimer.singleShot(100, self.app.exit_app)
            
            except Exception as e:
                logging.error(f"Erro ao redefinir o options.json: {e}")
                error_msg = QtWidgets.QMessageBox()
                error_msg.setWindowTitle("Erro")
                error_msg.setText(f"Ocorreu um erro ao redefinir: {str(e)}")
                error_msg.exec_()

    def add_new_button_clicked(self):
        dialog = ButtonEditDialog(self, title="Adicionar Novo Botão")
        if dialog.exec_():
            bd = dialog.get_button_data()
            data = self.load_options()
            data[bd["name"]] = {
                "prefix": bd["prefix"],
                "instruction": bd["instruction"],
                "icon": bd["icon"],
                "open_in_window": bd["open_in_window"]
            }
            self.save_options(data)

            self.build_buttons_list()
            self.rebuild_grid_layout()

            self.hide()
            
            QtWidgets.QMessageBox.information(
                self, 
                "Encerrando para aplicar o novo botão...",
                "O Writing Tools precisa ser reiniciado para aplicar seu novo botão e agora será encerrado.\nPor favor, reinicie o Writing Tools.exe para ver seu novo botão."
            )

            self.app.load_options()
            self.close()
            QtCore.QTimer.singleShot(100, self.app.exit_app)

    def edit_button_clicked(self, btn):
        """O usuário clicou no pequeno ícone de lápis sobre um botão."""
        key = btn.key
        data = self.load_options()
        bd = data[key]
        bd["name"] = key
        
        dialog = ButtonEditDialog(self, bd)
        if dialog.exec_():
            new_data = dialog.get_button_data()
            data = self.load_options()
            if new_data["name"] != key:
                del data[key]
            data[new_data["name"]] = {
                "prefix": new_data["prefix"],
                "instruction": new_data["instruction"],
                "icon": new_data["icon"],
                "open_in_window": new_data["open_in_window"]
            }
            self.save_options(data)

            self.build_buttons_list()
            self.rebuild_grid_layout()

            self.hide()

            QtWidgets.QMessageBox.information(
                self, 
                "Encerrando para aplicar as mudanças neste botão...",
                "O Writing Tools precisa ser reiniciado para aplicar suas mudanças e agora será encerrado.\nPor favor, reinicie o Writing Tools.exe para ver suas mudanças."
            )

            self.app.load_options()
            self.close()
            QtCore.QTimer.singleShot(100, self.app.exit_app)

    def delete_button_clicked(self, btn):
        """Trata a exclusão de um botão."""
        key = btn.key
        confirm = QtWidgets.QMessageBox()
        confirm.setWindowTitle("Confirmar Exclusão e Encerramento?")
        confirm.setText(f"Para excluir o botão '{key}', o Writing Tools precisará ser encerrado, então você precisará reiniciar o Writing Tools.exe.\nTem certeza de que deseja continuar?")
        confirm.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        confirm.setDefaultButton(QtWidgets.QMessageBox.No)
        
        if confirm.exec_() == QtWidgets.QMessageBox.Yes:
            try:
                data = self.load_options()
                del data[key]
                self.save_options(data)

                for btn_ in self.button_widgets[:]:
                    if btn_.key == key:
                        if hasattr(btn_, 'icon_container') and btn_.icon_container:
                            btn_.icon_container.deleteLater()
                        btn_.deleteLater()
                        self.button_widgets.remove(btn_)
                
                self.app.load_options()
                self.close()
                QtCore.QTimer.singleShot(100, self.app.exit_app)
                
            except Exception as e:
                logging.error(f"Erro ao excluir o botão: {e}")
                error_msg = QtWidgets.QMessageBox()
                error_msg.setWindowTitle("Erro")
                error_msg.setText(f"Ocorreu um erro ao excluir o botão: {str(e)}")
                error_msg.exec_()

    def update_json_from_grid(self):
        """
        Chamado após a reorganização por drag & drop. Reflete a nova ordem no options.json,
        para que a disposição personalizada do usuário seja mantida.
        """
        data = self.load_options()
        new_data = {"Custom": data["Custom"]} if "Custom" in data else {}
        for b in self.button_widgets:
            new_data[b.key] = data[b.key]
        self.save_options(new_data)

    def on_custom_change(self):
        txt = self.custom_input.text().strip()
        if txt:
            self.app.process_option('Custom', self.selected_text, txt)
            self.close()

    def on_generic_instruction(self, instruction):
        if not self.edit_mode:
            self.app.process_option(instruction, self.selected_text)
            self.close()

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.WindowDeactivate:
            if not self.edit_mode:
                self.hide()
                return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)
