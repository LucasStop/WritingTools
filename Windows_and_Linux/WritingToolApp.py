import gettext
import json
import logging
import os
import signal
import sys
import threading
import time

import darkdetect
import pyperclip
from pynput import keyboard as pykeyboard
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import QLocale, Signal, Slot
from PySide6.QtGui import QCursor, QGuiApplication
from PySide6.QtWidgets import QApplication, QMessageBox

import ui.AboutWindow
import ui.CustomPopupWindow
import ui.OnboardingWindow
import ui.ResponseWindow
import ui.SettingsWindow
from aiprovider import GeminiProvider, OllamaProvider, OpenAICompatibleProvider
from update_checker import UpdateChecker

_ = gettext.gettext


class WritingToolApp(QtWidgets.QApplication):
    """
    A classe principal do aplicativo Writing Tools.
    """
    output_ready_signal = Signal(str)
    show_message_signal = Signal(str, str)  # sinal para exibir caixas de mensagem
    hotkey_triggered_signal = Signal()
    followup_response_signal = Signal(str)

    def __init__(self, argv):
        super().__init__(argv)
        self.current_response_window = None
        logging.debug('Inicializando WritingToolApp')
        self.output_ready_signal.connect(self.replace_text)
        self.show_message_signal.connect(self.show_message_box)
        self.hotkey_triggered_signal.connect(self.on_hotkey_pressed)
        self.config = None
        self.config_path = None
        self.load_config()
        self.options = None
        self.options_path = None
        self.load_options()
        self.onboarding_window = None
        self.popup_window = None
        self.tray_icon = None
        self.tray_menu = None
        self.settings_window = None
        self.about_window = None
        self.registered_hotkey = None
        self.output_queue = ""
        self.last_replace = 0
        self.hotkey_listener = None
        self.paused = False
        self.toggle_action = None

        self._ = gettext.gettext

        # Inicializa o listener de tecla Ctrl+C
        self.ctrl_c_timer = None
        self.setup_ctrl_c_listener()

        # Configura os provedores de IA disponíveis
        self.providers = [GeminiProvider(self), OpenAICompatibleProvider(self), OllamaProvider(self)]

        if not self.config:
            logging.debug('Nenhuma configuração encontrada, mostrando a tela de boas-vindas')
            self.show_onboarding()
        else:
            logging.debug('Configuração encontrada, configurando a tecla de atalho e o ícone da bandeja')
            # Inicializa o provedor atual, usando Gemini como padrão
            provider_name = self.config.get('provider', 'Gemini')

            self.current_provider = next((provider for provider in self.providers if provider.provider_name == provider_name), None)
            if not self.current_provider:
                logging.warning(f'Provedor {provider_name} não encontrado. Usando o provedor padrão.')
                self.current_provider = self.providers[0]

            self.current_provider.load_config(self.config.get("providers", {}).get(provider_name, {}))

            self.create_tray_icon()
            self.register_hotkey()

            try:
                lang = self.config['locale']
            except KeyError:
                lang = None
            self.change_language(lang)

            # Inicializa o verificador de atualizações
            self.update_checker = UpdateChecker(self)
            self.update_checker.check_updates_async()

        self.recent_triggers = []  # Armazena os acionamentos recentes da tecla de atalho
        self.TRIGGER_WINDOW = 1.5  # Janela de tempo em segundos
        self.MAX_TRIGGERS = 3  # Máximo de acionamentos permitidos na janela

    def setup_translations(self, lang=None):
        if not lang:
            lang = QLocale.system().name().split('_')[0]

        try:
            translation = gettext.translation(
                'messages',
                localedir=os.path.join(os.path.dirname(__file__), 'locales'),
                languages=[lang]
            )
        except FileNotFoundError:
            translation = gettext.NullTranslations()

        translation.install()
        # Atualiza a função de tradução para todos os componentes da interface
        self._ = translation.gettext
        ui.AboutWindow._ = self._
        ui.SettingsWindow._ = self._
        ui.ResponseWindow._ = self._
        ui.OnboardingWindow._ = self._
        ui.CustomPopupWindow._ = self._

    def retranslate_ui(self):
        self.update_tray_menu()

    def change_language(self, lang):
        self.setup_translations(lang)
        self.retranslate_ui()

        # Atualiza todas as outras janelas
        for widget in QApplication.topLevelWidgets():
            if widget != self and hasattr(widget, 'retranslate_ui'):
                widget.retranslate_ui()

    def check_trigger_spam(self):
        """
        Verifica se a tecla de atalho está sendo acionada com muita frequência (3+ vezes em 1.5 segundos).
        Retorna True se spam for detectado.
        """
        current_time = time.time()
        # Adiciona o acionamento atual
        self.recent_triggers.append(current_time)
        # Remove acionamentos antigos fora da janela
        self.recent_triggers = [t for t in self.recent_triggers if current_time - t <= self.TRIGGER_WINDOW]
        # Verifica se há acionamentos demais na janela
        return len(self.recent_triggers) >= self.MAX_TRIGGERS

    def load_config(self):
        """
        Carrega o arquivo de configuração.
        """
        self.config_path = os.path.join(os.path.dirname(sys.argv[0]), 'config.json')
        logging.debug(f'Carregando configuração de {self.config_path}')
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
                logging.debug('Configuração carregada com sucesso')
        else:
            logging.debug('Arquivo de configuração não encontrado')
            self.config = None

    def load_options(self):
        """
        Carrega o arquivo de opções.
        """
        self.options_path = os.path.join(os.path.dirname(sys.argv[0]), 'options.json')
        logging.debug(f'Carregando opções de {self.options_path}')
        if os.path.exists(self.options_path):
            with open(self.options_path, 'r') as f:
                self.options = json.load(f)
                logging.debug('Opções carregadas com sucesso')
        else:
            logging.debug('Arquivo de opções não encontrado')
            self.options = None

    def save_config(self, config):
        """
        Salva o arquivo de configuração.
        """
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=4)
            logging.debug('Configuração salva com sucesso')
        self.config = config

    def show_onboarding(self):
        """
        Exibe a janela de boas-vindas para usuários de primeira viagem.
        """
        logging.debug('Exibindo a janela de boas-vindas')
        self.onboarding_window = ui.OnboardingWindow.OnboardingWindow(self)
        self.onboarding_window.close_signal.connect(self.exit_app)
        self.onboarding_window.show()

    def start_hotkey_listener(self):
        """
        Cria um listener para teclas de atalho no Linux/Mac.
        """
        orig_shortcut = self.config.get('shortcut', 'ctrl+space')
        # Analisa a string do atalho, por exemplo, ctrl+alt+h -> <ctrl>+<alt>+h
        shortcut = '+'.join([f'{t}' if len(t) <= 1 else f'<{t}>' for t in orig_shortcut.split('+')])
        logging.debug(f'Registrando tecla de atalho global para: {shortcut}')
        try:
            if self.hotkey_listener is not None:
                self.hotkey_listener.stop()

            def on_activate():
                if self.paused:
                    return
                logging.debug('Tecla de atalho acionada')
                self.hotkey_triggered_signal.emit()  # Emite o sinal quando a tecla é pressionada

            # Define a combinação de tecla de atalho
            hotkey = pykeyboard.HotKey(pykeyboard.HotKey.parse(shortcut), on_activate)
            self.registered_hotkey = orig_shortcut

            # Função auxiliar para padronizar o evento de tecla
            def for_canonical(f):
                return lambda k: f(self.hotkey_listener.canonical(k))

            # Cria um listener e armazena como atributo para poder pará-lo depois
            self.hotkey_listener = pykeyboard.Listener(
                on_press=for_canonical(hotkey.press),
                on_release=for_canonical(hotkey.release)
            )

            # Inicia o listener
            self.hotkey_listener.start()
        except Exception as e:
            logging.error(f'Falha ao registrar a tecla de atalho: {e}')

    def register_hotkey(self):
        """
        Registra a tecla de atalho global para ativar o Writing Tools.
        """
        logging.debug('Registrando a tecla de atalho')
        self.start_hotkey_listener()
        logging.debug('Tecla de atalho registrada')

    def on_hotkey_pressed(self):
        """
        Trata o evento de pressionar a tecla de atalho.
        """
        logging.debug('Tecla de atalho pressionada')
        # Verifica se há spam de acionamentos
        if self.check_trigger_spam():
            logging.warning('Spam de tecla de atalho detectado - encerrando o aplicativo')
            self.exit_app()
            return

        # Continuação do tratamento original da tecla de atalho...
        if self.current_provider:
            logging.debug("Cancelando a solicitação do provedor atual")
            self.current_provider.cancel()
            self.output_queue = ""

        # Chama o método _show_popup de forma segura em thread
        QtCore.QMetaObject.invokeMethod(self, "_show_popup", QtCore.Qt.ConnectionType.QueuedConnection)

    @Slot()
    def _show_popup(self):
        """
        Exibe a janela pop-up quando a tecla de atalho é pressionada.
        """
        logging.debug('Exibindo janela pop-up')
        # Primeira tentativa com tempo de espera padrão
        selected_text = self.get_selected_text()

        # Tenta novamente com tempo de espera maior se nenhum texto foi capturado
        if not selected_text:
            logging.debug('Nenhum texto capturado, tentando novamente com tempo de espera maior')
            selected_text = self.get_selected_text(sleep_duration=0.5)

        logging.debug(f'Texto selecionado: "{selected_text}"')
        try:
            if self.popup_window is not None:
                logging.debug('Janela pop-up existente encontrada')
                if self.popup_window.isVisible():
                    logging.debug('Fechando janela pop-up visível existente')
                    self.popup_window.close()
                self.popup_window = None
            logging.debug('Criando nova janela pop-up')
            self.popup_window = ui.CustomPopupWindow.CustomPopupWindow(self, selected_text)

            # Define o ícone da janela
            icon_path = os.path.join(os.path.dirname(sys.argv[0]), 'icons', 'app_icon.png')
            if os.path.exists(icon_path):
                self.setWindowIcon(QtGui.QIcon(icon_path))
            # Obtém a tela onde o cursor está localizado
            cursor_pos = QCursor.pos()
            screen = QGuiApplication.screenAt(cursor_pos)
            if screen is None:
                screen = QGuiApplication.primaryScreen()
            screen_geometry = screen.geometry()
            logging.debug(f'Cursor está na tela: {screen.name()}')
            logging.debug(f'Geometria da tela: {screen_geometry}')
            # Exibe a janela pop-up para obter seu tamanho
            self.popup_window.show()
            self.popup_window.adjustSize()
            # Garante que a janela pop-up receba foco, mesmo em máquinas de baixo desempenho
            self.popup_window.activateWindow()
            QtCore.QTimer.singleShot(100, self.popup_window.custom_input.setFocus)

            popup_width = self.popup_window.width()
            popup_height = self.popup_window.height()
            # Calcula a posição
            x = cursor_pos.x()
            y = cursor_pos.y() + 20  # 20 pixels abaixo do cursor
            # Ajusta se a janela pop-up extrapolar a borda direita da tela
            if x + popup_width > screen_geometry.right():
                x = screen_geometry.right() - popup_width
            # Ajusta se a janela pop-up extrapolar a borda inferior da tela
            if y + popup_height > screen_geometry.bottom():
                y = cursor_pos.y() - popup_height - 10  # 10 pixels acima do cursor
            self.popup_window.move(x, y)
            logging.debug(f'Janela pop-up movida para a posição: ({x}, {y})')
        except Exception as e:
            logging.error(f'Erro ao exibir a janela pop-up: {e}', exc_info=True)

    def get_selected_text(self, sleep_duration=0.2):
        """
        Obtém o texto atualmente selecionado em qualquer aplicativo.
        Args:
            sleep_duration (float): Tempo de espera para a atualização da área de transferência.
        """
        # Faz backup da área de transferência
        clipboard_backup = pyperclip.paste()
        logging.debug(f'Backup da área de transferência: "{clipboard_backup}" (aguardar: {sleep_duration}s)')

        # Limpa a área de transferência
        self.clear_clipboard()

        # Simula Ctrl+C
        logging.debug('Simulando Ctrl+C')
        kbrd = pykeyboard.Controller()

        def press_ctrl_c():
            kbrd.press(pykeyboard.Key.ctrl.value)
            kbrd.press('c')
            kbrd.release('c')
            kbrd.release(pykeyboard.Key.ctrl.value)

        press_ctrl_c()

        # Aguarda a atualização da área de transferência
        time.sleep(sleep_duration)
        logging.debug(f'Aguardou {sleep_duration}s para a atualização da área de transferência')

        # Obtém o texto selecionado
        selected_text = pyperclip.paste()

        # Restaura a área de transferência
        pyperclip.copy(clipboard_backup)

        return selected_text

    @staticmethod
    def clear_clipboard():
        """
        Limpa a área de transferência do sistema.
        """
        try:
            pyperclip.copy('')
        except Exception as e:
            logging.error(f'Erro ao limpar a área de transferência: {e}')

    def process_option(self, option, selected_text, custom_change=None):
        """
        Processa a opção de escrita selecionada em uma thread separada.
        """
        logging.debug(f'Opção de processamento: {option}')

        # Para Summary, Key Points, Table e prompts custom com texto vazio, cria uma janela de resposta
        if (option == 'Custom' and not selected_text.strip()) or self.options[option]['open_in_window']:
            window_title = "Chat" if (option == 'Custom' and not selected_text.strip()) else option
            self.current_response_window = self.show_response_window(window_title, selected_text)
            # Inicializa o histórico de chat com o texto/prompt
            if option == 'Custom' and not selected_text.strip():
                # Para consultas diretas à IA, não inclui texto vazio
                self.current_response_window.chat_history = []
            else:
                # Para outras opções, inclui o texto original
                self.current_response_window.chat_history = [
                    {
                        "role": "user",
                        "content": f"Texto original para {option.lower()}:\n\n{selected_text}"
                    }
                ]
        else:
            # Remove qualquer referência de janela de resposta existente para opções sem janela
            if hasattr(self, 'current_response_window'):
                delattr(self, 'current_response_window')

        threading.Thread(target=self.process_option_thread, args=(option, selected_text, custom_change), daemon=True).start()

    def process_option_thread(self, option, selected_text, custom_change=None):
        """
        Função da thread para processar a opção de escrita selecionada utilizando o modelo de IA.
        """
        logging.debug(f'Iniciando thread de processamento para a opção: {option}')
        try:
            if selected_text.strip() == '':
                # Nenhum texto selecionado
                if option == 'Custom':
                    prompt = custom_change
                    system_instruction = ("Você é um assistente de conversação de IA amigável, útil, compassivo e cativante. "
                                          "Evite fazer suposições ou gerar conteúdo prejudicial, tendencioso ou inadequado. "
                                          "Em caso de dúvida, não invente informações. Peça esclarecimentos ao usuário, se necessário. "
                                          "Tente não ser repetitivo desnecessariamente em sua resposta. "
                                          "Você pode e deve, quando apropriado, usar formatação Markdown para tornar sua resposta mais legível.")
                else:
                    self.show_message_signal.emit('Erro', 'Por favor, selecione o texto para usar esta opção.')
                    return
            else:
                selected_prompt = self.options.get(option, ('', ''))
                prompt_prefix = selected_prompt['prefix']
                system_instruction = selected_prompt['instruction']
                if option == 'Custom':
                    prompt = f"{prompt_prefix}Mudança descrita: {custom_change}\n\nTexto: {selected_text}"
                else:
                    prompt = f"{prompt_prefix}{selected_text}"

            self.output_queue = ""
            logging.debug(f'Obtendo resposta do provedor para a opção: {option}')

            if (option == 'Custom' and not selected_text.strip()) or self.options[option]['open_in_window']:
                logging.debug('Obtendo resposta para exibição em janela')
                response = self.current_provider.get_response(system_instruction, prompt, return_response=True)
                logging.debug(f'Obtive resposta de comprimento: {len(response) if response else 0}')

                # Para prompts custom sem texto, adiciona a pergunta ao histórico de chat
                if option == 'Custom' and not selected_text.strip():
                    self.current_response_window.chat_history.append({
                        "role": "user",
                        "content": custom_change
                    })

                # Define a resposta inicial usando QMetaObject.invokeMethod para garantir segurança de thread
                if hasattr(self, 'current_response_window'):
                    QtCore.QMetaObject.invokeMethod(
                        self.current_response_window,
                        'set_text',
                        QtCore.Qt.ConnectionType.QueuedConnection,
                        QtCore.Q_ARG(str, response)
                    )
                    logging.debug('Chamou set_text na janela de resposta')
            else:
                logging.debug('Obtendo resposta para substituição direta')
                self.current_provider.get_response(system_instruction, prompt)
                logging.debug('Resposta processada')

        except Exception as e:
            logging.error(f'Ocorreu um erro: {e}', exc_info=True)
            if "Resource has been exhausted" in str(e):
                self.show_message_signal.emit(
                    'Erro - Limite de Taxa Atingido',
                    ("Ops! Você atingiu o limite de taxa por minuto da API Gemini. "
                     "Por favor, tente novamente em alguns instantes.\n\nSe isso ocorrer com frequência, "
                     "simplesmente altere para um modelo Gemini com um limite de uso maior em Configurações.")
                )
                self.followup_response_signal.emit("Desculpe, ocorreu um erro ao processar sua pergunta.")
            else:
                self.show_message_signal.emit('Erro', f'Ocorreu um erro: {e}')
                self.followup_response_signal.emit("Desculpe, ocorreu um erro ao processar sua pergunta.")

    @Slot(str, str)
    def show_message_box(self, title, message):
        """
        Exibe uma caixa de mensagem com o título e a mensagem fornecidos.
        """
        QMessageBox.warning(None, title, message)

    def show_response_window(self, option, text):
        """
        Exibe a resposta em uma nova janela em vez de colá-la.
        """
        response_window = ui.ResponseWindow.ResponseWindow(self, f"{option} Result")
        response_window.selected_text = text  # Armazena o texto para regeneração
        response_window.show()
        return response_window

    def replace_text(self, new_text):
        """
        Substitui o texto colando o texto gerado pela IA. Para "Key Points" e "Summary", invoca uma janela com a saída.
        """
        error_message = 'ERROR_TEXT_INCOMPATIBLE_WITH_REQUEST'

        # Verifica se new_text existe e é uma string
        if new_text and isinstance(new_text, str):
            self.output_queue += new_text
            current_output = self.output_queue.strip()  # Remove espaços para comparação

            # Se o novo texto for a mensagem de erro, exibe uma caixa de mensagem
            if current_output == error_message:
                self.show_message_signal.emit('Erro', 'O texto é incompatível com a alteração solicitada.')
                return

            # Verifica se estamos formando a mensagem de erro (para evitar colagens parciais)
            if len(current_output) <= len(error_message):
                clean_current = ''.join(current_output.split())
                clean_error = ''.join(error_message.split())
                if clean_current == clean_error[:len(clean_current)]:
                    return

            logging.debug('Processando o texto de saída')
            try:
                # Para Summary e Key Points, exibe na janela de resposta
                if hasattr(self, 'current_response_window'):
                    self.current_response_window.append_text(new_text)
                    # Se for a resposta inicial, adiciona ao histórico de chat
                    if len(self.current_response_window.chat_history) == 1:  # Apenas o texto original existe
                        self.current_response_window.chat_history.append({
                            "role": "assistant",
                            "content": self.output_queue.rstrip('\n')
                        })
                else:
                    # Para outras opções, usa a substituição baseada na área de transferência
                    clipboard_backup = pyperclip.paste()
                    cleaned_text = self.output_queue.rstrip('\n')
                    pyperclip.copy(cleaned_text)

                    kbrd = pykeyboard.Controller()

                    def press_ctrl_v():
                        kbrd.press(pykeyboard.Key.ctrl.value)
                        kbrd.press('v')
                        kbrd.release('v')
                        kbrd.release(pykeyboard.Key.ctrl.value)

                    press_ctrl_v()
                    time.sleep(0.2)
                    pyperclip.copy(clipboard_backup)

                if not hasattr(self, 'current_response_window'):
                    self.output_queue = ""

            except Exception as e:
                logging.error(f'Erro ao processar a saída: {e}')
        else:
            logging.debug('Nenhum novo texto para processar')

    def create_tray_icon(self):
        """
        Cria o ícone da bandeja do sistema para o aplicativo.
        """
        if self.tray_icon:
            logging.debug('Ícone da bandeja já existe')
            return

        logging.debug('Criando ícone da bandeja')
        icon_path = os.path.join(os.path.dirname(sys.argv[0]), 'icons', 'app_icon.png')
        if not os.path.exists(icon_path):
            logging.warning(f'Ícone da bandeja não encontrado em {icon_path}')
            self.tray_icon = QtWidgets.QSystemTrayIcon(self)
        else:
            self.tray_icon = QtWidgets.QSystemTrayIcon(QtGui.QIcon(icon_path), self)
        # Define o tooltip (nome ao passar o mouse) para o ícone da bandeja
        self.tray_icon.setToolTip("WritingTools")
        self.tray_menu = QtWidgets.QMenu()
        self.tray_icon.setContextMenu(self.tray_menu)

        self.update_tray_menu()
        self.tray_icon.show()
        logging.debug('Ícone da bandeja exibido')

    def update_tray_menu(self):
        """
        Atualiza o menu da bandeja com todos os itens, incluindo a funcionalidade de pausa
        e traduções adequadas.
        """
        self.tray_menu.clear()
        # Aplica estilos de modo escuro usando darkdetect
        self.apply_dark_mode_styles(self.tray_menu)
        # Item de menu para Configurações
        settings_action = self.tray_menu.addAction(self._('Configurações'))
        settings_action.triggered.connect(self.show_settings)
        # Item de menu para alternar Pausar/Retomar
        self.toggle_action = self.tray_menu.addAction(self._('Retomar') if self.paused else self._('Pausar'))
        self.toggle_action.triggered.connect(self.toggle_paused)
        # Item de menu para Sobre
        about_action = self.tray_menu.addAction(self._('Sobre'))
        about_action.triggered.connect(self.show_about)
        # Item de menu para Sair
        exit_action = self.tray_menu.addAction(self._('Sair'))
        exit_action.triggered.connect(self.exit_app)

    def toggle_paused(self):
        """Alterna o estado de pausa do aplicativo."""
        logging.debug('Alternando estado de pausa')
        self.paused = not self.paused
        self.toggle_action.setText(self._('Retomar') if self.paused else self._('Pausar'))
        logging.debug('Aplicativo em pausa' if self.paused else 'Aplicativo retomado')

    @staticmethod
    def apply_dark_mode_styles(menu):
        """
        Aplica estilos ao menu da bandeja com base no tema do sistema usando darkdetect.
        """
        is_dark_mode = darkdetect.isDark()
        palette = menu.palette()

        if is_dark_mode:
            logging.debug('Ícone da bandeja em modo escuro')
            palette.setColor(QtGui.QPalette.Window, QtGui.QColor("#2d2d2d"))
            palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor("#ffffff"))
        else:
            logging.debug('Ícone da bandeja em modo claro')
            palette.setColor(QtGui.QPalette.Window, QtGui.QColor("#ffffff"))
            palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor("#000000"))

        menu.setPalette(palette)

    def process_followup_question(self, response_window, question):
        """
        Processa uma pergunta de acompanhamento na janela de chat.
        """
        logging.debug(f'Processando pergunta de acompanhamento: {question}')
        
        def process_thread():
            logging.debug('Iniciando thread de processamento de acompanhamento')
            try:
                if not response_window.chat_history:
                    logging.error("Histórico de chat não encontrado")
                    self.show_message_signal.emit('Erro', 'Histórico de chat não encontrado')
                    return

                # Adiciona a pergunta atual ao histórico de chat
                response_window.chat_history.append({
                    "role": "user",
                    "content": question
                })
                
                # Obtém o histórico de chat
                history = response_window.chat_history.copy()
                
                # Instrução do sistema baseada na opção original
                system_instruction = ("Você é um assistente de IA útil. Forneça respostas claras e diretas, mantendo o mesmo formato e estilo de suas respostas anteriores. "
                                        "Se apropriado, use formatação Markdown para tornar sua resposta mais legível.")
                
                logging.debug('Enviando requisição para o provedor de IA')
                
                # Formata a conversa de forma diferente com base no provedor
                if isinstance(self.current_provider, GeminiProvider):
                    chat_messages = []
                    # Converte nossos papéis para os papéis esperados pelo Gemini
                    for msg in history:
                        gemini_role = "model" if msg["role"] == "assistant" else "user"
                        chat_messages.append({
                            "role": gemini_role,
                            "parts": msg["content"]
                        })
                    # Inicia a conversa com o histórico
                    chat = self.current_provider.model.start_chat(history=chat_messages)
                    # Obtém a resposta usando a conversa
                    response = chat.send_message(question)
                    response_text = response.text

                elif isinstance(self.current_provider, OllamaProvider):
                    # Para Ollama, prepara as mensagens com a instrução do sistema e o histórico
                    messages = [{"role": "system", "content": system_instruction}]
                    for msg in history:
                        messages.append({
                            "role": msg["role"],
                            "content": msg["content"]
                        })
                    # Obtém a resposta do Ollama
                    response_text = self.current_provider.get_response(
                        system_instruction,
                        messages,
                        return_response=True
                    )

                else:
                    # Para provedores OpenAI/compatíveis, prepara um array de mensagens com a mensagem do sistema
                    messages = [{"role": "system", "content": system_instruction}]
                    for msg in history:
                        role = "assistant" if msg["role"] == "assistant" else "user"
                        messages.append({"role": role, "content": msg["content"]})
                    response_text = self.current_provider.get_response(
                        system_instruction,
                        messages,
                        return_response=True
                    )

                logging.debug(f'Recebida resposta de comprimento: {len(response_text)}')
                
                # Adiciona a resposta ao histórico de chat
                response_window.chat_history.append({
                    "role": "assistant",
                    "content": response_text
                })
                
                # Emite a resposta via sinal
                self.followup_response_signal.emit(response_text)

            except Exception as e:
                logging.error(f'Erro ao processar a pergunta de acompanhamento: {e}', exc_info=True)
                if "Resource has been exhausted" in str(e):
                    self.show_message_signal.emit(
                        'Erro - Limite de Taxa Atingido',
                        ("Ops! Você atingiu o limite de taxa por minuto da API Gemini. Por favor, tente novamente em alguns instantes.\n\n"
                         "Se isso ocorrer com frequência, altere para um modelo Gemini com um limite de uso maior em Configurações.")
                    )
                    self.followup_response_signal.emit("Desculpe, ocorreu um erro ao processar sua pergunta.")
                else:
                    self.show_message_signal.emit('Erro', f'Ocorreu um erro: {e}')
                    self.followup_response_signal.emit("Desculpe, ocorreu um erro ao processar sua pergunta.")

        threading.Thread(target=process_thread, daemon=True).start()

    def show_settings(self, providers_only=False):
        """
        Exibe a janela de configurações.
        """
        logging.debug('Exibindo janela de configurações')
        self.settings_window = ui.SettingsWindow.SettingsWindow(self, providers_only=providers_only)
        self.settings_window.close_signal.connect(self.exit_app)
        self.settings_window.retranslate_ui()
        self.settings_window.show()

    def show_about(self):
        """
        Exibe a janela "Sobre".
        """
        logging.debug('Exibindo janela Sobre')
        if not self.about_window:
            self.about_window = ui.AboutWindow.AboutWindow()
        self.about_window.show()

    def setup_ctrl_c_listener(self):
        """
        Listener para Ctrl+C para encerrar o aplicativo.
        """
        signal.signal(signal.SIGINT, lambda signum, frame: self.handle_sigint(signum, frame))
        # Este timer vazio é necessário para garantir que o handler de SIGINT seja verificado no loop principal:
        self.ctrl_c_timer = QtCore.QTimer()
        self.ctrl_c_timer.start(100)
        self.ctrl_c_timer.timeout.connect(lambda: None)

    def handle_sigint(self, signum, frame):
        """
        Trata o sinal SIGINT (Ctrl+C) para encerrar o aplicativo graciosamente.
        """
        logging.info("Recebido SIGINT. Encerrando...")
        self.exit_app()

    def exit_app(self):
        """
        Encerra o aplicativo.
        """
        logging.debug('Parando o listener')
        if self.hotkey_listener is not None:
            self.hotkey_listener.stop()
        logging.debug('Encerrando o aplicativo')
        self.quit()
