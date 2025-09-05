#!/usr/bin/env python3
"""
Custom Ollama-compatible LLM client for Graphiti that properly handles JSON schemas
"""

import json
import logging
import typing
from typing import ClassVar

import openai
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

from graphiti_core.prompts.models import Message
from graphiti_core.llm_client.client import MULTILINGUAL_EXTRACTION_RESPONSES, LLMClient
from graphiti_core.llm_client.config import DEFAULT_MAX_TOKENS, LLMConfig, ModelSize
from graphiti_core.llm_client.errors import RateLimitError, RefusalError

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "llama3.1:8b"


class OllamaGraphitiClient(LLMClient):
    """
    Ollama-optimized client for Graphiti that handles JSON schemas correctly.

    This client fixes the issue where models return the JSON schema itself
    instead of data matching the schema.
    """

    MAX_RETRIES: ClassVar[int] = 2

    def __init__(
        self,
        config: LLMConfig | None = None,
        cache: bool = False,
        client: typing.Any = None,
    ):
        if cache:
            raise NotImplementedError("Caching is not implemented for this client")

        if config is None:
            config = LLMConfig()

        super().__init__(config, cache)

        if client is None:
            self.client = AsyncOpenAI(api_key=config.api_key, base_url=config.base_url)
        else:
            self.client = client

    async def _generate_response(
        self,
        messages: list[Message],
        response_model: type[BaseModel] | None = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        model_size: ModelSize = ModelSize.medium,
    ) -> dict[str, typing.Any]:
        openai_messages: list[ChatCompletionMessageParam] = []
        for m in messages:
            m.content = self._clean_input(m.content)
            if m.role == "user":
                openai_messages.append({"role": "user", "content": m.content})
            elif m.role == "system":
                openai_messages.append({"role": "system", "content": m.content})
        try:
            response = await self.client.chat.completions.create(
                model=self.model or DEFAULT_MODEL,
                messages=openai_messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"},
            )
            result = response.choices[0].message.content or ""
            return json.loads(result)
        except openai.RateLimitError as e:
            raise RateLimitError from e
        except Exception as e:
            logger.error(f"Error in generating LLM response: {e}")
            raise

    async def generate_response(
        self,
        messages: list[Message],
        response_model: type[BaseModel] | None = None,
        max_tokens: int | None = None,
        model_size: ModelSize = ModelSize.medium,
    ) -> dict[str, typing.Any]:
        if max_tokens is None:
            max_tokens = self.max_tokens

        retry_count = 0
        last_error = None

        if response_model is not None:
            # Get a simpler example-based prompt instead of the full schema
            schema = response_model.model_json_schema()

            # Create a clearer instruction for the model
            schema_instruction = self._create_schema_instruction(
                schema, response_model.__name__
            )

            messages[-1].content += schema_instruction

        # Add multilingual extraction instructions
        messages[0].content += MULTILINGUAL_EXTRACTION_RESPONSES

        while retry_count <= self.MAX_RETRIES:
            try:
                response = await self._generate_response(
                    messages,
                    response_model,
                    max_tokens=max_tokens,
                    model_size=model_size,
                )
                return response
            except (RateLimitError, RefusalError):
                raise
            except (
                openai.APITimeoutError,
                openai.APIConnectionError,
                openai.InternalServerError,
            ):
                raise
            except Exception as e:
                last_error = e

                if retry_count >= self.MAX_RETRIES:
                    logger.error(
                        f"Max retries ({self.MAX_RETRIES}) exceeded. Last error: {e}"
                    )
                    raise

                retry_count += 1

                error_context = (
                    f"The previous response was invalid. "
                    f"Error: {str(e)}. "
                    f"Please provide a valid JSON response with the correct structure."
                )

                error_message = Message(role="user", content=error_context)
                messages.append(error_message)
                logger.warning(
                    f"Retrying after error (attempt {retry_count}/{self.MAX_RETRIES}): {e}"
                )

        raise last_error or Exception("Max retries exceeded with no specific error")

    def _create_schema_instruction(self, schema: dict, model_name: str) -> str:
        """
        Create a clear instruction for the model to generate data matching the schema,
        not return the schema itself.
        """
        # Extract the properties and structure
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        # Build a clearer instruction
        instruction = f"\n\nIMPORTANT: Return a JSON object with actual data (NOT the schema definition).\n"

        if model_name == "ExtractedEdges":
            instruction += """
Your response must be a JSON object with an "edges" array containing edge objects.
Each edge object should have these fields:
- relation_type: A SCREAMING_SNAKE_CASE relationship type
- source_entity_id: The ID of the source entity (integer)
- target_entity_id: The ID of the target entity (integer)
- fact: The factual statement
- valid_at: ISO 8601 timestamp or null
- invalid_at: ISO 8601 timestamp or null

Example response format:
{
  "edges": [
    {
      "relation_type": "LIKES",
      "source_entity_id": 0,
      "target_entity_id": 1,
      "fact": "Alice likes the search feature",
      "valid_at": null,
      "invalid_at": null
    }
  ]
}
"""
        elif model_name == "ExtractedNodes":
            instruction += """
Your response must be a JSON object with a "nodes" array containing entity objects.
Each entity should have these fields:
- id: A unique integer ID for the entity
- name: The entity name
- summary: A brief description of the entity

Example response format:
{
  "nodes": [
    {"id": 0, "name": "Alice", "summary": "A person who likes the search feature"},
    {"id": 1, "name": "Search Feature", "summary": "A feature that Alice likes"}
  ]
}
"""
        elif model_name == "ExtractedEntities":
            instruction += """
Your response must be a JSON object with an "extracted_entities" array.
Each entity in the array should have these fields:
- name: The entity name (NOT entity_name)
- entity_type_id: An integer representing the entity type
- description: A brief description of the entity
- labels: An array of label strings
- custom_properties: An object with any custom properties

Example response format:
{
  "extracted_entities": [
    {
      "name": "Alice",
      "entity_type_id": 0,
      "description": "A person who likes the search feature",
      "labels": ["person"],
      "custom_properties": {}
    },
    {
      "name": "Search Feature",
      "entity_type_id": 0,
      "description": "A feature that users interact with",
      "labels": ["feature"],
      "custom_properties": {}
    }
  ]
}

IMPORTANT: Use "name" not "entity_name" for the entity name field.
"""
        else:
            # Generic instruction with the schema
            instruction += f"""
The response should match this structure:
Required fields: {', '.join(required)}

DO NOT return the schema definition. Return actual data values.
"""

        return instruction
