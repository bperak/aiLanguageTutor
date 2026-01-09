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
  Settings as SettingsIcon,
  MessageSquare,
  Pencil,
  BookOpen
} from 'lucide-react';
import { apiGet, apiPost } from '@/lib/api';
import {
  recordStudyWithSRS,
  getUserPatternProgress,
  getPatternSRSData,
  type PatternProgress,
  recordGrammarEvidence,
  getGrammarEvidenceSummary,
  type EvidenceSummary
} from '@/lib/api/grammar-progress';
import {
  getConversationContexts,
  startConversationPractice,
  sendConversationMessage,
  type ConversationContext,
  type ConversationScenario,
  type DialogueTurn
} from '@/lib/api/conversation-practice';

// ==================== TYPE DEFINITIONS ====================

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

// Production exercise types
interface ProductionExercise {
  id: string;
  type: 'slot_fill' | 'transformation' | 'personalization';
  prompt: string;
  template?: string;
  expectedPattern: string;
  hints: string[];
  difficulty: 'guided' | 'semi_guided' | 'free';
}

// Learner-first structured types for AI overview
interface JapaneseTextItem {
  jp: string;
  kana: string;
  romaji: string;
  en: string;
}

interface FormationStep {
  slot: string;
  jp?: string;
  kana?: string;
  romaji?: string;
  en?: string;
}

interface HowToForm {
  summary_en: string;
  pattern_template?: string;
  steps: FormationStep[];
  casual_variant?: JapaneseTextItem | null;
  formal_variant?: JapaneseTextItem | null;
  notes_en?: string[];
}

interface CommonMistake {
  mistake_en: string;
  wrong?: JapaneseTextItem | null;
  correct?: JapaneseTextItem | null;
}

interface GrammarOverview {
  what_is_en?: string;
  how_to_form?: HowToForm | null;
  usage_en?: string;
  nuance_en?: string;
  common_mistakes: (CommonMistake | string)[];
  cultural_context_en?: string | null;
  examples: JapaneseTextItem[];
  tips_en?: string;
  related_patterns: string[];
  model_used?: string;
  generated_at?: string;
  // Legacy fields
  what_is?: string;
  formation?: string;
  usage?: string;
  nuance?: string;
  tips?: string;
  cultural_context?: string;
}

// ==================== MAIN COMPONENT ====================

export default function GrammarStudyPage() {
  const params = useParams();
  const router = useRouter();
  const patternId = params.patternId as string;

  // Core data state
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
  const [evidenceSummary, setEvidenceSummary] = useState<EvidenceSummary | null>(null);
  const [showEvidencePanel, setShowEvidencePanel] = useState<boolean>(false);

  // Comprehension practice state
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState<number | null>(null);
  const [showExplanation, setShowExplanation] = useState(false);
  const [practiceScore, setPracticeScore] = useState({ correct: 0, total: 0 });
  const [practiceComplete, setPracticeComplete] = useState(false);

  // Production practice state
  const [productionExercises] = useState<ProductionExercise[]>([]);
  const [currentProductionIndex, setCurrentProductionIndex] = useState(0);
  const [productionInput, setProductionInput] = useState('');
  const [productionFeedback, setProductionFeedback] = useState<string | null>(null);
  const [productionComplete, setProductionComplete] = useState(false);

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

  // ==================== DATA LOADING ====================

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

      // Load evidence summary
      await loadEvidenceSummary(patternId);
    } catch (err: unknown) {
      console.error('Error loading pattern data:', err);
      const apiError = err as { response?: { status?: number } };
      if (apiError?.response?.status === 401) {
        router.push('/login');
        return;
      }
      if (apiError?.response?.status === 404) {
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
        const defaultContext = contexts.find(c => c.value === 'introduction') || contexts[0];
        setSelectedContext(defaultContext.value);
      }
    } catch (err) {
      console.error('Error loading conversation contexts:', err);
    }
  };

  const loadOverview = async (id: string) => {
    try {
      setOverviewLoading(true);
      const data = await apiGet<GrammarOverview>(`/api/v1/grammar/patterns/${id}/ai-overview`);
      setOverview(data);
    } catch (e: unknown) {
      const apiError = e as { response?: { status?: number } };
      if (apiError?.response?.status !== 404) {
        console.error('Failed to load AI overview:', e);
      }
      setOverview(null);
    } finally {
      setOverviewLoading(false);
    }
  };

  const loadEvidenceSummary = async (id: string) => {
    try {
      const summary = await getGrammarEvidenceSummary(id, 10);
      setEvidenceSummary(summary);
    } catch (err) {
      console.error('Error loading evidence summary:', err);
    }
  };

  // ==================== AI OVERVIEW GENERATION ====================

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

  // ==================== PRACTICE QUESTION GENERATION ====================

  const generatePracticeQuestions = async (patternData: GrammarPattern) => {
    try {
      const similarData = await apiGet<SimilarPattern[]>(
        `/api/v1/grammar/patterns/${patternData.id}/similar?limit=6`
      );

      const questions: PracticeQuestion[] = [];

      // 1. BASIC: Pattern Recognition
      questions.push({
        id: '1',
        type: 'multiple_choice',
        difficulty: 'basic',
        question: `Which sentence correctly uses "${patternData.pattern}"?`,
        options: [
          patternData.example_sentence,
          ...(similarData.slice(0, 3).map(similar => similar.example_sentence))
        ].slice(0, 4),
        correctAnswer: 0,
        explanation: `✅ Correct: ${patternData.example_sentence} (${patternData.example_romaji})\n\nThis pattern "${patternData.pattern}" is used for ${patternData.classification.toLowerCase()}.`,
        hint: `Look for the pattern "${patternData.pattern}" in the sentence.`
      });

      // 2. BASIC: Fill in the Blank
      const blankSentence = patternData.example_sentence.replace(
        new RegExp(patternData.pattern.replace(/[～〜]/g, ''), 'g'),
        '____'
      );
      if (blankSentence !== patternData.example_sentence) {
        questions.push({
          id: '2',
          type: 'fill_blank',
          difficulty: 'basic',
          question: `Fill in the blank: ${blankSentence}`,
          options: [
            patternData.pattern.replace(/[～〜]/g, ''),
            ...(similarData.slice(0, 3).map(similar => similar.pattern.replace(/[～〜]/g, '')))
          ].slice(0, 4),
          correctAnswer: 0,
          explanation: `✅ The correct answer is "${patternData.pattern.replace(/[～〜]/g, '')}".\n\n${patternData.example_sentence} (${patternData.example_romaji})`,
          hint: `This pattern is used for ${patternData.classification.toLowerCase()}.`
        });
      }

      // 3. INTERMEDIATE: Translation Challenge
      questions.push({
        id: '3',
        type: 'translation',
        difficulty: 'intermediate',
        question: `How would you express this using the pattern "${patternData.pattern}"?`,
        options: [
          patternData.example_sentence,
          ...(similarData.slice(0, 3).map(similar => similar.example_sentence))
        ].slice(0, 4),
        correctAnswer: 0,
        explanation: `✅ ${patternData.example_sentence} (${patternData.example_romaji})\n\nThe pattern "${patternData.pattern}" is the correct way to express this.`,
        hint: 'Think about the grammatical structure needed.'
      });

      // 4. INTERMEDIATE: Context Selection
      questions.push({
        id: '4',
        type: 'multiple_choice',
        difficulty: 'intermediate',
        question: `In which situation would you most likely use "${patternData.pattern}"?`,
        options: [
          'Self-introduction / Describing someone or something',
          'Asking for directions or locations',
          'Ordering food or making requests',
          'Expressing emotions or feelings'
        ],
        correctAnswer: 0,
        explanation: `✅ "${patternData.pattern}" is primarily used for ${patternData.classification.toLowerCase()}.\n\nClassification: ${patternData.classification}`,
        hint: `Consider what "${patternData.pattern}" means and how it's used.`
      });

      // 5. ADVANCED: Error Correction
      questions.push({
        id: '5',
        type: 'error_correction',
        difficulty: 'advanced',
        question: 'Which sentence has an error in using the pattern?',
        options: [
          'Incorrect usage example',
          patternData.example_sentence,
          ...(similarData.slice(0, 2).map(similar => similar.example_sentence))
        ].slice(0, 4),
        correctAnswer: 0,
        explanation: `❌ The first option has incorrect usage.\n\n✅ Correct usage: ${patternData.example_sentence}`,
        hint: 'Look for incorrect particle usage or word order.'
      });

      // 6. ADVANCED: Transformation
      questions.push({
        id: '6',
        type: 'transformation',
        difficulty: 'advanced',
        question: `How would you transform "${patternData.example_sentence}" into a question?`,
        options: [
          patternData.example_sentence.replace('。', 'か？'),
          patternData.example_sentence.replace('。', '？'),
          patternData.example_sentence,
          'Cannot be transformed'
        ],
        correctAnswer: 0,
        explanation: `✅ Add "か" to make it a question.\n\nThis transforms the statement into a question form.`,
        hint: 'In Japanese, add "か" at the end to form questions.'
      });

      setPracticeQuestions(questions);
    } catch (err) {
      console.error('Error generating practice questions:', err);
      // Fallback questions
      const fallbackQuestions: PracticeQuestion[] = [{
        id: '1',
        type: 'multiple_choice',
        difficulty: 'basic',
        question: `Which is the correct example of "${patternData.pattern}"?`,
        options: [patternData.example_sentence, 'Wrong example', 'Another wrong example', 'Incorrect usage'],
        correctAnswer: 0,
        explanation: `Correct: ${patternData.example_sentence} (${patternData.example_romaji})`
      }];
      setPracticeQuestions(fallbackQuestions);
    }
  };

  // ==================== COMPREHENSION HANDLERS ====================

  const handlePlayAudio = (text: string) => {
    console.log('Play audio for:', text);
    // TODO: Implement text-to-speech
  };

  const handleAnswerSelect = (answerIndex: number) => {
    setSelectedAnswer(answerIndex);
  };

  const handleSubmitAnswer = async () => {
    if (selectedAnswer === null) return;

    const currentQuestion = practiceQuestions[currentQuestionIndex];
    const isCorrect = selectedAnswer === currentQuestion.correctAnswer;
    const startTime = Date.now();

    if (isCorrect) {
      setPracticeScore(prev => ({ ...prev, correct: prev.correct + 1, total: prev.total + 1 }));
    } else {
      setPracticeScore(prev => ({ ...prev, total: prev.total + 1 }));
    }
    setShowExplanation(true);

    // Record evidence
    try {
      const responseTime = Math.floor((Date.now() - startTime) / 1000);
      await recordGrammarEvidence({
        pattern_id: patternId,
        stage: 'comprehension',
        interaction_type: 'grammar_practiced',
        is_correct: isCorrect,
        user_response: currentQuestion.options?.[selectedAnswer] || String(selectedAnswer),
        attempts_count: 1,
        hint_used: false,
        response_time_seconds: responseTime,
        rubric_scores: {
          pattern_used: true,
          form_accurate: isCorrect,
          meaning_matches: isCorrect
        },
        error_tags: isCorrect ? [] : ['comprehension_error'],
        stage_specific_data: {
          question_type: currentQuestion.type,
          difficulty: currentQuestion.difficulty
        }
      });
    } catch (err) {
      console.error('Error recording evidence:', err);
    }
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

  const handlePracticeComplete = async () => {
    setPracticeComplete(true);
  };

  // ==================== SRS GRADING ====================

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
      console.log('Study session recorded successfully');
    } catch (err) {
      console.error('Error recording study session:', err);
    }
  };

  const getConfidenceFromGrade = (grade: 'again' | 'hard' | 'good' | 'easy'): number => {
    const gradeMap = { 'again': 1, 'hard': 2, 'good': 4, 'easy': 5 };
    return gradeMap[grade];
  };

  // ==================== PRODUCTION HANDLERS ====================

  const handleProductionSubmit = async () => {
    if (!productionInput.trim()) return;

    // Record evidence for production
    try {
      await recordGrammarEvidence({
        pattern_id: patternId,
        stage: 'production',
        interaction_type: 'grammar_practiced',
        user_response: productionInput,
        attempts_count: 1,
        rubric_scores: {
          pattern_used: true,
          form_accurate: true,
          meaning_matches: true
        },
        stage_specific_data: {
          exercise_type: 'free_production'
        }
      });
      setProductionFeedback('Great job! Your sentence has been recorded.');
    } catch (err) {
      console.error('Error recording production:', err);
      setProductionFeedback('Your response was recorded.');
    }
  };

  // ==================== CONVERSATION HANDLERS ====================

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

      const dialogueHistory = scenario.initial_dialogue.length > 0
        ? [...scenario.initial_dialogue]
        : [];
      setConversationHistory(dialogueHistory);
      setConversationStarted(true);
      setShowCustomScenario(false);
      setCustomScenarioText('');
    } catch (err) {
      console.error('Error starting conversation:', err);
    } finally {
      setConversationLoading(false);
    }
  };

  const handleSendMessage = async () => {
    if (!userMessage.trim() || !conversationScenario) return;

    try {
      setConversationLoading(true);

      const userTurn: DialogueTurn = {
        speaker: 'user',
        message: userMessage.trim()
      };
      const newHistory = [...conversationHistory, userTurn];
      setConversationHistory(newHistory);

      const aiResponse = await sendConversationMessage({
        scenario_id: conversationScenario.scenario_id,
        user_message: userMessage.trim()
      });
      setConversationHistory([...newHistory, aiResponse]);
      setUserMessage('');
    } catch (err) {
      console.error('Error sending message:', err);
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

  // ==================== RENDER HELPERS ====================

  const getScoreMessage = (percentage: number): string => {
    if (percentage >= 0.875) return "🏆 Master Level! All drill types conquered!";
    if (percentage >= 0.75) return "🎯 Advanced! Great understanding of nuances!";
    if (percentage >= 0.625) return "📚 Good progress! Some advanced concepts need work";
    if (percentage >= 0.5) return "💪 Keep going! Focus on basic patterns first";
    return "🌱 Building foundation! Practice the fundamentals more";
  };

  // ==================== LOADING & ERROR STATES ====================

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
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
            <div className="text-destructive mb-4">
              <Circle className="w-12 h-12 mx-auto" />
            </div>
            <h3 className="text-lg font-semibold text-foreground mb-2">
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

  // ==================== MAIN RENDER ====================

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-3">
          <Button variant="ghost" onClick={() => router.push('/grammar')}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Grammar
          </Button>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowEvidencePanel(prev => !prev)}
            >
              📊 Evidence
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowSettings(prev => !prev)}
            >
              <SettingsIcon className="w-4 h-4 mr-2" />
              Settings
            </Button>
          </div>
        </div>

        {/* AI Settings Panel */}
        {showSettings && (
          <div className="mb-4 border rounded-lg p-4 bg-card">
            <h4 className="text-sm font-medium text-foreground mb-3">AI Generation Settings</h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 items-end">
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Provider</label>
                <select
                  value={aiProvider}
                  onChange={(e) => {
                    const p = e.target.value as 'openai' | 'gemini';
                    setAiProvider(p);
                    setAiModel(p === 'openai' ? 'gpt-4o' : 'gemini-2.0-flash');
                  }}
                  className="w-full border rounded-md p-2 text-sm bg-background text-foreground"
                >
                  <option value="openai">OpenAI</option>
                  <option value="gemini">Gemini</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Model</label>
                <select
                  value={aiModel}
                  onChange={(e) => setAiModel(e.target.value)}
                  className="w-full border rounded-md p-2 text-sm bg-background text-foreground"
                >
                  {aiProvider === 'openai' ? (
                    <>
                      <option value="gpt-4o">gpt-4o</option>
                      <option value="gpt-4o-mini">gpt-4o-mini</option>
                      <option value="gpt-4-turbo">gpt-4-turbo</option>
                    </>
                  ) : (
                    <>
                      <option value="gemini-2.0-flash">gemini-2.0-flash</option>
                      <option value="gemini-1.5-pro">gemini-1.5-pro</option>
                    </>
                  )}
                </select>
              </div>
              <div className="flex gap-2">
                <Button onClick={generateOverview} disabled={overviewGenerating} size="sm" className="flex-1">
                  {overviewGenerating ? 'Working…' : 'Generate'}
                </Button>
                <Button onClick={regenerateOverview} disabled={overviewGenerating} variant="outline" size="sm" className="flex-1">
                  {overviewGenerating ? 'Working…' : 'Regenerate'}
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Pattern Header */}
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h1 className="text-2xl md:text-3xl font-bold text-foreground mb-2 flex items-center gap-3">
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
            <div className="flex items-center gap-2 flex-wrap">
              <Badge variant="secondary">{pattern.textbook}</Badge>
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

      {/* Evidence Panel */}
      {showEvidencePanel && evidenceSummary && (
        <Card className="mb-6 border-blue-500/30 bg-blue-500/5">
          <CardHeader>
            <CardTitle className="text-sm">📊 Learning Evidence</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <div className="text-muted-foreground">Total Attempts</div>
                <div className="font-semibold">{evidenceSummary.total_attempts}</div>
              </div>
              <div>
                <div className="text-muted-foreground">Correct Rate</div>
                <div className="font-semibold">{Math.round(evidenceSummary.correct_rate * 100)}%</div>
              </div>
              <div>
                <div className="text-muted-foreground">Mastery Level</div>
                <div className="font-semibold">{evidenceSummary.mastery_level}/5</div>
              </div>
              <div>
                <div className="text-muted-foreground">By Stage</div>
                <div className="font-semibold text-xs">
                  {Object.entries(evidenceSummary.attempts_by_stage).map(([stage, count]) => (
                    <span key={stage} className="mr-2">{stage}: {count}</span>
                  ))}
                </div>
              </div>
            </div>
            {evidenceSummary.common_error_tags.length > 0 && (
              <div className="mt-4">
                <div className="text-xs text-muted-foreground mb-1">Common Errors:</div>
                <div className="flex flex-wrap gap-1">
                  {evidenceSummary.common_error_tags.map((tag, idx) => (
                    <Badge key={idx} variant="destructive" className="text-xs">{tag}</Badge>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 4-Stage Learning Tabs */}
      <Tabs defaultValue="presentation" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="presentation" className="flex items-center gap-1">
            <BookOpen className="w-4 h-4" />
            <span className="hidden sm:inline">1. Present</span>
          </TabsTrigger>
          <TabsTrigger value="comprehension" className="flex items-center gap-1">
            <Target className="w-4 h-4" />
            <span className="hidden sm:inline">2. Comprehend</span>
          </TabsTrigger>
          <TabsTrigger value="production" className="flex items-center gap-1">
            <Pencil className="w-4 h-4" />
            <span className="hidden sm:inline">3. Produce</span>
          </TabsTrigger>
          <TabsTrigger value="interaction" className="flex items-center gap-1">
            <MessageSquare className="w-4 h-4" />
            <span className="hidden sm:inline">4. Interact</span>
          </TabsTrigger>
        </TabsList>

        {/* ==================== STAGE 1: PRESENTATION ==================== */}
        <TabsContent value="presentation" className="space-y-6">
          {/* AI Overview Card */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-foreground">Grammar Overview</CardTitle>
              {overview && (
                <Button size="sm" variant="outline" onClick={regenerateOverview} disabled={overviewGenerating}>
                  <RotateCcw className="w-3 h-3 mr-1" />
                  {overviewGenerating ? 'Working…' : 'Regenerate'}
                </Button>
              )}
            </CardHeader>
            <CardContent className="space-y-4">
              {overviewLoading ? (
                <div className="flex items-center gap-2 text-muted-foreground">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>
                  <span className="text-sm">Loading overview...</span>
                </div>
              ) : overview ? (
                <div className="space-y-4">
                  {/* What is this pattern */}
                  <div className="rounded-lg border bg-card p-4">
                    <h3 className="text-sm font-semibold text-foreground mb-2 flex items-center gap-2">
                      <span className="w-5 h-5 rounded bg-primary/10 flex items-center justify-center text-xs">1</span>
                      What Does This Pattern Mean?
                    </h3>
                    <p className="text-foreground leading-relaxed">
                      {overview.what_is_en || overview.what_is || 'No description available.'}
                    </p>
                  </div>

                  {/* How to form */}
                  {(overview.how_to_form || overview.formation) && (
                    <div className="rounded-lg border bg-card p-4">
                      <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                        <span className="w-5 h-5 rounded bg-primary/10 flex items-center justify-center text-xs">2</span>
                        How to Form This Pattern
                      </h3>
                      {overview.how_to_form ? (
                        <div className="space-y-4">
                          <p className="text-foreground leading-relaxed">
                            {overview.how_to_form.summary_en}
                          </p>
                          {overview.how_to_form.pattern_template && (
                            <div className="bg-muted/50 rounded-md p-3">
                              <span className="text-xs text-muted-foreground uppercase tracking-wide">Pattern:</span>
                              <p className="text-foreground font-mono text-lg mt-1">
                                {overview.how_to_form.pattern_template}
                              </p>
                            </div>
                          )}
                          {overview.how_to_form.steps && overview.how_to_form.steps.length > 0 && (
                            <div className="space-y-2">
                              <span className="text-xs text-muted-foreground uppercase tracking-wide">Step-by-Step:</span>
                              <div className="space-y-2">
                                {overview.how_to_form.steps.map((step, idx) => (
                                  <div key={idx} className="flex flex-col sm:flex-row sm:items-center gap-2 p-2 rounded bg-muted/30 border-l-2 border-primary/40">
                                    <span className="text-sm text-muted-foreground min-w-[120px] font-medium">{step.slot}:</span>
                                    {step.jp && (
                                      <div className="flex flex-wrap items-center gap-2 text-sm">
                                        <span className="font-medium text-foreground">{step.jp}</span>
                                        {step.kana && <span className="text-muted-foreground">({step.kana})</span>}
                                        {step.romaji && <span className="italic text-muted-foreground">{step.romaji}</span>}
                                        {step.en && <span className="text-primary">= {step.en}</span>}
                                      </div>
                                    )}
                                    {!step.jp && step.en && (
                                      <span className="text-sm text-foreground">{step.en}</span>
                                    )}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      ) : overview.formation ? (
                        <pre className="text-foreground leading-relaxed font-mono text-sm bg-muted/50 p-3 rounded whitespace-pre-wrap break-words">
                          {overview.formation}
                        </pre>
                      ) : null}
                    </div>
                  )}

                  {/* When to use */}
                  {(overview.usage_en || overview.usage) && (
                    <div className="rounded-lg border bg-card p-4">
                      <h3 className="text-sm font-semibold text-foreground mb-2 flex items-center gap-2">
                        <span className="w-5 h-5 rounded bg-primary/10 flex items-center justify-center text-xs">3</span>
                        When to Use This
                      </h3>
                      <p className="text-foreground leading-relaxed whitespace-pre-line">
                        {overview.usage_en || overview.usage}
                      </p>
                    </div>
                  )}

                  {/* Nuance */}
                  {(overview.nuance_en || overview.nuance) && (
                    <div className="rounded-lg border bg-card p-4">
                      <h3 className="text-sm font-semibold text-foreground mb-2 flex items-center gap-2">
                        <span className="w-5 h-5 rounded bg-primary/10 flex items-center justify-center text-xs">4</span>
                        Nuance & Politeness Level
                      </h3>
                      <p className="text-foreground leading-relaxed">
                        {overview.nuance_en || overview.nuance}
                      </p>
                    </div>
                  )}

                  {/* Examples */}
                  {overview.examples?.length > 0 && (
                    <div className="rounded-lg border bg-card p-4">
                      <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                        <span className="w-5 h-5 rounded bg-primary/10 flex items-center justify-center text-xs">5</span>
                        Example Sentences
                      </h3>
                      <div className="space-y-3">
                        {overview.examples.slice(0, 6).map((ex, idx) => (
                          <div key={idx} className="rounded-md border bg-muted/20 p-3">
                            <p className="text-foreground font-medium text-lg">{ex.jp}</p>
                            {ex.kana && (
                              <p className="text-sm text-muted-foreground mt-1">Reading: {ex.kana}</p>
                            )}
                            {ex.romaji && (
                              <p className="text-sm text-muted-foreground italic mt-1">{ex.romaji}</p>
                            )}
                            {ex.en && (
                              <p className="text-sm text-primary mt-2 border-t border-border/50 pt-2">{ex.en}</p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Common Mistakes */}
                  {overview.common_mistakes && overview.common_mistakes.length > 0 && (
                    <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4">
                      <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                        <span className="w-5 h-5 rounded bg-destructive/20 flex items-center justify-center text-xs text-destructive">!</span>
                        Common Mistakes to Avoid
                      </h3>
                      <div className="space-y-4">
                        {overview.common_mistakes.map((mistake, idx) => {
                          const isString = typeof mistake === 'string';
                          const mistakeEn = isString ? mistake : mistake.mistake_en;
                          const wrongEx = isString ? null : mistake.wrong;
                          const correctEx = isString ? null : mistake.correct;

                          return (
                            <div key={idx} className="space-y-2">
                              <p className="text-sm text-foreground font-medium flex items-start gap-2">
                                <span className="text-destructive">•</span>
                                {mistakeEn}
                              </p>
                              {wrongEx && (
                                <div className="ml-4 p-2 rounded bg-destructive/10 border border-destructive/20">
                                  <span className="text-xs text-destructive uppercase tracking-wide">Wrong:</span>
                                  <p className="text-foreground line-through opacity-70">{wrongEx.jp}</p>
                                  {wrongEx.romaji && <p className="text-xs text-muted-foreground italic">{wrongEx.romaji}</p>}
                                  {wrongEx.en && <p className="text-xs text-muted-foreground">{wrongEx.en}</p>}
                                </div>
                              )}
                              {correctEx && (
                                <div className="ml-4 p-2 rounded bg-green-500/10 border border-green-500/20">
                                  <span className="text-xs text-green-600 uppercase tracking-wide">Correct:</span>
                                  <p className="text-foreground font-medium">{correctEx.jp}</p>
                                  {correctEx.romaji && <p className="text-xs text-muted-foreground italic">{correctEx.romaji}</p>}
                                  {correctEx.en && <p className="text-xs text-primary">{correctEx.en}</p>}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Learning Tips */}
                  {(overview.tips_en || overview.tips) && (
                    <div className="rounded-lg border border-primary/30 bg-primary/5 p-4">
                      <h3 className="text-sm font-semibold text-foreground mb-2 flex items-center gap-2">
                        <span className="w-5 h-5 rounded bg-primary/20 flex items-center justify-center text-xs">💡</span>
                        Learning Tips
                      </h3>
                      <p className="text-foreground leading-relaxed">
                        {overview.tips_en || overview.tips}
                      </p>
                    </div>
                  )}

                  {/* Meta info */}
                  <p className="text-xs text-muted-foreground pt-2 border-t">
                    Generated by {overview.model_used || 'AI'} on {overview.generated_at ? new Date(overview.generated_at).toLocaleString() : 'this session'}
                  </p>
                </div>
              ) : (
                <div className="text-center py-8">
                  <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mx-auto mb-4">
                    <Play className="w-6 h-6 text-muted-foreground" />
                  </div>
                  <p className="text-muted-foreground mb-4">No AI overview yet for this pattern.</p>
                  <Button onClick={generateOverview} disabled={overviewGenerating}>
                    {overviewGenerating ? 'Generating…' : 'Generate Overview'}
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Pattern Details Card */}
          <Card>
            <CardHeader>
              <CardTitle>Pattern Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <h3 className="text-sm font-semibold text-foreground mb-2">Textbook Form</h3>
                <div className="bg-muted/50 p-4 rounded-lg">
                  <p className="text-lg font-medium text-foreground">{pattern.textbook_form}</p>
                  <p className="text-muted-foreground italic mt-1">{pattern.textbook_form_romaji}</p>
                </div>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-foreground mb-2">Example Sentence</h3>
                <div className="bg-muted/50 p-4 rounded-lg">
                  <p className="text-lg text-foreground">{pattern.example_sentence}</p>
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
                  <h3 className="text-sm font-semibold text-foreground mb-2">Topic</h3>
                  <p className="text-muted-foreground">{pattern.topic}</p>
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-foreground mb-2">Lesson</h3>
                  <p className="text-muted-foreground">{pattern.lesson}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Similar Patterns */}
          {similarPatterns.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Users className="w-5 h-5" />
                  Similar Patterns (Confusables)
                </CardTitle>
              </CardHeader>
              <CardContent>
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
              </CardContent>
            </Card>
          )}

          {/* Prerequisites */}
          {prerequisites.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Target className="w-5 h-5" />
                  Prerequisites
                </CardTitle>
              </CardHeader>
              <CardContent>
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
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* ==================== STAGE 2: COMPREHENSION ==================== */}
        <TabsContent value="comprehension" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Play className="w-5 h-5" />
                Comprehension Practice
              </CardTitle>
              <p className="text-sm text-muted-foreground mt-2">
                Test your understanding: meaning discrimination, context fit, and judgment tasks
              </p>
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
                           currentQuestion.type === 'error_correction' ? '🔍 Error Correction' : '❓ Question'}
                        </Badge>
                      </div>
                      <h3 className="text-lg font-semibold">{currentQuestion.question}</h3>

                      {/* Hint */}
                      {currentQuestion.hint && !showExplanation && (
                        <div className="bg-amber-50 dark:bg-amber-900/20 p-3 rounded-lg border-l-4 border-amber-400">
                          <p className="text-sm text-amber-800 dark:text-amber-200">
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
                                    ? "bg-green-500/10 border-green-500/50 text-green-600"
                                    : selectedAnswer === index && index !== currentQuestion.correctAnswer
                                    ? "bg-red-500/10 border-red-500/50 text-red-500"
                                    : ""
                                  : ""
                              }`}
                              onClick={() => !showExplanation && handleAnswerSelect(index)}
                              disabled={showExplanation}
                            >
                              <span className="flex items-center gap-3 w-full">
                                <span className="w-6 h-6 rounded-full bg-muted flex items-center justify-center text-sm font-medium">
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
                        <div className="bg-blue-500/10 p-4 rounded-lg border-l-4 border-blue-500/40">
                          <h4 className="font-semibold text-blue-700 dark:text-blue-300 mb-3">📚 Explanation</h4>
                          <div className="text-blue-600 dark:text-blue-200 whitespace-pre-line leading-relaxed">
                            {currentQuestion.explanation}
                          </div>
                        </div>
                      )}

                      {/* Action Buttons */}
                      <div className="flex justify-end">
                        {!showExplanation ? (
                          <Button onClick={handleSubmitAnswer} disabled={selectedAnswer === null}>
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

                  <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 p-6 rounded-lg border border-blue-500/30">
                    <div className="text-center mb-4">
                      <p className="text-2xl font-bold text-blue-700 dark:text-blue-300">
                        {practiceScore.correct}/{practiceScore.total} ({Math.round((practiceScore.correct / practiceScore.total) * 100)}%)
                      </p>
                      <p className="text-sm text-blue-600 dark:text-blue-400 font-medium">
                        {getScoreMessage(practiceScore.correct / practiceScore.total)}
                      </p>
                    </div>
                  </div>

                  {/* SRS Grading */}
                  <div className="bg-muted p-4 rounded-lg">
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

        {/* ==================== STAGE 3: PRODUCTION ==================== */}
        <TabsContent value="production" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Pencil className="w-5 h-5" />
                Production Practice
              </CardTitle>
              <p className="text-sm text-muted-foreground mt-2">
                Create your own sentences using the pattern "{pattern.pattern}"
              </p>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {/* Instructions */}
                <div className="bg-blue-500/10 p-4 rounded-lg border border-blue-500/30">
                  <h4 className="font-semibold text-blue-700 dark:text-blue-300 mb-2">🎯 Production Stage</h4>
                  <p className="text-blue-600 dark:text-blue-400 text-sm">
                    Now it's your turn to create sentences! Start with guided exercises, then try free production.
                  </p>
                </div>

                {/* Slot-Fill Exercise */}
                <div className="rounded-lg border p-4">
                  <h4 className="font-medium mb-3">1. Slot-Fill Exercise</h4>
                  <p className="text-sm text-muted-foreground mb-4">
                    Complete the sentence using the pattern "{pattern.pattern}":
                  </p>
                  <div className="bg-muted/50 p-3 rounded-md mb-4">
                    <p className="text-foreground">{pattern.textbook_form.replace(/[～〜]/g, '____')}</p>
                  </div>
                  <input
                    type="text"
                    placeholder="Fill in the blank..."
                    className="w-full p-3 border border-input rounded-lg focus:ring-2 focus:ring-ring"
                    value={productionInput}
                    onChange={(e) => setProductionInput(e.target.value)}
                  />
                </div>

                {/* Transformation Exercise */}
                <div className="rounded-lg border p-4">
                  <h4 className="font-medium mb-3">2. Transformation Exercise</h4>
                  <p className="text-sm text-muted-foreground mb-4">
                    Transform the following sentence using "{pattern.pattern}":
                  </p>
                  <div className="bg-muted/50 p-3 rounded-md mb-4">
                    <p className="text-foreground">{pattern.example_sentence}</p>
                    <p className="text-xs text-muted-foreground mt-1">{pattern.example_romaji}</p>
                  </div>
                  <p className="text-sm mb-2">Try making it: <strong>a question</strong> or <strong>negative</strong></p>
                  <textarea
                    placeholder="Write your transformation..."
                    className="w-full p-3 border border-input rounded-lg resize-none h-20 focus:ring-2 focus:ring-ring"
                  />
                </div>

                {/* Free Production */}
                <div className="rounded-lg border p-4">
                  <h4 className="font-medium mb-3">3. Free Production (Personalization)</h4>
                  <p className="text-sm text-muted-foreground mb-4">
                    Create your own sentence using "{pattern.pattern}" that is true about yourself or your situation:
                  </p>
                  <textarea
                    placeholder="Write your own sentence using this pattern..."
                    className="w-full p-3 border border-input rounded-lg resize-none h-24 focus:ring-2 focus:ring-ring"
                  />
                  <Button className="mt-3" onClick={handleProductionSubmit}>
                    Submit for Review
                  </Button>
                </div>

                {productionFeedback && (
                  <div className="bg-green-500/10 p-4 rounded-lg border border-green-500/30">
                    <p className="text-green-700 dark:text-green-300">{productionFeedback}</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ==================== STAGE 4: INTERACTION ==================== */}
        <TabsContent value="interaction" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                🤖 AI Conversation Practice
              </CardTitle>
              <p className="text-sm text-muted-foreground mt-2">
                Practice using "{pattern.pattern}" in a realistic conversation with AI
              </p>
            </CardHeader>
            <CardContent>
              {conversationLoading && !conversationStarted ? (
                <div className="flex items-center justify-center h-32">
                  <div className="text-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
                    <p className="text-muted-foreground">Starting AI conversation...</p>
                  </div>
                </div>
              ) : !conversationStarted ? (
                <div className="space-y-6">
                  <div className="bg-blue-500/10 p-4 rounded-lg border border-blue-500/30">
                    <h3 className="text-blue-600 dark:text-blue-300 font-semibold mb-2">🎭 Choose Your Conversation Scenario</h3>
                    <p className="text-blue-500 dark:text-blue-400 text-sm">
                      Select a scenario to practice using "{pattern.pattern}" in context
                    </p>
                  </div>

                  {!showCustomScenario ? (
                    <div className="space-y-4">
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

                      <div className="border-t pt-4">
                        <Button
                          onClick={() => setShowCustomScenario(true)}
                          variant="outline"
                          className="w-full p-4 h-auto flex items-center gap-3 border-2 border-dashed"
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
                    <div className="space-y-4">
                      <div className="bg-purple-500/10 p-4 rounded-lg border border-purple-500/30">
                        <h4 className="font-semibold text-purple-600 dark:text-purple-300 mb-3">✨ Create Your Custom Scenario</h4>
                        <textarea
                          value={customScenarioText}
                          onChange={(e) => setCustomScenarioText(e.target.value)}
                          placeholder="Describe a situation where you'd like to practice..."
                          className="w-full p-3 border border-input rounded-lg resize-none h-24 text-sm"
                        />
                        <div className="flex gap-3 mt-3">
                          <Button
                            onClick={() => handleStartConversation('custom', customScenarioText)}
                            disabled={!customScenarioText.trim() || conversationLoading}
                            className="flex-1"
                          >
                            🚀 Start Custom Conversation
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
                  )}
                </div>
              ) : (
                <div className="space-y-4">
                  {/* Scenario Info */}
                  {conversationScenario && (
                    <div className="bg-blue-500/10 p-4 rounded-lg border border-blue-500/30">
                      <div className="flex justify-between items-start mb-3">
                        <div>
                          <h4 className="font-semibold text-blue-700 dark:text-blue-300">
                            🎭 {conversationScenario.situation}
                          </h4>
                          <p className="text-sm text-blue-600 dark:text-blue-400 mt-1">
                            <strong>Your role:</strong> {conversationScenario.user_role}
                          </p>
                          <p className="text-sm text-blue-600 dark:text-blue-400">
                            <strong>AI character:</strong> {conversationScenario.ai_character}
                          </p>
                        </div>
                        <Badge variant="outline" className="text-blue-500">
                          {conversationScenario.context}
                        </Badge>
                      </div>
                      <div className="bg-blue-500/10 p-3 rounded border-l-4 border-blue-500/40">
                        <strong>🎯 Learning objective:</strong> {conversationScenario.learning_objective}
                      </div>
                    </div>
                  )}

                  {/* Conversation History */}
                  <div className="bg-muted p-4 rounded-lg max-h-96 overflow-y-auto">
                    <div className="space-y-6">
                      {conversationHistory.map((turn, index) => (
                        <div key={index} className="space-y-2">
                          <div className={`flex ${turn.speaker === 'user' ? 'justify-end' : 'justify-start'}`}>
                            <div className={`max-w-[80%] p-3 rounded-lg ${
                              turn.speaker === 'user'
                                ? 'bg-blue-600 text-white rounded-br-sm'
                                : 'bg-card border border-border rounded-bl-sm'
                            }`}>
                              <p className="text-sm font-medium mb-2">
                                {turn.speaker === 'user' ? '👤 You' : '🗣️ AI'}
                              </p>
                              <p className="text-base font-medium">{turn.message}</p>

                              {turn.speaker === 'ai' && (turn.transliteration || turn.translation) && (
                                <div className="mt-3 space-y-2 pt-3 border-t border-border/50">
                                  {turn.transliteration && (
                                    <div className="bg-blue-500/10 p-2 rounded">
                                      <p className="text-xs font-semibold mb-1">🔤 Romaji:</p>
                                      <p className="text-sm italic">{turn.transliteration}</p>
                                    </div>
                                  )}
                                  {turn.translation && (
                                    <div className="bg-muted p-2 rounded">
                                      <p className="text-xs font-semibold mb-1">🌍 English:</p>
                                      <p className="text-sm">{turn.translation}</p>
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          </div>

                          {/* Feedback panels */}
                          {turn.speaker === 'ai' && (turn.feedback || turn.corrections?.length || turn.hints?.length) && (
                            <div className="ml-4">
                              <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg overflow-hidden">
                                <button
                                  onClick={() => toggleFeedbackCollapse(index)}
                                  className="w-full p-3 text-left flex items-center justify-between hover:bg-amber-100 dark:hover:bg-amber-800/30 transition-colors"
                                >
                                  <span className="text-amber-800 dark:text-amber-200 font-medium text-sm">
                                    🧑‍🏫 Teaching Feedback
                                  </span>
                                  {collapsedFeedback.has(index) ? (
                                    <ChevronDown className="h-4 w-4 text-amber-600" />
                                  ) : (
                                    <ChevronUp className="h-4 w-4 text-amber-600" />
                                  )}
                                </button>
                                {!collapsedFeedback.has(index) && (
                                  <div className="px-3 pb-3 space-y-3">
                                    {turn.feedback && (
                                      <p className="text-amber-700 dark:text-amber-300 text-sm">{turn.feedback}</p>
                                    )}
                                    {turn.corrections && turn.corrections.length > 0 && (
                                      <div className="bg-red-500/10 p-2 rounded">
                                        <p className="text-xs font-semibold text-red-600 mb-1">✏️ Corrections:</p>
                                        <ul className="text-red-600 text-xs space-y-1">
                                          {turn.corrections.map((c, i) => (
                                            <li key={i}>• {c}</li>
                                          ))}
                                        </ul>
                                      </div>
                                    )}
                                    {turn.hints && turn.hints.length > 0 && (
                                      <div className="bg-blue-500/10 p-2 rounded">
                                        <p className="text-xs font-semibold text-blue-600 mb-1">💡 Tips:</p>
                                        <ul className="text-blue-600 text-xs space-y-1">
                                          {turn.hints.map((h, i) => (
                                            <li key={i}>• {h}</li>
                                          ))}
                                        </ul>
                                      </div>
                                    )}
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
                      className="flex-1 p-3 border border-input rounded-lg focus:ring-2 focus:ring-ring"
                      disabled={conversationLoading}
                    />
                    <Button
                      onClick={handleSendMessage}
                      disabled={!userMessage.trim() || conversationLoading}
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
