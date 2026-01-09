"""
Tests for User Path Service.

Tests the main path generation service that orchestrates
personalized learning path creation.
"""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.user_path_service import UserPathService
from app.schemas.profile import LearningPathData, LearningPathStep
from app.models.database_models import User, UserProfile


@pytest.fixture
def user_path_service():
    """Create UserPathService instance."""
    return UserPathService()


@pytest.fixture
def mock_user():
    """Create mock user."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.current_level = "beginner_1"
    user.target_languages = ["ja"]
    user.learning_goals = ["conversation"]
    return user


@pytest.fixture
def mock_profile():
    """Create mock user profile."""
    profile = MagicMock(spec=UserProfile)
    profile.learning_goals = ["conversation", "travel"]
    profile.previous_knowledge = {"has_experience": False}
    profile.learning_experiences = {"preferred_methods": ["conversation"]}
    profile.usage_context = {"contexts": ["travel"]}
    return profile


@pytest.fixture
def mock_cando_descriptors():
    """Create mock CanDo descriptors."""
    return [
        {
            "uid": "JF:1",
            "level": "A1",
            "descriptionEn": "Can introduce myself",
            "descriptionJa": "自己紹介ができる",
            "primaryTopicEn": "Self Introduction",
            "primaryTopic": "自己紹介",
            "skillDomain": "産出",
            "type": "表現",
            "source": "JFまるごと"
        },
        {
            "uid": "JF:2",
            "level": "A1",
            "descriptionEn": "Can greet people",
            "descriptionJa": "挨拶ができる",
            "primaryTopicEn": "Greetings",
            "primaryTopic": "挨拶",
            "skillDomain": "産出",
            "type": "表現",
            "source": "JFまるごと"
        }
    ]


@pytest.mark.asyncio
async def test_analyze_profile_for_path(user_path_service, mock_user, mock_profile):
    """Test profile analysis for path generation."""
    context = user_path_service.analyze_profile_for_path(mock_profile, mock_user)
    
    assert context["current_level"] == "beginner_1"
    assert "conversation" in context["learning_goals"]
    assert context["target_languages"] == ["ja"]
    assert "previous_knowledge" in context


@pytest.mark.asyncio
async def test_analyze_profile_without_profile(user_path_service, mock_user):
    """Test profile analysis when no profile exists."""
    context = user_path_service.analyze_profile_for_path(None, mock_user)
    
    assert context["current_level"] == "beginner_1"
    assert context["learning_goals"] == ["conversation"]
    assert context["target_languages"] == ["ja"]


@pytest.mark.asyncio
async def test_generate_user_path_success(
    user_path_service,
    mock_user,
    mock_profile,
    mock_cando_descriptors
):
    """Test successful path generation."""
    user_id = mock_user.id
    
    # Mock database session
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock()
    
    # Mock user query result
    mock_user_result = MagicMock()
    mock_user_result.scalar_one_or_none.return_value = mock_user
    mock_db.execute.return_value = mock_user_result
    
    # Mock profile query result
    mock_profile_result = MagicMock()
    mock_profile_result.scalar_one_or_none.return_value = mock_profile
    mock_db.execute.side_effect = [mock_user_result, mock_profile_result]
    
    # Mock Neo4j session
    mock_neo4j = AsyncMock()
    
    # Mock selector service
    with patch.object(user_path_service.selector_service, 'select_initial_candos') as mock_select:
        mock_select.return_value = mock_cando_descriptors
        
        # Mock path builder
        with patch.object(user_path_service.path_builder, 'build_semantic_path') as mock_build:
            mock_build.return_value = mock_cando_descriptors
            
            # Mock step generation
            with patch.object(user_path_service, '_generate_path_steps') as mock_steps:
                mock_steps.return_value = [
                    {
                        "step_id": "step_1",
                        "title": "Step 1",
                        "description": "Test step",
                        "estimated_duration_days": 7,
                        "prerequisites": [],
                        "learning_objectives": ["Learn something"],
                        "can_do_descriptors": ["JF:1"],
                        "resources": [],
                        "difficulty_level": "beginner"
                    }
                ]
                
                # Mock milestone generation
                with patch.object(user_path_service, '_generate_milestones') as mock_milestones:
                    mock_milestones.return_value = []
                    
                    path_data = await user_path_service.generate_user_path(
                        db=mock_db,
                        neo4j_session=mock_neo4j,
                        user_id=user_id,
                        profile_data=mock_profile
                    )
                    
                    assert isinstance(path_data, LearningPathData)
                    assert len(path_data.steps) > 0
                    assert path_data.starting_level == "beginner_1"


@pytest.mark.asyncio
async def test_generate_user_path_no_candos(user_path_service, mock_user, mock_profile):
    """Test path generation when no CanDo descriptors are found."""
    user_id = mock_user.id
    
    # Mock database session
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock()
    
    # Mock user query result
    mock_user_result = MagicMock()
    mock_user_result.scalar_one_or_none.return_value = mock_user
    mock_db.execute.return_value = mock_user_result
    
    # Mock Neo4j session
    mock_neo4j = AsyncMock()
    
    # Mock selector service returning empty list
    with patch.object(user_path_service.selector_service, 'select_initial_candos') as mock_select:
        mock_select.return_value = []
        
        path_data = await user_path_service.generate_user_path(
            db=mock_db,
            neo4j_session=mock_neo4j,
            user_id=user_id,
            profile_data=mock_profile
        )
        
        # Should return default path
        assert isinstance(path_data, LearningPathData)
        assert path_data.path_name == "Default Learning Path"


def test_map_level_to_difficulty(user_path_service):
    """Test level to difficulty mapping."""
    assert user_path_service._map_level_to_difficulty("A1") == "beginner"
    assert user_path_service._map_level_to_difficulty("B1") == "intermediate"
    assert user_path_service._map_level_to_difficulty("C1") == "advanced"


def test_determine_target_level(user_path_service):
    """Test target level determination."""
    assert user_path_service._determine_target_level("beginner_1", 20) == "intermediate_2"
    assert user_path_service._determine_target_level("beginner_1", 10) == "intermediate_1"
    assert user_path_service._determine_target_level("beginner_1", 5) == "beginner_2"


def test_generate_path_name(user_path_service):
    """Test path name generation."""
    context = {"learning_goals": ["conversation"]}
    name = user_path_service._generate_path_name(context)
    assert "Conversation" in name or "conversation" in name.lower()


def test_generate_path_description(user_path_service):
    """Test path description generation."""
    context = {
        "learning_goals": ["conversation"],
        "current_level": "beginner_1"
    }
    desc = user_path_service._generate_path_description(context, 10)
    assert "beginner_1" in desc
    assert "10" in desc or "ten" in desc.lower()

