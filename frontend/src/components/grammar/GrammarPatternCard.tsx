"use client";

import React from 'react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { BookOpen, Volume2, Users, Target } from 'lucide-react';

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

interface GrammarPatternCardProps {
  pattern: GrammarPattern;
  onStudy?: (patternId: string) => void;
  onPlayAudio?: (text: string) => void;
  showDetails?: boolean;
  className?: string;
}

export const GrammarPatternCard: React.FC<GrammarPatternCardProps> = ({
  pattern,
  onStudy,
  onPlayAudio,
  showDetails = true,
  className = ""
}) => {
  const getLevelColor = (textbook: string) => {
    const colorMap: Record<string, string> = {
      "入門(りかい)": "bg-green-100 text-green-800",
      "初級1(りかい)": "bg-blue-100 text-blue-800", 
      "初級2(りかい)": "bg-blue-200 text-blue-900",
      "初中級": "bg-yellow-100 text-yellow-800",
      "中級1": "bg-orange-100 text-orange-800",
      "中級2": "bg-red-100 text-red-800"
    };
    return colorMap[textbook] || "bg-gray-100 text-gray-800";
  };

  const getClassificationIcon = (classification: string) => {
    // Map classifications to appropriate icons
    const iconMap: Record<string, React.ReactNode> = {
      "説明": <BookOpen className="w-4 h-4" />,
      "時間的前後": <Target className="w-4 h-4" />,
      "様子・状態": <Users className="w-4 h-4" />,
      // Add more mappings as needed
    };
    return iconMap[classification] || <BookOpen className="w-4 h-4" />;
  };

  return (
    <Card className={`grammar-pattern-card hover:shadow-lg transition-shadow ${className}`}>
      <CardHeader className="pb-3">
        <div className="flex justify-between items-start">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <h3 className="text-xl font-bold text-gray-900">{pattern.pattern}</h3>
              {onPlayAudio && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onPlayAudio(pattern.pattern)}
                  className="p-1"
                >
                  <Volume2 className="w-4 h-4" />
                </Button>
              )}
            </div>
            <p className="text-muted-foreground italic">{pattern.patternRomaji}</p>
          </div>
          <div className="flex flex-col gap-1">
            <Badge className={getLevelColor(pattern.textbook)}>
              {pattern.textbook}
            </Badge>
            <span className="text-xs text-muted-foreground">#{pattern.sequenceNumber}</span>
          </div>
        </div>
      </CardHeader>
      
      <CardContent>
        <div className="space-y-4">
          {/* Example Section */}
          <div className="example-section">
            <p className="text-sm font-medium text-gray-600 mb-1">Example:</p>
            <div className="bg-gray-50 p-3 rounded-md">
              <p className="text-lg font-medium text-gray-900 mb-1">
                {pattern.exampleSentence}
              </p>
              <p className="text-sm text-muted-foreground italic">
                {pattern.exampleRomaji}
              </p>
            </div>
          </div>

          {/* Classification and Context */}
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline" className="flex items-center gap-1">
              {getClassificationIcon(pattern.classification)}
              {pattern.classification}
            </Badge>
            <Badge variant="secondary">{pattern.jfsCategory}</Badge>
          </div>

          {/* Textbook Form (if showing details) */}
          {showDetails && pattern.textbookForm && (
            <div className="textbook-form">
              <p className="text-sm font-medium text-gray-600 mb-1">Textbook Form:</p>
              <div className="text-sm text-gray-700">
                <p>{pattern.textbookForm}</p>
                <p className="text-muted-foreground italic">{pattern.textbookFormRomaji}</p>
              </div>
            </div>
          )}

          {/* Topic and Lesson Info */}
          {showDetails && (
            <div className="context-info text-xs text-muted-foreground">
              <p>📖 Topic: {pattern.topic}</p>
              <p>📝 Lesson: {pattern.lesson}</p>
            </div>
          )}

          {/* Action Button */}
          {onStudy && (
            <Button 
              onClick={() => onStudy(pattern.id)}
              className="w-full mt-3"
              variant="default"
            >
              Study This Pattern
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default GrammarPatternCard;
