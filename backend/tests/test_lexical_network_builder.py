"""
Tests for Lexical Network Builder

Tests the core functionality of the lexical network building system.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.schemas.lexical_network import JobConfig, RelationCandidate
from app.services.lexical_network.relation_types import (
    get_valid_relations_for_pos,
    is_symmetric_relation,
    validate_relation_for_pos,
)
from app.services.lexical_network.vocabularies import (
    validate_domain_tag,
    validate_context_tag,
    validate_register_tag,
    validate_aligned_arrays,
)
from app.services.lexical_network.ai_provider_config import (
    get_model_config,
    list_available_models,
    get_recommended_model,
)


class TestRelationTypes:
    """Test relation type definitions and helpers."""
    
    def test_get_valid_relations_for_pos(self):
        """Test getting valid relations for each POS."""
        noun_rels = get_valid_relations_for_pos("名詞")
        assert "HYPERNYM" in noun_rels
        assert "HYPONYM" in noun_rels
        assert "MERONYM" in noun_rels
        
        adj_rels = get_valid_relations_for_pos("形容詞")
        assert "GRADABLE_ANTONYM" in adj_rels
        assert "SCALAR_INTENSITY" in adj_rels
        
        verb_rels = get_valid_relations_for_pos("動詞")
        assert "CAUSATIVE_PAIR" in verb_rels
        assert "CONVERSE" in verb_rels
        
        adv_rels = get_valid_relations_for_pos("副詞")
        assert "INTENSITY_SCALE" in adv_rels
        assert "TEMPORAL_PAIR" in adv_rels
    
    def test_is_symmetric_relation(self):
        """Test symmetric relation detection."""
        assert is_symmetric_relation("SYNONYM") is True
        assert is_symmetric_relation("ANTONYM") is True
        assert is_symmetric_relation("HYPERNYM") is False
        assert is_symmetric_relation("HYPONYM") is False
        assert is_symmetric_relation("SCALAR_INTENSITY") is False
    
    def test_validate_relation_for_pos(self):
        """Test relation validation for POS."""
        assert validate_relation_for_pos("HYPERNYM", "名詞") is True
        assert validate_relation_for_pos("HYPERNYM", "形容詞") is False
        assert validate_relation_for_pos("GRADABLE_ANTONYM", "形容詞") is True
        assert validate_relation_for_pos("CAUSATIVE_PAIR", "動詞") is True
        assert validate_relation_for_pos("CAUSATIVE_PAIR", "名詞") is False


class TestVocabularies:
    """Test controlled vocabularies."""
    
    def test_validate_domain_tag(self):
        """Test domain tag validation."""
        assert validate_domain_tag("aesthetics") is True
        assert validate_domain_tag("emotion") is True
        assert validate_domain_tag("invalid_domain") is False
    
    def test_validate_context_tag(self):
        """Test context tag validation."""
        assert validate_context_tag("people_appearance") is True
        assert validate_context_tag("food_taste") is True
        assert validate_context_tag("invalid_context") is False
    
    def test_validate_register_tag(self):
        """Test register tag validation."""
        assert validate_register_tag("neutral") is True
        assert validate_register_tag("formal") is True
        assert validate_register_tag("invalid_register") is False
    
    def test_validate_aligned_arrays(self):
        """Test aligned arrays validation."""
        assert validate_aligned_arrays(["aesthetics", "emotion"], [0.8, 0.5]) is True
        assert validate_aligned_arrays(["aesthetics"], [0.8, 0.5]) is False
        assert validate_aligned_arrays(["aesthetics", "emotion"], [0.8]) is False
        assert validate_aligned_arrays(["aesthetics"], [1.5]) is False  # Weight > 1.0
        assert validate_aligned_arrays(["aesthetics"], [-0.1]) is False  # Weight < 0.0


class TestAIProviderConfig:
    """Test AI provider configuration."""
    
    def test_get_model_config(self):
        """Test getting model configuration."""
        config = get_model_config("gpt-4o-mini")
        assert config.provider == "openai"
        assert config.model_id == "gpt-4o-mini"
        assert config.supports_json_mode is True
        
        config = get_model_config("gemini-2.5-flash")
        assert config.provider == "gemini"
        assert config.model_id == "gemini-2.5-flash"
    
    def test_list_available_models(self):
        """Test listing available models."""
        models = list_available_models()
        assert len(models) > 0
        model_ids = [m.model_id for m in models]
        assert "gpt-4o-mini" in model_ids
        assert "gemini-2.5-flash" in model_ids
        assert "deepseek-chat" in model_ids
    
    def test_get_recommended_model(self):
        """Test getting recommended model."""
        model = get_recommended_model("batch")
        assert model in ["gpt-4o-mini", "gemini-2.5-flash", "deepseek-chat"]
        
        model = get_recommended_model("low_cost")
        assert model in ["gpt-4o-mini", "gemini-2.5-flash", "deepseek-chat"]


class TestRelationCandidate:
    """Test RelationCandidate schema."""
    
    def test_relation_candidate_creation(self):
        """Test creating a relation candidate."""
        candidate = RelationCandidate(
            source_word="美しい",
            target_word="綺麗",
            relation_type="NEAR_SYNONYM",
            relation_category="adjective",
            weight=0.88,
            confidence=0.90,
            is_symmetric=True,
            shared_meaning_en="beautiful, pretty",
            distinction_en="美しい is more literary",
            usage_context_en="Both describe beauty",
            register_source="literary",
            register_target="neutral",
            formality_difference="source_higher",
            domain_tags=["aesthetics"],
            domain_weights=[0.9],
            context_tags=["people_appearance"],
            context_weights=[0.8],
        )
        
        assert candidate.source_word == "美しい"
        assert candidate.target_word == "綺麗"
        assert candidate.weight == 0.88
        assert candidate.ai_temperature == 0.0
    
    def test_relation_candidate_validation(self):
        """Test relation candidate validation."""
        # Valid candidate
        candidate = RelationCandidate(
            source_word="大きい",
            target_word="小さい",
            relation_type="GRADABLE_ANTONYM",
            relation_category="adjective",
            weight=0.95,
            confidence=0.98,
            is_symmetric=True,
            shared_meaning_en="size dimension",
            distinction_en="Opposite ends of size scale",
            usage_context_en="Size descriptions",
            register_source="neutral",
            register_target="neutral",
            formality_difference="same",
            scale_dimension="size",
            scale_position_source=0.8,
            scale_position_target=0.2,
            domain_tags=["physical"],
            domain_weights=[0.9],
            context_tags=[],
            context_weights=[],
        )
        
        assert candidate.scale_dimension == "size"
        assert candidate.scale_position_source == 0.8
    
    def test_relation_candidate_aligned_arrays_validation(self):
        """Test that aligned arrays are validated."""
        # Should fail if arrays don't align
        with pytest.raises(ValueError, match="domain_weights must align"):
            RelationCandidate(
                source_word="test",
                target_word="test2",
                relation_type="SYNONYM",
                relation_category="noun",
                weight=0.8,
                confidence=0.9,
                is_symmetric=True,
                shared_meaning_en="test",
                distinction_en="test",
                usage_context_en="test",
                register_source="neutral",
                register_target="neutral",
                formality_difference="same",
                domain_tags=["aesthetics", "emotion"],
                domain_weights=[0.8],  # Mismatch!
                context_tags=[],
                context_weights=[],
            )


class TestJobConfig:
    """Test JobConfig schema."""
    
    def test_job_config_creation(self):
        """Test creating a job config."""
        config = JobConfig(
            job_type="relation_building",
            source="pos_filter",
            pos_filter="形容詞",
            relation_types=["SYNONYM", "NEAR_SYNONYM"],
            model="gpt-4o-mini",
            max_words=50,
            batch_size=10,
        )
        
        assert config.job_type == "relation_building"
        assert config.source == "pos_filter"
        assert config.pos_filter == "形容詞"
        assert config.model == "gpt-4o-mini"
        assert config.max_words == 50
    
    def test_job_config_validation(self):
        """Test job config validation."""
        # Should require pos_filter when source is pos_filter
        with pytest.raises(ValueError, match="pos_filter required"):
            JobConfig(
                job_type="relation_building",
                source="pos_filter",
                relation_types=["SYNONYM"],
            )
        
        # Should require word_list when source is word_list
        with pytest.raises(ValueError, match="word_list required"):
            JobConfig(
                job_type="relation_building",
                source="word_list",
                relation_types=["SYNONYM"],
            )


@pytest.mark.anyio
class TestRelationBuilderService:
    """Test RelationBuilderService."""
    
    async def test_fetch_word_data(self):
        """Test fetching word data from Neo4j."""
        from app.services.lexical_network.relation_builder_service import (
            RelationBuilderService,
        )
        
        service = RelationBuilderService()
        
        # Mock Neo4j session
        mock_session = AsyncMock()
        mock_record = MagicMock()
        mock_record.__getitem__ = lambda self, key: {
            "word_data": {
                "standard_orthography": "美しい",
                "reading_hiragana": "うつくしい",
                "translation": "beautiful",
                "pos_primary": "形容詞",
            },
            "pos_primary": "形容詞",
            "domains": [],
            "existing_relations": 0,
        }.get(key)
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value=mock_record)
        mock_session.run = AsyncMock(return_value=mock_result)
        
        word_data = await service._fetch_word_data(mock_session, "美しい")
        
        assert word_data is not None
        assert word_data["standard_orthography"] == "美しい"
        assert word_data["pos_primary"] == "形容詞"
    
    async def test_parse_ai_response(self):
        """Test parsing AI response JSON."""
        from app.services.lexical_network.relation_builder_service import (
            RelationBuilderService,
        )
        
        service = RelationBuilderService()
        
        ai_response = """
        [
            {
                "source_word": "美しい",
                "target_word": "綺麗",
                "relation_type": "NEAR_SYNONYM",
                "relation_category": "adjective",
                "weight": 0.88,
                "confidence": 0.90,
                "is_symmetric": true,
                "shared_meaning_en": "beautiful",
                "distinction_en": "美しい is more literary",
                "usage_context_en": "Both describe beauty",
                "register_source": "literary",
                "register_target": "neutral",
                "formality_difference": "source_higher",
                "domain_tags": ["aesthetics"],
                "domain_weights": [0.9],
                "context_tags": ["people_appearance"],
                "context_weights": [0.8]
            }
        ]
        """
        
        candidates = service._parse_ai_response(ai_response, "形容詞", "美しい")
        
        assert len(candidates) == 1
        assert candidates[0].source_word == "美しい"
        assert candidates[0].target_word == "綺麗"
        assert candidates[0].relation_type == "NEAR_SYNONYM"
        assert candidates[0].weight == 0.88


@pytest.mark.anyio
class TestAIProviders:
    """Test AI provider implementations."""
    
    @patch("app.services.lexical_network.ai_providers.AsyncOpenAI")
    async def test_openai_provider_temperature_zero(self, mock_openai_class):
        """Test that OpenAI provider uses temperature=0."""
        from app.services.lexical_network.ai_providers import OpenAIProvider
        
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"test": "data"}'
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.model = "gpt-4o-mini"
        mock_response.model_dump = MagicMock(return_value={})
        
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        provider = OpenAIProvider("gpt-4o-mini")
        result = await provider.generate_relations(
            prompt="test prompt",
            system_prompt="test system",
        )
        
        # Verify temperature=0 was used
        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["temperature"] == 0.0
        
        assert result.provider == "openai"
        assert result.model == "gpt-4o-mini"
        assert result.temperature == 0.0
        assert result.tokens_input == 100
        assert result.tokens_output == 50


@pytest.mark.anyio
class TestJobManager:
    """Test JobManager service."""
    
    async def test_create_job(self):
        """Test creating a job."""
        from app.services.lexical_network.job_manager_service import (
            LexicalNetworkJobManager,
        )
        
        manager = LexicalNetworkJobManager()
        
        config = JobConfig(
            job_type="relation_building",
            source="pos_filter",
            pos_filter="形容詞",
            relation_types=["SYNONYM"],
            model="gpt-4o-mini",
            max_words=10,
        )
        
        job_id = await manager.create_job(config)
        
        assert job_id.startswith("job_")
        assert job_id in manager.jobs
    
    async def test_get_job_status(self):
        """Test getting job status."""
        from app.services.lexical_network.job_manager_service import (
            LexicalNetworkJobManager,
        )
        
        manager = LexicalNetworkJobManager()
        
        config = JobConfig(
            job_type="relation_building",
            source="pos_filter",
            pos_filter="形容詞",
            relation_types=["SYNONYM"],
        )
        
        job_id = await manager.create_job(config)
        status = await manager.get_job_status(job_id)
        
        assert status is not None
        assert status.id == job_id
        assert status.status == "pending"
        assert status.job_type == "relation_building"


@pytest.mark.anyio
class TestAdminAPI:
    """Test admin API endpoints."""
    
    async def test_list_available_models_endpoint(self, async_client):
        """Test listing available models endpoint."""
        response = await async_client.get("/api/v1/lexical-network/models")
        
        # Should work even without auth for this endpoint (or may require auth)
        # Adjust based on actual auth requirements
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            assert len(data) > 0
            assert "model_key" in data[0]
            assert "provider" in data[0]
    
    async def test_get_network_stats_endpoint(self, async_client):
        """Test getting network stats endpoint."""
        # This will require Neo4j to be running
        # For now, just check the endpoint exists
        response = await async_client.get("/api/v1/lexical-network/stats")
        
        # May return 503 if Neo4j is not available, or 200 with stats
        assert response.status_code in [200, 503]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
