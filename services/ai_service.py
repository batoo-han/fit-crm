"""AI service for working with Yandex GPT and OpenAI."""
import aiohttp
import json
from typing import Dict, Any, Optional
from loguru import logger
from config import (
    YANDEX_API_KEY,
    YANDEX_FOLDER_ID,
    YANDEX_GPT_MODEL,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    PROXYAPI_BASE_URL,
    PROXYAPI_API_KEY,
)


class AIService:
    """Service for AI interactions with fallback options."""
    
    def __init__(self):
        self.preferred_provider = self._detect_provider()
    
    def _detect_provider(self) -> str:
        """Detect which AI provider is configured."""
        if YANDEX_API_KEY and YANDEX_FOLDER_ID:
            return "yandex"
        elif PROXYAPI_API_KEY:
            return "proxyapi"
        elif OPENAI_API_KEY:
            return "openai"
        return "none"
    
    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> str:
        """Generate AI response with automatic fallback."""
        
        if self.preferred_provider == "yandex":
            return await self._yandex_completion(prompt, system_prompt, max_tokens, temperature)
        elif self.preferred_provider == "proxyapi":
            return await self._openai_via_proxy(prompt, system_prompt, max_tokens, temperature)
        elif self.preferred_provider == "openai":
            return await self._openai_completion(prompt, system_prompt, max_tokens, temperature)
        else:
            return "AI сервис не настроен. Пожалуйста, обратитесь к тренеру."
    
    async def _yandex_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> str:
        """Generate completion using Yandex GPT."""
        try:
            url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
            
            headers = {
                "Authorization": f"Api-Key {YANDEX_API_KEY}",
                "Content-Type": "application/json"
            }
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "text": system_prompt})
            messages.append({"role": "user", "text": prompt})
            
            payload = {
                "modelUri": f"gpt://{YANDEX_FOLDER_ID}/{YANDEX_GPT_MODEL}",
                "completionOptions": {
                    "stream": False,
                    "temperature": temperature,
                    "maxTokens": str(max_tokens),
                },
                "messages": messages
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=30) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"Yandex GPT error: {resp.status} - {error_text}")
                        raise Exception(f"Yandex GPT error: {resp.status}")
                    
                    data = await resp.json()
                    result = data.get("result", {}).get("alternatives", [{}])[0].get("message", {}).get("text", "")
                    return result
                    
        except Exception as e:
            logger.error(f"Yandex GPT error: {e}")
            # Fallback to other providers
            if PROXYAPI_API_KEY:
                return await self._openai_via_proxy(prompt, system_prompt, max_tokens, temperature)
            elif OPENAI_API_KEY:
                return await self._openai_completion(prompt, system_prompt, max_tokens, temperature)
            raise
    
    async def _openai_via_proxy(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> str:
        """Generate completion using OpenAI via ProxyAPI."""
        try:
            url = f"{PROXYAPI_BASE_URL}/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {PROXYAPI_API_KEY}",
                "Content-Type": "application/json"
            }
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            payload = {
                "model": OPENAI_MODEL,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=30) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"ProxyAPI error: {resp.status} - {error_text}")
                        raise Exception(f"ProxyAPI error: {resp.status}")
                    
                    data = await resp.json()
                    result = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    return result
                    
        except Exception as e:
            logger.error(f"ProxyAPI error: {e}")
            # Fallback to direct OpenAI
            if OPENAI_API_KEY and not PROXYAPI_API_KEY:
                return await self._openai_completion(prompt, system_prompt, max_tokens, temperature)
            raise
    
    async def _openai_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> str:
        """Generate completion using OpenAI directly."""
        try:
            url = "https://api.openai.com/v1/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            payload = {
                "model": OPENAI_MODEL,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=30) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"OpenAI error: {resp.status} - {error_text}")
                        raise Exception(f"OpenAI error: {resp.status}")
                    
                    data = await resp.json()
                    result = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    return result
                    
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            raise


# Global instance
ai_service = AIService()
