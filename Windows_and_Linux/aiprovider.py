"""
Arquitetura de Provedores de IA para o Writing Tools
------------------------------------------------------

Este módulo gerencia diferentes provedores de modelos de IA (Gemini, compatível com OpenAI, Ollama) e administra suas interações
com o aplicativo principal. Utiliza um padrão de classe base abstrata para as implementações dos provedores.

Componentes Principais:
1. AIProviderSetting – Classe base para configurações do provedor (por exemplo, chaves de API, nomes de modelos)
    • TextSetting      – Um campo de texto simples para configurações
    • DropdownSetting  – Uma configuração via dropdown

2. AIProvider – Classe base abstrata que todos os provedores implementam.
   Define a interface para:
      • Obter uma resposta do modelo de IA
      • Carregar e salvar configurações
      • Cancelar uma requisição em andamento

3. Implementações de Provedores:
    • GeminiProvider – Utiliza a API de IA Generativa do Google (Gemini) para gerar conteúdo.
    • OpenAICompatibleProvider – Conecta-se a qualquer API compatível com OpenAI (v1/chat/completions)
    • OllamaProvider – Conecta-se a um servidor Ollama em execução localmente (por exemplo, para llama.cpp)

Fluxo de Resposta:
   • O aplicativo principal chama get_response() com uma instrução do sistema e um prompt.
   • O provedor formata e envia a requisição para seu endpoint de API.
   • Para operações que exigem uma janela (por exemplo, Resumo, Pontos-Chave), o provedor retorna o texto completo.
   • Para substituição direta de texto, o provedor emite o texto completo via output_ready_signal.
   • O histórico de conversação (para perguntas de acompanhamento) é mantido pelo aplicativo principal.

Nota: O streaming foi completamente removido ao longo do código.
"""

import logging
import webbrowser
from abc import ABC, abstractmethod
from typing import List

# Bibliotecas externas
import google.generativeai as genai
from google.generativeai.types import HarmBlockThreshold, HarmCategory
from ollama import Client as OllamaClient
from openai import OpenAI
from PySide6 import QtWidgets
from PySide6.QtWidgets import QVBoxLayout
from ui.UIUtils import colorMode


class AIProviderSetting(ABC):
    """
    Classe base abstrata para uma configuração de provedor (por exemplo, chave de API, seleção de modelo).
    """
    def __init__(self, name: str, display_name: str = None, default_value: str = None, description: str = None):
        self.name = name
        self.display_name = display_name if display_name else name
        self.default_value = default_value if default_value else ""
        self.description = description if description else ""

    @abstractmethod
    def render_to_layout(self, layout: QVBoxLayout):
        """Renderiza o(s) widget(s) da configuração no layout fornecido."""
        pass

    @abstractmethod
    def set_value(self, value):
        """Define o valor interno a partir da configuração."""
        pass

    @abstractmethod
    def get_value(self):
        """Retorna o valor atual do widget."""
        pass


class TextSetting(AIProviderSetting):
    """
    Uma configuração baseada em texto (para chaves de API, URLs, etc.).
    """
    def __init__(self, name: str, display_name: str = None, default_value: str = None, description: str = None):
        super().__init__(name, display_name, default_value, description)
        self.internal_value = default_value
        self.input = None

    def render_to_layout(self, layout: QVBoxLayout):
        row_layout = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel(self.display_name)
        label.setStyleSheet(f"font-size: 16px; color: {'#ffffff' if colorMode=='dark' else '#333333'};")
        row_layout.addWidget(label)
        self.input = QtWidgets.QLineEdit(self.internal_value)
        self.input.setStyleSheet(f"""
            font-size: 16px;
            padding: 5px;
            background-color: {'#444' if colorMode=='dark' else 'white'};
            color: {'#ffffff' if colorMode=='dark' else '#000000'};
            border: 1px solid {'#666' if colorMode=='dark' else '#ccc'};
        """)
        self.input.setPlaceholderText(self.description)
        row_layout.addWidget(self.input)
        layout.addLayout(row_layout)

    def set_value(self, value):
        self.internal_value = value

    def get_value(self):
        return self.input.text()


class DropdownSetting(AIProviderSetting):
    """
    Uma configuração via dropdown (por exemplo, para selecionar um modelo).
    """
    def __init__(self, name: str, display_name: str = None, default_value: str = None,
                 description: str = None, options: list = None):
        super().__init__(name, display_name, default_value, description)
        self.options = options if options else []
        self.internal_value = default_value
        self.dropdown = None

    def render_to_layout(self, layout: QVBoxLayout):
        row_layout = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel(self.display_name)
        label.setStyleSheet(f"font-size: 16px; color: {'#ffffff' if colorMode=='dark' else '#333333'};")
        row_layout.addWidget(label)
        self.dropdown = QtWidgets.QComboBox()
        self.dropdown.setStyleSheet(f"""
            font-size: 16px;
            padding: 5px;
            background-color: {'#444' if colorMode=='dark' else 'white'};
            color: {'#ffffff' if colorMode=='dark' else '#000000'};
            border: 1px solid {'#666' if colorMode=='dark' else '#ccc'};
        """)
        for option, value in self.options:
            self.dropdown.addItem(option, value)
        index = self.dropdown.findData(self.internal_value)
        if index != -1:
            self.dropdown.setCurrentIndex(index)
        row_layout.addWidget(self.dropdown)
        layout.addLayout(row_layout)

    def set_value(self, value):
        self.internal_value = value

    def get_value(self):
        return self.dropdown.currentData()


class AIProvider(ABC):
    """
    Classe base abstrata para provedores de IA.
    
    Todos os provedores devem implementar:
      • get_response(system_instruction, prompt) -> str
      • after_load() para criar seu cliente ou instância de modelo
      • before_load() para limpar qualquer cliente existente
      • cancel() para cancelar uma requisição em andamento
    """
    def __init__(self, app, provider_name: str, settings: List[AIProviderSetting],
                 description: str = "Um provedor de IA inacabado!",
                 logo: str = "genérico",
                 button_text: str = "Ir para URL",
                 button_action: callable = None):
        self.provider_name = provider_name
        self.settings = settings
        self.app = app
        self.description = description if description else "Um provedor de IA inacabado!"
        self.logo = logo
        self.button_text = button_text
        self.button_action = button_action

    @abstractmethod
    def get_response(self, system_instruction: str, prompt: str) -> str:
        """
        Envia a instrução do sistema e o prompt para o provedor de IA e retorna o texto completo da resposta.
        """
        pass

    def load_config(self, config: dict):
        """
        Carrega as configurações no provedor.
        """
        for setting in self.settings:
            if setting.name in config:
                setattr(self, setting.name, config[setting.name])
                setting.set_value(config[setting.name])
            else:
                setattr(self, setting.name, setting.default_value)
        self.after_load()

    def save_config(self):
        """
        Salva as configurações do provedor no arquivo de configuração principal.
        """
        config = {}
        for setting in self.settings:
            config[setting.name] = setting.get_value()
        self.app.config["providers"][self.provider_name] = config
        self.app.save_config(self.app.config)

    @abstractmethod
    def after_load(self):
        """
        Chamado após a configuração ser carregada; crie seu cliente de API aqui.
        """
        pass

    @abstractmethod
    def before_load(self):
        """
        Chamado antes de recarregar a configuração; limpe seu cliente de API aqui.
        """
        pass

    @abstractmethod
    def cancel(self):
        """
        Cancela qualquer requisição de API em andamento.
        """
        pass


class GeminiProvider(AIProvider):
    """
    Provedor para a API Gemini do Google.
    
    Utiliza google.generativeai.GenerativeModel.generate_content() para gerar texto.
    O streaming não é utilizado; sempre é realizada uma requisição única.
    """
    def __init__(self, app):
        self.close_requested = False
        self.model = None

        settings = [
            TextSetting(name="api_key", display_name="Chave de API", description="Cole sua chave da API Gemini aqui"),
            DropdownSetting(
                name="model_name",
                display_name="Modelo",
                default_value="gemini-2.0-flash",
                description="Selecione o modelo Gemini a ser usado",
                options=[
                    ("Gemini 2.0 Flash Lite (inteligente | muito rápido | 30 usos/min)", "gemini-2.0-flash-lite-preview-02-05"),
                    ("Gemini 2.0 Flash (muito inteligente | rápido | 15 usos/min)", "gemini-2.0-flash"),
                    ("Gemini 2.0 Flash Thinking (mais inteligente | lento | 10 usos/min)", "gemini-2.0-flash-thinking-exp-01-21"),
                    ("Gemini 2.0 Pro (mais inteligente | lento | 2 usos/min)", "gemini-2.0-pro-exp-02-05"),
                ]
            )
        ]
        super().__init__(app, "Gemini (Recomendado)", settings,
            "• O Gemini do Google é um modelo de IA poderoso disponível gratuitamente!\n"
            "• É necessária uma chave de API para conectar-se ao Gemini em seu nome.\n"
            "• Clique no botão abaixo para obter sua chave de API.",
            "gemini",
            "Obter Chave de API",
            lambda: webbrowser.open("https://aistudio.google.com/app/apikey"))

    def get_response(self, system_instruction: str, prompt: str, return_response: bool = False) -> str:
        """
        Gera conteúdo utilizando o Gemini.
        
        Realiza sempre uma requisição única com streaming desativado.
        Retorna o texto completo da resposta se return_response for True,
        caso contrário, emite o texto via output_ready_signal.
        """
        self.close_requested = False

        # Chamada única com streaming desativado
        response = self.model.generate_content(
            contents=[system_instruction, prompt],
            stream=False
        )

        try:
            response_text = response.text.rstrip('\n')
            if not return_response and not hasattr(self.app, 'current_response_window'):
                self.app.output_ready_signal.emit(response_text)
                self.app.replace_text(True)
                return ""
            return response_text
        except Exception as e:
            logging.error(f"Erro ao processar resposta do Gemini: {e}")
            self.app.output_ready_signal.emit("Ocorreu um erro ao processar a resposta.")
        finally:
            self.close_requested = False

        return ""

    def after_load(self):
        """
        Configura o cliente do google.generativeai e cria o modelo generativo.
        """
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=genai.types.GenerationConfig(
                candidate_count=1,
                max_output_tokens=1000,
                temperature=0.5
            ),
            safety_settings={
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
        )

    def before_load(self):
        self.model = None

    def cancel(self):
        self.close_requested = True


class OpenAICompatibleProvider(AIProvider):
    """
    Provedor para APIs compatíveis com OpenAI.
    
    Utiliza self.client.chat.completions.create() para obter uma resposta.
    O streaming foi completamente removido.
    """
    def __init__(self, app):
        self.close_requested = None
        self.client = None

        settings = [
            TextSetting(name="api_key", display_name="Chave de API", description="Chave de API para a API compatível com OpenAI."),
            TextSetting("api_base", "URL Base da API", "https://api.openai.com/v1", "Ex.: https://api.openai.com/v1"),
            TextSetting("api_organisation", "Organização da API", "", "Deixe em branco se não aplicável."),
            TextSetting("api_project", "Projeto da API", "", "Deixe em branco se não aplicável."),
            TextSetting("api_model", "Modelo da API", "gpt-4o-mini", "Ex.: gpt-4o-mini"),
        ]
        super().__init__(app, "OpenAI Compatible (Para Especialistas)", settings,
           "• Conecte-se a QUALQUER API compatível com OpenAI (v1/chat/completions).\n"
            "• Você deve obedecer aos Termos de Serviço do serviço.",
            "openai", "Obter Chave API da OpenAI", lambda: webbrowser.open("https://platform.openai.com/account/api-keys"))

    def get_response(self, system_instruction: str, prompt: str | list, return_response: bool = False) -> str:
        """
        Envia uma requisição de chat para a API compatível com OpenAI.
        
        Realiza sempre uma requisição sem streaming.
        Se prompt não for uma lista, constrói uma conversa simples com duas mensagens.
        Retorna o texto da resposta se return_response for True,
        caso contrário, emite-o via output_ready_signal.
        """
        self.close_requested = False

        if isinstance(prompt, list):
            messages = prompt
        else:
            messages = [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ]

        try:
            response = self.client.chat.completions.create(
                model=self.api_model,
                messages=messages,
                temperature=0.5,
                stream=False
            )
            response_text = response.choices[0].message.content.strip()

            if not return_response and not hasattr(self.app, 'current_response_window'):
                self.app.output_ready_signal.emit(response_text)
            return response_text

        except Exception as e:
            error_str = str(e)
            logging.error(f"Erro durante a geração de conteúdo: {error_str}")
            if "exceeded" in error_str or "rate limit" in error_str:
                self.app.show_message_signal.emit(
                    "Limite de Taxa Atingido",
                    "Parece que você atingiu um limite de taxa/uso da API. Por favor, tente novamente mais tarde ou ajuste suas configurações."
                )
            else:
                self.app.show_message_signal.emit("Erro", f"Ocorreu um erro: {error_str}")
            return ""

    def after_load(self):
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.api_base,
            organization=self.api_organisation,
            project=self.api_project
        )

    def before_load(self):
        self.client = None

    def cancel(self):
        self.close_requested = True


class OllamaProvider(AIProvider):
    """
    Provedor para conectar a um servidor Ollama.
    
    Utiliza o endpoint /chat do servidor Ollama para gerar uma resposta.
    O streaming não é utilizado.
    """
    def __init__(self, app):
        self.close_requested = None
        self.client = None
        self.app = app
        settings = [
            TextSetting("api_base", "URL Base da API", "http://localhost:11434", "Ex.: http://localhost:11434"),
            TextSetting("api_model", "Modelo da API", "llama3.1:8b", "Ex.: llama3.1:8b"),
            TextSetting("keep_alive", "Tempo para manter o modelo carregado em memória (em minutos)", "5", "Ex.: 5")
        ]
        super().__init__(app, "Ollama (Para Especialistas)", settings,
           "• Conectar-se a um servidor Ollama (LLM local).",
            "ollama", "Instruções de Configuração do Ollama",
            lambda: webbrowser.open("https://github.com/theJayTea/WritingTools?tab=readme-ov-file#-optional-ollama-local-llm-instructions-for-windows-v7-onwards"))

    def get_response(self, system_instruction: str, prompt: str | list, return_response: bool = False) -> str:
        """
        Envia uma requisição de chat para o servidor Ollama.
        
        Realiza sempre uma requisição sem streaming.
        Retorna o texto da resposta se return_response for True,
        caso contrário, emite-o via output_ready_signal.
        """
        self.close_requested = False

        if isinstance(prompt, list):
            messages = prompt
        else:
            messages = [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ]

        try:
            response = self.client.chat(model=self.api_model, messages=messages)
            response_text = response['message']['content'].strip()
            if not return_response and not hasattr(self.app, 'current_response_window'):
                self.app.output_ready_signal.emit(response_text)
            return response_text
        except Exception as e:
            logging.error(f"Erro durante o chat do Ollama: {e}")
            self.app.output_ready_signal.emit("Ocorreu um erro durante o chat do Ollama.")
            return ""

    def after_load(self):
        self.client = OllamaClient(host=self.api_base)

    def before_load(self):
        self.client = None

    def cancel(self):
        self.close_requested = True
