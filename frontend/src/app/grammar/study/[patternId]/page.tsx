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
  RotateCcw
} from 'lucide-react';

import { apiGet } from '@/lib/api';

interface GrammarPattern {
  id: string;
  sequenceNumber: number;
  pattern: string;
  patternRomaji: string;
  textbookForm: string;
  textbookFormRomaji: string;
  exampleSentence: string;
  exampleRomaji: string;
  classification: string;
  textbook: string;
  topic: string;
  lesson: string;
  jfsCategory: string;
}

interface SimilarPattern {
  pattern: string;
  patternRomaji: string;
  exampleSentence: string;
  textbook: string;
  similarityReason: string;
}

interface PracticeQuestion {
  id: string;
  question: string;
  options: string[];
  correctAnswer: number;
  explanation: string;
}

export default function GrammarStudyPage() {
  const params = useParams();
  const router = useRouter();
  const patternId = params.patternId as string;

  const [pattern, setPattern] = useState<GrammarPattern | null>(null);
  const [similarPatterns, setSimilarPatterns] = useState<SimilarPattern[]>([]);
  const [prerequisites, setPrerequisites] = useState<GrammarPattern[]>([]);
  const [practiceQuestions, setPracticeQuestions] = useState<PracticeQuestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Practice state
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState<number | null>(null);
  const [showExplanation, setShowExplanation] = useState(false);
  const [practiceScore, setPracticeScore] = useState({ correct: 0, total: 0 });
  const [practiceComplete, setPracticeComplete] = useState(false);

  const loadPatternData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Load pattern details, similar patterns, and prerequisites in parallel
      const [patternData, similarData, prerequisitesData] = await Promise.all([
        apiGet<GrammarPattern>(`/api/v1/grammar/patterns/${patternId}`),
        apiGet<SimilarPattern[]>(`/api/v1/grammar/patterns/${patternId}/similar?limit=5`),
        apiGet<GrammarPattern[]>(`/api/v1/grammar/patterns/${patternId}/prerequisites`)
      ]);

      setPattern(patternData);
      setSimilarPatterns(similarData);
      setPrerequisites(prerequisitesData);
      
      // Generate simple practice questions (in a real app, this would come from the backend)
      generatePracticeQuestions(patternData);

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
    }
  }, [patternId, loadPatternData]);

  const generatePracticeQuestions = (pattern: GrammarPattern) => {
    // Simple practice questions generation (in a real app, this would be AI-generated)
    const questions: PracticeQuestion[] = [
      {
        id: '1',
        question: `Which is the correct usage of "${pattern.pattern}"?`,
        options: [
          pattern.exampleSentence,
          `Wrong example using ${pattern.pattern}`,
          `Another wrong example with ${pattern.pattern}`,
          `Incorrect usage of ${pattern.pattern}`
        ],
        correctAnswer: 0,
        explanation: `The correct usage is: ${pattern.exampleSentence} (${pattern.exampleRomaji})`
      },
      {
        id: '2',
        question: `What is the main function of "${pattern.pattern}"?`,
        options: [
          pattern.classification,
          'Wrong classification',
          'Another wrong option',
          'Incorrect function'
        ],
        correctAnswer: 0,
        explanation: `This pattern is used for: ${pattern.classification}`
      }
    ];
    
    setPracticeQuestions(questions);
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
      setPracticeComplete(true);
    }
  };

  const handleRestartPractice = () => {
    setCurrentQuestionIndex(0);
    setSelectedAnswer(null);
    setShowExplanation(false);
    setPracticeScore({ correct: 0, total: 0 });
    setPracticeComplete(false);
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
        <Button 
          variant="ghost" 
          onClick={() => router.push('/grammar')}
          className="mb-4"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Grammar
        </Button>
        
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2 flex items-center gap-3">
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
            <p className="text-xl text-muted-foreground italic mb-2">{pattern.patternRomaji}</p>
            <div className="flex items-center gap-2">
              <Badge className="bg-blue-100 text-blue-800">{pattern.textbook}</Badge>
              <Badge variant="outline">{pattern.classification}</Badge>
              <Badge variant="outline">{pattern.jfsCategory}</Badge>
            </div>
          </div>
        </div>
      </div>

      {/* Study Content */}
      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="similar">Similar Patterns</TabsTrigger>
          <TabsTrigger value="prerequisites">Prerequisites</TabsTrigger>
          <TabsTrigger value="practice">Practice</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Pattern Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <h3 className="font-semibold text-gray-900 mb-2">Textbook Form</h3>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <p className="text-lg font-medium">{pattern.textbookForm}</p>
                  <p className="text-muted-foreground italic">{pattern.textbookFormRomaji}</p>
                </div>
              </div>
              
              <div>
                <h3 className="font-semibold text-gray-900 mb-2">Example Sentence</h3>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <p className="text-lg">{pattern.exampleSentence}</p>
                  <p className="text-muted-foreground italic mt-1">{pattern.exampleRomaji}</p>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handlePlayAudio(pattern.exampleSentence)}
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
                          <p className="text-muted-foreground italic text-sm">{similar.patternRomaji}</p>
                        </div>
                        <Badge variant="outline">{similar.textbook}</Badge>
                      </div>
                      <p className="text-sm mb-2">{similar.exampleSentence}</p>
                      <p className="text-xs text-muted-foreground">{similar.similarityReason}</p>
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
                          <p className="text-muted-foreground italic text-sm">{prereq.patternRomaji}</p>
                        </div>
                        <Badge variant="outline">{prereq.textbook}</Badge>
                      </div>
                      <p className="text-sm mb-2">{prereq.exampleSentence}</p>
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
                      <h3 className="text-lg font-semibold">{currentQuestion.question}</h3>
                      
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
                            <span className="mr-3 font-semibold">{String.fromCharCode(65 + index)}.</span>
                            {option}
                          </Button>
                        ))}
                      </div>

                      {/* Explanation */}
                      {showExplanation && (
                        <div className="bg-blue-50 p-4 rounded-lg">
                          <h4 className="font-semibold text-blue-900 mb-2">Explanation</h4>
                          <p className="text-blue-800">{currentQuestion.explanation}</p>
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
                <div className="text-center space-y-4">
                  <CheckCircle className="w-16 h-16 text-green-500 mx-auto" />
                  <h3 className="text-xl font-semibold">Practice Complete!</h3>
                  <p className="text-lg">
                    Final Score: {practiceScore.correct}/{practiceScore.total} 
                    ({Math.round((practiceScore.correct / practiceScore.total) * 100)}%)
                  </p>
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
      </Tabs>
    </div>
  );
}
