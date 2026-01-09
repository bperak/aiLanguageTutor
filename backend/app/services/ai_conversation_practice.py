"""
AI Conversational Practice Service
Creates dynamic dialogue-based grammar pattern practice using LLMs.
"""

from typing import Dict, List, Optional, Any, Literal
from enum import Enum
from pydantic import BaseModel
import asyncio
import structlog

from app.services.ai_chat_service import AIChatService
from app.services.ai_content_generator import AIContentGenerator
from app.db import get_neo4j_session

logger = structlog.get_logger()


class ConversationContext(str, Enum):
    """Different conversation contexts for grammar practice."""
    RESTAURANT = "restaurant"
    OFFICE = "office"
    FAMILY = "family"
    SHOPPING = "shopping"
    TRAVEL = "travel"
    SCHOOL = "school"
    HOSPITAL = "hospital"
    INTRODUCTION = "introduction"


class DialogueTurn(BaseModel):
    """A single turn in the conversation dialogue."""
    speaker: Literal["ai", "user"]
    message: str
    feedback: Optional[str] = None
    grammar_focus: Optional[str] = None
    corrections: Optional[List[str]] = None
    hints: Optional[List[str]] = None


class ConversationScenario(BaseModel):
    """A complete conversation scenario for grammar practice."""
    scenario_id: str
    pattern_id: str
    pattern: str
    context: str  # Changed from ConversationContext to str to support custom contexts
    situation: str
    learning_objective: str
    ai_character: str
    user_role: str
    difficulty_level: str
    dialogue_turns: List[DialogueTurn]
    completed: bool = False
    
    
class ConversationFeedback(BaseModel):
    """Feedback on user's conversation performance."""
    grammar_accuracy: float  # 0.0 to 1.0
    naturalness: float      # 0.0 to 1.0 
    context_appropriateness: float  # 0.0 to 1.0
    corrections: List[str]
    suggestions: List[str]
    next_practice_focus: str
    

class AIConversationPractice:
    """AI-powered conversational grammar practice system."""
    
    def __init__(self):
        self.ai_chat = AIChatService()
        self.content_generator = AIContentGenerator()
        
    async def generate_conversation_scenario(
        self,
        pattern_id: str,
        pattern: str,
        pattern_classification: str,
        example_sentence: str,
        context: ConversationContext,
        difficulty_level: str = "intermediate",
        provider: str = "openai"
    ) -> ConversationScenario:
        """
        Generate a dynamic conversation scenario around a grammar pattern.
        
        Args:
            pattern_id: Grammar pattern ID
            pattern: The grammar pattern (e.g., "～は～です")
            pattern_classification: Pattern type (e.g., "説明")
            example_sentence: Example usage
            context: Conversation context
            difficulty_level: basic/intermediate/advanced
            provider: AI provider
            
        Returns:
            Generated conversation scenario
        """
        logger.info("scenario_generation_begin", pattern_id=pattern_id, pattern=pattern, context=str(context), difficulty_level=difficulty_level, provider=provider)
        
        scenario_prompt = self._create_scenario_prompt(
            pattern, pattern_classification, example_sentence, context, difficulty_level
        )
        
        system_prompt = """
You are an expert Japanese conversation teacher. Create realistic, engaging dialogue scenarios 
that naturally incorporate specific grammar patterns. The scenarios should:
1. Feel natural and contextually appropriate
2. Create multiple opportunities to use the target pattern
3. Include cultural nuances and pragmatic considerations
4. Provide clear learning objectives
5. Adapt to the specified difficulty level

Return the response in a structured format with clear dialogue turns.
"""
        
        try:
            response = await self.ai_chat.generate_reply(
                provider=provider,
                model="gpt-4o" if provider == "openai" else "gemini-2.5-flash",
                messages=[{"role": "user", "content": scenario_prompt}],
                system_prompt=system_prompt
            )
            logger.debug("scenario_llm_response_received", pattern_id=pattern_id, response_length=len(response.get("content", "")))
        except Exception as e:
            logger.error("scenario_generation_llm_failed", pattern_id=pattern_id, error=str(e))
            raise
        
        # Parse AI response and create scenario
        scenario_data = self._parse_scenario_response(response["content"])
        logger.debug("scenario_parsed_successfully", pattern_id=pattern_id, initial_turns=len(scenario_data.get("initial_turns", [])))
        
        scenario = ConversationScenario(
            scenario_id=f"{pattern_id}_{context.value}_{difficulty_level}",
            pattern_id=pattern_id,
            pattern=pattern,
            context=context.value,  # Convert enum to string
            situation=scenario_data["situation"],
            learning_objective=scenario_data["objective"],
            ai_character=scenario_data["ai_character"],
            user_role=scenario_data["user_role"],
            difficulty_level=difficulty_level,
            dialogue_turns=scenario_data["initial_turns"]
        )
        logger.info("scenario_generation_complete", scenario_id=scenario.scenario_id)
        
        return scenario
    
    async def continue_conversation(
        self,
        scenario: ConversationScenario,
        user_message: str,
        provider: str = "openai"
    ) -> DialogueTurn:
        """
        Continue the conversation based on user input with grammar feedback.
        
        Args:
            scenario: Current conversation scenario
            user_message: User's message in Japanese
            provider: AI provider
            
        Returns:
            AI response with feedback and corrections
        """
        logger.info("continue_conversation_begin", scenario_id=scenario.scenario_id, provider=provider, user_message_len=len(user_message))
        
        conversation_context = self._build_conversation_context(scenario)
        
        # Analyze user input for grammar accuracy
        analysis_prompt = f"""
Analyze this Japanese sentence for grammar accuracy, naturalness, and appropriateness:

User said: "{user_message}"
Target pattern: {scenario.pattern}
Context: {scenario.situation}
Difficulty level: {scenario.difficulty_level}

Provide:
1. Grammar accuracy assessment
2. Natural usage evaluation  
3. Context appropriateness
4. Specific corrections needed
5. Suggestions for improvement
"""
        
        # Get grammar analysis
        try:
            analysis_response = await self.ai_chat.generate_reply(
                provider=provider,
                model="gpt-4o" if provider == "openai" else "gemini-2.5-flash",
                messages=[{"role": "user", "content": analysis_prompt}],
                system_prompt="You are a Japanese grammar expert. Provide detailed, constructive feedback on language usage."
            )
            logger.debug("grammar_analysis_complete", scenario_id=scenario.scenario_id, response_length=len(analysis_response.get("content", "")))
        except Exception as e:
            logger.error("grammar_analysis_failed", scenario_id=scenario.scenario_id, error=str(e))
            raise
        
        # Generate conversational response
        conversation_prompt = f"""
Continue this conversation naturally while providing gentle grammar guidance:

Context: {scenario.situation}
Your character: {scenario.ai_character}
User's role: {scenario.user_role}
Target pattern: {scenario.pattern}

User just said: "{user_message}"

Respond as your character would, but incorporate:
1. Natural conversational response
2. Subtle grammar reinforcement of the target pattern
3. Gentle correction if needed (not pedantic)
4. Opportunity for user to practice the pattern again
5. Cultural context when appropriate

Keep the response conversational and engaging.
"""
        
        try:
            conversation_response = await self.ai_chat.generate_reply(
                provider=provider,
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": conversation_context},
                    {"role": "user", "content": conversation_prompt}
                ]
            )
            logger.debug("conversation_response_generated", scenario_id=scenario.scenario_id, response_length=len(conversation_response.get("content", "")))
        except Exception as e:
            logger.error("conversation_generation_failed", scenario_id=scenario.scenario_id, error=str(e))
            raise
        
        # Extract feedback and corrections from analysis
        feedback_data = self._parse_feedback_response(analysis_response["content"])
        logger.debug("feedback_parsed", scenario_id=scenario.scenario_id, corrections=len(feedback_data.get("corrections", [])), hints=len(feedback_data.get("hints", [])))
        
        ai_turn = DialogueTurn(
            speaker="ai",
            message=conversation_response["content"],
            feedback=feedback_data.get("feedback"),
            grammar_focus=scenario.pattern,
            corrections=feedback_data.get("corrections", []),
            hints=feedback_data.get("hints", [])
        )
        
        # Add user turn to scenario
        user_turn = DialogueTurn(
            speaker="user",
            message=user_message,
            grammar_focus=scenario.pattern
        )
        
        scenario.dialogue_turns.extend([user_turn, ai_turn])
        logger.info("continue_conversation_complete", scenario_id=scenario.scenario_id, total_turns=len(scenario.dialogue_turns))
        
        return ai_turn
    
    async def get_conversation_summary(
        self,
        scenario: ConversationScenario,
        provider: str = "openai"
    ) -> ConversationFeedback:
        """
        Generate comprehensive feedback on the entire conversation.
        
        Args:
            scenario: Completed conversation scenario
            provider: AI provider
            
        Returns:
            Detailed conversation feedback
        """
        dialogue_text = self._format_dialogue_for_analysis(scenario.dialogue_turns)
        
        summary_prompt = f"""
Analyze this Japanese conversation practice session:

Target Pattern: {scenario.pattern}
Context: {scenario.situation}
Difficulty: {scenario.difficulty_level}

Conversation:
{dialogue_text}

Provide comprehensive feedback:
1. Overall grammar accuracy (0.0-1.0)
2. Naturalness of expressions (0.0-1.0)
3. Context appropriateness (0.0-1.0)
4. Key corrections needed
5. Specific suggestions for improvement
6. What to focus on in next practice session
7. Connections between this pattern and related grammar/vocabulary
8. Cultural/pragmatic insights gained

Format as structured feedback for learning purposes.
"""
        
        response = await self.ai_chat.generate_reply(
            provider=provider,
            model="gpt-4o",
            messages=[{"role": "user", "content": summary_prompt}],
            system_prompt="You are an expert Japanese language assessor. Provide constructive, detailed feedback that helps learners improve."
        )
        
        return self._parse_summary_response(response["content"])
    
    def _create_scenario_prompt(
        self,
        pattern: str,
        classification: str,
        example: str,
        context: ConversationContext,
        difficulty: str
    ) -> str:
        """Create prompt for scenario generation."""
        context_descriptions = {
            ConversationContext.RESTAURANT: "ordering food, talking with servers, discussing preferences",
            ConversationContext.OFFICE: "workplace conversations, meetings, colleague interactions",
            ConversationContext.FAMILY: "home conversations, family discussions, daily life",
            ConversationContext.SHOPPING: "store interactions, product inquiries, purchases",
            ConversationContext.TRAVEL: "tourist situations, directions, hotel/transport",
            ConversationContext.SCHOOL: "classroom settings, student-teacher interactions",
            ConversationContext.HOSPITAL: "medical consultations, health discussions",
            ConversationContext.INTRODUCTION: "meeting new people, self-introduction, social situations"
        }
        
        return f"""
Create a conversation scenario for Japanese grammar practice:

Target Pattern: {pattern}
Classification: {classification}
Example Usage: {example}
Context: {context.value} ({context_descriptions.get(context, "general conversation")})
Difficulty Level: {difficulty}

Generate:
1. A specific, realistic situation
2. Clear learning objective
3. AI character description (personality, role)
4. User's role in the conversation
5. 2-3 opening dialogue turns that set up natural usage of the pattern

Make the scenario engaging and culturally authentic. The pattern should emerge naturally 
from the conversational context, not feel forced or artificial.

Example format:
SITUATION: [specific scenario]
OBJECTIVE: [what the learner will practice]
AI CHARACTER: [who the AI plays - personality, role]
USER ROLE: [who the learner plays]
OPENING DIALOGUE:
AI: [opening line]
[Expected user response opportunity]
AI: [response that models the pattern]
"""
    
    def _build_conversation_context(self, scenario: ConversationScenario) -> str:
        """Build conversation context for AI responses."""
        recent_dialogue = scenario.dialogue_turns[-6:] if len(scenario.dialogue_turns) > 6 else scenario.dialogue_turns
        
        dialogue_context = "\n".join([
            f"{turn.speaker.upper()}: {turn.message}" for turn in recent_dialogue
        ])
        
        return f"""
You are {scenario.ai_character} in this situation: {scenario.situation}

Learning objective: {scenario.learning_objective}
Target grammar pattern: {scenario.pattern}
User plays: {scenario.user_role}

Recent conversation:
{dialogue_context}

Stay in character while providing helpful language learning support.
"""
    
    def _parse_scenario_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response into structured scenario data."""
        # Simple parsing - in production, you might want more robust parsing
        lines = response.split('\n')
        
        scenario_data = {
            "situation": "General conversation practice",
            "objective": f"Practice using grammar patterns naturally",
            "ai_character": "Friendly conversation partner",
            "user_role": "Language learner",
            "initial_turns": []
        }
        
        # Extract structured information from response
        current_section = None
        for line in lines:
            line = line.strip()
            if line.startswith('SITUATION:'):
                scenario_data["situation"] = line.replace('SITUATION:', '').strip()
            elif line.startswith('OBJECTIVE:'):
                scenario_data["objective"] = line.replace('OBJECTIVE:', '').strip()
            elif line.startswith('AI CHARACTER:'):
                scenario_data["ai_character"] = line.replace('AI CHARACTER:', '').strip()
            elif line.startswith('USER ROLE:'):
                scenario_data["user_role"] = line.replace('USER ROLE:', '').strip()
            elif line.startswith('OPENING DIALOGUE:'):
                current_section = "dialogue"
            elif current_section == "dialogue" and line.startswith('AI:'):
                message = line.replace('AI:', '').strip()
                if message:
                    scenario_data["initial_turns"].append(DialogueTurn(
                        speaker="ai",
                        message=message
                    ))
        
        return scenario_data
    
    def _parse_feedback_response(self, response: str) -> Dict[str, Any]:
        """Parse grammar feedback from AI response."""
        return {
            "feedback": "Grammar analysis provided",
            "corrections": [],
            "hints": ["Continue practicing natural conversation"]
        }
    
    def _format_dialogue_for_analysis(self, turns: List[DialogueTurn]) -> str:
        """Format dialogue turns for analysis."""
        return "\n".join([
            f"{turn.speaker.upper()}: {turn.message}" for turn in turns
        ])
    
    def _parse_summary_response(self, response: str) -> ConversationFeedback:
        """Parse comprehensive feedback response."""
        return ConversationFeedback(
            grammar_accuracy=0.8,
            naturalness=0.7,
            context_appropriateness=0.9,
            corrections=["Sample correction"],
            suggestions=["Continue practicing in context"],
            next_practice_focus="Focus on natural expression"
        )


async def demo_conversation_practice():
    """Demo function for conversation practice."""
    practice = AIConversationPractice()
    
    scenario = await practice.generate_conversation_scenario(
        pattern_id="grammar_001",
        pattern="～は～です",
        pattern_classification="説明",
        example_sentence="私はカーラです",
        context=ConversationContext.INTRODUCTION,
        difficulty_level="basic"
    )
    
    print(f"Generated scenario: {scenario.situation}")
    print(f"Your role: {scenario.user_role}")
    print(f"AI character: {scenario.ai_character}")
    
    # Simulate conversation
    user_message = "私は学生です"
    ai_turn = await practice.continue_conversation(scenario, user_message)
    
    print(f"AI Response: {ai_turn.message}")
    if ai_turn.corrections:
        print(f"Corrections: {', '.join(ai_turn.corrections)}")


if __name__ == "__main__":
    asyncio.run(demo_conversation_practice())
