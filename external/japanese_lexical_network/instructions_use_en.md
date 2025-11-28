# Japanese Lexical Graph - User Instructions

## Overview

The Japanese Lexical Graph is an interactive 3D visualization tool that helps you explore and understand Japanese vocabulary through semantic relationships. The application displays Japanese words as interconnected nodes in a 3D space, allowing you to discover how words relate to each other through synonyms, translations, and linguistic properties.

**Note**: This application also supports Croatian language exploration, though the primary focus is on Japanese vocabulary.

## Getting Started

### Accessing the Application

1. **Start the Application**:
   - Open your terminal/command prompt
   - Navigate to the project directory
   - Run: `python app.py`
   - Open your web browser and go to: `http://localhost:5000`

2. **Language Selection**:
   - Use the language dropdown in the top-left corner
   - Select "🇯🇵 Japanese" for Japanese vocabulary exploration
   - Select "🇭🇷 Croatian" for Croatian vocabulary exploration

## Core Features

### 1. Interactive 3D Graph Visualization

The main interface displays Japanese words as nodes in a 3D space, connected by lines representing semantic relationships.

**Navigation Controls**:
- **Mouse**: 
  - Left-click and drag to rotate the view
  - Right-click and drag to pan
  - Scroll to zoom in/out
- **Touch**: 
  - Single finger drag to rotate
  - Two finger pinch to zoom
  - Two finger drag to pan

**Node Interaction**:
- **Click on any node** to select it and view detailed information
- **Hover over nodes** to see basic information
- **Double-click** to focus the camera on a specific node

### 2. Search Functionality

The search bar allows you to find specific Japanese words or concepts.

**Search Options**:
- **Kanji**: Search by Japanese kanji characters (e.g., "花" for flower)
- **Hiragana**: Search by hiragana reading (e.g., "はな" for flower)
- **POS**: Search by part of speech (e.g., "noun", "verb", "adjective")
- **Translation**: Search by English meaning (e.g., "flower", "love")
- **JLPT**: Search by JLPT level (e.g., "N5", "N4", "N3", "N2", "N1")
- **JLPT Jisho Lemma**: Search by Jisho dictionary lemma
- **JLPT Jisho Synonym**: Search by Jisho dictionary synonyms

**Search Settings**:
- **Depth**: Control how many levels of connections to display (1-3)
- **Exact Match**: Toggle between exact and partial matching
- **Search Button**: Click to execute the search

**Example Searches**:
- Search for "愛" (love) using Kanji attribute
- Search for "noun" using POS attribute to see all nouns
- Search for "N5" using JLPT attribute to see beginner-level words

### 3. Node Information Panel

When you select a node, detailed information appears in the left sidebar.

**Japanese Node Information**:
- **ID**: Unique identifier for the word
- **Kanji**: Japanese kanji characters
- **Hiragana**: Hiragana reading
- **Translation**: English meaning
- **POS**: Part of speech
- **JLPT Level**: Japanese Language Proficiency Test level
- **Relationship Strength**: How strongly connected this word is to others

**Neighbors Panel**:
- Shows all words directly connected to the selected word
- Displays relationship types and strengths
- Click on neighbor names to navigate to those words

### 4. AI-Powered Analysis

The application integrates with Google's Gemini AI to provide intelligent analysis and explanations.

**Available AI Features**:
- **Term Explanation**: Get detailed explanations of Japanese words
- **Term Comparison**: Compare two selected words to understand differences
- **Relationship Analysis**: Understand how words are semantically connected
- **Learning Exercises**: Generate interactive exercises for language learning

**Using AI Features**:
1. Select a node in the graph
2. Look for AI-related buttons in the information panels
3. Click to generate AI analysis
4. Wait for the AI response (may take a few seconds)

### 5. Wikidata Integration

Access rich, structured information about Japanese terms from Wikidata.

**Wikidata Information**:
- **Definitions**: Detailed definitions and descriptions
- **Categories**: Subject categories and classifications
- **Related Terms**: Connections to other concepts
- **Cultural Context**: Historical and cultural information

**Accessing Wikidata**:
- Select a node in the graph
- Look for Wikidata information in the node details
- Click on Wikidata links to explore further

### 6. Interactive Learning Exercises

Generate AI-powered exercises to practice Japanese vocabulary.

**Exercise Types**:
- **Vocabulary Practice**: Multiple choice questions about word meanings
- **Sentence Completion**: Fill-in-the-blank exercises
- **Translation Practice**: Translate between Japanese and English
- **Context Usage**: Understand words in different contexts

**Using Exercises**:
1. Select a word in the graph
2. Look for exercise generation options
3. Choose difficulty level (N5-N1)
4. Generate and complete exercises
5. Review answers and explanations

### 7. Readability Analysis

The application can analyze Japanese text for difficulty level.

**Readability Features**:
- **Automatic Assessment**: Analyzes text complexity
- **6-Level Scale**: From Lower-elementary to Upper-advanced
- **Visual Indicators**: Color-coded difficulty badges
- **Educational Alignment**: Helps choose appropriate content

## Advanced Features

### 1. Graph Controls

Adjust the visualization to suit your needs.

**Display Options**:
- **Node Size**: Adjust how large nodes appear
- **Link Thickness**: Control the thickness of connection lines
- **Color Schemes**: Change the visual theme
- **Animation Speed**: Adjust how quickly the graph settles

### 2. Term Comparison

Compare two Japanese words to understand their differences and similarities.

**How to Compare Terms**:
1. Select the first word by clicking on it
2. Hold Ctrl (or Cmd on Mac) and click on a second word
3. Look for comparison options in the interface
4. View AI-generated analysis of the differences

### 3. Search Information Panel

The bottom panel shows statistics about your current view.

**Information Displayed**:
- **Total Nodes**: Number of words currently visible
- **Total Links**: Number of connections shown
- **Search Term**: What you're currently searching for
- **Search Field**: Which attribute you're searching by

## Tips for Effective Use

### 1. Start with Simple Searches
- Begin with basic vocabulary words you know
- Use the JLPT N5 level to find beginner-friendly words
- Explore connections from familiar words

### 2. Use Multiple Search Methods
- Try searching by kanji, hiragana, and English translation
- Use POS search to find words of a specific type
- Combine searches to narrow down results

### 3. Explore Connections
- Click on nodes to see related words
- Follow interesting connections to discover new vocabulary
- Use the neighbors panel to find similar words

### 4. Leverage AI Features
- Use AI explanations for complex words
- Generate exercises for words you want to practice
- Compare similar words to understand nuances

### 5. Use Wikidata for Context
- Access cultural and historical information
- Understand word origins and usage
- Explore related concepts and categories

## Troubleshooting

### Common Issues

**Graph Not Loading**:
- Check your internet connection
- Refresh the page
- Ensure the application server is running

**Search Not Working**:
- Verify you've selected the correct search attribute
- Try different search terms
- Check if "Exact Match" is enabled/disabled as needed

**AI Features Not Responding**:
- Wait a few seconds for AI responses
- Check if you have a valid Gemini API key configured
- Try refreshing the page

**Performance Issues**:
- Reduce the search depth to 1 or 2
- Close other browser tabs
- Try a different browser

### Getting Help

If you encounter issues:
1. Check the browser console for error messages
2. Restart the application server
3. Clear your browser cache
4. Check the project documentation for known issues

## Croatian Language Support

The application also supports Croatian vocabulary exploration with similar features:

**Croatian Search Attributes**:
- **Natuknica**: Dictionary headword
- **Normalized**: Normalized form of the word
- **Definition**: Croatian definition
- **POS**: Part of speech
- **UPOS**: Universal part of speech
- **Translation**: English translation

**Croatian Features**:
- Interactive 3D graph visualization
- AI-powered analysis and exercises
- Node information display
- Search functionality

To use Croatian features, simply select "🇭🇷 Croatian" from the language dropdown and explore Croatian vocabulary in the same way as Japanese.

## Conclusion

The Japanese Lexical Graph provides a powerful tool for exploring Japanese vocabulary through interactive visualization and AI-powered analysis. Whether you're a beginner learning basic vocabulary or an advanced learner exploring complex semantic relationships, the application offers valuable insights into the Japanese language.

Start with simple searches, explore connections, and use the AI features to deepen your understanding of Japanese vocabulary and its relationships.
