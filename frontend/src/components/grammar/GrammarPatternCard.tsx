"use client";

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { BookOpen, Volume2, Users, Target, Star, Clock, CheckCircle, Eye, EyeOff } from 'lucide-react';

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
  // Optional AI overview snippet if present on backend list response (not guaranteed)
  what_is?: string;
}

interface SRSData {
  mastery_level: number; // 1-5 scale
  next_review_date: string;
  interval_days: number;
  ease_factor: number;
  last_studied?: string;
}

interface GrammarPatternCardProps {
  pattern: GrammarPattern;
  srsData?: SRSData;
  onStudy?: (patternId: string) => void;
  onPlayAudio?: (text: string) => void;
  onMarkAsStudied?: (patternId: string, grade: 'again' | 'hard' | 'good' | 'easy') => void;
  showDetails?: boolean;
  showProgress?: boolean;
  interactive?: boolean;
  className?: string;
}

export const GrammarPatternCard: React.FC<GrammarPatternCardProps> = ({
  pattern,
  srsData,
  onStudy,
  onPlayAudio,
  onMarkAsStudied,
  showDetails = true,
  showProgress = true,
  interactive = true,
  className = ""
}) => {
  const [isFlipped, setIsFlipped] = useState(false);
  const [showSRSButtons, setShowSRSButtons] = useState(false);
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

  const getMasteryProgress = (srsData?: SRSData) => {
    if (!srsData) return 0;
    return (srsData.mastery_level / 5) * 100;
  };

  const getMasteryColor = (masteryLevel: number) => {
    if (masteryLevel >= 4) return "text-green-600";
    if (masteryLevel >= 3) return "text-yellow-600";
    if (masteryLevel >= 2) return "text-orange-600";
    return "text-red-600";
  };

  const getNextReviewStatus = (nextReviewDate?: string) => {
    if (!nextReviewDate) return { text: "Not studied", color: "text-gray-500" };
    
    const now = new Date();
    const reviewDate = new Date(nextReviewDate);
    const diffTime = reviewDate.getTime() - now.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays < 0) return { text: "Review overdue", color: "text-red-600" };
    if (diffDays === 0) return { text: "Review today", color: "text-blue-600" };
    if (diffDays === 1) return { text: "Review tomorrow", color: "text-yellow-600" };
    return { text: `Review in ${diffDays} days`, color: "text-green-600" };
  };

  const handleSRSGrade = (grade: 'again' | 'hard' | 'good' | 'easy') => {
    if (onMarkAsStudied) {
      onMarkAsStudied(pattern.id, grade);
      setShowSRSButtons(false);
    }
  };

  const reviewStatus = getNextReviewStatus(srsData?.next_review_date);
  const masteryProgress = getMasteryProgress(srsData);

  return (
    <Card className={`grammar-pattern-card hover:shadow-lg transition-all duration-300 ${className} ${isFlipped ? 'transform' : ''}`}>
      <CardHeader className="pb-3">
        {/* SRS Progress Bar */}
        {showProgress && srsData && (
          <div className="mb-3">
            <div className="flex justify-between items-center mb-1">
              <div className="flex items-center gap-2">
                <Star className={`w-4 h-4 ${getMasteryColor(srsData.mastery_level)}`} />
                <span className="text-sm font-medium">Mastery Level {srsData.mastery_level}/5</span>
              </div>
              <div className="flex items-center gap-1 text-xs">
                <Clock className="w-3 h-3" />
                <span className={reviewStatus.color}>{reviewStatus.text}</span>
              </div>
            </div>
            <Progress value={masteryProgress} className="h-2" />
          </div>
        )}
        
        <div className="flex justify-between items-start">
          <div className="flex-1">
            <CardTitle className="text-xl mb-2">
              <div className="flex items-center gap-2">
                <span>{pattern.pattern}</span>
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
              {interactive && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsFlipped(!isFlipped)}
                  className="p-1"
                  title={isFlipped ? "Show Japanese" : "Hide Japanese"}
                >
                  {isFlipped ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                </Button>
              )}
              </div>
            </CardTitle>
            <p className={`text-muted-foreground italic transition-opacity duration-300 ${isFlipped ? 'opacity-30' : 'opacity-100'}`}>
              {isFlipped ? '[Hidden - Click eye to reveal]' : pattern.pattern_romaji}
            </p>
          </div>
          <div className="flex flex-col gap-1">
            <Badge className={getLevelColor(pattern.textbook)}>
              {pattern.textbook}
            </Badge>
            <span className="text-xs text-muted-foreground">#{pattern.sequence_number}</span>
          </div>
        </div>
      </CardHeader>
      
      <CardContent>
        <div className="space-y-4">
          {/* Description (AI what_is) - optional if available; shown above Example */}
          {pattern.what_is && (
            <div className="description-section">
              <p className="text-sm font-medium text-gray-600 mb-1">Description:</p>
              <div className="bg-gray-50 p-3 rounded-md">
                <p className="text-sm text-gray-700 leading-relaxed">{pattern.what_is}</p>
              </div>
            </div>
          )}

          {/* Example Section */}
          <div className="example-section">
            <p className="text-sm font-medium text-gray-600 mb-1">Example:</p>
            <div className="bg-gray-50 p-3 rounded-md">
              <p className={`text-lg font-medium text-gray-900 mb-1 transition-opacity duration-300 ${isFlipped ? 'opacity-30' : 'opacity-100'}`}>
                {isFlipped ? '[Hidden - Click eye to reveal]' : pattern.example_sentence}
              </p>
              <p className={`text-sm text-muted-foreground italic transition-opacity duration-300 ${isFlipped ? 'opacity-30' : 'opacity-100'}`}>
                {isFlipped ? '[Hidden]' : pattern.example_romaji}
              </p>
            </div>
          </div>

          {/* Classification and Context */}
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline" className="flex items-center gap-1">
              {getClassificationIcon(pattern.classification)}
              {pattern.classification}
            </Badge>
            <Badge variant="secondary">{pattern.jfs_category}</Badge>
          </div>

          {/* Pattern structure (if showing details) */}
          {showDetails && pattern.textbook_form && (
            <div className="textbook-form">
              <p className="text-sm font-medium text-gray-600 mb-1">Pattern structure:</p>
              <div className="text-sm text-gray-700">
                <p>{pattern.textbook_form}</p>
                <p className="text-muted-foreground italic">{pattern.textbook_form_romaji}</p>
              </div>
            </div>
          )}

          

          {/* Action Buttons */}
          <div className="action-buttons space-y-3">
            {onStudy && (
              <Button 
                onClick={() => onStudy(pattern.id)}
                className="w-full"
                variant="default"
              >
                Study This Pattern
              </Button>
            )}

            {/* SRS Study Buttons */}
            {interactive && onMarkAsStudied && (
              <div className="srs-section">
                {!showSRSButtons ? (
                  <Button
                    onClick={() => setShowSRSButtons(true)}
                    className="w-full"
                    variant="outline"
                    size="sm"
                  >
                    <CheckCircle className="w-4 h-4 mr-2" />
                    Quick Study
                  </Button>
                ) : (
                  <div className="space-y-2">
                    <p className="text-sm font-medium text-center text-gray-700">How well did you know this?</p>
                    <div className="grid grid-cols-2 gap-2">
                      <Button
                        onClick={() => handleSRSGrade('again')}
                        variant="outline"
                        size="sm"
                        className="text-red-600 hover:bg-red-50"
                      >
                        Again
                      </Button>
                      <Button
                        onClick={() => handleSRSGrade('hard')}
                        variant="outline"
                        size="sm"
                        className="text-orange-600 hover:bg-orange-50"
                      >
                        Hard
                      </Button>
                      <Button
                        onClick={() => handleSRSGrade('good')}
                        variant="outline"
                        size="sm"
                        className="text-blue-600 hover:bg-blue-50"
                      >
                        Good
                      </Button>
                      <Button
                        onClick={() => handleSRSGrade('easy')}
                        variant="outline"
                        size="sm"
                        className="text-green-600 hover:bg-green-50"
                      >
                        Easy
                      </Button>
                    </div>
                    <Button
                      onClick={() => setShowSRSButtons(false)}
                      variant="ghost"
                      size="sm"
                      className="w-full"
                    >
                      Cancel
                    </Button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default GrammarPatternCard;
