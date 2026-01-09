"use client";
import React, { useCallback, useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  BookOpen,
  ChevronDown,
  ChevronRight,
  Filter,
  Loader2,
  Search,
  Target,
  TrendingUp,
  Users,
} from "lucide-react";
import GrammarPatternCard from "@/components/grammar/GrammarPatternCard";
import GrammarLearningPath from "@/components/grammar/GrammarLearningPath";
import { apiGet } from "@/lib/api";
import {
  getUserPatternProgress,
  type PatternProgress,
  recordStudyWithSRS,
} from "@/lib/api/grammar-progress";
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
  what_is?: string;
}
interface FilterOptions {
  level: string;
  classification: string;
  jfsCategory: string;
  search: string;
}
export default function GrammarPage() {
  const [patterns, setPatterns] = useState<GrammarPattern[]>([]);
  const [filteredPatterns, setFilteredPatterns] = useState<GrammarPattern[]>(
    [],
  );
  const [initialLoading, setInitialLoading] = useState(true);
  const [isFetching, setIsFetching] = useState(false);
  const [pageSize, setPageSize] = useState<number>(20);
  const [offset, setOffset] = useState<number>(0);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [filtersOpen, setFiltersOpen] = useState<boolean>(false);
  const [countLoading, setCountLoading] = useState<boolean>(false);
  const [searchInput, setSearchInput] = useState<string>("");
  const [filters, setFilters] = useState<FilterOptions>({
    level: "all",
    classification: "all",
    jfsCategory: "all",
    search: "",
  });

  // Progress tracking state
const [patternProgress, setPatternProgress] = useState<
    Record<string, PatternProgress>
  >({});

  // Available filter options
const [levels, setLevels] = useState<string[]>([]);
  const [classifications, setClassifications] = useState<string[]>([]);
  const [jfsCategories, setJfsCategories] = useState<string[]>([]);

  // Learning path state
const [selectedPattern, setSelectedPattern] = useState<string>("");
  const [learningPath, setLearningPath] = useState<Array<{
    from_pattern: string;
    to_pattern: string;
    path_length: number;
    intermediate_patterns: string[];
    pattern_ids: string[];
  }> | null>(null);
  const applyFilters = useCallback(() => {
    let filtered = patterns;
    if (filters.level && filters.level !== "all") {
      filtered = filtered.filter((p) => p.textbook === filters.level);
    }
if (filters.classification && filters.classification !== "all") {
      filtered = filtered.filter(
        (p) => p.classification === filters.classification,
      );
    }
if (filters.jfsCategory && filters.jfsCategory !== "all") {
      filtered = filtered.filter((p) => p.jfs_category === filters.jfsCategory);
    }
if (filters.search) {
      const searchTerm = filters.search.toLowerCase();
      filtered = filtered.filter(
        (p) =>
          // p.pattern.toLowerCase().includes(searchTerm) ||
          p.pattern_romaji.toLowerCase().includes(searchTerm) ||
          p.example_sentence.toLowerCase().includes(searchTerm) ||
          p.example_romaji.toLowerCase().includes(searchTerm),
      );
    }

    setFilteredPatterns(filtered);
  }, [patterns, filters]);

  useEffect(() => {
    // Initial load
    (async () => {
      // await
      loadGrammarData(true);
      setInitialLoading(false);
    })();
    loadFilterOptions();
    loadProgressData();
    loadTotalCount();
  }, []);

  useEffect(() => {
    applyFilters();
  }, [patterns, filters, applyFilters]);

  // Refetch from server when pagination or server-side filters change
useEffect(() => {
    if (!initialLoading) {
      loadGrammarData();
    }
  }, [
    // pageSize,
    // offset,
    // filters.level,
    // filters.classification,
    // filters.jfsCategory,
    // filters.search,
    // initialLoading,
  ]);

  // Debounce search to avoid blocking UI while typing
  useEffect(() => {
    const t = setTimeout(() => {
      setOffset(0);
      setFilters((prev) => ({ ...prev, search: searchInput }));
    }, 400);
    return () => clearTimeout(t);
  }, [searchInput]);

  // Recount total when filters/search change (independent of pagination);
  useEffect(() => {
    loadTotalCount();
  }, [
    // filters.level,
    // filters.classification,
    // filters.jfsCategory,
    // filters.search,
  ]);
  const loadGrammarData = async (isInitial: boolean = false) => {
    try {
      if (isInitial) {
        setInitialLoading(true);
      }
      setIsFetching(true);
      const params = new URLSearchParams();
      params.append("limit", String(pageSize));
      params.append("offset", String(offset));
      if (filters.level && filters.level !== "all") {
        params.append("level", filters.level);
      }
if (filters.classification && filters.classification !== "all") {
        params.append("classification", filters.classification);
      }
if (filters.jfsCategory && filters.jfsCategory !== "all") {
        params.append("jfs_category", filters.jfsCategory);
      }
if (filters.search) params.append("search", filters.search);
      const data = await apiGet<GrammarPattern[]>(
        `/api/v1/grammar/patterns?${params.toString()}`,
      );
      setPatterns(data);
    } catch (error: unknown) {
      console.error("Error loading grammar patterns:", error);
      if (
        (error as { response?: { status?: number } })?.response?.status === 401
      ) {
        // Redirect to login if not authenticated
        window.location.href = "/login";
        return;
      }
      setPatterns([]);
    }
finally {
      setIsFetching(false);
      if (isInitial) setInitialLoading(false);
    }
  };
  const loadTotalCount = async () => {
    try {
      setCountLoading(true);
      const params = new URLSearchParams();
      if (filters.level && filters.level !== "all") {
        params.append("level", filters.level);
      }
if (filters.classification && filters.classification !== "all") {
        params.append("classification", filters.classification);
      }
if (filters.jfsCategory && filters.jfsCategory !== "all") {
        params.append("jfs_category", filters.jfsCategory);
      }
if (filters.search) params.append("search", filters.search);
      const data = await apiGet<{ total: number }>(
        `/api/v1/grammar/patterns/count?${params.toString()}`,
      );
      setTotalCount(data.total || 0);
    } catch (e) {
      console.error("Error loading total count:", e);
      setTotalCount(0);
    } finally {
      setCountLoading(false);
    }
  };
  const loadFilterOptions = async () => {
    try {
      const [levelsData, classificationsData, categoriesData] =
        await Promise.all([
          apiGet<Array<{ name?: string }>>("/api/v1/grammar/levels"),
          apiGet<Array<{ name?: string }>>("/api/v1/grammar/classifications"),
          apiGet<Array<{ name?: string }>>("/api/v1/grammar/jfs-categories"),
        ]);

      setLevels(levelsData.map((l) => l.name || String(l)));
      setClassifications(classificationsData.map((c) => c.name || String(c)));
      setJfsCategories(categoriesData.map((j) => j.name || String(j)));
    } catch (error: unknown) {
      console.error("Error loading filter options:", error);
      if (
        (error as { response?: { status?: number } })?.response?.status === 401
      ) {
        // Redirect to login if not authenticated
        window.location.href = "/login";
        return;
      }
      // Set empty arrays on error
      setLevels([]);
      setClassifications([]);
      setJfsCategories([]);
    }
  };
  const loadProgressData = async () => {
    try {
      const progressData = await getUserPatternProgress();
      const progressMap: Record<string, PatternProgress> = {};
      progressData.forEach((progress) => {
        progressMap[progress.pattern_id] = progress;
      });
      setPatternProgress(progressMap);
    } catch (error: unknown) {
      console.error("Error loading progress data:", error);
      // Continue without progress data if not authenticated
      setPatternProgress({});
    }
  };
  const handleMarkAsStudied = async (
    patternId: string,
    grade: "again" | "hard" | "good" | "easy",
  ) => {
    try {
      const updatedProgress = await recordStudyWithSRS(patternId, grade, 30, 3); // Default 30 sec study time, confidence 3
      setPatternProgress((prev) => ({
        ...prev,
        [patternId]: updatedProgress,
      }));
    } catch (error: unknown) {
      console.error("Error recording study session:", error);
    }
  };
  const handlePatternStudy = (patternId: string) => {
    // Navigate to the dedicated study page for this pattern
    window.location.href = `/grammar/study/${patternId}`;
  };
  const handlePlayAudio = (text: string) => {
    // TODO: Implement text-to-speech
    console.log("Play audio for:", text);
  };
  const generateLearningPath = async (fromPattern: string, toLevel: string) => {
    try {
      const pathData = await apiGet<
        Array<{
          from_pattern: string;
          to_pattern: string;
          path_length: number;
          intermediate_patterns: string[];
          pattern_ids: string[];
        }>
      >(
        `/api/v1/grammar/learning-path?from_pattern=${fromPattern}&to_level=${encodeURIComponent(toLevel)}`
      );
      console.log("Learning path data received:", pathData);
      console.log("Current patterns loaded:", patterns.map((p) => p.id));
      setLearningPath(pathData);
    } catch (error: unknown) {
      console.error("Error generating learning path:", error);
      if (
        (error as { response?: { status?: number } })?.response?.status === 401
      ) {
        // Redirect to login if not authenticated
        window.location.href = "/login";
        return;
      }
      // Clear learning path on error
      setLearningPath(null);
    }
  };
  const clearFilters = () => {
    setFilters({
      level: "all",
      classification: "all",
      jfsCategory: "all",
      search: "",
    });
  };
  if (initialLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
            <p className="text-muted-foreground">Loading grammar patterns...</p>
          </div>
        </div>
      </div>
    );
  }
return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-foreground leading-tight">
          // Japanese Grammar Patterns
        </h1>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="browse" className="space-y-6">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="browse" className="flex items-center gap-2">
            <BookOpen className="w-4 h-4" />
            // Browse Patterns
          </TabsTrigger>
          <TabsTrigger
            value="learning-path"
            className="flex items-center gap-2"
          >
            <Target className="w-4 h-4" />
            // Learning Paths
          </TabsTrigger>
          <TabsTrigger
            value="recommendations"
            className="flex items-center gap-2"
          >
            <TrendingUp className="w-4 h-4" />
            // Recommendations
          </TabsTrigger>
        </TabsList>

        {/* Browse Patterns Tab */}
        <TabsContent value="browse" className="space-y-6">
          {/* Filters */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Filter className="w-5 h-5" />
                  // Filters
                </CardTitle>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setFiltersOpen(!filtersOpen)}
                  className="flex items-center gap-1"
                >
                  {filtersOpen ? (
                    <ChevronDown className="w-4 h-4" />
                  ) : (
                    <ChevronRight className="w-4 h-4" />
                  )}
                  {filtersOpen ? "Hide" : "Show"}
                </Button>
              </div>
            </CardHeader>
            {filtersOpen && (
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  {/* Search */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Search</label>
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                      <Input
                        placeholder="Search patterns..."
                        value={searchInput}
                        onChange={(e) => setSearchInput(e.target.value)}
                        className="pl-10"
                      />
                    </div>
                  </div>

                  {/* Level Filter */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Level</label>
                    <Select
                      value={filters.level}
                      onValueChange={(value) => {
                        setOffset(0);
                        setFilters((prev) => ({ ...prev, level: value }));
                      }}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="All levels" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All levels</SelectItem>
                        {levels.map((level) => (
                          <SelectItem key={level} value={level}>
                            {level}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Classification Filter */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Classification</label>
                    <Select
                      value={filters.classification}
                      onValueChange={(value) => {
                        setOffset(0);
                        setFilters((prev) => ({
                          ...prev,
                          classification: value,
                        }));
                      }}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="All types" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All types</SelectItem>
                        {classifications.map((classification) => (
                          <SelectItem
                            key={classification}
                            value={classification}
                          >
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
                      onValueChange={(value) => {
                        setOffset(0);
                        setFilters((prev) => ({ ...prev, jfsCategory: value }));
                      }}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="All topics" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All topics</SelectItem>
                        {jfsCategories.map((category) => (
                          <SelectItem key={category} value={category}>
                            {category}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="flex justify-end items-center mt-4">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setOffset(0);
                      setFilters({
                        level: "all",
                        classification: "all",
                        jfsCategory: "all",
                        search: "",
                      });
                    }}
                  >
                    // Clear Filters
                  </Button>
                </div>
              </CardContent>
            )}
          </Card>

          {/* Pagination Controls */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <span className="text-sm text-muted-foreground">Page size</span>
              <Select
                value={String(pageSize)}
                onValueChange={(v) => {
                  setOffset(0);
                  setPageSize(Number(v));
                }}
              >
                <SelectTrigger className="w-28">
                  <SelectValue placeholder="Page size" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="20">20</SelectItem>
                  <SelectItem value="50">50</SelectItem>
                  <SelectItem value="100">100</SelectItem>
                </SelectContent>
              </Select>
              <span className="text-sm text-muted-foreground flex items-center gap-2">
                {totalCount === 0
                  ? "Showing 0"
                  : `Showing ${Math.min(offset + 1, totalCount)}–${Math.min(
                      offset + patterns.length,
                      // totalCount,
                    )}`}{" "}
                of {totalCount} patterns
                {(isFetching || countLoading) && (
                  <Loader2 className="w-4 h-4 animate-spin" />
                )}
              </span>
            </div>
            <div className="flex items-center gap-2">
              {/* Numeric page buttons */}
              {(() => {
                const currentPage =
                  totalCount > 0 ? Math.floor(offset / pageSize) + 1 : 1;
                const totalPages = Math.max(
                  // 1,
                  Math.
                  ceil(totalCount / pageSize || 1),
                );
                const items: Array<number | string> = [];
                const add = (v: number | string) => items.push(v);
                const pushRange = (start: number, end: number) => {
                  for (let i = start; i <= end; i++) add(i);
                };
                if (totalPages <= 7) {
                  pushRange(1, totalPages);
                } else {
                  const showLeft = Math.max(2, currentPage - 1);
                  const showRight = Math.min(totalPages - 1, currentPage + 1);
                  add(1);
                  if (showLeft > 2) add("…");
                  pushRange(showLeft, showRight);
                  if (showRight < totalPages - 1) add("…");
                  add(totalPages);
                }
return (
                  <div className="flex items-center gap-1">
                    {items.map((it, idx) =>
                      typeof it === "number" ? (
                        <Button
                          key={`p-${it}-${idx}`}
                          variant={
                            it === Math.floor(offset / pageSize) + 1
                              ? "default"
                              : "outline"
                          }
                          size="sm"
                          onClick={() => setOffset((it - 1) * pageSize)}
                        >
                          {it}
                        </Button>
                      ) : (
                        <span
                          key={`e-${idx}`}
                          className="px-2 text-muted-foreground"
                        >
                          {it}
                        </span>
                      ),
                    )}
                  </div>
                );
              })()}
              <Button
                variant="outline"
                size="sm"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - pageSize))}
              >
                // Prev
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={offset + pageSize >= totalCount}
                onClick={() => setOffset(offset + pageSize)}
              >
                // Next
              </Button>
            </div>
          </div>

          {/* Pattern Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredPatterns.map((pattern) => {
              const progress = patternProgress[pattern.id];
              const srsData = progress
                ? {
                    mastery_level: progress.mastery_level,
                    next_review_date: progress.next_review_date || "",
                    interval_days: Math.round(
                      (new Date(
                        progress.next_review_date || new Date()
                      ).getTime() -
                        new Date().getTime()) /
                        (1000 * 60 * 60 * 24)
                    ),
                    ease_factor: 2.5, // Default ease factor
                    last_studied: progress.last_studied,
                  }
                : undefined;
              return (
                <GrammarPatternCard
                  key={pattern.id}
                  pattern={pattern}
                  srsData={srsData}
                  onStudy={handlePatternStudy}
                  onPlayAudio={handlePlayAudio}
                  onMarkAsStudied={handleMarkAsStudied}
                  showDetails={false}
                  showProgress={true}
                  interactive={true}
                />
              );
            })}
          </div>

          {/* Empty State */}
          {filteredPatterns.length === 0 && (
            <Card>
              <CardContent className="text-center py-12">
                <BookOpen className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-foreground mb-2">
                  // No patterns found
                </h3>
                <p className="text-muted-foreground mb-4">
                  // Try adjusting your filters or search terms
                </p>
                <Button
                  variant="outline"
                  onClick={() => {
                    setOffset(0);
                    setFilters({
                      level: "all",
                      classification: "all",
                      jfsCategory: "all",
                      search: "",
                    });
                  }}
                >
                  // Clear All Filters
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
                  <Select
                    value={selectedPattern}
                    onValueChange={setSelectedPattern}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select starting pattern" />
                    </SelectTrigger>
                    <SelectContent>
                      {patterns.slice(0, 20).map((pattern) => (
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
                      {levels.map((level) => (
                        <SelectItem key={level} value={level}>
                          {level}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="flex items-end">
                  <Button
                    onClick={() =>
                      generateLearningPath(selectedPattern, "中級1")
                    }
                    disabled={!selectedPattern}
                    className="w-full"
                  >
                    // Generate Path
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
                // Personalized Recommendations
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground mb-4">
                // Based on your current level and learning progress, here are
                // recommended patterns to study next.
              </p>

              {/* TODO: Implement recommendations based on user progress */}
              <div className="text-center py-8">
                <Users className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                <p className="text-muted-foreground">
                  // Recommendations will be available once you start studying
                  // patterns
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
