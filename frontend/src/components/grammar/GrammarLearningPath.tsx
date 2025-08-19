"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { ArrowRight, CheckCircle, Circle, Target, BookOpen } from 'lucide-react';

interface LearningPath {
  from_pattern: string;
  to_pattern: string;
  path_length: number;
  intermediate_patterns: string[];
  pattern_ids: string[];
}

interface GrammarLearningPathProps {
  learningPath: LearningPath[];
  onPatternClick?: (patternId: string) => void;
  onStartLearning?: (patternId: string) => void;
  className?: string;
}

export const GrammarLearningPath: React.FC<GrammarLearningPathProps> = ({
  learningPath,
  onPatternClick,
  onStartLearning,
  className = ""
}) => {
  const [currentStep, setCurrentStep] = useState(0);
  
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
  
  // Calculate progress (for now, assume no patterns are completed)
  const completedSteps = 0; // This would come from user progress data
  const progressPercentage = (completedSteps / allPatterns.length) * 100;
  
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
            {completedSteps}/{allPatterns.length} Complete
          </Badge>
        </div>
        
        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm text-muted-foreground">
            <span>Progress</span>
            <span>{Math.round(progressPercentage)}%</span>
          </div>
          <Progress value={progressPercentage} className="w-full" />
        </div>
      </CardHeader>
      
      <CardContent>
        <div className="learning-path-flow">
          {allPatterns.map((pattern, index) => {
            const patternId = (selectedPath.pattern_ids && selectedPath.pattern_ids[index]) || `pattern_${index}`;
            const isFirst = index === 0;
            const isLast = index === allPatterns.length - 1;
            const isCurrent = index === 0; // For now, assume first pattern is current
            const isCompleted = false; // This would come from user progress data
            
            return (
              <div key={patternId} className="path-step">
                {/* Step Node */}
                <div 
                  className={`
                    step-node flex items-center gap-3 p-3 rounded-lg border transition-all cursor-pointer
                    ${isCurrent ? 'border-blue-500 bg-blue-50' : ''}
                    ${isCompleted ? 'border-green-500 bg-green-50' : ''}
                    ${!isCompleted && !isCurrent ? 'border-gray-200 hover:border-gray-300' : ''}
                  `}
                  onClick={() => handlePatternClick(patternId)}
                >
                  {/* Status Icon */}
                  <div className="status-icon">
                    {isCompleted ? (
                      <CheckCircle className="w-6 h-6 text-green-600" />
                    ) : isCurrent ? (
                      <Circle className="w-6 h-6 text-blue-600 fill-current" />
                    ) : (
                      <Circle className="w-6 h-6 text-gray-400" />
                    )}
                  </div>
                  
                  {/* Pattern Info */}
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="font-semibold text-gray-900">{pattern}</h4>
                      <Badge variant="outline" className="text-xs">
                        {isFirst ? 'Start' : isLast ? 'Target' : 'Step'}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">Pattern {index + 1}</p>
                  </div>
                  
                  {/* Action Button */}
                  <div className="action-button">
                    {isCurrent && onStartLearning && (
                      <Button 
                        size="sm" 
                        onClick={(e) => {
                          e.stopPropagation();
                          handleStartLearning(patternId);
                        }}
                      >
                        Study Now
                      </Button>
                    )}
                    {!isCompleted && !isCurrent && (
                      <Button variant="ghost" size="sm">
                        <BookOpen className="w-4 h-4" />
                      </Button>
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
