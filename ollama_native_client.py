"""
Native Ollama client for Graphiti that uses structured outputs.
This bypasses OpenAI compatibility layer for direct schema enforcement.
"""

import json
import logging
from typing import Any, Optional, Dict
from ollama import AsyncClient
from pydantic import BaseModel

from graphiti_core.llm_client.client import LLMClient
from graphiti_core.llm_client.config import LLMConfig, DEFAULT_MAX_TOKENS, ModelSize
from graphiti_core.prompts.models import Message

logger = logging.getLogger(__name__)


class OllamaNativeClient(LLMClient):
    """
    Direct Ollama client that uses native format parameter for structured outputs.
    This ensures 100% schema compliance for Pydantic models.
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize Ollama native client with configuration."""
        if config is None:
            config = LLMConfig(
                model="llama3.2:3b",
                base_url="http://localhost:11434",
                temperature=0.1,  # Lower for consistent structure
                max_tokens=2048,
            )

        super().__init__(config, cache=False)

        # Parse host from base_url if provided
        host = config.base_url if config.base_url else "http://localhost:11434"
        # Remove /v1 suffix if present (from OpenAI compatibility)
        if host.endswith("/v1"):
            host = host[:-3]

        # Use Ollama's native AsyncClient
        self.client = AsyncClient(host=host)
        self.model = config.model if config.model else "llama3.2:3b"
        self.temperature = config.temperature if config.temperature else 0.1
        self.max_tokens = config.max_tokens if config.max_tokens else DEFAULT_MAX_TOKENS

    async def _generate_response(
        self,
        messages: list[Message],
        response_model: Optional[type[BaseModel]] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        model_size: ModelSize = ModelSize.medium,
    ) -> Dict[str, Any]:
        """
        Generate response using Ollama's native chat API with structured output.

        Critical: Uses format parameter for guaranteed schema compliance.
        """
        # Convert Graphiti messages to Ollama format
        ollama_messages = []
        for msg in messages:
            # Clean the content
            content = self._clean_input(msg.content)
            ollama_messages.append({"role": msg.role, "content": content})

        # Prepare chat parameters
        chat_params = {
            "model": self.model,
            "messages": ollama_messages,
            "options": {
                "temperature": self.temperature,
                "num_predict": max_tokens,
            },
        }

        # THE CRITICAL PART: Use native format parameter for structured output
        if response_model:
            # Get JSON schema from Pydantic model
            schema = response_model.model_json_schema()
            chat_params["format"] = schema

            logger.debug(
                f"Using structured output with schema: {json.dumps(schema, indent=2)}"
            )

            # Add a system message to reinforce JSON output (belt-and-suspenders)
            system_instruction = {
                "role": "system",
                "content": f"You MUST respond with valid JSON that exactly matches this schema. Do not include any text before or after the JSON: {json.dumps(schema)}",
            }
            ollama_messages.insert(0, system_instruction)
            chat_params["messages"] = ollama_messages

        try:
            # Make the actual call to Ollama
            logger.debug(f"Calling Ollama with model: {self.model}")
            response = await self.client.chat(**chat_params)

            # Extract content from response
            content = response["message"]["content"]
            logger.debug(f"Raw response from Ollama: {content[:200]}...")

            # Parse JSON response
            try:
                result = json.loads(content)

                # If we have a response model, validate against it
                if response_model:
                    # Validate using Pydantic model
                    validated = response_model.model_validate(result)
                    validated_dict = validated.model_dump()
                    logger.debug(
                        f"Successfully validated response with {response_model.__name__}"
                    )
                    return validated_dict

                return result

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from Ollama: {e}")
                logger.error(f"Raw content: {content}")
                # Try to extract JSON from the content if it's wrapped in text
                import re

                json_match = re.search(r"\{.*\}", content, re.DOTALL)
                if json_match:
                    try:
                        result = json.loads(json_match.group())
                        if response_model:
                            validated = response_model.model_validate(result)
                            return validated.model_dump()
                        return result
                    except:
                        pass
                raise e

        except Exception as e:
            logger.error(f"Ollama API call failed: {e}")
            raise

    async def generate_response(
        self,
        messages: list[Message],
        response_model: Optional[type[BaseModel]] = None,
        max_tokens: Optional[int] = None,
        model_size: ModelSize = ModelSize.medium,
    ) -> Dict[str, Any]:
        """
        Public interface for generating responses with automatic retries.
        """
        if max_tokens is None:
            max_tokens = self.max_tokens

        # For Ollama, we rely on the format parameter for structure
        # No need to append schema to the prompt like OpenAIGenericClient does

        # Add multilingual support if needed
        from graphiti_core.llm_client.client import MULTILINGUAL_EXTRACTION_RESPONSES

        if messages and len(messages) > 0:
            messages[0].content += MULTILINGUAL_EXTRACTION_RESPONSES

        max_retries = 2
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                return await self._generate_response(
                    messages=messages,
                    response_model=response_model,
                    max_tokens=max_tokens,
                    model_size=model_size,
                )
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying...")
                    # Add error context to messages for retry
                    error_msg = Message(
                        role="user",
                        content=f"The previous attempt failed. Please try again with valid JSON output. Error: {str(e)}",
                    )
                    messages.append(error_msg)
                else:
                    logger.error(
                        f"All {max_retries + 1} attempts failed. Last error: {e}"
                    )
                    raise

        raise last_error or Exception("Failed to generate response")

    async def generate_structured_response(
        self,
        messages: list[Message],
        response_model: type[BaseModel],
        max_tokens: Optional[int] = None,
    ) -> BaseModel:
        """
        Convenience method that returns a validated Pydantic model directly.
        """
        if max_tokens is None:
            max_tokens = self.max_tokens

        result = await self.generate_response(
            messages=messages, response_model=response_model, max_tokens=max_tokens
        )

        # Return as validated Pydantic model
        return response_model.model_validate(result)
