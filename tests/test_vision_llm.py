"""Tests for lookBOOK vision LLM module."""

import pytest
from unittest.mock import patch, MagicMock

from lookbook.pipeline.vision_llm import (
    OpenAIVisionAnalyzer,
    ClaudeVisionAnalyzer,
    GeminiVisionAnalyzer,
    get_analyzer
)


class TestOpenAIVisionAnalyzer:
    @patch('lookbook.pipeline.vision_llm._OpenAIClient')
    @patch.object(OpenAIVisionAnalyzer, '_encode_image', return_value='fakeb64')
    def test_describe_panel(self, mock_b64, mock_openai_class):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="A dark alley scene."))]
        mock_response.usage = MagicMock(prompt_tokens=1000, completion_tokens=200)
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        analyzer = OpenAIVisionAnalyzer()
        result = analyzer.describe_panel("dummy.jpg")
        assert "description" in result
        assert result["description"] == "A dark alley scene."
        assert result["source"] == "OpenAIVisionAnalyzer"
        assert result["cost_usd"] > 0

    @patch('lookbook.pipeline.vision_llm._OpenAIClient')
    @patch.object(OpenAIVisionAnalyzer, '_encode_image', return_value='fakeb64')
    def test_extract_characters(self, mock_b64, mock_openai_class):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Character A: hero."))]
        mock_response.usage = MagicMock(prompt_tokens=500, completion_tokens=100)
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        analyzer = OpenAIVisionAnalyzer()
        result = analyzer.extract_characters("dummy.jpg")
        assert "characters" in result


class TestClaudeVisionAnalyzer:
    @patch('lookbook.pipeline.vision_llm._anthropic.Anthropic')
    @patch.object(ClaudeVisionAnalyzer, '_encode_image', return_value='fakeb64')
    def test_describe_panel(self, mock_b64, mock_anthropic_class):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="A rainy rooftop chase.")]
        mock_response.usage = MagicMock(input_tokens=2000, output_tokens=400)
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client

        analyzer = ClaudeVisionAnalyzer()
        result = analyzer.describe_panel("dummy.jpg")
        assert "description" in result
        assert result["description"] == "A rainy rooftop chase."


class TestGeminiVisionAnalyzer:
    @patch('lookbook.pipeline.vision_llm._PILImage')
    @patch('lookbook.pipeline.vision_llm._genai_types')
    @patch('lookbook.pipeline.vision_llm._genai')
    def test_describe_panel(self, mock_genai, mock_types, mock_image):
        mock_client = MagicMock()
        mock_response = MagicMock(text="A futuristic cityscape.")
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        analyzer = GeminiVisionAnalyzer()
        result = analyzer.describe_panel("dummy.jpg")
        assert "description" in result
        assert result["description"] == "A futuristic cityscape."


class TestFallback:
    def test_get_analyzer_unknown_provider(self):
        with pytest.raises(ValueError):
            get_analyzer("unknown_provider")

    @patch.dict('os.environ', {'OPENAI_API_KEY': 'sk-test'})
    @patch('lookbook.pipeline.vision_llm._OpenAIClient')
    def test_get_analyzer_openai(self, mock_openai):
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        analyzer = get_analyzer("openai")
        assert isinstance(analyzer, OpenAIVisionAnalyzer)
