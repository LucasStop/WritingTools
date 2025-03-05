import webbrowser

from PySide6 import QtCore, QtGui, QtWidgets

from ui.UIUtils import UIUtils, colorMode

_ = lambda x: x

class AboutWindow(QtWidgets.QWidget):
    """
    A janela "Sobre" do aplicativo.
    """
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """
        Inicializa a interface de usuário da janela "Sobre".
        """
        self.setWindowTitle(' ')  # Hack para esconder o texto da barra de título. TODO: Encontrar uma solução melhor.
        self.setGeometry(300, 300, 650, 720)  # Define o tamanho da janela

        # Centraliza a janela na tela. Não conheço métodos em UIUtils para isso, então farei manualmente.
        screen = QtWidgets.QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

        UIUtils.setup_window_and_layout(self)

        # Desabilita o botão minimizar e o ícone na barra de título
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowMinimizeButtonHint & ~QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowCloseButtonHint | QtCore.Qt.WindowTitleHint)

        # Remove o ícone da janela. Deve ser feito após UIUtils.setup_window_and_layout().
        pixmap = QtGui.QPixmap(32, 32)
        pixmap.fill(QtCore.Qt.transparent)
        self.setWindowIcon(QtGui.QIcon(pixmap))

        content_layout = QtWidgets.QVBoxLayout(self.background)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(20)

        title_label = QtWidgets.QLabel(_("Sobre o Writing Tools"))
        title_label.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {'#ffffff' if colorMode == 'dark' else '#333333'};")
        content_layout.addWidget(title_label, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

        about_text = "<p style='text-align: center;'>" + \
                _("Writing Tools é uma ferramenta gratuita e leve que ajuda você a melhorar sua escrita com IA, semelhante ao novo recurso Apple Intelligence da Apple. Ela funciona com uma ampla variedade de LLMs de IA, tanto online quanto localmente.") + \
                """
                     <br>
                </p>
                <p style='text-align: center;'>""" + \
                "<b>" + _("Criado com carinho por Jesai, um estudante do ensino médio.") +"</b><br><br>" + \
                _("Sinta-se à vontade para conferir meu outro aplicativo de IA") + ", <a href=\"https://play.google.com/store/apps/details?id=com.jesai.blissai\"><b>Bliss AI</b></a>. " + _("É um tutor de IA inovador, gratuito na Google Play Store :)") + "<br><br>" + \
                "<b>" + _("Entre em contato") +":</b> jesaitarun@gmail.com<br><br>" + \
                """</p>
                <p style='text-align: center;'>
                <b>⭐ """ + \
                _("O Writing Tools não seria o que é hoje sem seus <u>incríveis</u> colaboradores") + ":</b><br>" + \
                "<b>1. <a href=\"https://github.com/momokrono\">momokrono</a>:</b><br>" + \
                _("Adicionou suporte ao Linux, trocou para a API pynput para melhorar a estabilidade no Windows. Adicionou suporte à API Ollama, a lógica central para botões personalizáveis e a localização. Corrigiu diversos bugs e adicionou suporte para encerramento gracioso ao tratar o sinal SIGINT.") + "<br>" + \
                "<b>2. <a href=\"https://github.com/CameronRedmore\">Cameron Redmore (CameronRedmore)</a>:</b><br>" + \
                _("Refatorou extensivamente o Writing Tools e adicionou suporte para API compatível com OpenAI, respostas transmitidas e o modo de geração de texto quando nenhum texto está selecionado.") + "<br>" + \
                '<b>3. <a href="https://github.com/Soszust40">Soszust40 (Soszust40)</a>:</b><br>' + \
                _('Contribuiu para adicionar o modo escuro, o tema simples, correções no menu da bandeja e melhorias na interface do usuário.') + '</b><br>' + \
                '<b>4. <a href="https://github.com/arsaboo">Alok Saboo (arsaboo)</a>:</b><br>' + \
                _('Contribuiu para melhorar a confiabilidade da seleção de texto.') + '</b><br>' + \
                '<b>5. <a href="https://github.com/raghavdhingra24">raghavdhingra24</a>:</b><br>' + \
                _('Aprimorou o anti-aliasing dos cantos arredondados, deixando-os mais bonitos.')+'</b><br>' + \
                '<b>6. <a href="https://github.com/ErrorCatDev">ErrorCatDev</a>:</b><br>' + \
                _('Melhorou significativamente a janela Sobre, tornando-a rolável e mais organizada. Também aprimorou nosso .gitignore e requirements.txt.') + '</b><br>' + \
                '<b>7. <a href="https://github.com/Vadim-Karpenko">Vadim Karpenko</a>:</b><br>' + \
                _('Contribuiu para adicionar a configuração de iniciar com o sistema.')+ "</b><br><br>" + \
                'Se você tiver um Mac, confira a <a href="https://github.com/theJayTea/WritingTools#-macos">versão para macOS do Writing Tools</a> por <a href="https://github.com/Aryamirsepasi">Arya Mirsepasi</a>!<br>' + \
                """</p>
                <p style='text-align: center;'>
                <b>Versão:</b> 7.0 (Codinome: Impecavelmente Melhorado)
                </p>
                <p />
                """

        about_label = QtWidgets.QLabel(about_text)
        about_label.setStyleSheet(f"font-size: 16px; color: {'#ffffff' if colorMode == 'dark' else '#333333'};")
        about_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        about_label.setWordWrap(True)
        about_label.setOpenExternalLinks(True)  # Permite a abertura de links externos

        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidget(about_label)
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("background: transparent;")

        content_layout.addWidget(scroll_area)

        # Adiciona o botão "Verificar atualizações"
        update_button = QtWidgets.QPushButton('Verificar atualizações')
        update_button.setStyleSheet("""
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
        update_button.clicked.connect(self.check_for_updates)
        content_layout.addWidget(update_button)

    def check_for_updates(self):
        """
        Abre a página de releases do GitHub para verificar atualizações.
        """
        webbrowser.open("https://github.com/theJayTea/WritingTools/releases")

    def original_app(self):
        """
        Abre a página do GitHub do aplicativo original.
        """
        webbrowser.open("https://github.com/TheJayTea/WritingTools")
