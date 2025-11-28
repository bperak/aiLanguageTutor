"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { ArrowRight, CheckCircle, Circle, Target, BookOpen, Star, Clock, Award, TrendingUp } from 'lucide-react';

interface LearningPath {
  from_pattern: string;
  to_pattern: string;
  path_length: number;
  intermediate_patterns: string[];
  pattern_ids: string[];
}

interface PatternProgress {
  pattern_id: string;
  pattern_name: string;
  mastery_level: number; // 1-5 scale
  last_studied?: string;
  next_review_date?: string;
  is_completed: boolean;
  study_count: number;
}

interface LearningPathStats {
  total_patterns: number;
  completed_patterns: number;
  average_mastery: number;
  estimated_completion_days: number;
  total_study_time_minutes: number;
}

interface GrammarLearningPathProps {
  learningPath: LearningPath[];
  patternProgress?: PatternProgress[];
  pathStats?: LearningPathStats;
  onPatternClick?: (patternId: string) => void;
  onStartLearning?: (patternId: string) => void;
  onMarkAsStudied?: (patternId: string, grade: 'again' | 'hard' | 'good' | 'easy') => void;
  interactive?: boolean;
  showStats?: boolean;
  className?: string;
}

export const GrammarLearningPath: React.FC<GrammarLearningPathProps> = ({
  learningPath,
  patternProgress = [],
  pathStats,
  onPatternClick,
  onStartLearning,
  onMarkAsStudied,
  interactive = true,
  showStats = true,
  className = ""
}) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [selectedPatternForSRS, setSelectedPatternForSRS] = useState<string | null>(null);

  // Helper functions for progress tracking
  const getPatternProgress = (patternId: string): PatternProgress | undefined => {
    return patternProgress.find(p => p.pattern_id === patternId);
  };

  const getMasteryColor = (masteryLevel: number) => {
    if (masteryLevel >= 4) return "text-green-600";
    if (masteryLevel >= 3) return "text-yellow-600";
    if (masteryLevel >= 2) return "text-orange-600";
    return "text-red-600";
  };

  const getNextReviewStatus = (nextReviewDate?: string) => {
    if (!nextReviewDate) return { text: "Not studied", color: "text-gray-500", urgent: false };
    
    const now = new Date();
    const reviewDate = new Date(nextReviewDate);
    const diffTime = reviewDate.getTime() - now.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays < 0) return { text: "Review overdue", color: "text-red-600", urgent: true };
    if (diffDays === 0) return { text: "Review today", color: "text-blue-600", urgent: true };
    if (diffDays === 1) return { text: "Review tomorrow", color: "text-yellow-600", urgent: false };
    return { text: `Review in ${diffDays} days`, color: "text-green-600", urgent: false };
  };

  const calculateStepProgress = (allPatterns: string[]) => {
    const completedCount = allPatterns.filter(patternName => {
      const progress = patternProgress.find(p => p.pattern_name === patternName);
      return progress?.is_completed || false;
    }).length;
    return { completed: completedCount, total: allPatterns.length };
  };

  const handleSRSGrade = (patternId: string, grade: 'again' | 'hard' | 'good' | 'easy') => {
    if (onMarkAsStudied) {
      onMarkAsStudied(patternId, grade);
      setSelectedPatternForSRS(null);
    }
  };
  
  // Handle empty or invalid learning path
  if (!learningPath || learningPath.length === 0) {
    return (
      <Card className={`learning-path-card ${className}`}>
        <CardContent className="text-center py-12">
          <Target className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No learning path found</h3>
          <p className="text-muted-foreground">
            No learning path could be generated for the selected patterns and level.
          </p>
        </CardContent>
      </Card>
    );
  }
  
  // Use the first learning path for now
  const selectedPath = learningPath[0];
  const allPatterns = [
    selectedPath.from_pattern, 
    ...(selectedPath.intermediate_patterns || []), 
    selectedPath.to_pattern
  ].filter(Boolean); // Remove any undefined/null patterns
  
  // Calculate real progress
  const stepProgress = calculateStepProgress(allPatterns);
  const progressPercentage = (stepProgress.completed / stepProgress.total) * 100;
  
  const handlePatternClick = (patternId: string) => {
    if (onPatternClick) {
      onPatternClick(patternId);
    }
  };

  const handleStartLearning = (patternId: string) => {
    if (onStartLearning) {
      onStartLearning(patternId);
    }
  };

  return (
    <Card className={`learning-path-card ${className}`}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Target className="w-5 h-5" />
            Learning Path
          </CardTitle>
          <Badge variant="outline">
            {stepProgress.completed}/{stepProgress.total} Complete
          </Badge>
        </div>
        
        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm text-muted-foreground">
            <span>Progress</span>
            <span>{Math.round(progressPercentage)}%</span>
          </div>
          <Progress value={progressPercentage} className="w-full h-3" />
        </div>

        {/* Learning Path Statistics */}
        {showStats && pathStats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4 p-4 bg-gray-50 rounded-lg">
            <div className="text-center">
              <div className="flex items-center justify-center mb-1">
                <Award className="w-4 h-4 text-blue-600 mr-1" />
                <span className="text-sm font-medium">Avg Mastery</span>
              </div>
              <p className="text-lg font-bold text-blue-600">
                {pathStats.average_mastery.toFixed(1)}/5
              </p>
            </div>
            <div className="text-center">
              <div className="flex items-center justify-center mb-1">
                <Clock className="w-4 h-4 text-green-600 mr-1" />
                <span className="text-sm font-medium">Est. Days</span>
              </div>
              <p className="text-lg font-bold text-green-600">
                {pathStats.estimated_completion_days}
              </p>
            </div>
            <div className="text-center">
              <div className="flex items-center justify-center mb-1">
                <BookOpen className="w-4 h-4 text-purple-600 mr-1" />
                <span className="text-sm font-medium">Study Time</span>
              </div>
              <p className="text-lg font-bold text-purple-600">
                {Math.round(pathStats.total_study_time_minutes / 60)}h
              </p>
            </div>
            <div className="text-center">
              <div className="flex items-center justify-center mb-1">
                <TrendingUp className="w-4 h-4 text-orange-600 mr-1" />
                <span className="text-sm font-medium">Patterns</span>
              </div>
              <p className="text-lg font-bold text-orange-600">
                {pathStats.total_patterns}
              </p>
            </div>
          </div>
        )}
      </CardHeader>
      
      <CardContent>
        <div className="learning-path-flow">
          {allPatterns.map((pattern, index) => {
            const patternId = (selectedPath.pattern_ids && selectedPath.pattern_ids[index]) || `pattern_${index}`;
            const progress = getPatternProgress(patternId) || patternProgress.find(p => p.pattern_name === pattern);
            const isFirst = index === 0;
            const isLast = index === allPatterns.length - 1;
            const isCompleted = progress?.is_completed || false;
            const isCurrent = !isCompleted && (index === 0 || (index > 0 && (getPatternProgress(selectedPath.pattern_ids?.[index - 1] || '') || patternProgress.find(p => p.pattern_name === allPatterns[index - 1]))?.is_completed));
            const reviewStatus = getNextReviewStatus(progress?.next_review_date);
            
            return (
              <div key={patternId} className="path-step">
                {/* Step Node */}
                <div 
                  className={`
                    step-node flex items-center gap-3 p-4 rounded-lg border transition-all cursor-pointer
                    ${isCurrent ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-200' : ''}
                    ${isCompleted ? 'border-green-500 bg-green-50' : ''}
                    ${reviewStatus.urgent ? 'border-orange-400 bg-orange-50' : ''}
                    ${!isCompleted && !isCurrent && !reviewStatus.urgent ? 'border-gray-200 hover:border-gray-300' : ''}
                  `}
                  onClick={() => handlePatternClick(patternId)}
                >
                  {/* Status Icon with Mastery */}
                  <div className="status-icon relative">
                    {isCompleted ? (
                      <div className="relative">
                        <CheckCircle className="w-8 h-8 text-green-600" />
                        {progress && progress.mastery_level > 0 && (
                          <div className="absolute -top-1 -right-1 flex items-center">
                            <Star className={`w-4 h-4 ${getMasteryColor(progress.mastery_level)} fill-current`} />
                            <span className="text-xs font-bold">{progress.mastery_level}</span>
                          </div>
                        )}
                      </div>
                    ) : isCurrent ? (
                      <div className="relative">
                        <Circle className="w-8 h-8 text-blue-600 fill-current animate-pulse" />
                        <div className="absolute inset-0 flex items-center justify-center">
                          <div className="w-3 h-3 bg-white rounded-full"></div>
                        </div>
                      </div>
                    ) : reviewStatus.urgent ? (
                      <div className="relative">
                        <Clock className="w-8 h-8 text-orange-600" />
                        <div className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
                      </div>
                    ) : (
                      <Circle className="w-8 h-8 text-gray-400" />
                    )}
                  </div>
                  
                  {/* Pattern Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="font-semibold text-gray-900 truncate">{pattern}</h4>
                      <Badge variant="outline" className="text-xs flex-shrink-0">
                        {isFirst ? 'Start' : isLast ? 'Target' : 'Step'}
                      </Badge>
                      {reviewStatus.urgent && (
                        <Badge variant="destructive" className="text-xs flex-shrink-0 animate-pulse">
                          Due
                        </Badge>
                      )}
                    </div>
                    
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <span>Pattern {index + 1}</span>
                      {progress && progress.study_count > 0 && (
                        <span className="flex items-center gap-1">
                          <BookOpen className="w-3 h-3" />
                          {progress.study_count} studies
                        </span>
                      )}
                      <span className={reviewStatus.color}>
                        {reviewStatus.text}
                      </span>
                    </div>

                    {progress && progress.last_studied && (
                      <p className="text-xs text-muted-foreground mt-1">
                        Last studied: {new Date(progress.last_studied).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                  
                  {/* Action Button */}
                  <div className="action-button flex flex-col gap-1">
                    {/* Primary Action */}
                    {isCurrent && onStartLearning && (
                      <Button 
                        size="sm" 
                        onClick={(e) => {
                          e.stopPropagation();
                          handleStartLearning(patternId);
                        }}
                        className="bg-blue-600 hover:bg-blue-700"
                      >
                        Study Now
                      </Button>
                    )}
                    
                    {reviewStatus.urgent && !isCurrent && onStartLearning && (
                      <Button 
                        size="sm" 
                        variant="outline"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleStartLearning(patternId);
                        }}
                        className="border-orange-400 text-orange-700 hover:bg-orange-50"
                      >
                        Review
                      </Button>
                    )}

                    {!isCompleted && !isCurrent && !reviewStatus.urgent && (
                      <Button variant="ghost" size="sm" disabled>
                        <BookOpen className="w-4 h-4" />
                      </Button>
                    )}

                    {/* SRS Quick Study */}
                    {interactive && onMarkAsStudied && progress && selectedPatternForSRS !== patternId && (
                      <Button 
                        size="sm"
                        variant="outline"
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedPatternForSRS(patternId);
                        }}
                        className="text-xs py-1 h-auto"
                      >
                        <CheckCircle className="w-3 h-3 mr-1" />
                        Quick
                      </Button>
                    )}

                    {/* SRS Grade Buttons */}
                    {selectedPatternForSRS === patternId && (
                      <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleSRSGrade(patternId, 'hard')}
                          className="text-xs p-1 h-auto text-orange-600"
                          title="Hard"
                        >
                          H
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleSRSGrade(patternId, 'good')}
                          className="text-xs p-1 h-auto text-blue-600"
                          title="Good"
                        >
                          G
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleSRSGrade(patternId, 'easy')}
                          className="text-xs p-1 h-auto text-green-600"
                          title="Easy"
                        >
                          E
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
                
                {/* Arrow Connector */}
                {index < allPatterns.length - 1 && (
                  <div className="connector flex justify-center py-2">
                    <ArrowRight className="w-5 h-5 text-gray-400" />
                  </div>
                )}
              </div>
            );
          })}
        </div>
        
        {/* Path Summary */}
        <div className="path-summary mt-4 p-3 bg-gray-50 rounded-lg">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">
              From: <strong>{selectedPath.from_pattern}</strong>
            </span>
            <span className="text-muted-foreground">
              To: <strong>{selectedPath.to_pattern}</strong>
            </span>
          </div>
          <div className="text-xs text-muted-foreground mt-1">
            Path length: {selectedPath.path_length} steps
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default GrammarLearningPath;
