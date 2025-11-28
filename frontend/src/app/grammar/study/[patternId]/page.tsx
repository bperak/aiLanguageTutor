"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { 
  ArrowLeft, 
  Volume2, 
  Target, 
  Users, 
  CheckCircle,
  Circle,
  Play,
  RotateCcw,
  ChevronDown,
  ChevronUp,
  Settings as SettingsIcon
} from 'lucide-react';

import { apiGet, apiPost } from '@/lib/api';
import { recordStudyWithSRS, getUserPatternProgress, getPatternSRSData, type PatternProgress } from '@/lib/api/grammar-progress';
import { 
  getConversationContexts, 
  startConversationPractice, 
  sendConversationMessage,
  type ConversationContext,
  type ConversationScenario,
  type DialogueTurn
} from '@/lib/api/conversation-practice';

interface GrammarPattern {
  id: string;
  sequence_number: number;
  pattern: string;
  pattern_romaji: string;
  textbook_form: string;
  textbook_form_romaji: string;
  example_sentence: string;
  example_romaji: string;
  classification: string;
  textbook: string;
  topic: string;
  lesson: string;
  jfs_category: string;
}

interface SimilarPattern {
  pattern: string;
  pattern_romaji: string;
  example_sentence: string;
  textbook: string;
  similarity_reason: string;
}

interface PracticeQuestion {
  id: string;
  type: 'multiple_choice' | 'fill_blank' | 'translation' | 'transformation' | 'error_correction';
  question: string;
  options?: string[];
  correctAnswer: number | string;
  explanation: string;
  difficulty: 'basic' | 'intermediate' | 'advanced';
  hint?: string;
}

interface GrammarOverviewExample {
  jp: string;
  romaji?: string;
  en?: string;
}

interface GrammarOverview {
  what_is: string;
  usage: string;
  cultural_context?: string;
  examples: GrammarOverviewExample[];
  tips?: string;
  related_patterns?: string[];
  model_used?: string;
  generated_at?: string;
}

export default function GrammarStudyPage() {
  const params = useParams();
  const router = useRouter();
  const patternId = params.patternId as string;

  const [pattern, setPattern] = useState<GrammarPattern | null>(null);
  const [similarPatterns, setSimilarPatterns] = useState<SimilarPattern[]>([]);
  const [prerequisites, setPrerequisites] = useState<GrammarPattern[]>([]);
  const [overview, setOverview] = useState<GrammarOverview | null>(null);
  const [overviewLoading, setOverviewLoading] = useState<boolean>(false);
  const [overviewGenerating, setOverviewGenerating] = useState<boolean>(false);
  const [practiceQuestions, setPracticeQuestions] = useState<PracticeQuestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // AI generation settings
  const [showSettings, setShowSettings] = useState<boolean>(false);
  const [aiProvider, setAiProvider] = useState<'openai' | 'gemini'>(() => {
    if (typeof window === 'undefined') return 'openai';
    return (localStorage.getItem('aiProvider') as 'openai' | 'gemini') || 'openai';
  });
  const [aiModel, setAiModel] = useState<string>(() => {
    if (typeof window === 'undefined') return 'gpt-4o';
    return localStorage.getItem('aiModel') || 'gpt-4o';
  });
  
  // Progress tracking state
  const [patternProgress, setPatternProgress] = useState<PatternProgress | null>(null);
  const [studyStartTime, setStudyStartTime] = useState<number | null>(null);
  
  // Practice state
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState<number | null>(null);
  const [showExplanation, setShowExplanation] = useState(false);
  const [practiceScore, setPracticeScore] = useState({ correct: 0, total: 0 });
  const [practiceComplete, setPracticeComplete] = useState(false);

  // AI Conversation state
  const [conversationContexts, setConversationContexts] = useState<ConversationContext[]>([]);
  const [selectedContext, setSelectedContext] = useState<string>('');
  const [conversationScenario, setConversationScenario] = useState<ConversationScenario | null>(null);
  const [conversationHistory, setConversationHistory] = useState<DialogueTurn[]>([]);
  const [userMessage, setUserMessage] = useState('');
  const [conversationLoading, setConversationLoading] = useState(false);
  const [conversationStarted, setConversationStarted] = useState(false);
  const [collapsedFeedback, setCollapsedFeedback] = useState<Set<number | string>>(new Set());
  const [showCustomScenario, setShowCustomScenario] = useState(false);
  const [customScenarioText, setCustomScenarioText] = useState('');

  const loadPatternData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      setStudyStartTime(Date.now());

      // Load pattern details, similar patterns, prerequisites, and progress in parallel
      const [patternData, similarData, prerequisitesData, progressData] = await Promise.all([
        apiGet<GrammarPattern>(`/api/v1/grammar/patterns/${patternId}`),
        apiGet<SimilarPattern[]>(`/api/v1/grammar/patterns/${patternId}/similar?limit=5`),
        apiGet<GrammarPattern[]>(`/api/v1/grammar/patterns/${patternId}/prerequisites`),
        getUserPatternProgress({ pattern_ids: [patternId], limit: 1 }).catch(() => [])
      ]);

      setPattern(patternData);
      setSimilarPatterns(similarData);
      setPrerequisites(prerequisitesData);
      setPatternProgress(progressData.length > 0 ? progressData[0] : null);
      // Load AI overview (if already generated)
      await loadOverview(patternId);
      
      // Generate practice questions with realistic alternatives
      await generatePracticeQuestions(patternData);

    } catch (error: unknown) {
      console.error('Error loading pattern data:', error);
      if ((error as {response?: {status?: number}})?.response?.status === 401) {
        router.push('/login');
        return;
      }
      if ((error as {response?: {status?: number}})?.response?.status === 404) {
        setError('Grammar pattern not found');
      } else {
        setError('Failed to load pattern data');
      }
    } finally {
      setLoading(false);
    }
  }, [patternId, router]);

  useEffect(() => {
    if (patternId) {
      loadPatternData();
      loadConversationContexts();
    }
  }, [patternId, loadPatternData]);

  // Persist AI settings
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('aiProvider', aiProvider);
      localStorage.setItem('aiModel', aiModel);
    }
  }, [aiProvider, aiModel]);

  const loadConversationContexts = async () => {
    try {
      const contexts = await getConversationContexts();
      setConversationContexts(contexts);
      if (contexts.length > 0) {
        setSelectedContext(contexts[0].value);
        // Try auto-start conversation with default context (introduction - most versatile)
        const defaultContext = contexts.find(c => c.value === 'introduction') || contexts[0];
        setSelectedContext(defaultContext.value);
        await autoStartConversation(defaultContext.value);
      }
    } catch (error) {
      console.error('Error loading conversation contexts:', error);
    }
  };

  const loadOverview = async (id: string) => {
    try {
      setOverviewLoading(true);
      const data = await apiGet<GrammarOverview>(`/api/v1/grammar/patterns/${id}/ai-overview`);
      setOverview(data);
    } catch (e: any) {
      // 404 means not generated yet; keep null overview
      if (e?.response?.status !== 404) {
        console.error('Failed to load AI overview:', e);
      }
      setOverview(null);
    } finally {
      setOverviewLoading(false);
    }
  };

  const generateOverview = async () => {
    if (!pattern) return;
    try {
      setOverviewGenerating(true);
      const data = await apiPost<GrammarOverview>(
        `/api/v1/grammar/patterns/${pattern.id}/ai-overview`,
        {},
        undefined,
        { params: { provider: aiProvider, model: aiModel, force: false } }
      );
      setOverview(data);
    } catch (e) {
      console.error('Failed to generate AI overview:', e);
    } finally {
      setOverviewGenerating(false);
    }
  };

  const regenerateOverview = async () => {
    if (!pattern) return;
    try {
      setOverviewGenerating(true);
      const data = await apiPost<GrammarOverview>(
        `/api/v1/grammar/patterns/${pattern.id}/ai-overview`,
        {},
        undefined,
        { params: { provider: aiProvider, model: aiModel, force: true } }
      );
      setOverview(data);
    } catch (e) {
      console.error('Failed to regenerate AI overview:', e);
    } finally {
      setOverviewGenerating(false);
    }
  };

  const autoStartConversation = async (context: string, customScenario?: string) => {
    if (!pattern) {
      console.log('Auto-start skipped: no pattern loaded yet');
      return;
    }
    
    try {
      setConversationLoading(true);
      console.log('Auto-starting conversation with context:', context, 'custom:', !!customScenario);
      
      const requestData = {
        pattern_id: pattern.id,
        context: context,
        difficulty_level: 'intermediate',
        custom_scenario: customScenario || undefined
      };
      
      const scenario = await startConversationPractice(requestData);
      console.log('Scenario created:', scenario);
      
      setConversationScenario(scenario);
      
      // Use backend-generated initial message with full meta structure
      // The backend now returns a single initial message with transliteration, translation, and feedback
      const dialogueHistory = scenario.initial_dialogue.length > 0 
        ? [...scenario.initial_dialogue]
        : [];
      
      setConversationHistory(dialogueHistory);
      setConversationStarted(true);
      console.log('Auto-start successful, conversation started with meta message structure');
    } catch (error) {
      console.error('Error auto-starting conversation:', error);
      // On error, fall back to manual start
      setConversationStarted(false);
    } finally {
      setConversationLoading(false);
    }
  };

  const generatePracticeQuestions = async (pattern: GrammarPattern) => {
    try {
      // Get similar patterns to use as realistic distractors
      const similarData = await apiGet<SimilarPattern[]>(`/api/v1/grammar/patterns/${pattern.id}/similar?limit=6`);
      
      const questions: PracticeQuestion[] = [];
      
      // 1. BASIC: Pattern Recognition (Multiple Choice)
      questions.push({
        id: '1',
        type: 'multiple_choice',
        difficulty: 'basic',
        question: `Which sentence correctly uses "${pattern.pattern}"?`,
        options: [
          pattern.example_sentence,
          ...(similarData.slice(0, 3).map(similar => similar.example_sentence))
        ].slice(0, 4),
        correctAnswer: 0,
        explanation: `✅ Correct: ${pattern.example_sentence} (${pattern.example_romaji})\n\nThis pattern "${pattern.pattern}" is used for ${pattern.classification.toLowerCase()}.`,
        hint: `Look for the pattern "${pattern.pattern}" in the sentence.`
      });

      // 2. BASIC: Fill in the Blank
      const blankSentence = pattern.example_sentence.replace(new RegExp(pattern.pattern.replace(/[～〜]/g, ''), 'g'), '____');
      if (blankSentence !== pattern.example_sentence) {
        questions.push({
        id: '2',
          type: 'fill_blank',
          difficulty: 'basic',
          question: `Fill in the blank: ${blankSentence}`,
        options: [
            pattern.pattern.replace(/[～〜]/g, ''),
            ...(similarData.slice(0, 3).map(similar => similar.pattern.replace(/[～〜]/g, '')))
          ].slice(0, 4),
        correctAnswer: 0,
          explanation: `✅ The correct answer is "${pattern.pattern.replace(/[～〜]/g, '')}".\n\n${pattern.example_sentence} (${pattern.example_romaji})`,
          hint: `This pattern is used for ${pattern.classification.toLowerCase()}.`
        });
      }

      // 3. INTERMEDIATE: Translation Challenge
      questions.push({
        id: '3',
        type: 'translation',
        difficulty: 'intermediate',
        question: `How would you say "I am Carla" in Japanese using the pattern "${pattern.pattern}"?`,
        options: [
          pattern.example_sentence,
          '私がカーラです',
          '私のカーラです', 
          'カーラは私です'
        ],
        correctAnswer: 0,
        explanation: `✅ ${pattern.example_sentence} (${pattern.example_romaji})\n\nThe pattern "${pattern.pattern}" is the correct way to express identity/description.`,
        hint: 'Think about the word order: [Subject] は [Object/Description] です'
      });

      // 4. INTERMEDIATE: Context Selection
      questions.push({
        id: '4',
        type: 'multiple_choice',
        difficulty: 'intermediate',
        question: `In which situation would you most likely use "${pattern.pattern}"?`,
        options: [
          'Self-introduction / Describing someone',
          'Asking for directions',
          'Ordering food',
          'Expressing feelings'
        ],
        correctAnswer: 0,
        explanation: `✅ "${pattern.pattern}" is primarily used for self-introduction and describing people or things.\n\nClassification: ${pattern.classification}`,
        hint: `Consider what "${pattern.pattern}" means: [Topic] は [Description] です`
      });

      // 5. ADVANCED: Error Correction
      questions.push({
        id: '5',
        type: 'error_correction',
        difficulty: 'advanced',
        question: 'Which sentence has an error in using the pattern?',
        options: [
          '私がカーラはです', // Wrong: mixed が and は
          pattern.example_sentence, // Correct
          '田中さんは先生です', // Correct usage
          'これは本です' // Correct usage
        ],
        correctAnswer: 0,
        explanation: `❌ "私がカーラはです" is incorrect because it mixes が and は particles.\n\n✅ Correct: Use either "私がカーラです" or "私はカーラです" but not both particles together.`,
        hint: 'Look for incorrect particle usage with は and が.'
      });

      // 6. ADVANCED: Transformation
      questions.push({
        id: '6',
        type: 'transformation',
        difficulty: 'advanced',
        question: `How would you make "${pattern.example_sentence}" into a question?`,
        options: [
          '私はカーラですか？',
          '私はカーラです？',
          'カーラですか私は？',
          '私？カーラです？'
        ],
        correctAnswer: 0,
        explanation: `✅ Add "か" to make it a question: ${pattern.example_sentence.replace('。', '')}か？\n\nThis transforms the statement into "Am I Carla?" or when asking someone else "Are you Carla?"`,
        hint: 'In Japanese, add "か" at the end to form questions.'
      });

      // 7. ADVANCED: Formal vs Casual
      questions.push({
        id: '7',
        type: 'multiple_choice', 
        difficulty: 'advanced',
        question: 'What is the casual form of "私はカーラです"?',
        options: [
          '私、カーラ',
          '私はカーラる',
          '私がカーラだ',
          'カーラは私だ'
        ],
        correctAnswer: 0,
        explanation: `✅ In casual conversation: "私、カーラ" (dropping particles and です)\n\nOther options:\n・私がカーラだ (possible but less common)\n・カーラは私だ (reverses meaning: "Carla is me")`,
        hint: 'In casual speech, particles and です are often dropped.'
      });

      // 8. ADVANCED: Nuanced Usage
      questions.push({
        id: '8',
        type: 'multiple_choice',
        difficulty: 'advanced', 
        question: `What's the difference between "私はカーラです" and "私がカーラです"?`,
        options: [
          'は: general statement, が: emphasis/contrast',
          'は: question, が: statement', 
          'は: casual, が: formal',
          'No difference in meaning'
        ],
        correctAnswer: 0,
        explanation: `✅ は (wa): General statement "I am Carla"\nが (ga): Emphasis "I (specifically) am Carla" or answering "who"\n\nExample:\n・誰がカーラですか？→ 私がカーラです (I am the one who is Carla)\n・私はカーラです (General self-introduction)`,
        hint: 'Think about は for topics and が for emphasis/subjects.'
      });
    
    setPracticeQuestions(questions);
    } catch (error) {
      console.error('Error generating practice questions:', error);
      // Simplified fallback
      const fallbackQuestions: PracticeQuestion[] = [
        {
          id: '1',
          type: 'multiple_choice',
          difficulty: 'basic',
          question: `Which is the correct example of "${pattern.pattern}"?`,
          options: [pattern.example_sentence, 'Wrong example', 'Another wrong example', 'Incorrect usage'],
          correctAnswer: 0,
          explanation: `Correct: ${pattern.example_sentence} (${pattern.example_romaji})`
        }
      ];
      setPracticeQuestions(fallbackQuestions);
    }
  };

  const handlePlayAudio = (text: string) => {
    // TODO: Implement text-to-speech
    console.log('Play audio for:', text);
  };

  const handleAnswerSelect = (answerIndex: number) => {
    setSelectedAnswer(answerIndex);
  };

  const handleSubmitAnswer = () => {
    if (selectedAnswer === null) return;
    
    const currentQuestion = practiceQuestions[currentQuestionIndex];
    const isCorrect = selectedAnswer === currentQuestion.correctAnswer;
    
    if (isCorrect) {
      setPracticeScore(prev => ({ ...prev, correct: prev.correct + 1, total: prev.total + 1 }));
    } else {
      setPracticeScore(prev => ({ ...prev, total: prev.total + 1 }));
    }
    
    setShowExplanation(true);
  };

  const handleNextQuestion = () => {
    if (currentQuestionIndex < practiceQuestions.length - 1) {
      setCurrentQuestionIndex(prev => prev + 1);
      setSelectedAnswer(null);
      setShowExplanation(false);
    } else {
      handlePracticeComplete();
    }
  };

  const handleRestartPractice = () => {
    setCurrentQuestionIndex(0);
    setSelectedAnswer(null);
    setShowExplanation(false);
    setPracticeScore({ correct: 0, total: 0 });
    setPracticeComplete(false);
  };

  const handleSRSGrading = async (grade: 'again' | 'hard' | 'good' | 'easy') => {
    if (!pattern || !studyStartTime) return;

    try {
      const studyTimeSeconds = Math.floor((Date.now() - studyStartTime) / 1000);
      const confidence = getConfidenceFromGrade(grade);

      const updatedProgress = await recordStudyWithSRS(
        pattern.id,
        grade,
        studyTimeSeconds,
        confidence
      );

      setPatternProgress(updatedProgress);
      
      // Show success feedback
      console.log('Study session recorded successfully');
      
    } catch (error) {
      console.error('Error recording study session:', error);
      // Show error feedback to user
    }
  };

  const getConfidenceFromGrade = (grade: 'again' | 'hard' | 'good' | 'easy'): number => {
    const gradeMap = {
      'again': 1,
      'hard': 2,
      'good': 4,
      'easy': 5
    };
    return gradeMap[grade];
  };

  const handlePracticeComplete = async () => {
    setPracticeComplete(true);
    
    // Note: We no longer auto-grade, letting users choose their own SRS rating
    // This promotes self-assessment and gives learners control over their pace
  };

  // AI Conversation handlers
  const handleStartConversation = async (context?: string, customScenario?: string) => {
    if (!pattern) return;
    
    const contextToUse = context || selectedContext;
    if (!contextToUse && !customScenario) return;
    
    try {
      setConversationLoading(true);
      
      const requestData = {
        pattern_id: pattern.id,
        context: contextToUse || 'introduction',
        difficulty_level: 'intermediate',
        custom_scenario: customScenario || undefined
      };
      
      const scenario = await startConversationPractice(requestData);
      
      setConversationScenario(scenario);
      
      // Ensure conversation always starts with AI greeting
      // Use backend-generated initial message with full meta structure
      const dialogueHistory = scenario.initial_dialogue.length > 0 
        ? [...scenario.initial_dialogue]
        : [];
      
      setConversationHistory(dialogueHistory);
      setConversationStarted(true);
      setShowCustomScenario(false);
      setCustomScenarioText('');
    } catch (error) {
      console.error('Error starting conversation:', error);
    } finally {
      setConversationLoading(false);
    }
  };

  const handleSendMessage = async () => {
    if (!userMessage.trim() || !conversationScenario) return;
    
    try {
      setConversationLoading(true);
      
      // Add user message to history
      const userTurn: DialogueTurn = {
        speaker: 'user',
        message: userMessage.trim()
      };
      
      const newHistory = [...conversationHistory, userTurn];
      setConversationHistory(newHistory);
      
      // Get AI response
      const aiResponse = await sendConversationMessage({
        scenario_id: conversationScenario.scenario_id,
        user_message: userMessage.trim()
      });
      
      setConversationHistory([...newHistory, aiResponse]);
      setUserMessage('');
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      setConversationLoading(false);
    }
  };

  const handleResetConversation = () => {
    setConversationScenario(null);
    setConversationHistory([]);
    setConversationStarted(false);
    setUserMessage('');
    setCollapsedFeedback(new Set());
  };

  const toggleFeedbackCollapse = (turnIndex: number | string) => {
    const newCollapsed = new Set(collapsedFeedback);
    if (newCollapsed.has(turnIndex)) {
      newCollapsed.delete(turnIndex);
    } else {
      newCollapsed.add(turnIndex);
    }
    setCollapsedFeedback(newCollapsed);
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-muted-foreground">Loading pattern details...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error || !pattern) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card>
          <CardContent className="text-center py-12">
            <div className="text-red-500 mb-4">
              <Circle className="w-12 h-12 mx-auto" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              {error || 'Pattern not found'}
            </h3>
            <p className="text-muted-foreground mb-4">
              The requested grammar pattern could not be loaded.
            </p>
            <Button onClick={() => router.push('/grammar')}>
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Grammar
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const currentQuestion = practiceQuestions[currentQuestionIndex];
  const practiceProgress = ((currentQuestionIndex + (showExplanation ? 1 : 0)) / practiceQuestions.length) * 100;

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-3">
          <Button 
            variant="ghost" 
            onClick={() => router.push('/grammar')}
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Grammar
          </Button>

          <div className="relative">
            <Button variant="outline" size="sm" onClick={() => setShowSettings(prev => !prev)}>
              <SettingsIcon className="w-4 h-4 mr-2" />
              Settings
            </Button>
          </div>
        </div>

        {showSettings && (
          <div className="mb-4 border rounded-md p-3 bg-gray-50">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 items-end">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Provider</label>
                <select
                  value={aiProvider}
                  onChange={(e) => {
                    const p = e.target.value as 'openai' | 'gemini';
                    setAiProvider(p);
                    // Set default model per provider
                    setAiModel(p === 'openai' ? 'gpt-4o' : 'gemini-2.5-flash');
                  }}
                  className="w-full border rounded-md p-2 text-sm"
                >
                  <option value="openai">OpenAI</option>
                  <option value="gemini">Gemini</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Model</label>
                <select
                  value={aiModel}
                  onChange={(e) => setAiModel(e.target.value)}
                  className="w-full border rounded-md p-2 text-sm"
                >
                  {aiProvider === 'openai' ? (
                    <>
                      <option value="gpt-4o">gpt-4o</option>
                      <option value="gpt-4o-mini">gpt-4o-mini</option>
                      <option value="gpt-4.5">gpt-4.5</option>
                    </>
                  ) : (
                    <>
                      <option value="gemini-2.5-flash">gemini-2.5-flash</option>
                      <option value="gemini-2.5-pro">gemini-2.5-pro</option>
                    </>
                  )}
                </select>
              </div>
              <div className="flex gap-2">
                <Button onClick={generateOverview} disabled={overviewGenerating} className="flex-1">
                  {overviewGenerating ? 'Working…' : 'Generate with Model'}
                </Button>
                <Button onClick={regenerateOverview} disabled={overviewGenerating} variant="outline" className="flex-1">
                  {overviewGenerating ? 'Working…' : 'Regenerate'}
                </Button>
              </div>
            </div>
          </div>
        )}

        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h1
              className="text-2xl md:text-3xl font-bold text-gray-900 mb-2 flex items-center gap-3 leading-tight"
              style={{
                display: '-webkit-box',
                WebkitLineClamp: 2,
                WebkitBoxOrient: 'vertical' as any,
                overflow: 'hidden'
              }}
            >
              {pattern.pattern}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handlePlayAudio(pattern.pattern)}
                className="p-2"
              >
                <Volume2 className="w-5 h-5" />
              </Button>
            </h1>
            <p className="text-xl text-muted-foreground italic mb-2">{pattern.pattern_romaji}</p>
            <div className="flex items-center gap-2">
              <Badge className="bg-blue-100 text-blue-800">{pattern.textbook}</Badge>
              <Badge variant="outline">{pattern.classification}</Badge>
              <Badge variant="outline">{pattern.jfs_category}</Badge>
            </div>
          </div>
          
          {/* SRS Progress Display */}
          {patternProgress && (
            <div className="flex flex-col items-end gap-2">
              <div className="flex items-center gap-2">
                <Target className="w-4 h-4 text-blue-600" />
                <span className="text-sm font-medium">Mastery Level {patternProgress.mastery_level}/5</span>
              </div>
              <Progress value={(patternProgress.mastery_level / 5) * 100} className="w-24 h-2" />
              {patternProgress.next_review_date && (
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <CheckCircle className="w-3 h-3" />
                  <span>Next review: {new Date(patternProgress.next_review_date).toLocaleDateString()}</span>
                </div>
              )}
              <div className="text-xs text-muted-foreground">
                Studies: {patternProgress.study_count}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Study Content */}
      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="similar">Similar Patterns</TabsTrigger>
          <TabsTrigger value="prerequisites">Prerequisites</TabsTrigger>
          <TabsTrigger value="practice">Practice</TabsTrigger>
          <TabsTrigger value="conversation">🤖 AI Chat</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          <Card className="bg-gradient-to-br from-sky-50 to-indigo-50 border-sky-100">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-sky-900">AI Overview</CardTitle>
              {overview && (
                <Button size="sm" variant="outline" onClick={regenerateOverview} disabled={overviewGenerating}>
                  {overviewGenerating ? 'Working…' : 'Regenerate'}
                </Button>
              )}
            </CardHeader>
            <CardContent className="space-y-5">
              {overviewLoading ? (
                <p className="text-sm text-sky-700">Generating overview...</p>
              ) : overview ? (
                <div className="space-y-5">
                  <div className="bg-white/80 backdrop-blur rounded-lg p-4 border border-sky-100">
                    <h3 className="font-semibold text-sky-900 mb-1">What is it?</h3>
                    <p className="text-sky-800 leading-relaxed">{overview.what_is}</p>
                  </div>
                  <div className="bg-white/80 backdrop-blur rounded-lg p-4 border border-indigo-100">
                    <h3 className="font-semibold text-indigo-900 mb-1">Usage</h3>
                    <p className="text-indigo-800 leading-relaxed whitespace-pre-line">{overview.usage}</p>
                  </div>
                  {overview.cultural_context && (
                    <div className="bg-white/80 backdrop-blur rounded-lg p-4 border border-amber-100">
                      <h3 className="font-semibold text-amber-900 mb-1">Cultural Context</h3>
                      <p className="text-amber-800 leading-relaxed">{overview.cultural_context}</p>
                    </div>
                  )}
                  {overview.examples?.length > 0 && (
                    <div className="bg-white/80 backdrop-blur rounded-lg p-4 border border-emerald-100">
                      <h3 className="font-semibold text-emerald-900 mb-3">Examples</h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {overview.examples.slice(0, 6).map((ex, idx) => (
                          <div key={idx} className="rounded-md border border-emerald-100 p-3">
                            <p className="text-gray-900 font-medium">{ex.jp}</p>
                            {ex.romaji && <p className="text-xs text-emerald-700 italic">{ex.romaji}</p>}
                            {ex.en && <p className="text-xs text-gray-600">{ex.en}</p>}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {overview.tips && (
                    <div className="bg-white/80 backdrop-blur rounded-lg p-4 border border-purple-100">
                      <h3 className="font-semibold text-purple-900 mb-1">Tips</h3>
                      <p className="text-purple-800 leading-relaxed">{overview.tips}</p>
                    </div>
                  )}
                  {overview.related_patterns && overview.related_patterns.length > 0 && (
                    <div className="bg-white/80 backdrop-blur rounded-lg p-4 border border-blue-100">
                      <h3 className="font-semibold text-blue-900 mb-2">Related Patterns</h3>
                      <div className="flex flex-wrap gap-2">
                        {overview.related_patterns.map((rp, i) => (
                          <a
                            key={i}
                            href={`/grammar/study/${encodeURIComponent(rp)}`}
                            className="text-xs px-2 py-1 rounded-full bg-blue-50 text-blue-800 border border-blue-200 hover:bg-blue-100"
                            title={`Open ${rp}`}
                          >
                            {rp}
                          </a>
                        ))}
                      </div>
                    </div>
                  )}
                  <p className="text-xs text-sky-700">
                    Generated by {overview.model_used || 'AI'} on {overview.generated_at ? new Date(overview.generated_at).toLocaleString() : 'this session'}
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  <p className="text-sm text-sky-700">No AI overview yet for this pattern.</p>
                  <Button onClick={generateOverview} disabled={overviewGenerating} className="bg-sky-600 hover:bg-sky-700">
                    {overviewGenerating ? 'Generating…' : 'Generate Overview'}
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Pattern Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <h3 className="font-semibold text-gray-900 mb-2">Textbook Form</h3>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <p className="text-lg font-medium">{pattern.textbook_form}</p>
                  <p className="text-muted-foreground italic">{pattern.textbook_form_romaji}</p>
                </div>
              </div>
              
              <div>
                <h3 className="font-semibold text-gray-900 mb-2">Example Sentence</h3>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <p className="text-lg">{pattern.example_sentence}</p>
                  <p className="text-muted-foreground italic mt-1">{pattern.example_romaji}</p>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handlePlayAudio(pattern.example_sentence)}
                    className="mt-2"
                  >
                    <Volume2 className="w-4 h-4 mr-2" />
                    Play Audio
                  </Button>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h3 className="font-semibold text-gray-900 mb-2">Topic</h3>
                  <p className="text-muted-foreground">{pattern.topic}</p>
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 mb-2">Lesson</h3>
                  <p className="text-muted-foreground">{pattern.lesson}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Similar Patterns Tab */}
        <TabsContent value="similar" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Users className="w-5 h-5" />
                Similar Patterns
              </CardTitle>
            </CardHeader>
            <CardContent>
              {similarPatterns.length > 0 ? (
                <div className="space-y-4">
                  {similarPatterns.map((similar, index) => (
                    <div key={index} className="border rounded-lg p-4">
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <h4 className="font-semibold">{similar.pattern}</h4>
                          <p className="text-muted-foreground italic text-sm">{similar.pattern_romaji}</p>
                        </div>
                        <Badge variant="outline">{similar.textbook}</Badge>
                      </div>
                      <p className="text-sm mb-2">{similar.example_sentence}</p>
                      <p className="text-xs text-muted-foreground">{similar.similarity_reason}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <Users className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                  <p className="text-muted-foreground">No similar patterns found</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Prerequisites Tab */}
        <TabsContent value="prerequisites" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Target className="w-5 h-5" />
                Prerequisites
              </CardTitle>
            </CardHeader>
            <CardContent>
              {prerequisites.length > 0 ? (
                <div className="space-y-4">
                  {prerequisites.map((prereq) => (
                    <div key={prereq.id} className="border rounded-lg p-4">
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <h4 className="font-semibold">{prereq.pattern}</h4>
                          <p className="text-muted-foreground italic text-sm">{prereq.pattern_romaji}</p>
                        </div>
                        <Badge variant="outline">{prereq.textbook}</Badge>
                      </div>
                      <p className="text-sm mb-2">{prereq.example_sentence}</p>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => router.push(`/grammar/study/${prereq.id}`)}
                      >
                        Study This First
                      </Button>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
                  <p className="text-muted-foreground">No prerequisites needed</p>
                  <p className="text-sm text-muted-foreground">You can start studying this pattern directly</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Practice Tab */}
        <TabsContent value="practice" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Play className="w-5 h-5" />
                Practice Questions
              </CardTitle>
            </CardHeader>
            <CardContent>
              {!practiceComplete ? (
                <div className="space-y-6">
                  {/* Progress */}
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>Question {currentQuestionIndex + 1} of {practiceQuestions.length}</span>
                      <span>Score: {practiceScore.correct}/{practiceScore.total}</span>
                    </div>
                    <Progress value={practiceProgress} className="w-full" />
                  </div>

                  {/* Current Question */}
                  {currentQuestion && (
                    <div className="space-y-4">
                      {/* Question Header with Difficulty */}
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-3">
                            <Badge variant={
                              currentQuestion.difficulty === 'basic' ? 'default' :
                              currentQuestion.difficulty === 'intermediate' ? 'secondary' : 'outline'
                            }>
                              {currentQuestion.difficulty === 'basic' ? '🟢 Basic' :
                               currentQuestion.difficulty === 'intermediate' ? '🟡 Intermediate' : '🔴 Advanced'}
                            </Badge>
                            <Badge variant="outline">
                              {currentQuestion.type === 'multiple_choice' ? '📝 Multiple Choice' :
                               currentQuestion.type === 'fill_blank' ? '✏️ Fill in Blank' :
                               currentQuestion.type === 'translation' ? '🗣️ Translation' :
                               currentQuestion.type === 'transformation' ? '🔄 Transformation' :
                               currentQuestion.type === 'error_correction' ? '🔍 Error Correction' : 
                               '❓ Question'}
                            </Badge>
                          </div>
                      <h3 className="text-lg font-semibold">{currentQuestion.question}</h3>
                        </div>
                      </div>

                      {/* Hint (if available and no answer shown yet) */}
                      {currentQuestion.hint && !showExplanation && (
                        <div className="bg-amber-50 p-3 rounded-lg border-l-4 border-amber-400">
                          <p className="text-sm text-amber-800">
                            💡 <strong>Hint:</strong> {currentQuestion.hint}
                          </p>
                        </div>
                      )}
                      
                      {/* Answer Options */}
                      {currentQuestion.options && (
                      <div className="space-y-2">
                        {currentQuestion.options.map((option, index) => (
                          <Button
                            key={index}
                            variant={selectedAnswer === index ? "default" : "outline"}
                            className={`w-full text-left justify-start h-auto p-4 ${
                              showExplanation 
                                ? index === currentQuestion.correctAnswer 
                                  ? "bg-green-100 border-green-500 text-green-800" 
                                  : selectedAnswer === index && index !== currentQuestion.correctAnswer
                                    ? "bg-red-100 border-red-500 text-red-800"
                                    : ""
                                : ""
                            }`}
                            onClick={() => !showExplanation && handleAnswerSelect(index)}
                            disabled={showExplanation}
                          >
                              <span className="flex items-center gap-3 w-full">
                                <span className="w-6 h-6 rounded-full bg-gray-200 flex items-center justify-center text-sm font-medium">
                                  {String.fromCharCode(65 + index)}
                                </span>
                                <span className="text-left flex-1">{option}</span>
                                {showExplanation && index === currentQuestion.correctAnswer && (
                                  <CheckCircle className="w-5 h-5 text-green-600" />
                                )}
                              </span>
                          </Button>
                        ))}
                      </div>
                      )}

                      {/* Explanation */}
                      {showExplanation && (
                        <div className="bg-blue-50 p-4 rounded-lg border-l-4 border-blue-400">
                          <h4 className="font-semibold text-blue-900 mb-3 flex items-center gap-2">
                            📚 Explanation
                          </h4>
                          <div className="text-blue-800 whitespace-pre-line leading-relaxed">
                            {currentQuestion.explanation}
                          </div>
                        </div>
                      )}

                      {/* Action Buttons */}
                      <div className="flex justify-between">
                        <div></div>
                        {!showExplanation ? (
                          <Button 
                            onClick={handleSubmitAnswer}
                            disabled={selectedAnswer === null}
                          >
                            Submit Answer
                          </Button>
                        ) : (
                          <Button onClick={handleNextQuestion}>
                            {currentQuestionIndex < practiceQuestions.length - 1 ? 'Next Question' : 'Finish Practice'}
                          </Button>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                /* Practice Complete */
                <div className="text-center space-y-6">
                  <CheckCircle className="w-16 h-16 text-green-500 mx-auto" />
                  <h3 className="text-xl font-semibold">Practice Complete!</h3>
                  
                  {/* Comprehensive Score Display */}
                  <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-6 rounded-lg border border-blue-200">
                    <div className="text-center mb-4">
                      <p className="text-2xl font-bold text-blue-900">
                        {practiceScore.correct}/{practiceScore.total} 
                    ({Math.round((practiceScore.correct / practiceScore.total) * 100)}%)
                  </p>
                      <p className="text-sm text-blue-700 font-medium">
                        {(() => {
                          const scorePercentage = practiceScore.correct / practiceScore.total;
                          if (scorePercentage >= 0.875) return "🏆 Master Level! All drill types conquered!";
                          else if (scorePercentage >= 0.75) return "🎯 Advanced! Great understanding of nuances!";
                          else if (scorePercentage >= 0.625) return "📚 Good progress! Some advanced concepts need work";
                          else if (scorePercentage >= 0.5) return "💪 Keep going! Focus on basic patterns first";
                          else return "🌱 Building foundation! Practice the fundamentals more";
                        })()}
                      </p>
                    </div>

                    {/* Drill Breakdown */}
                    <div className="grid grid-cols-3 gap-4 mt-4 text-center">
                      <div className="bg-green-100 p-3 rounded-md">
                        <div className="text-green-800 font-semibold">🟢 Basic</div>
                        <div className="text-sm text-green-600">
                          {practiceQuestions.slice(0, 2).length > 0 ? 
                            `${practiceQuestions.slice(0, 2).filter((_, idx) => idx < practiceScore.correct).length}/${practiceQuestions.slice(0, 2).length}` 
                            : '0/0'}
                        </div>
                        <div className="text-xs text-green-500">Pattern Recognition</div>
                      </div>
                      <div className="bg-yellow-100 p-3 rounded-md">
                        <div className="text-yellow-800 font-semibold">🟡 Intermediate</div>
                        <div className="text-sm text-yellow-600">
                          {practiceQuestions.slice(2, 4).length > 0 ? 
                            `${Math.max(0, Math.min(practiceScore.correct - 2, 2))}/${practiceQuestions.slice(2, 4).length}` 
                            : '0/0'}
                        </div>
                        <div className="text-xs text-yellow-500">Context & Usage</div>
                      </div>
                      <div className="bg-red-100 p-3 rounded-md">
                        <div className="text-red-800 font-semibold">🔴 Advanced</div>
                        <div className="text-sm text-red-600">
                          {practiceQuestions.slice(4).length > 0 ? 
                            `${Math.max(0, practiceScore.correct - 4)}/${practiceQuestions.slice(4).length}` 
                            : '0/0'}
                        </div>
                        <div className="text-xs text-red-500">Nuances & Errors</div>
                      </div>
                    </div>

                    {/* Drill Types Completed */}
                    <div className="mt-4 text-center">
                      <p className="text-xs text-blue-600 mb-2">✅ Completed Drill Types:</p>
                      <div className="flex flex-wrap justify-center gap-1">
                        <Badge variant="secondary">📝 Multiple Choice</Badge>
                        <Badge variant="secondary">✏️ Fill Blanks</Badge>
                        <Badge variant="secondary">🗣️ Translation</Badge>
                        <Badge variant="secondary">🔄 Transformation</Badge>
                        <Badge variant="secondary">🔍 Error Correction</Badge>
                      </div>
                    </div>
                  </div>
                  
                  {/* SRS Manual Grading with Explanations */}
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <p className="text-sm font-medium mb-4">🎯 How well do you understand this pattern?</p>
                    <div className="grid grid-cols-2 gap-2">
                      <Button
                        onClick={() => handleSRSGrading('again')}
                        variant="outline"
                        size="sm"
                        className="text-red-600 hover:bg-red-50 h-auto p-3 flex-col"
                      >
                        <span className="font-medium">Need More Practice</span>
                        <span className="text-xs mt-1">Review in 1 day</span>
                      </Button>
                      <Button
                        onClick={() => handleSRSGrading('hard')}
                        variant="outline"
                        size="sm"
                        className="text-orange-600 hover:bg-orange-50 h-auto p-3 flex-col"
                      >
                        <span className="font-medium">Challenging</span>
                        <span className="text-xs mt-1">Review in 3 days</span>
                      </Button>
                      <Button
                        onClick={() => handleSRSGrading('good')}
                        variant="outline"
                        size="sm"
                        className="text-blue-600 hover:bg-blue-50 h-auto p-3 flex-col"
                      >
                        <span className="font-medium">Good</span>
                        <span className="text-xs mt-1">Review in 1 week</span>
                      </Button>
                      <Button
                        onClick={() => handleSRSGrading('easy')}
                        variant="outline"
                        size="sm"
                        className="text-green-600 hover:bg-green-50 h-auto p-3 flex-col"
                      >
                        <span className="font-medium">Too Easy</span>
                        <span className="text-xs mt-1">Review in 2+ weeks</span>
                      </Button>
                    </div>
                    <div className="mt-3 p-3 bg-blue-50 rounded-md">
                      <p className="text-xs text-blue-800">
                        <strong>Spaced Repetition System (SRS):</strong> Your choice determines when you'll see this pattern again. 
                        Choose honestly to optimize your learning schedule!
                      </p>
                    </div>
                  </div>

                  <div className="flex justify-center gap-4">
                    <Button onClick={handleRestartPractice} variant="outline">
                      <RotateCcw className="w-4 h-4 mr-2" />
                      Practice Again
                    </Button>
                    <Button onClick={() => router.push('/grammar')}>
                      <ArrowLeft className="w-4 h-4 mr-2" />
                      Back to Grammar
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* AI Conversation Tab */}
        <TabsContent value="conversation" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                🤖 AI Conversation Practice
              </CardTitle>
            </CardHeader>
            <CardContent>
              {conversationLoading && !conversationStarted ? (
                /* Loading State */
                <div className="flex items-center justify-center h-32">
                  <div className="text-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
                    <p className="text-muted-foreground">Starting AI conversation...</p>
                  </div>
                </div>
              ) : !conversationStarted ? (
                /* Fallback Manual Start */
                <div className="space-y-6">
                  <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                    <h3 className="text-blue-800 font-semibold mb-2">🎭 Choose Your Conversation Scenario</h3>
                    <p className="text-blue-700 text-sm">
                      Select a pre-made scenario or create your own custom situation to practice "{pattern?.pattern}"
                    </p>
                  </div>

                  {!showCustomScenario ? (
                    <div className="space-y-4">
                      {/* Pre-made Scenarios */}
                      <div>
                        <h4 className="font-medium mb-3">📋 Pre-made Scenarios</h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          {conversationContexts.map((context) => (
                            <Button
                              key={context.value}
                              variant={selectedContext === context.value ? "default" : "outline"}
                              className="h-auto p-4 flex flex-col items-start text-left"
                              onClick={() => {
                                setSelectedContext(context.value);
                                handleStartConversation(context.value);
                              }}
                            >
                              <span className="font-semibold">{context.label}</span>
                              <span className="text-xs text-muted-foreground mt-1">
                                {context.description}
                              </span>
                            </Button>
                          ))}
                        </div>
                      </div>

                      {/* Custom Scenario Option */}
                      <div className="border-t pt-4">
                        <Button
                          onClick={() => setShowCustomScenario(true)}
                          variant="outline"
                          className="w-full p-4 h-auto flex items-center gap-3 border-2 border-dashed border-gray-300 hover:border-blue-400 hover:bg-blue-50"
                        >
                          <div className="text-2xl">✨</div>
                          <div className="text-left">
                            <div className="font-semibold">Create Custom Scenario</div>
                            <div className="text-xs text-muted-foreground">
                              Describe your own situation for practice
                            </div>
                          </div>
                        </Button>
                      </div>
                    </div>
                  ) : (
                    /* Custom Scenario Input */
                    <div className="space-y-4">
                      <div className="bg-purple-50 p-4 rounded-lg border border-purple-200">
                        <h4 className="font-semibold text-purple-800 mb-3">✨ Create Your Custom Scenario</h4>
                        <p className="text-purple-700 text-sm mb-4">
                          Describe a situation where you'd like to practice using "{pattern?.pattern}". 
                          Be specific about the setting, people involved, and what you want to accomplish.
                        </p>
                        
                        <div className="space-y-3">
                          <textarea
                            value={customScenarioText}
                            onChange={(e) => setCustomScenarioText(e.target.value)}
                            placeholder="Example: I'm at a Japanese coffee shop and want to order a latte and ask the barista about their recommendations. The barista is friendly and wants to practice English, but I want to practice Japanese..."
                            className="w-full p-3 border border-gray-300 rounded-lg resize-none h-24 text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                          />
                          
                          <div className="flex gap-3">
                            <Button
                              onClick={() => handleStartConversation('custom', customScenarioText)}
                              disabled={!customScenarioText.trim() || conversationLoading}
                              className="bg-purple-600 hover:bg-purple-700 text-white flex-1"
                            >
                              {conversationLoading ? (
                                <>
                                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                  Starting...
                                </>
                              ) : (
                                <>🚀 Start Custom Conversation</>
                              )}
                            </Button>
                            <Button
                              onClick={() => {
                                setShowCustomScenario(false);
                                setCustomScenarioText('');
                              }}
                              variant="outline"
                            >
                              Cancel
                            </Button>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                /* Active Conversation */
                <div className="space-y-4">
                  {/* Scenario Info */}
                  {conversationScenario && (
                    <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                      <div className="flex justify-between items-start mb-3">
                        <div>
                          <h4 className="font-semibold text-blue-900">
                            🎭 {conversationScenario.situation}
                          </h4>
                          <p className="text-sm text-blue-700 mt-1">
                            <strong>Your role:</strong> {conversationScenario.user_role}
                          </p>
                          <p className="text-sm text-blue-700">
                            <strong>AI character:</strong> {conversationScenario.ai_character}
                          </p>
                        </div>
                        <Badge variant="outline" className="text-blue-800">
                          {conversationScenario.context} • {conversationScenario.difficulty_level}
                        </Badge>
                      </div>
                      <div className="bg-blue-100 p-3 rounded border-l-4 border-blue-400">
                        <strong>🎯 Learning objective:</strong> {conversationScenario.learning_objective}
                      </div>
                    </div>
                  )}

                  {/* Conversation History */}
                  <div className="bg-gray-50 p-4 rounded-lg max-h-96 overflow-y-auto">
                    <div className="space-y-6">
                      {conversationHistory.map((turn, index) => (
                        <div key={index} className="space-y-2">
                          {/* Conversation Bubble */}
                          <div className={`flex ${turn.speaker === 'user' ? 'justify-end' : 'justify-start'}`}>
                            <div
                              className={`max-w-[80%] p-3 rounded-lg ${
                                turn.speaker === 'user'
                                  ? 'bg-blue-600 text-white rounded-br-sm'
                                  : 'bg-white border border-gray-200 rounded-bl-sm'
                              }`}
                            >
                              <p className="text-sm font-medium mb-2">
                                {turn.speaker === 'user' ? '👤 You' : '🗣️ AI Person'}
                              </p>
                              <p className="text-base font-medium">{turn.message}</p>
                              
                              {/* Transliteration and Translation for AI messages */}
                              {turn.speaker === 'ai' && (turn.transliteration || turn.translation) && (
                                <div className="mt-3 space-y-2 pt-3 border-t border-gray-100">
                                  {turn.transliteration && (
                                    <div className="bg-blue-50 p-2 rounded border-l-4 border-blue-300">
                                      <p className="text-xs font-semibold text-blue-800 mb-1">🔤 Pronunciation (Romaji):</p>
                                      <p className="text-sm text-blue-700 font-mono italic">{turn.transliteration}</p>
                                    </div>
                                  )}
                                  {turn.translation && (
                                    <div className="bg-gray-50 p-2 rounded border-l-4 border-gray-300">
                                      <p className="text-xs font-semibold text-gray-800 mb-1">🌍 English Translation:</p>
                                      <p className="text-sm text-gray-700">{turn.translation}</p>
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          </div>

                          {/* User Input Feedback Panel (directly after user messages) */}
                          {turn.speaker === 'user' && (
                            (() => {
                              // Find the next AI turn that contains user_feedback for this user message
                              const nextAiTurn = conversationHistory
                                .slice(index + 1)
                                .find(nextTurn => nextTurn.speaker === 'ai' && nextTurn.user_feedback);
                              
                              return nextAiTurn?.user_feedback ? (
                                <div className="ml-4 mt-3">
                                  <div className="bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200 rounded-lg overflow-hidden">
                                    {/* Collapsible Header */}
                                    <button
                                      onClick={() => toggleFeedbackCollapse(`user-${index}`)}
                                      className="w-full p-3 text-left flex items-center justify-between hover:bg-green-100 transition-colors"
                                    >
                                      <div className="flex items-center gap-2">
                                        <span className="text-green-800 font-medium text-sm">📝 Your Input Analysis</span>
                                      </div>
                                      {collapsedFeedback.has(`user-${index}`) ? (
                                        <ChevronDown className="h-4 w-4 text-green-600" />
                                      ) : (
                                        <ChevronUp className="h-4 w-4 text-green-600" />
                                      )}
                                    </button>

                                    {/* Collapsible Content */}
                                    {!collapsedFeedback.has(`user-${index}`) && (
                                      <div className="px-3 pb-3">
                                        <div className="bg-white p-3 rounded-lg border-l-4 border-green-400">
                                          <h5 className="font-medium text-green-800 mb-1 text-sm">Grammar & Usage Analysis:</h5>
                                          <p className="text-green-700 text-sm">{nextAiTurn.user_feedback}</p>
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                </div>
                              ) : null;
                            })()
                          )}

                          {/* Teaching Direction Feedback Panel (after AI responses) */}
                          {turn.speaker === 'ai' && (turn.feedback || turn.corrections?.length || turn.hints?.length) && (
                            <div className="ml-4">
                              <div className="bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 rounded-lg overflow-hidden">
                                {/* Collapsible Header */}
                                <button
                                  onClick={() => toggleFeedbackCollapse(index)}
                                  className="w-full p-3 text-left flex items-center justify-between hover:bg-amber-100 transition-colors"
                                >
                                  <div className="flex items-center gap-2">
                                    <span className="text-amber-800 font-medium text-sm">🧑‍🏫 Teaching Direction & Strategy</span>
                                  </div>
                                  {collapsedFeedback.has(index) ? (
                                    <ChevronDown className="h-4 w-4 text-amber-600" />
                                  ) : (
                                    <ChevronUp className="h-4 w-4 text-amber-600" />
                                  )}
                                </button>

                                {/* Collapsible Content */}
                                {!collapsedFeedback.has(index) && (
                                  <div className="px-3 pb-3 space-y-3">
                                    {turn.feedback && (
                                      <div className="bg-white p-3 rounded-lg border-l-4 border-amber-400">
                                        <h5 className="font-medium text-amber-800 mb-1 text-sm">Teaching Strategy:</h5>
                                        <p className="text-amber-700 text-sm">{turn.feedback}</p>
                                      </div>
                                    )}
                                    
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                      {turn.corrections && turn.corrections.length > 0 && (
                                        <div className="bg-red-50 p-3 rounded-lg border-l-4 border-red-400">
                                          <h5 className="font-medium text-red-800 mb-2 flex items-center gap-1 text-sm">
                                            ✏️ Corrections
                                          </h5>
                                          <ul className="text-red-700 text-xs space-y-1">
                                            {turn.corrections.map((correction, i) => (
                                              <li key={i} className="flex items-start gap-1">
                                                <span className="text-red-500 mt-0.5">•</span>
                                                <span>{correction}</span>
                                              </li>
                                            ))}
                                          </ul>
                                        </div>
                                      )}
                                      
                                      {turn.hints && turn.hints.length > 0 && (
                                        <div className="bg-blue-50 p-3 rounded-lg border-l-4 border-blue-400">
                                          <h5 className="font-medium text-blue-800 mb-2 flex items-center gap-1 text-sm">
                                            💡 Learning Tips
                                          </h5>
                                          <ul className="text-blue-700 text-xs space-y-1">
                                            {turn.hints.map((hint, i) => (
                                              <li key={i} className="flex items-start gap-1">
                                                <span className="text-blue-500 mt-0.5">•</span>
                                                <span>{hint}</span>
                                              </li>
                                            ))}
                                          </ul>
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Message Input */}
                  <div className="flex gap-3">
                    <input
                      type="text"
                      value={userMessage}
                      onChange={(e) => setUserMessage(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && !conversationLoading && handleSendMessage()}
                      placeholder="Type your response in Japanese..."
                      className="flex-1 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      disabled={conversationLoading}
                    />
                    <Button
                      onClick={handleSendMessage}
                      disabled={!userMessage.trim() || conversationLoading}
                      className="px-6"
                    >
                      {conversationLoading ? (
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                      ) : (
                        'Send'
                      )}
                    </Button>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex justify-between pt-4 border-t">
                    <Button variant="outline" onClick={handleResetConversation}>
                      <RotateCcw className="w-4 h-4 mr-2" />
                      New Conversation
                    </Button>
                    <Button variant="outline" onClick={() => router.push('/grammar')}>
                      <ArrowLeft className="w-4 h-4 mr-2" />
                      Back to Grammar
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
