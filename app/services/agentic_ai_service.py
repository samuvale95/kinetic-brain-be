"""
Enhanced AI Service for Agentic Coach.
Integrates with OpenAI (GPT-4) and Anthropic (Claude) for structured workout generation.
"""
from typing import Optional, Dict, Any, Type
from pydantic import BaseModel
import json
import openai
from anthropic import Anthropic
from loguru import logger

from app.config import settings
from app.schemas.agentic_coach import AthleteStateAssessment, AgenticWeeklyPlan


class LLMConfig(BaseModel):
    """Configuration for LLM calls."""
    provider: str = "openai"  # "openai" or "anthropic"
    model: str = "gpt-4-turbo-preview"
    temperature: float = 0.7
    max_tokens: int = 4000
    timeout: int = 60


class AgenticAIService:
    """
    AI service specifically designed for Agentic Coach.
    Handles structured JSON generation with retry logic.
    """
    
    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        
        # Initialize clients
        if self.config.provider == "openai":
            openai.api_key = settings.OPENAI_API_KEY
            self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        elif self.config.provider == "anthropic":
            self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        else:
            raise ValueError(f"Unsupported provider: {self.config.provider}")
        
        logger.info(f"AgenticAIService initialized with {self.config.provider}/{self.config.model}")
    
    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[BaseModel],
        max_retries: int = 3
    ) -> BaseModel:
        """
        Generate structured output matching a Pydantic model.
        
        Args:
            system_prompt: System instructions
            user_prompt: User query/context
            response_model: Pydantic model class for response validation
            max_retries: Number of retry attempts if parsing fails
        
        Returns:
            Validated instance of response_model
        
        Raises:
            ValueError: If max retries exceeded or response invalid
        """
        logger.info(f"Generating structured response for {response_model.__name__}")
        
        # Add JSON schema instruction to prompts
        schema = response_model.model_json_schema()
        enhanced_system = f"""{system_prompt}

CRITICAL: You MUST respond with valid JSON matching this exact schema:
{json.dumps(schema, indent=2)}

Do not include any text before or after the JSON object.
"""
        
        for attempt in range(max_retries):
            try:
                # Generate response
                raw_response = self._call_llm(enhanced_system, user_prompt)
                
                # Parse and validate
                parsed = self._extract_json(raw_response)
                validated = response_model.model_validate(parsed)
                
                logger.info(f"Successfully generated {response_model.__name__} on attempt {attempt + 1}")
                return validated
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}")
                
                if attempt == max_retries - 1:
                    logger.error(f"Max retries exceeded. Raw response: {raw_response[:500]}")
                    raise ValueError(f"Failed to generate valid {response_model.__name__} after {max_retries} attempts: {str(e)}")
                
                # If JSON parsing failed, add error feedback to next attempt
                if attempt < max_retries - 1:
                    user_prompt += f"\n\n[SYSTEM ERROR] Previous response was invalid: {str(e)}. Please try again with valid JSON."
        
        raise ValueError("Unreachable code")
    
    def _call_llm(self, system: str, user: str) -> str:
        """Call the configured LLM provider."""
        
        if self.config.provider == "openai":
            return self._call_openai(system, user)
        elif self.config.provider == "anthropic":
            return self._call_anthropic(system, user)
        else:
            raise ValueError(f"Unsupported provider: {self.config.provider}")
    
    def _call_openai(self, system: str, user: str) -> str:
        """Call OpenAI API."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                timeout=self.config.timeout,
                response_format={"type": "json_object"}  # Force JSON mode
            )
            
            return response.choices[0].message.content
            
        except openai.OpenAIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise
    
    def _call_anthropic(self, system: str, user: str) -> str:
        """Call Anthropic Claude API."""
        
        try:
            response = self.client.messages.create(
                model=self.config.model or "claude-3-5-sonnet-20241022",
                system=system,
                messages=[
                    {"role": "user", "content": user}
                ],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                timeout=self.config.timeout
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Anthropic API error: {str(e)}")
            raise
    
    def _extract_json(self, response: str) -> Dict[str, Any]:
        """
        Extract JSON from LLM response.
        Handles responses with markdown code blocks or extra text.
        """
        # Remove markdown code blocks if present
        response = response.strip()
        
        if response.startswith("```json"):
            response = response[7:]  # Remove ```json
        elif response.startswith("```"):
            response = response[3:]  # Remove ```
        
        if response.endswith("```"):
            response = response[:-3]
        
        response = response.strip()
        
        # Try to find JSON object boundaries
        start_idx = response.find('{')
        end_idx = response.rfind('}')
        
        if start_idx == -1 or end_idx == -1:
            raise ValueError("No JSON object found in response")
        
        json_str = response[start_idx:end_idx + 1]
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {str(e)}\nContent: {json_str[:500]}")
            raise ValueError(f"Invalid JSON: {str(e)}")
    
    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation (1 token ≈ 4 characters)."""
        return len(text) // 4
    
    def get_cost_estimate(self, input_tokens: int, output_tokens: int) -> float:
        """
        Estimate cost based on token usage.
        Prices as of Jan 2024 (update as needed).
        """
        if self.config.provider == "openai":
            if "gpt-4-turbo" in self.config.model:
                # GPT-4 Turbo: $0.01/1k input, $0.03/1k output
                cost = (input_tokens / 1000 * 0.01) + (output_tokens / 1000 * 0.03)
            elif "gpt-4" in self.config.model:
                # GPT-4: $0.03/1k input, $0.06/1k output
                cost = (input_tokens / 1000 * 0.03) + (output_tokens / 1000 * 0.06)
            else:
                # GPT-3.5: $0.0015/1k input, $0.002/1k output
                cost = (input_tokens / 1000 * 0.0015) + (output_tokens / 1000 * 0.002)
        elif self.config.provider == "anthropic":
            # Claude 3.5 Sonnet: $0.003/1k input, $0.015/1k output
            cost = (input_tokens / 1000 * 0.003) + (output_tokens / 1000 * 0.015)
        else:
            cost = 0.0
        
        return round(cost, 4)


# Convenience function
def create_agentic_ai_service(
    provider: str = "openai",
    model: Optional[str] = None,
    temperature: float = 0.7
) -> AgenticAIService:
    """
    Factory function to create AI service with common configurations.
    
    Args:
        provider: "openai" or "anthropic"
        model: Model name (defaults to best for provider)
        temperature: 0.0-1.0 (lower = more deterministic)
    """
    if not model:
        model = "gpt-4-turbo-preview" if provider == "openai" else "claude-3-5-sonnet-20241022"
    
    config = LLMConfig(
        provider=provider,
        model=model,
        temperature=temperature
    )
    
    return AgenticAIService(config)
