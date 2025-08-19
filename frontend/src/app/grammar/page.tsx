"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Search, Filter, BookOpen, Target, Users, TrendingUp } from 'lucide-react';

import GrammarPatternCard from '@/components/grammar/GrammarPatternCard';
import GrammarLearningPath from '@/components/grammar/GrammarLearningPath';
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

interface FilterOptions {
  level: string;
  classification: string;
  jfsCategory: string;
  search: string;
}

export default function GrammarPage() {
  const [patterns, setPatterns] = useState<GrammarPattern[]>([]);
  const [filteredPatterns, setFilteredPatterns] = useState<GrammarPattern[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState<FilterOptions>({
    level: 'all',
    classification: 'all',
    jfsCategory: 'all',
    search: ''
  });
  
  // Available filter options
  const [levels, setLevels] = useState<string[]>([]);
  const [classifications, setClassifications] = useState<string[]>([]);
  const [jfsCategories, setJfsCategories] = useState<string[]>([]);
  
  // Learning path state
  const [selectedPattern, setSelectedPattern] = useState<string>('');
  const [learningPath, setLearningPath] = useState<Array<{
    from_pattern: string;
    to_pattern: string;
    path_length: number;
    intermediate_patterns: string[];
    pattern_ids: string[];
  }> | null>(null);

  const applyFilters = useCallback(() => {
    let filtered = patterns;

    if (filters.level && filters.level !== 'all') {
      filtered = filtered.filter(p => p.textbook === filters.level);
    }

    if (filters.classification && filters.classification !== 'all') {
      filtered = filtered.filter(p => p.classification === filters.classification);
    }

    if (filters.jfsCategory && filters.jfsCategory !== 'all') {
      filtered = filtered.filter(p => p.jfsCategory === filters.jfsCategory);
    }

    if (filters.search) {
      const searchTerm = filters.search.toLowerCase();
      filtered = filtered.filter(p => 
        p.pattern.toLowerCase().includes(searchTerm) ||
        p.patternRomaji.toLowerCase().includes(searchTerm) ||
        p.exampleSentence.toLowerCase().includes(searchTerm) ||
        p.exampleRomaji.toLowerCase().includes(searchTerm)
      );
    }

    setFilteredPatterns(filtered);
  }, [patterns, filters]);

  useEffect(() => {
    loadGrammarData();
    loadFilterOptions();
  }, []);

  useEffect(() => {
    applyFilters();
  }, [patterns, filters, applyFilters]);

  const loadGrammarData = async () => {
    try {
      setLoading(true);
      const data = await apiGet<GrammarPattern[]>('/api/v1/grammar/patterns?limit=100');
      setPatterns(data);
    } catch (error: unknown) {
      console.error('Error loading grammar patterns:', error);
      if ((error as {response?: {status?: number}})?.response?.status === 401) {
        // Redirect to login if not authenticated
        window.location.href = '/login';
        return;
      }
      setPatterns([]);
    } finally {
      setLoading(false);
    }
  };

  const loadFilterOptions = async () => {
    try {
      const [levelsData, classificationsData, categoriesData] = await Promise.all([
        apiGet<Array<{name?: string}>>('/api/v1/grammar/levels'),
        apiGet<Array<{name?: string}>>('/api/v1/grammar/classifications'),
        apiGet<Array<{name?: string}>>('/api/v1/grammar/jfs-categories')
      ]);
      
      setLevels(levelsData.map((l) => l.name || String(l)));
      setClassifications(classificationsData.map((c) => c.name || String(c)));
      setJfsCategories(categoriesData.map((j) => j.name || String(j)));
    } catch (error: unknown) {
      console.error('Error loading filter options:', error);
      if ((error as {response?: {status?: number}})?.response?.status === 401) {
        // Redirect to login if not authenticated
        window.location.href = '/login';
        return;
      }
      // Set empty arrays on error
      setLevels([]);
      setClassifications([]);
      setJfsCategories([]);
    }
  };

  const handlePatternStudy = (patternId: string) => {
    // Navigate to the dedicated study page for this pattern
    window.location.href = `/grammar/study/${patternId}`;
  };

  const handlePlayAudio = (text: string) => {
    // TODO: Implement text-to-speech
    console.log('Play audio for:', text);
  };

  const generateLearningPath = async (fromPattern: string, toLevel: string) => {
    try {
      const pathData = await apiGet<Array<{
        from_pattern: string;
        to_pattern: string;
        path_length: number;
        intermediate_patterns: string[];
        pattern_ids: string[];
      }>>(
        `/api/v1/grammar/learning-path?from_pattern=${fromPattern}&to_level=${encodeURIComponent(toLevel)}`
      );
      console.log('Learning path data received:', pathData);
      console.log('Current patterns loaded:', patterns.map(p => p.id));
      setLearningPath(pathData);
    } catch (error: unknown) {
      console.error('Error generating learning path:', error);
      if ((error as {response?: {status?: number}})?.response?.status === 401) {
        // Redirect to login if not authenticated
        window.location.href = '/login';
        return;
      }
      // Clear learning path on error
      setLearningPath(null);
    }
  };

  const clearFilters = () => {
    setFilters({
      level: 'all',
      classification: 'all',
      jfsCategory: 'all',
      search: ''
    });
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-muted-foreground">Loading grammar patterns...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Japanese Grammar Patterns</h1>
        <p className="text-muted-foreground">
          Explore {patterns.length} grammar patterns from the Marugoto textbook series
        </p>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="browse" className="space-y-6">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="browse" className="flex items-center gap-2">
            <BookOpen className="w-4 h-4" />
            Browse Patterns
          </TabsTrigger>
          <TabsTrigger value="learning-path" className="flex items-center gap-2">
            <Target className="w-4 h-4" />
            Learning Paths
          </TabsTrigger>
          <TabsTrigger value="recommendations" className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4" />
            Recommendations
          </TabsTrigger>
        </TabsList>

        {/* Browse Patterns Tab */}
        <TabsContent value="browse" className="space-y-6">
          {/* Filters */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Filter className="w-5 h-5" />
                Filters
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* Search */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">Search</label>
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <Input
                      placeholder="Search patterns..."
                      value={filters.search}
                      onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
                      className="pl-10"
                    />
                  </div>
                </div>

                {/* Level Filter */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">Level</label>
                  <Select 
                    value={filters.level} 
                    onValueChange={(value) => setFilters(prev => ({ ...prev, level: value }))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="All levels" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All levels</SelectItem>
                      {levels.map(level => (
                        <SelectItem key={level} value={level}>{level}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Classification Filter */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">Classification</label>
                  <Select 
                    value={filters.classification} 
                    onValueChange={(value) => setFilters(prev => ({ ...prev, classification: value }))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="All types" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All types</SelectItem>
                      {classifications.map(classification => (
                        <SelectItem key={classification} value={classification}>
                          {classification}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* JFS Category Filter */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">Topic</label>
                  <Select 
                    value={filters.jfsCategory} 
                    onValueChange={(value) => setFilters(prev => ({ ...prev, jfsCategory: value }))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="All topics" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All topics</SelectItem>
                      {jfsCategories.map(category => (
                        <SelectItem key={category} value={category}>{category}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
              {/* Clear Filters */}
              <div className="flex justify-between items-center mt-4">
                <p className="text-sm text-muted-foreground">
                  Showing {filteredPatterns.length} of {patterns.length} patterns
                </p>
                <Button variant="outline" size="sm" onClick={clearFilters}>
                  Clear Filters
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Pattern Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredPatterns.map(pattern => (
              <GrammarPatternCard
                key={pattern.id}
                pattern={pattern}
                onStudy={handlePatternStudy}
                onPlayAudio={handlePlayAudio}
                showDetails={true}
              />
            ))}
          </div>

          {/* Empty State */}
          {filteredPatterns.length === 0 && (
            <Card>
              <CardContent className="text-center py-12">
                <BookOpen className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">No patterns found</h3>
                <p className="text-muted-foreground mb-4">
                  Try adjusting your filters or search terms
                </p>
                <Button variant="outline" onClick={clearFilters}>
                  Clear All Filters
                </Button>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Learning Paths Tab */}
        <TabsContent value="learning-path" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Generate Learning Path</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">From Pattern</label>
                  <Select value={selectedPattern} onValueChange={setSelectedPattern}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select starting pattern" />
                    </SelectTrigger>
                    <SelectContent>
                      {patterns.slice(0, 20).map(pattern => (
                        <SelectItem key={pattern.id} value={pattern.id}>
                          {pattern.pattern}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                
                <div className="space-y-2">
                  <label className="text-sm font-medium">To Level</label>
                  <Select>
                    <SelectTrigger>
                      <SelectValue placeholder="Select target level" />
                    </SelectTrigger>
                    <SelectContent>
                      {levels.map(level => (
                        <SelectItem key={level} value={level}>{level}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                
                <div className="flex items-end">
                  <Button 
                    onClick={() => generateLearningPath(selectedPattern, '中級1')}
                    disabled={!selectedPattern}
                    className="w-full"
                  >
                    Generate Path
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Learning Path Display */}
          {learningPath && (
            <GrammarLearningPath
              learningPath={learningPath}
              onPatternClick={handlePatternStudy}
              onStartLearning={handlePatternStudy}
            />
          )}
        </TabsContent>

        {/* Recommendations Tab */}
        <TabsContent value="recommendations" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="w-5 h-5" />
                Personalized Recommendations
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground mb-4">
                Based on your current level and learning progress, here are recommended patterns to study next.
              </p>
              
              {/* TODO: Implement recommendations based on user progress */}
              <div className="text-center py-8">
                <Users className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                <p className="text-muted-foreground">
                  Recommendations will be available once you start studying patterns
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
