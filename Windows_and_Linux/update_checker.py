import logging
import threading
import time
from urllib.error import HTTPError
from urllib.request import URLError, urlopen

CURRENT_VERSION = 7
UPDATE_CHECK_URL = "https://raw.githubusercontent.com/theJayTea/WritingTools/main/Windows_and_Linux/Latest_Version_for_Update_Check.txt"
UPDATE_DOWNLOAD_URL = "https://github.com/theJayTea/WritingTools/releases"

class UpdateChecker:
    def __init__(self, app):
        self.app = app
        
    def _fetch_latest_version(self):
        """
        Busca o número da versão mais recente no GitHub.
        Retorna o número da versão ou None se falhar.
        """
        try:
            with urlopen(UPDATE_CHECK_URL, timeout=5) as response:
                data = response.read().decode('utf-8').strip()
                try:
                    return int(data)
                except ValueError:
                    logging.warning(f"Formato de número de versão inválido: {data}")
                    return None
        except (URLError, HTTPError) as e:
            logging.warning(f"Falha ao buscar informações de versão: {e}")
            return None
        except Exception as e:
            logging.error(f"Erro inesperado ao verificar atualizações: {e}")
            return None

    def _retry_fetch_version(self):
        """
        Tenta buscar a versão com uma única nova tentativa.
        """
        result = self._fetch_latest_version()
        if result is None:
            # Aguarda 2 segundos antes de tentar novamente
            time.sleep(2)
            result = self._fetch_latest_version()
        return result

    def check_updates(self):
        """
        Verifica se uma atualização está disponível.
        Sempre compara com o valor na nuvem e atualiza a configuração conforme necessário.
        Retorna True se uma atualização estiver disponível.
        """
        latest_version = self._retry_fetch_version()
        
        if latest_version is None:
            return False
            
        update_available = latest_version > CURRENT_VERSION
        
        # Sempre atualiza a configuração com o status atualizado
        if "update_available" in self.app.config or update_available:
            self.app.config["update_available"] = update_available
            self.app.save_config(self.app.config)
            
        return update_available

    def check_updates_async(self):
        """
        Realiza a verificação de atualizações em uma thread em segundo plano.
        """
        def check_thread():
            self.check_updates()
            
        thread = threading.Thread(target=check_thread, daemon=True)
        thread.start()
