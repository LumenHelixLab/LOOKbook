"""lookBOOK — Vision LLM Integration Module
Supports OpenAI, Claude, and Gemini for multimodal panel analysis.
"""

import base64
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Optional, Any

from ..config import get_config, get_api_key

# Optional dependencies — module-level with graceful fallback
try:
    from openai import OpenAI as _OpenAIClient
except Exception:
    _OpenAIClient = None

try:
    import anthropic as _anthropic
except Exception:
    _anthropic = None

try:
    from google import genai as _genai
    from google.genai import types as _genai_types
except Exception:
    _genai = None
    _genai_types = None

try:
    from PIL import Image as _PILImage
except Exception:
    _PILImage = None


class VisionAnalyzer(ABC):
    """Abstract base for vision LLM providers."""

    def __init__(self, model: Optional[str] = None, max_tokens: int = 2048):
        self.model = model
        self.max_tokens = max_tokens
        self.cost_usd = 0.0
        self.calls = 0

    @abstractmethod
    def _call_vision(self, image_path: str, prompt: str) -> str:
        pass

    def _encode_image(self, image_path: str) -> str:
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')

    def describe_panel(self, image_path: str) -> Dict:
        prompt = (
            "Describe this comic/manga panel in detail. Include: setting, action, "
            "character poses, camera angle, lighting mood, and any text or sound effects."
        )
        raw = self._call_vision(image_path, prompt)
        self.calls += 1
        return {"description": raw, "source": self.__class__.__name__, "cost_usd": round(self.cost_usd, 4)}

    def extract_characters(self, image_path: str) -> Dict:
        prompt = (
            "List all visible characters in this panel. For each: name (if known), "
            "appearance, clothing, expression, pose, and relative position in the frame."
        )
        raw = self._call_vision(image_path, prompt)
        self.calls += 1
        return {"characters": raw, "source": self.__class__.__name__, "cost_usd": round(self.cost_usd, 4)}

    def build_scene_graph(self, image_path: str) -> Dict:
        prompt = (
            "Analyze the scene composition. Identify: foreground subjects, midground elements, "
            "background details, depth layers, and spatial relationships between objects."
        )
        raw = self._call_vision(image_path, prompt)
        self.calls += 1
        return {"scene_graph": raw, "source": self.__class__.__name__, "cost_usd": round(self.cost_usd, 4)}

    def generate_shot_list(self, image_path: str) -> Dict:
        prompt = (
            "Convert this static panel into an animation shot list. Suggest: shot type, "
            "camera movement, duration, key poses, and transitions."
        )
        raw = self._call_vision(image_path, prompt)
        self.calls += 1
        return {"shot_list": raw, "source": self.__class__.__name__, "cost_usd": round(self.cost_usd, 4)}


class OpenAIVisionAnalyzer(VisionAnalyzer):
    def __init__(self, model: Optional[str] = None, max_tokens: int = 2048):
        super().__init__(model or 'gpt-4o', max_tokens)
        if _OpenAIClient is None:
            raise RuntimeError("OpenAI client unavailable. Install: pip install openai")
        self.client = _OpenAIClient(api_key=get_api_key('openai'))

    def _call_vision(self, image_path: str, prompt: str) -> str:
        b64 = self._encode_image(image_path)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                    ]
                }
            ],
            max_tokens=self.max_tokens
        )
        usage = response.usage
        # Approximate pricing for gpt-4o: $0.005/1K input tokens, $0.015/1K output tokens
        if usage:
            self.cost_usd += (usage.prompt_tokens * 0.005 + usage.completion_tokens * 0.015) / 1000
        return response.choices[0].message.content


class ClaudeVisionAnalyzer(VisionAnalyzer):
    def __init__(self, model: Optional[str] = None, max_tokens: int = 2048):
        super().__init__(model or 'claude-3-opus-20240229', max_tokens)
        if _anthropic is None:
            raise RuntimeError("Anthropic client unavailable. Install: pip install anthropic")
        self.client = _anthropic.Anthropic(api_key=get_api_key('claude'))

    def _call_vision(self, image_path: str, prompt: str) -> str:
        b64 = self._encode_image(image_path)
        media_type = "image/jpeg"
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                        {"type": "text", "text": prompt}
                    ]
                }
            ]
        )
        usage = response.usage
        # Approximate pricing for Claude 3 Opus: $15/1M input, $75/1M output
        if usage:
            self.cost_usd += (usage.input_tokens * 15 + usage.output_tokens * 75) / 1_000_000
        content = response.content
        return content[0].text if content else ""


class GeminiVisionAnalyzer(VisionAnalyzer):
    def __init__(self, model: Optional[str] = None, max_tokens: int = 2048):
        super().__init__(model or 'gemini-1.5-pro-latest', max_tokens)
        if _genai is None:
            raise RuntimeError("Gemini client unavailable. Install: pip install google-genai")
        self.client = _genai.Client(api_key=get_api_key('gemini'))

    def _call_vision(self, image_path: str, prompt: str) -> str:
        if _PILImage is None:
            raise RuntimeError("PIL unavailable. Install: pip install Pillow")
        if _genai_types is None:
            raise RuntimeError("Gemini client unavailable. Install: pip install google-genai")
        import io

        img = _PILImage.open(image_path)
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        image_bytes = buf.getvalue()
        image_part = _genai_types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
        assert self.model is not None
        contents: List[Any] = [prompt, image_part]
        response = self.client.models.generate_content(
            model=self.model,
            contents=contents
        )
        # Gemini pricing varies; use rough estimate
        self.cost_usd += 0.002  # placeholder per call
        return response.text or ""


def get_analyzer(provider: Optional[str] = None) -> VisionAnalyzer:
    cfg = get_config()
    p = (provider or cfg['vision']['provider']).lower()
    model = cfg['vision'].get('model')
    max_tokens = cfg['vision'].get('max_tokens', 2048)

    if p == 'openai':
        return OpenAIVisionAnalyzer(model=model, max_tokens=max_tokens)
    elif p == 'claude':
        return ClaudeVisionAnalyzer(model=model, max_tokens=max_tokens)
    elif p == 'gemini':
        return GeminiVisionAnalyzer(model=model, max_tokens=max_tokens)
    else:
        raise ValueError(f"Unknown vision provider: {p}")
