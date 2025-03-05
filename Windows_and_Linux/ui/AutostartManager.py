import logging
import sys

if sys.platform.startswith("win32"):
    import winreg

class AutostartManager:
    """
    Gerencia a funcionalidade de inicialização automática do Writing Tools.
    Trata a configuração e remoção das entradas de registro de inicialização automática no Windows.
    """
    
    @staticmethod
    def is_compiled():
        """
        Verifica se estamos executando a partir de um exe compilado ou do código-fonte.
        """
        return hasattr(sys, 'frozen') and hasattr(sys, '_MEIPASS')

    @staticmethod
    def get_startup_path():
        """
        Retorna o caminho que deve ser usado para a inicialização automática.
        Retorna None se estiver executando a partir do código-fonte ou em um sistema que não seja Windows.
        """
        if not sys.platform.startswith('win32'):
            return None
            
        if not AutostartManager.is_compiled():
            return None
            
        return sys.executable

    @staticmethod
    def set_autostart(enable: bool) -> bool:
        """
        Ativa ou desativa a inicialização automática do Writing Tools.
        
        Parâmetros:
            enable: True para ativar a inicialização automática, False para desativar
            
        Retorna:
            bool: True se a operação foi bem-sucedida, False se falhou ou não for suportada
        """
        try:
            startup_path = AutostartManager.get_startup_path()
            if not startup_path:
                return False

            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            
            try:
                if enable:
                    # Abre/cria a chave e define o valor
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, 
                                       winreg.KEY_WRITE)
                    winreg.SetValueEx(key, "WritingTools", 0, winreg.REG_SZ, 
                                    startup_path)
                else:
                    # Abre a chave e deleta o valor, se existir
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0,
                                       winreg.KEY_WRITE)
                    try:
                        winreg.DeleteValue(key, "WritingTools")
                    except WindowsError:
                        # O valor não existe, o que está ok
                        pass
                        
                winreg.CloseKey(key)
                return True
                
            except WindowsError as e:
                logging.error(f"Falha ao modificar o registro de inicialização automática: {e}")
                return False
                
        except Exception as e:
            logging.error(f"Erro ao gerenciar a inicialização automática: {e}")
            return False

    @staticmethod
    def check_autostart() -> bool:
        """
        Verifica se o Writing Tools está configurado para iniciar automaticamente.
        
        Retorna:
            bool: True se a inicialização automática estiver ativada, False se estiver desativada ou não for suportada
        """
        try:
            startup_path = AutostartManager.get_startup_path()
            if not startup_path:
                return False

            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                   r"Software\Microsoft\Windows\CurrentVersion\Run",
                                   0, winreg.KEY_READ)
                value, _ = winreg.QueryValueEx(key, "WritingTools")
                winreg.CloseKey(key)
                
                # Verifica se o caminho armazenado corresponde ao nosso exe atual
                return value.lower() == startup_path.lower()
                
            except WindowsError:
                # A chave ou valor não existe
                return False
                
        except Exception as e:
            logging.error(f"Erro ao verificar o status da inicialização automática: {e}")
            return False
