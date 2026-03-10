from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
import aiohttp
import json
from src.core.config import get_settings
from src.utils.logging import logger

settings = get_settings()


class BaseLLMClient(ABC):
    """Base class for LLM clients"""
    
    def __init__(self, model_name: str, api_key: Optional[str] = None):
        self.model_name = model_name
        self.api_key = api_key
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        """Generate text from prompt"""
        pass


class OpenAIClient(BaseLLMClient):
    """OpenAI API client"""
    
    def __init__(self, model_name: str = "gpt-4", api_key: Optional[str] = None):
        super().__init__(model_name, api_key or settings.OPENAI_API_KEY)
        self.base_url = "https://api.openai.com/v1/chat/completions"
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.base_url, headers=headers, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"OpenAI API error: {error_text}")
                
                result = await response.json()
                return result["choices"][0]["message"]["content"]


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude API client"""
    
    def __init__(self, model_name: str = "claude-3-opus-20240229", api_key: Optional[str] = None):
        super().__init__(model_name, api_key or settings.ANTHROPIC_API_KEY)
        self.base_url = "https://api.anthropic.com/v1/messages"
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        data = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.base_url, headers=headers, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Anthropic API error: {error_text}")
                
                result = await response.json()
                return result["content"][0]["text"]


class LocalLLMClient(BaseLLMClient):
    """Local LLM client (Ollama, LM Studio, etc.)"""
    
    def __init__(self, model_name: str = "llama2", base_url: str = "http://localhost:11434"):
        super().__init__(model_name, None)
        self.base_url = base_url
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        # Ollama API format
        url = f"{self.base_url}/api/generate"
        
        data = {
            "model": self.model_name,
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
            **kwargs
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Local LLM error: {error_text}")
                
                result = await response.json()
                return result["response"]


class LLMFactory:
    """
    Factory for creating LLM clients
    
    Supports multiple providers:
    - OpenAI (GPT-4, GPT-3.5)
    - Anthropic (Claude)
    - Local models (Ollama, LM Studio)
    - Azure OpenAI
    - Google Vertex AI
    """
    
    def __init__(self):
        self.clients = {}
        self.default_provider = settings.LLM_PROVIDER or "openai"
        
        logger.info(f"LLM Factory initialized with default provider: {self.default_provider}")
    
    def get_client(
        self,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        **kwargs
    ) -> BaseLLMClient:
        """
        Get LLM client for specified provider
        
        Args:
            provider: openai, anthropic, local, azure, vertex
            model_name: Specific model to use
            **kwargs: Additional provider-specific parameters
        """
        provider = provider or self.default_provider
        
        # Check cache
        cache_key = f"{provider}:{model_name}"
        if cache_key in self.clients:
            return self.clients[cache_key]
        
        # Create client based on provider
        if provider == "openai":
            client = OpenAIClient(
                model_name=model_name or "gpt-4",
                api_key=kwargs.get("api_key", settings.OPENAI_API_KEY)
            )
        elif provider == "anthropic":
            client = AnthropicClient(
                model_name=model_name or "claude-3-opus-20240229",
                api_key=kwargs.get("api_key", settings.ANTHROPIC_API_KEY)
            )
        elif provider == "local":
            client = LocalLLMClient(
                model_name=model_name or "llama2",
                base_url=kwargs.get("base_url", "http://localhost:11434")
            )
        elif provider == "azure":
            # Implement Azure OpenAI client
            client = self._create_azure_client(model_name, kwargs)
        elif provider == "vertex":
            # Implement Google Vertex AI client
            client = self._create_vertex_client(model_name, kwargs)
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")
        
        # Cache client
        self.clients[cache_key] = client
        
        logger.info(f"Created LLM client for provider: {provider}, model: {client.model_name}")
        return client
    
    def _create_azure_client(self, model_name: Optional[str], kwargs: Dict) -> BaseLLMClient:
        """Create Azure OpenAI client"""
        # Implementation for Azure OpenAI
        from openai import AsyncAzureOpenAI
        
        class AzureOpenAIClient(BaseLLMClient):
            def __init__(self, model_name: str, endpoint: str, api_key: str, api_version: str):
                super().__init__(model_name, api_key)
                self.client = AsyncAzureOpenAI(
                    azure_endpoint=endpoint,
                    api_key=api_key,
                    api_version=api_version
                )
            
            async def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 1000, **kwargs) -> str:
                response = await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                return response.choices[0].message.content
        
        return AzureOpenAIClient(
            model_name=model_name or "gpt-4",
            endpoint=kwargs.get("endpoint", settings.AZURE_OPENAI_ENDPOINT),
            api_key=kwargs.get("api_key", settings.AZURE_OPENAI_KEY),
            api_version=kwargs.get("api_version", "2024-02-15-preview")
        )
    
    def _create_vertex_client(self, model_name: Optional[str], kwargs: Dict) -> BaseLLMClient:
        """Create Google Vertex AI client"""
        # Implementation for Vertex AI
        # This would use the google-cloud-aiplatform library
        pass