"""
Croatian Lexical Exercises Script for Croatian Lexical Graph

This script generates interactive language learning exercises based on
the currently selected Croatian node in the lexical graph. It is designed
to be incorporated into the Node Information pane as a "Croatian Lexical Exercises" tab.

The exercises adapt to different learning levels and include translations
and explanations for beginner levels.
"""

import json
import os
import logging
import networkx as nx
from dotenv import load_dotenv
import google.generativeai as genai
from cache_helper import cache
from croatian_helper import load_croatian_graph, get_croatian_node_info, find_croatian_nodes

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure Gemini API
try:
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    if not GEMINI_API_KEY or GEMINI_API_KEY == 'your_gemini_api_key_here':
        logger.warning("No valid Gemini API key found in environment variables.")
        HAS_VALID_API_KEY = False
    else:
        genai.configure(api_key=GEMINI_API_KEY)
        HAS_VALID_API_KEY = True
except Exception as e:
    logger.error(f"Error configuring Gemini API: {e}")
    HAS_VALID_API_KEY = False

# Default model to use
DEFAULT_MODEL = 'gemini-2.0-flash'

# Croatian learning level descriptions
CROATIAN_LEVEL_DESCRIPTIONS = {
    1: "Beginner 1 - Basic Croatian vocabulary and simple sentence structures with full English translations",
    2: "Beginner 2 - Elementary Croatian vocabulary with pronunciation guidance and partial English support",
    3: "Intermediate 1 - Common everyday Croatian vocabulary with basic grammar patterns",
    4: "Intermediate 2 - Expanded Croatian vocabulary and more complex sentence structures",
    5: "Advanced 1 - Sophisticated Croatian vocabulary with cultural context and idiomatic expressions",
    6: "Advanced 2 - Native-like Croatian vocabulary with regional variations and cultural nuances"
}

# Croatian case system for educational purposes
CROATIAN_CASES = {
    "nominativ": "nominative (subject)",
    "genitiv": "genitive (possession, 'of')",
    "dativ": "dative (indirect object, 'to')",
    "akuzativ": "accusative (direct object)",
    "vokativ": "vocative (address)",
    "instrumental": "instrumental (means, 'with')",
    "lokativ": "locative (location, 'in/on')"
}

def is_available():
    """Check if Gemini API is available with valid API key."""
    return HAS_VALID_API_KEY

def get_croatian_graph():
    """Get the Croatian NetworkX graph."""
    try:
        # Try to import from app.py first
        from app import G_croatian
        if G_croatian and G_croatian.number_of_nodes() > 0:
            logger.info(f"Using shared Croatian graph with {G_croatian.number_of_nodes()} nodes and {G_croatian.number_of_edges()} edges")
            return G_croatian
    except (ImportError, AttributeError):
        logger.warning("Could not import Croatian graph from app.py, falling back to loading from pickle")
    
    # Fallback to loading from pickle file
    try:
        G_croatian = load_croatian_graph()
        if G_croatian:
            logger.info(f"Loaded Croatian graph from pickle with {G_croatian.number_of_nodes()} nodes and {G_croatian.number_of_edges()} edges")
            return G_croatian
    except Exception as e:
        logger.error(f"Error loading Croatian graph: {e}")
    
    return nx.Graph()  # Return empty graph on error

def get_croatian_node_context(node_id, max_neighbors=7):
    """Get context about a Croatian node and its neighbors from the graph."""
    G = get_croatian_graph()
    
    if node_id not in G.nodes:
        # Provide a fallback context for nodes not in the graph
        logger.warning(f"Croatian node '{node_id}' not found in graph, using fallback context")
        return {
            "node": {
                "id": node_id,
                "natuknica": node_id.split("-")[0] if "-" in node_id else node_id,
                "tekst": "",
                "translation": "",
                "pos": "",
                "upos": ""
            },
            "neighbors": [],
            "fallback": True
        }
    
    # Get node data using Croatian helper
    node_data = get_croatian_node_info(G, node_id)
    if not node_data:
        return {
            "node": {"id": node_id, "natuknica": "", "tekst": "", "translation": "", "pos": "", "upos": ""},
            "neighbors": [],
            "fallback": True
        }
    
    # If translation is empty, try to extract basic meaning from definition
    if not node_data.get('translation', '').strip():
        tekst = node_data.get('tekst', '')
        natuknica = node_data.get('natuknica', '')
        
        # Try to extract a basic translation from the definition
        if tekst and natuknica:
            # Specific word pattern matching instead of broad categorization
            if natuknica == 'ljubav' and ('osjećaj naklonosti' in tekst or 'privrženost' in tekst):
                node_data['translation'] = 'love'
            elif natuknica == 'majka' and ('roditelj ženskoga spola' in tekst or 'mama' in tekst):
                node_data['translation'] = 'mother'
            elif natuknica == 'otac' and ('roditelj muškoga spola' in tekst or 'tata' in tekst):
                node_data['translation'] = 'father'
            elif natuknica == 'dijete' and ('sin ili kći' in tekst or 'čedo' in tekst):
                node_data['translation'] = 'child'
            elif natuknica == 'obitelj' and ('skupina' in tekst and 'rodbina' in tekst):
                node_data['translation'] = 'family'
            # Add more specific word patterns as needed
            # Fallback: use the natuknica itself if no specific pattern matches
            else:
                # Don't assign generic translations - let the AI figure it out
                pass
    
    # Get neighbor data
    neighbors = []
    for neighbor in G.neighbors(node_id):
        neighbor_data = get_croatian_node_info(G, neighbor)
        if neighbor_data:
            # Fix neighbor translation too
            if not neighbor_data.get('translation', '').strip():
                neighbor_tekst = neighbor_data.get('tekst', '')
                if 'naklonost' in neighbor_data.get('natuknica', ''):
                    neighbor_data['translation'] = 'affection'
                elif 'privrženost' in neighbor_data.get('natuknica', ''):
                    neighbor_data['translation'] = 'attachment'
                elif 'odanost' in neighbor_data.get('natuknica', ''):
                    neighbor_data['translation'] = 'devotion'
                elif 'nježnost' in neighbor_data.get('natuknica', ''):
                    neighbor_data['translation'] = 'tenderness'
                elif 'strast' in neighbor_data.get('natuknica', ''):
                    neighbor_data['translation'] = 'passion'
                elif 'zaljubljenost' in neighbor_data.get('natuknica', ''):
                    neighbor_data['translation'] = 'being in love'
                elif 'bliskost' in neighbor_data.get('natuknica', ''):
                    neighbor_data['translation'] = 'intimacy'
                elif 'predanost' in neighbor_data.get('natuknica', ''):
                    neighbor_data['translation'] = 'dedication'
                else:
                    neighbor_data['translation'] = 'related concept'
            
            edge_data = G.get_edge_data(node_id, neighbor)
            
            # Determine relationship type and strength
            relationship_type = "related"
            relationship_strength = 0.5
            
            if edge_data:
                for key, data in edge_data.items():
                    if 'synonym_strength' in data:
                        relationship_type = "synonym"
                        relationship_strength = float(data['synonym_strength'])
                        break
                    elif 'antonym_strength' in data:
                        relationship_type = "antonym"
                        relationship_strength = float(data['antonym_strength'])
                        break
            
            neighbors.append({
                "id": neighbor,
                "natuknica": neighbor_data.get('natuknica', ''),
                "tekst": neighbor_data.get('tekst', ''),
                "translation": neighbor_data.get('translation', ''),
                "pos": neighbor_data.get('pos', ''),
                "upos": neighbor_data.get('upos', ''),
                "relationship": relationship_type,
                "strength": relationship_strength
            })
    
    # Sort by relationship strength and limit to max_neighbors
    neighbors.sort(key=lambda x: x['strength'], reverse=True)
    neighbors = neighbors[:max_neighbors]
    
    return {
        "node": node_data,
        "neighbors": neighbors,
        "fallback": False
    }

def generate_croatian_exercise(node_id, level=1, session_history=None, mode="exercise", model_name=DEFAULT_MODEL):
    """
    Generate an interactive Croatian language learning exercise for the given node.
    
    Args:
        node_id (str): The ID of the Croatian node (lempos format: word-POS)
        level (int): Learning level from 1-6
        session_history (list): Previous conversation history in this session
        mode (str): Exercise mode - "exercise" for structured learning, "conversation" for free-form practice
        model_name (str): Gemini model to use
        
    Returns:
        dict: Generated exercise content
    """
    if not HAS_VALID_API_KEY:
        return {
            "error": "No valid Gemini API key configured",
            "content": "Unable to generate exercises: API key not configured."
        }
    
    # Check cache first (only if no session history)
    if not session_history:
        cache_key = f"croatian_{mode}_{node_id}_{level}_{model_name}"
        cached_result = cache.get(cache_key)
        if cached_result:
            try:
                return json.loads(cached_result)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in cache for Croatian {mode} '{node_id}'. Regenerating content.")
    
    # Get Croatian node context from the graph
    context = get_croatian_node_context(node_id)
    
    # Check if we're using fallback data
    is_fallback = context.get("fallback", False)
    if is_fallback:
        logger.info(f"Using fallback context for Croatian node '{node_id}' - exercise generation will proceed with limited context")
    
    # Create a more human-friendly level description
    level_description = CROATIAN_LEVEL_DESCRIPTIONS.get(level, "Intermediate level")
    
    # Get Croatian word and translation
    croatian_word = context['node'].get('natuknica', node_id.split("-")[0] if "-" in node_id else node_id)
    translation = context['node'].get('translation', '')
    definition = context['node'].get('tekst', '')
    pos = context['node'].get('pos', '')
    upos = context['node'].get('upos', '')
    
    # Prepare related words for context
    related_words = [n['natuknica'] for n in context['neighbors'] if n['natuknica']]
    
    # Generate prompts based on whether this is initial or continuation
    if not session_history:
        # Initial prompt
        if mode == "exercise":
            # Structured exercise mode
            prompt = f"""
            You are a Croatian language teacher who specializes in interactive, engaging learning experiences. Create an interactive exercise for the Croatian word "{croatian_word}" meaning "{translation}".

            WORD DETAILS:
            - Croatian word: {croatian_word}
            - English translation: {translation}
            - Definition: {definition}
            - Part of speech: {pos} ({upos})
            - Related words: {', '.join(related_words[:5])}

            CURRENT LEARNING LEVEL: {level} - {level_description}

            CREATE AN INTERACTIVE CHATBOT EXERCISE that:
            1. Introduces the word "{croatian_word}" in a natural, conversational way
            2. Creates an engaging scenario or conversation that uses this word
            3. Includes 2-3 related words from the following list: {', '.join(related_words)}
            4. Asks the learner questions that encourage them to practice using the word
            5. Provides helpful corrections and explanations when needed
            6. Explains Croatian grammar concepts relevant to this word (cases, verb conjugations, etc.)
            
            SPECIFIC REQUIREMENTS FOR LEVEL {level}:
            """
            
            # Add level-specific requirements
            if level <= 2:  # Beginner levels
                prompt += f"""
                - Include pronunciation guidance for Croatian words
                - Use very simple sentence structures
                - Explain each new word with clear definitions
                - Include English translations for all Croatian sentences
                - Explain basic Croatian grammar rules relevant to the word
                - Use mostly present tense and simple constructions
                """
            elif level <= 4:  # Intermediate levels
                prompt += f"""
                - Include pronunciation guidance only for difficult words
                - Use natural, everyday conversational Croatian
                - Include cultural context where appropriate
                - Gradually introduce more complex grammar (different cases, verb aspects)
                - Provide English translations only when necessary
                - Include some idiomatic expressions
                """
            else:  # Advanced levels
                prompt += f"""
                - Use natural, native-like Croatian with regional variations
                - Include cultural references and context
                - Challenge the learner with complex grammar and idiomatic expressions
                - Focus on natural production and communication
                - Include literary or formal register when appropriate
                - Limit translations to only the most complex concepts
                """
                
            prompt += f"""
            CROATIAN LANGUAGE SPECIFICS TO CONSIDER:
            - Croatian uses 7 cases (nominativ, genitiv, dativ, akuzativ, vokativ, instrumental, lokativ)
            - Verb aspects (perfective vs imperfective)
            - Gender agreement (masculine, feminine, neuter)
            - Pronunciation is mostly phonetic
            
            FORMAT YOUR RESPONSE:
            1. Start with a brief, friendly introduction as a Croatian language tutor
            2. Create a natural conversational scenario using "{croatian_word}"
            3. Format teaching elements clearly:
               - Croatian text
               - English translations (as appropriate for the level)
               - Grammar explanations when introducing new concepts
               - Pronunciation notes when helpful
            4. Ask an engaging question at the end to prompt student response
            
            Begin your Croatian tutoring session now!
            """
        else:
            # Conversation mode - more free-form practice
            prompt = f"""
            You are a native Croatian speaker chatting with a language learner. Start a natural conversation that incorporates the Croatian word "{croatian_word}" meaning "{translation}".

            WORD DETAILS:
            - Croatian word: {croatian_word}
            - English translation: {translation}
            - Definition: {definition}
            - Part of speech: {pos} ({upos})
            - Related words: {', '.join(related_words[:5])}

            CURRENT LEARNING LEVEL: {level} - {level_description}

            CREATE A NATURAL CONVERSATION that:
            1. Feels authentic and casual, like talking with a Croatian friend
            2. Introduces "{croatian_word}" naturally in context
            3. Incorporates 1-2 related words from: {', '.join(related_words[:5])}
            4. Asks open-ended questions to encourage meaningful responses
            5. Is culturally appropriate and realistic for Croatian speakers
            
            SPECIFIC REQUIREMENTS FOR THE CONVERSATION:
            """
            
            # Add level-specific requirements
            if level <= 2:  # Beginner levels
                prompt += f"""
                - Use simple, everyday Croatian conversational patterns
                - Include English translations for all Croatian sentences
                - Focus on common situations and practical usage
                - Explain basic grammar when it comes up naturally
                - Use present tense and simple constructions
                """
            elif level <= 4:  # Intermediate levels
                prompt += f"""
                - Use natural Croatian expressions and some colloquialisms
                - Provide translations only for challenging concepts
                - Introduce culturally specific elements (food, customs, places)
                - Include different verb aspects and cases naturally
                - Use past and future tenses appropriately
                """
            else:  # Advanced levels
                prompt += f"""
                - Use authentic, native-like Croatian with regional expressions
                - Include colloquialisms, idioms, or cultural references
                - Create rich, nuanced conversation between Croatian speakers
                - Use complex grammar structures naturally
                - Limit translations to only specialized terms
                """
                
            prompt += f"""
            CROATIAN CULTURAL CONTEXT:
            - Reference Croatian culture, cities, food, traditions when appropriate
            - Use authentic Croatian expressions and greetings
            - Include cultural nuances in communication style
            
            FORMAT YOUR RESPONSE:
            1. Start with a natural Croatian greeting appropriate to the context
            2. Write a conversational opening that feels authentic
            3. Include:
               - Croatian text
               - English translations (as appropriate for the level)
               - Cultural context when relevant
            4. End with an open-ended question to encourage conversation
            
            Begin your Croatian conversation now!
            """
    else:
        # This is a continuation of a conversation
        # Format the history for the model
        history_text = "\n".join([
            f"Student: {msg['user']}\nTutor: {msg['tutor']}" 
            for msg in session_history
        ])
        
        # Create continuation prompt based on mode
        if mode == "exercise":
            # Structured exercise continuation
            prompt = f"""
            Continue this Croatian language learning conversation about the word "{croatian_word}". You are a helpful, encouraging Croatian tutor.

            CURRENT LEARNING LEVEL: {level} - {level_description}

            CONVERSATION HISTORY:
            {history_text}

            STUDENT'S LAST MESSAGE: {session_history[-1]['user']}

            GUIDELINES FOR YOUR RESPONSE:
            1. Respond directly to the student's message in a natural, encouraging way
            2. Continue to incorporate the target word "{croatian_word}" and related vocabulary
            3. Provide gentle corrections if the student makes mistakes
            4. Explain Croatian grammar concepts when relevant
            5. Keep maintaining the appropriate level of language complexity for Level {level}
            """
            
            # Add level-specific requirements
            if level <= 2:  # Beginner levels
                prompt += f"""
                6. Continue to include English translations for Croatian sentences
                7. Keep grammar explanations simple and clear
                8. Use encouraging, supportive language
                9. Focus on basic sentence patterns and present tense
                """
            elif level <= 4:  # Intermediate levels
                prompt += f"""
                6. Include translations only when necessary for comprehension
                7. Introduce intermediate grammar concepts gradually
                8. Encourage more complex sentence formation
                9. Include cultural context when appropriate
                """
            else:  # Advanced levels
                prompt += f"""
                6. Use natural, native-like Croatian
                7. Challenge the learner with complex grammar and expressions
                8. Focus on fluency and natural communication
                9. Include literary or formal register when appropriate
                """
        else:
            # Conversation mode continuation
            prompt = f"""
            Continue this natural Croatian conversation that includes the word "{croatian_word}". You are a Croatian native speaker chatting with a language learner.

            CURRENT LEARNING LEVEL: {level} - {level_description}

            CONVERSATION HISTORY:
            {history_text}

            STUDENT'S LAST MESSAGE: {session_history[-1]['user']}

            GUIDELINES FOR YOUR RESPONSE:
            1. Respond directly and naturally to the student's message
            2. Keep the conversation flowing authentically
            3. Use "{croatian_word}" or related vocabulary naturally when appropriate
            4. Adjust to the student's language level while gently challenging them
            5. Include Croatian cultural elements when relevant
            """
            
            # Add level-specific requirements
            if level <= 2:  # Beginner levels
                prompt += f"""
                6. Continue to include English translations for Croatian text
                7. Keep language simple and natural
                8. Focus on practical, everyday situations
                """
            elif level <= 4:  # Intermediate levels
                prompt += f"""
                6. Translate only when necessary for comprehension
                7. Use natural Croatian expressions and some colloquialisms
                8. Include cultural references appropriately
                """
            else:  # Advanced levels
                prompt += f"""
                6. Use fully authentic, native-like Croatian
                7. Include natural expressions, idioms, or cultural references
                8. Respond as you would to another Croatian speaker
                """
        
        prompt += f"""
        Format your response with appropriate Croatian, English translations (as needed for the level), and cultural context when relevant.
        
        Your response:
        """

    try:
        # Generate content with Gemini
        genai_model = genai.GenerativeModel(model_name)
        response = genai_model.generate_content(prompt)
        
        # Extract and format the response
        content = response.text
        
        # Cache the result (only for initial messages)
        if not session_history:
            cache_key = f"croatian_{mode}_{node_id}_{level}_{model_name}"
            cache.set(cache_key, json.dumps({
                "node_id": node_id,
                "level": level,
                "mode": mode,
                "content": content,
                "model": model_name,
                "language": "croatian"
            }), ex=86400)  # Cache for 24 hours
        
        return {
            "node_id": node_id,
            "level": level,
            "mode": mode,
            "content": content,
            "model": model_name,
            "language": "croatian",
            "croatian_word": croatian_word,
            "translation": translation
        }
    
    except Exception as e:
        logger.error(f"Error generating Croatian {mode} for '{node_id}': {e}")
        return {
            "error": str(e),
            "content": f"An error occurred while generating the Croatian {mode}: {str(e)}"
        }

def get_croatian_exercise_modes():
    """Get available exercise modes for Croatian."""
    return [
        {"id": "exercise", "name": "Structured Exercise", "description": "Guided learning with explanations"},
        {"id": "conversation", "name": "Free Conversation", "description": "Natural conversation practice"}
    ]

def get_croatian_learning_levels():
    """Get available learning levels for Croatian."""
    return [
        {"id": level, "name": f"Level {level}", "description": desc}
        for level, desc in CROATIAN_LEVEL_DESCRIPTIONS.items()
    ]

if __name__ == "__main__":
    """Test the Croatian exercise generation."""
    print("Testing Croatian Exercise Generation")
    print("=" * 50)
    
    # Test with a Croatian node
    test_node = "ljubav-NOUN"
    
    if not is_available():
        print("❌ Gemini API not available")
        exit(1)
    
    print(f"📝 Testing exercise generation for: {test_node}")
    
    # Test structured exercise mode
    result = generate_croatian_exercise(test_node, level=2, mode="exercise")
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ Exercise generated successfully!")
        print(f"📚 Level: {result['level']}")
        print(f"🎯 Mode: {result['mode']}")
        print(f"🔤 Croatian word: {result.get('croatian_word', 'N/A')}")
        print(f"🌍 Translation: {result.get('translation', 'N/A')}")
        print(f"💬 Content preview: {result['content'][:200]}...")
    
    print("\n" + "=" * 50)
    print("Croatian Exercise Generation Test Complete") 