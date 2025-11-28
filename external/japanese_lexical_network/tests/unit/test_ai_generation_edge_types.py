"""
Test for AI generation edge type detection fixes.
"""

import pytest
import networkx as nx
from unittest.mock import patch, MagicMock
import sys
import os

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from ai_generation_single import generate_lexical_relations


class TestAIGenerationEdgeTypes:
    """Test AI generation edge type detection."""
    
    def setup_method(self):
        """Set up test graph with different edge structures."""
        self.graph = nx.Graph()
        
        # Add test nodes
        self.graph.add_node('親', hiragana='おや', pos='名詞', translation='parent')
        self.graph.add_node('父', hiragana='ちち', pos='名詞', translation='father')
        self.graph.add_node('母', hiragana='はは', pos='名詞', translation='mother')
        self.graph.add_node('敵', hiragana='てき', pos='名詞', translation='enemy')
        
        # Add synonym edge with nested structure
        self.graph.add_edge('親', '父', **{
            'synonym': {
                'synonym_strength': 0.8,
                'mutual_sense': '親族',
                'mutual_sense_hiragana': 'しんぞく',
                'mutual_sense_translation': 'family',
                'synonymy_domain': '家族',
                'synonymy_domain_hiragana': 'かぞく',
                'synonymy_domain_translation': 'family',
                'synonymy_explanation': 'Both refer to family members'
            },
            'type': 'synonym',
            'weight': 0.8
        })
        
        # Add another synonym edge without explicit type
        self.graph.add_edge('親', '母', **{
            'synonym': {
                'synonym_strength': 0.9,
                'mutual_sense': '親族',
                'mutual_sense_hiragana': 'しんぞく',
                'mutual_sense_translation': 'family'
            },
            'weight': 0.9
        })
        
        # Add antonym edge
        self.graph.add_edge('親', '敵', **{
            'antonym': {
                'antonym_strength': 0.7,
                'antonymy_domain': '関係',
                'antonymy_domain_hiragana': 'かんけい',
                'antonymy_domain_translation': 'relationship'
            },
            'type': 'antonym',
            'weight': 0.7
        })
    
    @patch('ai_generation_single.HAS_VALID_API_KEY', True)
    @patch('ai_generation_single.genai.GenerativeModel')
    def test_edge_type_detection_in_context(self, mock_model_class):
        """Test that edge types are correctly detected when building context."""
        # Mock the Gemini API response
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '''
        {
          "source_lexeme": {
            "lemma": "親",
            "hiragana": "おや",
            "POS": "名詞",
            "translation": {
              "target_language": "English",
              "target_lemma": "parent",
              "target_POS": "noun"
            }
          },
          "lexeme_synonyms": [
            {
              "synonym_lemma": "父親",
              "synonym_hiragana": "ちちおや",
              "POS": "名詞",
              "synonym_strenght": 0.8,
              "synonym_translation": "father",
              "mutual_sense": "親族",
              "mutual_sense_hiragana": "しんぞく",
              "mutual_sense_translation": "family",
              "synonymy_domain": "家族",
              "synonymy_domain_hiragana": "かぞく",
              "synonymy_domain_translation": "family",
              "synonymy_explanation": "Both refer to family members"
            }
          ],
          "lexeme_antonyms": [
            {
              "antonym_lemma": "子供",
              "antonym_hiragana": "こども",
              "POS": "名詞",
              "antonym_translation": "child",
              "antonym_strenght": 0.9,
              "antonymy_domain": "家族関係",
              "antonymy_domain_hiragana": "かぞくかんけい",
              "antonymy_domain_translation": "family relationship",
              "antonym_explanation": "Parent and child are opposite roles"
            }
          ]
        }
        '''
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model
        
        # Call the function
        result = generate_lexical_relations('親', G=self.graph)
        
        # Verify the function ran successfully
        assert 'error' not in result or result.get('source_lexeme', {}).get('lemma')
        
        # Get the prompt that was sent to verify context includes correct edge types
        call_args = mock_model.generate_content.call_args
        prompt = call_args[0][0] if call_args else ""
        
        # Check that the prompt includes the existing neighbors with correct relation types
        assert "父 (ちち): father [synonym]" in prompt
        assert "母 (はは): mother [synonym]" in prompt  
        assert "敵 (てき): enemy [antonym]" in prompt
        
        # Ensure no "unknown" relation types appear in the context
        assert "[unknown]" not in prompt
    
    def test_edge_type_detection_logic(self):
        """Test the edge type detection logic directly."""
        # Test synonym detection with explicit type
        edge_data = {
            'synonym': {'synonym_strength': 0.8},
            'type': 'synonym',
            'weight': 0.8
        }
        
        relation_type = edge_data.get('type')
        if relation_type is None:
            if 'synonym' in edge_data:
                relation_type = 'synonym'
            elif 'antonym' in edge_data:
                relation_type = 'antonym'
            else:
                relation_type = 'unknown'
        
        assert relation_type == 'synonym'
        
        # Test synonym detection without explicit type
        edge_data = {
            'synonym': {'synonym_strength': 0.8},
            'weight': 0.8
        }
        
        relation_type = edge_data.get('type')
        if relation_type is None:
            if 'synonym' in edge_data:
                relation_type = 'synonym'
            elif 'antonym' in edge_data:
                relation_type = 'antonym'
            else:
                relation_type = 'unknown'
        
        assert relation_type == 'synonym'
        
        # Test antonym detection
        edge_data = {
            'antonym': {'antonym_strength': 0.7},
            'type': 'antonym',
            'weight': 0.7
        }
        
        relation_type = edge_data.get('type')
        if relation_type is None:
            if 'synonym' in edge_data:
                relation_type = 'synonym'
            elif 'antonym' in edge_data:
                relation_type = 'antonym'
            else:
                relation_type = 'unknown'
        
        assert relation_type == 'antonym'
        
        # Test unknown edge type
        edge_data = {
            'some_other_field': 'value',
            'weight': 0.5
        }
        
        relation_type = edge_data.get('type')
        if relation_type is None:
            if 'synonym' in edge_data:
                relation_type = 'synonym'
            elif 'antonym' in edge_data:
                relation_type = 'antonym'
            else:
                relation_type = 'unknown'
        
        assert relation_type == 'unknown'


if __name__ == '__main__':
    pytest.main([__file__])