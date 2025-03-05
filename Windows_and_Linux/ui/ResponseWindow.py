import logging
import os
import sys

import markdown2
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QScrollArea

from ui.UIUtils import UIUtils, colorMode

_ = lambda x: x

class MarkdownTextBrowser(QtWidgets.QTextBrowser):
    """Visualizador de texto aprimorado para exibir conteúdo Markdown com melhor dimensionamento"""
    
    def __init__(self, parent=None, is_user_message=False):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setOpenExternalLinks(True)
        self.zoom_factor = 1.2
        self.base_font_size = 14
        self.is_user_message = is_user_message
        
        # Remover barras de rolagem para evitar espaço extra
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Define as políticas de tamanho para evitar expansão indesejada
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Minimum
        )
        
        self._apply_zoom()
        
    def _apply_zoom(self):
        new_size = int(self.base_font_size * self.zoom_factor)
        
        # Atualiza o stylesheet com estilo para tabelas
        self.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {('transparent' if self.is_user_message else '#333' if colorMode == 'dark' else 'white')};
                color: {'#ffffff' if colorMode == 'dark' else '#000000'};
                border: {('none' if self.is_user_message else '1px solid ' + ('#555' if colorMode == 'dark' else '#ccc'))};
                border-radius: 8px;
                padding: 8px;
                margin: 0px;
                font-size: {new_size}px;
                line-height: 1.3;
                width: 100%;
            }}

            /* Estilos para tabelas */
            table {{
                border-collapse: collapse;
                width: 100%;
                margin: 10px 0;
            }}
            
            th, td {{
                border: 1px solid {'#555' if colorMode == 'dark' else '#ccc'};
                padding: 8px;
                text-align: left;
            }}
            
            th {{
                background-color: {'#444' if colorMode == 'dark' else '#f5f5f5'};
                font-weight: bold;
            }}
            
            tr:nth-child(even) {{
                background-color: {'#3a3a3a' if colorMode == 'dark' else '#f9f9f9'};
            }}
            
            tr:hover {{
                background-color: {'#484848' if colorMode == 'dark' else '#f0f0f0'};
            }}
        """)
        
    def _update_size(self):
        # Calcula a largura correta do documento
        available_width = self.viewport().width() - 16  # Considera o padding
        self.document().setTextWidth(available_width)
        
        # Obtém a altura precisa do conteúdo
        doc_size = self.document().size()
        content_height = doc_size.height()
        
        # Adiciona um pequeno padding para o conteúdo
        new_height = int(content_height + 16)
        
        if self.minimumHeight() != new_height:
            self.setMinimumHeight(new_height)
            self.setMaximumHeight(new_height)  # Força a altura fixa
            
            # Atualiza a área de rolagem, se necessário
            scroll_area = self.get_scroll_area()
            if scroll_area:
                scroll_area.update_content_height()
                
    def wheelEvent(self, event):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            # Obtém a janela de resposta principal
            parent = self.parent()
            while parent and not isinstance(parent, ResponseWindow):
                parent = parent.parent()
                
            if parent:
                if delta > 0:
                    parent.zoom_all_messages('in')
                else:
                    parent.zoom_all_messages('out')
                event.accept()
        else:
            # Passa os eventos de rolagem para o pai
            if self.parent():
                self.parent().wheelEvent(event)
            
    def zoom_in(self):
        old_factor = self.zoom_factor
        self.zoom_factor = min(3.0, self.zoom_factor * 1.1)
        if old_factor != self.zoom_factor:
            self._apply_zoom()
            self._update_size()
        
    def zoom_out(self):
        old_factor = self.zoom_factor
        self.zoom_factor = max(0.5, self.zoom_factor / 1.1)
        if old_factor != self.zoom_factor:
            self._apply_zoom()
            self._update_size()
        
    def reset_zoom(self):
        old_factor = self.zoom_factor
        self.zoom_factor = 1.2  # Redefine para o zoom padrão
        if old_factor != self.zoom_factor:
            self._apply_zoom()
            self._update_size()
    
    def get_scroll_area(self):
        """Localiza o ChatContentScrollArea pai"""
        parent = self.parent()
        while parent:
            if isinstance(parent, ChatContentScrollArea):
                return parent
            parent = parent.parent()
        return None
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_size()


class ChatContentScrollArea(QScrollArea):
    """Contêiner rolável aprimorado para mensagens de chat com dimensionamento dinâmico e espaçamento adequado"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.content_widget = None
        self.layout = None
        self.setup_ui()
        
    def setup_ui(self):
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Widget contêiner principal com política de tamanho explícita
        self.content_widget = QtWidgets.QWidget()
        self.content_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.MinimumExpanding
        )
        self.setWidget(self.content_widget)
        
        # Layout principal com espaçamento melhorado
        self.layout = QtWidgets.QVBoxLayout(self.content_widget)
        self.layout.setSpacing(8)  # Espaçamento reduzido entre mensagens
        self.layout.setContentsMargins(15, 15, 15, 15)  # Margens ajustadas
        self.layout.addStretch()
        
        # Estilização aprimorada da área de rolagem
        self.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
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

    def add_message(self, text, is_user=False):
        # Remove o stretch inferior
        self.layout.takeAt(self.layout.count() - 1)
        
        # Cria o contêiner de mensagem com largura aprimorada
        msg_container = QtWidgets.QWidget()
        msg_container.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Minimum
        )
        
        # Layout da mensagem com margens mínimas
        msg_layout = QtWidgets.QVBoxLayout(msg_container)
        msg_layout.setContentsMargins(0, 0, 0, 0)
        msg_layout.setSpacing(0)
        
        # Cria o display de texto com largura atualizada
        text_display = MarkdownTextBrowser(is_user_message=is_user)
        
        # Ativa a extensão de tabelas no markdown2
        html = markdown2.markdown(text, extras=['tables'])
        text_display.setHtml(html)
        
        # Calcula o tamanho adequado do display de texto usando a largura total
        text_display.document().setTextWidth(self.width() - 20)
        doc_size = text_display.document().size()
        text_display.setMinimumHeight(int(doc_size.height() + 16))
        
        msg_layout.addWidget(text_display)
        
        self.layout.addWidget(msg_container)
        self.layout.addStretch()
        
        if hasattr(self.parent(), 'current_text_display'):
            self.parent().current_text_display = text_display
            
        QtCore.QTimer.singleShot(50, self.post_message_updates)
        
        return text_display

    def post_message_updates(self):
        """Realiza atualizações após a adição de uma mensagem com o timing adequado"""
        self.scroll_to_bottom()
        if isinstance(self.parent(), ResponseWindow):
            self.parent()._adjust_window_height()

    def update_content_height(self):
        """Recalcula a altura total do conteúdo com cálculo aprimorado de espaçamento"""
        total_height = 0
        
        # Calcula a altura de todas as mensagens
        for i in range(self.layout.count() - 1):  # Ignora o item stretch
            item = self.layout.itemAt(i)
            if item and item.widget():
                widget_height = item.widget().sizeHint().height()
                total_height += widget_height
        
        # Adiciona o espaçamento entre mensagens e margens
        total_height += (self.layout.spacing() * (self.layout.count() - 2))
        total_height += self.layout.contentsMargins().top() + self.layout.contentsMargins().bottom()
        
        # Define a altura mínima com algum padding
        self.content_widget.setMinimumHeight(total_height + 10)
        
        # Atualiza a altura da janela, se necessário
        if isinstance(self.parent(), ResponseWindow):
            self.parent()._adjust_window_height()

    def scroll_to_bottom(self):
        """Rola suavemente até o final do conteúdo"""
        vsb = self.verticalScrollBar()
        vsb.setValue(vsb.maximum())

    def resizeEvent(self, event):
        """Trata eventos de redimensionamento com cálculos de largura aprimorados"""
        super().resizeEvent(event)
        
        # Atualiza a largura para todos os displays de mensagem
        available_width = self.width() - 40  # Considera as margens
        for i in range(self.layout.count() - 1):  # Ignora o item stretch
            item = self.layout.itemAt(i)
            if item and item.widget():
                container = item.widget()
                text_display = container.layout().itemAt(0).widget()
                if isinstance(text_display, MarkdownTextBrowser):
                    # Recalcula a largura e altura do texto
                    text_display.document().setTextWidth(available_width)
                    doc_size = text_display.document().size()
                    text_display.setMinimumHeight(int(doc_size.height() + 20))
                    

class ResponseWindow(QtWidgets.QWidget):
    """Janela de resposta aprimorada com dimensionamento e controle de zoom melhorados"""
    
    def __init__(self, app, title=_("Resposta"), parent=None):
        super().__init__(parent)
        self.app = app
        self.original_title = title
        self.setWindowTitle(title)
        self.option = title.replace(" Result", "")
        self.selected_text = None
        self.input_field = None
        self.loading_label = None
        self.loading_container = None
        self.chat_area = None
        self.chat_history = []

        # Configura a animação de "Pensando" com o conjunto completo de pontos
        self.thinking_timer = QtCore.QTimer(self)
        self.thinking_timer.timeout.connect(self.update_thinking_dots)
        self.thinking_dots_state = 0
        self.thinking_dots = ["", ".", "..", "..."]
        self.thinking_timer.setInterval(300)

        self.init_ui()
        logging.debug('Conectando sinais de resposta')
        self.app.followup_response_signal.connect(self.handle_followup_response)
        logging.debug('Sinais de resposta conectados')

        # Define o tamanho inicial para o estado "Pensando..."
        initial_width = 500
        initial_height = 250
        self.resize(initial_width, initial_height)
                
    def init_ui(self):
        # Configuração da janela com flags aprimoradas
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | 
                            Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint)
        self.setMinimumSize(600, 400)
        
        # Configuração do layout principal
        UIUtils.setup_window_and_layout(self)
        content_layout = QtWidgets.QVBoxLayout(self.background)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(10)

        # Barra superior com controles de zoom
        top_bar = QtWidgets.QHBoxLayout()
        
        title_label = QtWidgets.QLabel(self.option)
        title_label.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {'#ffffff' if colorMode == 'dark' else '#333333'};")
        top_bar.addWidget(title_label)
        
        top_bar.addStretch()

        # Rótulo de zoom
        zoom_label = QtWidgets.QLabel("Zoom:")
        zoom_label.setStyleSheet(f"""
            color: {'#aaaaaa' if colorMode == 'dark' else '#666666'};
            font-size: 14px;
            margin-right: 5px;
        """)
        top_bar.addWidget(zoom_label)
        
        # Controles de zoom com ordem alterada
        zoom_controls = [
            ('plus', 'Aumentar Zoom', lambda: self.zoom_all_messages('in')),
            ('minus', 'Diminuir Zoom', lambda: self.zoom_all_messages('out')),
            ('reset', 'Redefinir Zoom', lambda: self.zoom_all_messages('reset'))
        ]
            
        for icon, tooltip, action in zoom_controls:
            btn = QtWidgets.QPushButton()
            btn.setIcon(QtGui.QIcon(os.path.join(os.path.dirname(sys.argv[0]), 'icons', icon + ('_dark' if colorMode == 'dark' else '_light') + '.png')))
            btn.setStyleSheet(self.get_button_style())
            btn.setToolTip(tooltip)
            btn.clicked.connect(action)
            btn.setFixedSize(30, 30)
            top_bar.addWidget(btn)
            
        content_layout.addLayout(top_bar)

        # Barra de cópia com texto compatível
        copy_bar = QtWidgets.QHBoxLayout()
        copy_hint = QtWidgets.QLabel(_("Selecione para copiar com formatação"))
        copy_hint.setStyleSheet(f"color: {'#aaaaaa' if colorMode == 'dark' else '#666666'}; font-size: 14px;")
        copy_bar.addWidget(copy_hint)
        copy_bar.addStretch()
        
        copy_md_btn = QtWidgets.QPushButton(_("Copiar como Markdown"))
        copy_md_btn.setStyleSheet(self.get_button_style())
        copy_md_btn.clicked.connect(self.copy_first_response)  # Atualizado para copiar apenas a primeira resposta
        copy_bar.addWidget(copy_md_btn)
        content_layout.addLayout(copy_bar)

        # Indicador de carregamento
        loading_container = QtWidgets.QWidget()
        loading_layout = QtWidgets.QHBoxLayout(loading_container)
        loading_layout.setContentsMargins(0, 0, 0, 0)
        
        self.loading_label = QtWidgets.QLabel(_("Pensando"))
        self.loading_label.setStyleSheet(f"""
            QLabel {{
                color: {'#ffffff' if colorMode == 'dark' else '#333333'};
                font-size: 18px;
                padding: 20px;
            }}
        """)
        self.loading_label.setAlignment(Qt.AlignLeft)
        
        loading_inner_container = QtWidgets.QWidget()
        loading_inner_container.setFixedWidth(180)
        loading_inner_layout = QtWidgets.QHBoxLayout(loading_inner_container)
        loading_inner_layout.setContentsMargins(0, 0, 0, 0)
        loading_inner_layout.addWidget(self.loading_label)
        
        loading_layout.addStretch()
        loading_layout.addWidget(loading_inner_container)
        loading_layout.addStretch()
        
        content_layout.addWidget(loading_container)
        self.loading_container = loading_container
        
        # Inicia a animação de "Pensando"
        self.start_thinking_animation(initial=True)
        
        # Área de chat aprimorada com largura total
        self.chat_area = ChatContentScrollArea()
        content_layout.addWidget(self.chat_area)
        
        # Área de entrada com estilo aprimorado
        bottom_bar = QtWidgets.QHBoxLayout()
        
        self.input_field = QtWidgets.QLineEdit()
        self.input_field.setPlaceholderText(_("Faça uma pergunta de acompanhamento") + "...")
        self.input_field.setStyleSheet(f"""
            QLineEdit {{
                padding: 8px;
                border: 1px solid {'#777' if colorMode == 'dark' else '#ccc'};
                border-radius: 8px;
                background-color: {'#333' if colorMode == 'dark' else 'white'};
                color: {'#ffffff' if colorMode == 'dark' else '#000000'};
                font-size: 14px;
            }}
        """)
        self.input_field.returnPressed.connect(self.send_message)
        bottom_bar.addWidget(self.input_field)
        
        send_button = QtWidgets.QPushButton()
        send_button.setIcon(QtGui.QIcon(os.path.join(os.path.dirname(sys.argv[0]), 'icons', 'send' + ('_dark' if colorMode == 'dark' else '_light') + '.png')))
        send_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {'#2e7d32' if colorMode == 'dark' else '#4CAF50'};
                border: none;
                border-radius: 8px;
                padding: 5px;
            }}
            QPushButton:hover {{
                background-color: {'#1b5e20' if colorMode == 'dark' else '#45a049'};
            }}
        """)
        send_button.setFixedSize(self.input_field.sizeHint().height(), self.input_field.sizeHint().height())
        send_button.clicked.connect(self.send_message)
        bottom_bar.addWidget(send_button)
        
        content_layout.addLayout(bottom_bar)

    # Método para obter o texto da primeira resposta
    def get_first_response_text(self):
        """Obtém o texto da primeira resposta do modelo a partir do histórico de chat"""
        try:
            if not self.chat_history:
                return None
                
            for msg in self.chat_history:
                if msg["role"] == "assistant":
                    return msg["content"]
                    
            return None
        except Exception as e:
            logging.error(f"Erro ao obter a primeira resposta: {e}")
            return None

    def copy_first_response(self):
        """Copia apenas a primeira resposta do modelo como Markdown"""
        response_text = self.get_first_response_text()
        if response_text:
            QtWidgets.QApplication.clipboard().setText(response_text)

    def get_button_style(self):
        return f"""
            QPushButton {{
                background-color: {'#444' if colorMode == 'dark' else '#f0f0f0'};
                color: {'#ffffff' if colorMode == 'dark' else '#000000'};
                border: 1px solid {'#666' if colorMode == 'dark' else '#ccc'};
                border-radius: 5px;
                padding: 8px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {'#555' if colorMode == 'dark' else '#e0e0e0'};
            }}
        """

    def update_thinking_dots(self):
        """Atualiza os pontos da animação de 'Pensando' com ciclo adequado"""
        self.thinking_dots_state = (self.thinking_dots_state + 1) % len(self.thinking_dots)
        dots = self.thinking_dots[self.thinking_dots_state]
        
        if self.loading_label.isVisible():
            self.loading_label.setText(_("Pensando") + f"{dots}")
        else:
            self.input_field.setPlaceholderText(_("Pensando") + f"{dots}")
    
    def start_thinking_animation(self, initial=False):
        """Inicia a animação de 'Pensando' para carga inicial ou perguntas de acompanhamento"""
        self.thinking_dots_state = 0
        
        if initial:
            self.loading_label.setText(_("Pensando"))
            self.loading_label.setVisible(True)
            self.loading_container.setVisible(True)
        else:
            self.input_field.setPlaceholderText(_("Pensando"))
            self.loading_container.setVisible(False)
            
        self.thinking_timer.start()

    def stop_thinking_animation(self):
        """Para a animação de 'Pensando'"""
        self.thinking_timer.stop()
        self.loading_container.hide()
        self.loading_label.hide()
        self.input_field.setPlaceholderText(_("Faça uma pergunta de acompanhamento"))
        self.input_field.setEnabled(True)
        
        if self.layout():
            self.layout().invalidate()
            self.layout().activate()

    def zoom_all_messages(self, action='in'):
        """Aplica a ação de zoom a todas as mensagens no chat"""
        for i in range(self.chat_area.layout.count() - 1):  # Ignora o item stretch
            item = self.chat_area.layout.itemAt(i)
            if item and item.widget():
                text_display = item.widget().layout().itemAt(0).widget()
                if isinstance(text_display, MarkdownTextBrowser):
                    if action == 'in':
                        text_display.zoom_in()
                    elif action == 'out':
                        text_display.zoom_out()
                    else:
                        text_display.reset_zoom()
        
        self.chat_area.update_content_height()
        
    def _adjust_window_height(self):
        """Calcula e define a altura ideal da janela"""
        if hasattr(self, '_size_initialized'):
            return
                
        try:
            content_height = self.chat_area.content_widget.sizeHint().height()
                
            ui_elements_height = (
                self.layout().contentsMargins().top() +
                self.layout().contentsMargins().bottom() +
                self.input_field.height() +
                self.layout().spacing() * 5 +
                200
            )
                
            screen = QtWidgets.QApplication.screenAt(self.pos())
            if not screen:
                screen = QtWidgets.QApplication.primaryScreen()
                
            max_height = int(screen.geometry().height() * 0.85)
                
            desired_content_height = int(content_height * 0.85)
            desired_total_height = min(
                desired_content_height + ui_elements_height,
                max_height
            )
                
            final_height = max(600, desired_total_height)
                
            final_width = 600
                
            self.resize(final_width, final_height)
                
            frame_geometry = self.frameGeometry()
            screen_center = screen.geometry().center()
            frame_geometry.moveCenter(screen_center)
            self.move(frame_geometry.topLeft())
                
            self._size_initialized = True
                
        except Exception as e:
            logging.error(f"Erro ao ajustar a altura da janela: {e}")
            self.resize(600, 600)
            self._size_initialized = True

    @Slot(str)
    def set_text(self, text):
        """Define o texto da resposta inicial com tratamento aprimorado"""
        if not text.strip():
            return
                
        self.chat_history = [
            {"role": "user", "content": f"{self.option}: {self.selected_text}"},
            {"role": "assistant", "content": text}
        ]
        
        self.stop_thinking_animation()
        text_display = self.chat_area.add_message(text)
        
        if hasattr(self.app.config, 'response_window_zoom'):
            text_display.zoom_factor = self.app.config['response_window_zoom']
            text_display._apply_zoom()
        
        QtCore.QTimer.singleShot(100, self._adjust_window_height)
        
    @Slot(str)
    def handle_followup_response(self, response_text):
        """Trata a resposta de acompanhamento da IA com layout aprimorado"""
        if response_text:
            self.loading_label.setVisible(False)
            text_display = self.chat_area.add_message(response_text)
            
            if hasattr(self, 'current_text_display'):
                text_display.zoom_factor = self.current_text_display.zoom_factor
                text_display._apply_zoom()
            
            if len(self.chat_history) > 0 and self.chat_history[-1]["role"] != "assistant":
                self.chat_history.append({
                    "role": "assistant",
                    "content": response_text
                })
        
        self.stop_thinking_animation()
        self.input_field.setEnabled(True)
        
        QtCore.QTimer.singleShot(100, self._adjust_window_height)
        
    def send_message(self):
        """Envia uma nova mensagem/pergunta"""
        message = self.input_field.text().strip()
        if not message:
            return
            
        self.input_field.setEnabled(False)
        self.input_field.clear()
        
        text_display = self.chat_area.add_message(message, is_user=True)
        if hasattr(self, 'current_text_display'):
            text_display.zoom_factor = self.current_text_display.zoom_factor
            text_display._apply_zoom()
        
        self.chat_history.append({"role": "user", "content": message})
        self.start_thinking_animation()
        self.app.process_followup_question(self, message)
        
    def copy_as_markdown(self):
        """Copia a conversa como Markdown"""
        markdown_text = ""
        for msg in self.chat_history:
            if msg["role"] == "user":
                markdown_text += f"**Usuário**: {msg['content']}\n\n"
            else:
                markdown_text += f"**Assistente**: {msg['content']}\n\n"
                
        QtWidgets.QApplication.clipboard().setText(markdown_text)
        
    def closeEvent(self, event):
        """Trata o evento de fechamento da janela"""
        if hasattr(self, 'current_text_display'):
            self.app.config['response_window_zoom'] = self.current_text_display.zoom_factor
            self.app.save_config(self.app.config)

        self.chat_history = []
        
        if hasattr(self.app, 'current_response_window'):
            delattr(self.app, 'current_response_window')
        
        super().closeEvent(event)
