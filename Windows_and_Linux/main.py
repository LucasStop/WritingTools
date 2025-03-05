import logging
import sys

from WritingToolApp import WritingToolApp

# Configura o registro de log no console
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


def main():
    """
    O ponto de entrada principal do aplicativo.
    """
    app = WritingToolApp(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
