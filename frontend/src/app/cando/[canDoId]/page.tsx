"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useSearchParams } from "next/navigation";
import {
  apiGet,
  apiPost,
  compileLessonV2Stream,
  getLessonGenerationStatus,
  regenerateLessonStage,
} from "@/lib/api";
import { DisplaySettingsPanel } from "@/components/settings/DisplaySettingsPanel";
import { LessonRootRenderer } from "@/components/lesson/LessonRootRenderer";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import { useToast } from "@/components/ToastProvider";
import type { LessonRoot } from "@/types/lesson-root";
import {
  recordCanDoEvidence,
  getCanDoProgress,
  markStageComplete,
  getCanDoEvidenceSummary,
  type CanDoProgress,
  type CanDoEvidenceSummary,
} from "@/lib/api/cando-progress";
import {
  CheckCircle,
  Circle,
  BookOpen,
  Eye,
  PenTool,
  MessageSquare,
} from "lucide-react";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import {
  DEFAULT_METALANGUAGE,
  DEFAULT_MODEL,
  POLL_INTERVAL_ACTIVE,
  POLL_INTERVAL_IDLE,
  log,
  logError,
  logWarn,
} from "@/lib/constants";
import { getStorageItem, setStorageItem } from "@/lib/utils/storage";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import { handleDatabaseError, isDatabaseError } from "@/lib/database-error-handler";

type StageStatus = {
  content: string;
  comprehension: string;
  production: string;
  interaction: string;
};

type CompilationProgress = {
  step: string;
  progress: number;
  message: string;
  stage?: string;
  substep?: string;
};

function CanDoDetailPage() {
  const params = useParams<{ canDoId: string }>();
  const searchParams = useSearchParams();
  const canDoId = decodeURIComponent(params.canDoId);
  const { applyLevelPreset } = useDisplaySettings();
  const { showToast } = useToast();
  const { handleError } = useErrorHandler();

  // Refs for polling to avoid dependency issues
  const stageStatusRef = useRef<StageStatus>({
    content: "pending",
    comprehension: "pending",
    production: "pending",
    interaction: "pending",
  });
  const refreshLessonDataRef = useRef<(() => Promise<void>) | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const refreshQueueRef = useRef<Promise<void> | null>(null);
  const sessionExpiresAtRef = useRef<Date | null>(null);

  // Core state
  const [lessonRootData, setLessonRootData] = useState<LessonRoot | null>(null);
  const [isCompilingV2, setIsCompilingV2] = useState(false);
  const [isGeneratingImages, setIsGeneratingImages] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lessonSessionId, setLessonSessionId] = useState<string>("");
  const [showSettings, setShowSettings] = useState(false);

  // Stage state
  const [activeStage, setActiveStage] = useState<
    "content" | "comprehension" | "production" | "interaction"
  >("content");
  const [progress, setProgress] = useState<CanDoProgress | null>(null);
  const [evidenceSummary, setEvidenceSummary] =
    useState<CanDoEvidenceSummary | null>(null);
  const [loadingProgress, setLoadingProgress] = useState(false);

  // Pre-lesson kit state
  const [prelessonKitAvailable, setPrelessonKitAvailable] = useState<
    boolean | null
  >(null);
  const [prelessonKitUsage, setPrelessonKitUsage] = useState<{
    words?: { used?: string[]; count?: number; total?: number; required?: number; meets_requirement?: boolean };
    grammar?: { used?: string[]; count?: number; total?: number; required?: number; meets_requirement?: boolean };
    phrases?: { used?: string[]; count?: number; total?: number; required?: number; meets_requirement?: boolean };
    all_requirements_met?: boolean;
    usage_percentage?: number;
  } | null>(null);

  // Compilation progress
  const [compilationProgress, setCompilationProgress] =
    useState<CompilationProgress | null>(null);

  // Stage status (persisted to localStorage)
  const [stageStatus, setStageStatus] = useState<StageStatus>(() => {
    if (typeof window !== "undefined") {
      const saved = getStorageItem(canDoId);
      if (saved) {
        try {
          const parsed = JSON.parse(saved);
          stageStatusRef.current = parsed;
          return parsed;
        } catch {
          // Invalid JSON, use defaults
        }
      }
    }
    const defaults = {
      content: "pending",
      comprehension: "pending",
      production: "pending",
      interaction: "pending",
    };
    stageStatusRef.current = defaults;
    return defaults;
  });

  // Polling state
  const [pollingActive, setPollingActive] = useState(false);
  const [lastLessonId, setLastLessonId] = useState<number | null>(null);
  const [lastVersion, setLastVersion] = useState<number | null>(null);

  // Race condition protection for refreshLessonData
  const refreshQueue = useRef<Promise<void> | null>(null);
  
  // Session expiration tracking
  const sessionExpiresAt = useRef<Date | null>(null);

  // Update ref when stageStatus changes
  useEffect(() => {
    stageStatusRef.current = stageStatus;
  }, [stageStatus]);

  // Save stage status to localStorage whenever it changes
  useEffect(() => {
    if (typeof window !== "undefined") {
      setStorageItem(canDoId, JSON.stringify(stageStatus));
    }
  }, [stageStatus, canDoId]);

  // Apply level from URL query parameter
  useEffect(() => {
    const levelParam = searchParams.get("level");
    if (levelParam) {
      const level = parseInt(levelParam, 10);
      if (level >= 1 && level <= 6) {
        applyLevelPreset(level);
      }
    }
  }, [searchParams, applyLevelPreset]);

  // Optional: allow overriding the "fast" LLM model from the URL for quick A/B tests
  const fastModelOverride = searchParams.get("fastModel");

  // Helper function to parse and set lesson data
  const parseAndSetLessonData = useCallback(
    (lessonDetail: any): LessonRoot | null => {
      let lessonData: LessonRoot | null = null;

      // Case 1: Already in LessonRoot format {lesson: {...}}
      if (
        lessonDetail &&
        typeof lessonDetail === "object" &&
        lessonDetail.lesson
      ) {
        log("✅ Found lesson in LessonRoot format");
        lessonData = lessonDetail as LessonRoot;
      }
      // Case 2: Unwrapped structure (direct lesson with meta and cards)
      else if (
        lessonDetail &&
        typeof lessonDetail === "object" &&
        lessonDetail.meta &&
        lessonDetail.cards
      ) {
        log("📦 Wrapping unwrapped lesson data");
        lessonData = { lesson: lessonDetail };
      }
      // Case 3: Check if it's nested in lesson_plan property
      else if (lessonDetail?.lesson_plan) {
        const plan = lessonDetail.lesson_plan;
        if (plan?.lesson) {
          lessonData = plan as LessonRoot;
        } else if (plan?.meta && plan?.cards) {
          lessonData = { lesson: plan };
        }
      }

      return lessonData;
    },
    []
  );

  // Helper function to refresh lesson data (with race condition protection)
  const refreshLessonData = useCallback(async () => {
    try {
      const response = await apiGet<any>(
        `/api/v1/cando/lessons/list?can_do_id=${encodeURIComponent(
          canDoId
        )}&include_latest_content=true`
      );

      if (response?.lessons && response.lessons.length > 0) {
        const latestLesson = response.lessons[0];
        let lessonDetail = latestLesson.lesson || latestLesson;
        if (!latestLesson.lesson) {
          lessonDetail = await apiGet<any>(
            `/api/v1/cando/lessons/fetch/${latestLesson.id}`
          );
        }

        const lessonData = parseAndSetLessonData(lessonDetail);
        if (lessonData) {
          setLessonRootData(lessonData);

          // Update stage status from lesson metadata with defensive checks
          const generationStatus = lessonData?.lesson?.meta?.generation_status;
          if (generationStatus && typeof generationStatus === 'object') {
            const newStatus = {
              content: String(generationStatus.content || "pending"),
              comprehension: String(generationStatus.comprehension || "pending"),
              production: String(generationStatus.production || "pending"),
              interaction: String(generationStatus.interaction || "pending"),
            };
            setStageStatus(newStatus);
            stageStatusRef.current = newStatus;
          }

          // Extract pre-lesson kit info from existing lesson metadata
          if (lessonData.lesson?.meta) {
            const meta = lessonData.lesson.meta;
            if (meta.prelesson_kit_available !== undefined) {
              setPrelessonKitAvailable(meta.prelesson_kit_available);
            }
            if (meta.prelesson_kit_usage) {
              setPrelessonKitUsage(meta.prelesson_kit_usage);
            }
          }

          // Update lastLessonId and lastVersion for polling with null checks and validation
          if (latestLesson.id != null && latestLesson.version != null) {
            const lessonId = Number(latestLesson.id);
            const version = Number(latestLesson.version);
            if (lessonId > 0 && version > 0) {
              setLastLessonId(lessonId);
              setLastVersion(version);
            } else {
              logWarn("Invalid lesson ID or version:", { id: lessonId, version });
            }
          } else {
            logWarn("Lesson missing id or version:", latestLesson);
          }
        }
      }
    } catch (e: any) {
      logError("Failed to refresh lesson data:", e);
      
      // Handle database-specific errors
      if (isDatabaseError(e)) {
        const dbError = handleDatabaseError(e);
        if (dbError.shouldRefresh) {
          // For 409 conflicts, retry after a short delay
          setTimeout(() => {
            refreshLessonDataSafe();
          }, 1000);
        } else if (dbError.retryable && !error) {
          // For other retryable errors, show message but don't spam
          setError(dbError.message);
        } else if (!dbError.retryable) {
          setError(dbError.message);
        }
      } else {
        // Generic error handling - only set if no error already set
        const errorMessage = e?.response?.data?.detail || e?.message || "Failed to load lesson";
        if (!error) {
          // Check for CanDo not found errors and format them properly
          if (errorMessage.includes("cando_not_found") || errorMessage.includes("CanDo not found") || errorMessage.includes("not found in database") || errorMessage.toLowerCase().includes("cando")) {
            setError(
              `CanDo descriptor "${canDoId}" not found in database.\n\n` +
              `The CanDo descriptor must exist in Neo4j before a lesson can be created.\n\n` +
              `Please create the CanDo descriptor first using:\n` +
              `• The API endpoint: /api/v1/cando/create\n` +
              `• Or click the "Create CanDo Descriptor" button below`
            );
          } else {
            setError(errorMessage);
          }
        }
      }
    }
  }, [canDoId, parseAndSetLessonData, error]);

  // Store refreshLessonData in ref for polling
  useEffect(() => {
    refreshLessonDataRef.current = refreshLessonData;
  }, [refreshLessonData]);

  // Safe refresh function that prevents race conditions
  const refreshLessonDataSafe = useCallback(async () => {
    // If there's already a refresh in progress, wait for it
    if (refreshQueueRef.current) {
      await refreshQueueRef.current;
      return;
    }
    // Start new refresh and store in queue
    refreshQueueRef.current = refreshLessonData();
    try {
      await refreshQueueRef.current;
    } finally {
      refreshQueueRef.current = null;
    }
  }, [refreshLessonData]);

  // Check and refresh session if expired
  const checkSessionExpiration = useCallback(async (): Promise<string> => {
    const currentSessionId = lessonSessionId;
    
    // If no session, create one
    if (!currentSessionId) {
      const sessionResponse = await apiPost<{ session_id: string }>(
        "/api/v1/cando/lessons/session/create",
        { can_do_id: canDoId }
      );
      if (sessionResponse?.session_id) {
        setLessonSessionId(sessionResponse.session_id);
        // Set expiration to 2 hours from now (default TTL)
        sessionExpiresAtRef.current = new Date(Date.now() + 2 * 60 * 60 * 1000);
        return sessionResponse.session_id;
      }
      throw new Error("Failed to create session");
    }

    // Check if session is expired (with 5 minute buffer)
    if (sessionExpiresAtRef.current) {
      const bufferTime = 5 * 60 * 1000; // 5 minutes
      if (new Date() >= new Date(sessionExpiresAtRef.current.getTime() - bufferTime)) {
        logWarn("Session expired or expiring soon, refreshing...");
        try {
          // Try to get session info to check expiration
          const sessionInfo = await apiGet<any>(
            `/api/v1/cando/lessons/session/${currentSessionId}`
          );
          if (sessionInfo?.expires_at) {
            const expiresAt = new Date(sessionInfo.expires_at);
            if (new Date() >= expiresAt) {
              // Session expired, create new one
              const newSession = await apiPost<{ session_id: string }>(
                "/api/v1/cando/lessons/session/create",
                { can_do_id: canDoId }
              );
              if (newSession?.session_id) {
                setLessonSessionId(newSession.session_id);
                sessionExpiresAtRef.current = new Date(Date.now() + 2 * 60 * 60 * 1000);
                return newSession.session_id;
              }
            } else {
              // Update expiration time
              sessionExpiresAtRef.current = expiresAt;
              return currentSessionId;
            }
          }
        } catch (e: any) {
          // Session not found or error, create new one
          logWarn("Session check failed, creating new session:", e);
          const newSession = await apiPost<{ session_id: string }>(
            "/api/v1/cando/lessons/session/create",
            { can_do_id: canDoId }
          );
          if (newSession?.session_id) {
            setLessonSessionId(newSession.session_id);
            sessionExpiresAtRef.current = new Date(Date.now() + 2 * 60 * 60 * 1000);
            return newSession.session_id;
          }
        }
      } else {
        // Session still valid
        return currentSessionId;
      }
    }

    // If no expiration tracking, assume valid but set default expiration
    if (!sessionExpiresAtRef.current) {
      sessionExpiresAtRef.current = new Date(Date.now() + 2 * 60 * 60 * 1000);
    }
    
    return currentSessionId;
  }, [canDoId, lessonSessionId]);

  // Polling mechanism for checking generation status when SSE connection is lost
  useEffect(() => {
    if (!pollingActive || !lastLessonId || !lastVersion) return;
    
    // Validate version before polling
    if (lastVersion <= 0 || lastLessonId <= 0) {
      logWarn("Invalid lesson ID or version for polling:", { lastLessonId, lastVersion });
      setPollingActive(false);
      return;
    }

    const getPollInterval = () => {
      const hasGenerating = Object.values(stageStatus).some(
        (s) => s === "generating" || s === "pending"
      );
      return hasGenerating ? 5000 : 10000;
    };

    let pollInterval: NodeJS.Timeout | null = null;

    const poll = async () => {
      try {
        const statusResponse = await apiGet<any>(
          `/api/v1/cando/lessons/generation-status?lesson_id=${lastLessonId}&version=${lastVersion}`
        );

        if (statusResponse?.generation_status) {
          const status = statusResponse.generation_status;
          const newStatus = {
            content: status.content || "pending",
            comprehension: status.comprehension || "pending",
            production: status.production || "pending",
            interaction: status.interaction || "pending",
          };

          const hasChanges = Object.keys(newStatus).some(
            (key) =>
              newStatus[key as keyof typeof newStatus] !==
              stageStatus[key as keyof typeof stageStatus]
          );

          if (hasChanges) {
            setStageStatus(newStatus);

            if (
              status.comprehension === "complete" &&
              stageStatus.comprehension !== "complete"
            ) {
              log("📊 Polling detected comprehension stage complete");
              await refreshLessonDataSafe();
            }
            if (
              status.production === "complete" &&
              stageStatus.production !== "complete"
            ) {
              log("📊 Polling detected production stage complete");
              await refreshLessonDataSafe();
            }
            if (
              status.interaction === "complete" &&
              stageStatus.interaction !== "complete"
            ) {
              log("📊 Polling detected interaction stage complete");
              setPollingActive(false);
              await refreshLessonDataSafe();
            }

            const allComplete = Object.values(newStatus).every((s) => {
              if (s === "complete") return true;
              if (typeof s === "string" && s.startsWith("failed")) return true;
              return false;
            });

            if (allComplete) {
              setPollingActive(false);
            }
          }
        }
      } catch (err: any) {
        logError("Polling error:", err);
        
        // Handle database errors during polling
        if (isDatabaseError(err)) {
          const dbError = handleDatabaseError(err);
          if (dbError.status === 409) {
            // Conflict - refresh and continue polling
            await refreshLessonDataSafe();
          } else if (dbError.status === 503) {
            // Service unavailable - pause polling briefly
            logWarn("Database unavailable, pausing polling");
            setPollingActive(false);
            setTimeout(() => {
              if (lastLessonId && lastVersion) {
                setPollingActive(true);
              }
            }, 5000);
          } else if (!dbError.retryable) {
            // Non-retryable error - stop polling
            setPollingActive(false);
          }
        }
      }

      if (pollingActive && lastLessonId && lastVersion) {
        pollInterval = setTimeout(poll, getPollInterval());
      }
    };

    pollInterval = setTimeout(poll, getPollInterval());

    return () => {
      if (pollInterval) clearTimeout(pollInterval);
    };
  }, [
    pollingActive,
    lastLessonId,
    lastVersion,
    // Removed stageStatus and refreshLessonDataSafe from deps - using refs instead
  ]);

  // Load LessonRoot V2
  const loadLessonV2 = useCallback(async () => {
    // Cancel any existing compilation
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    setError(null);
    setIsCompilingV2(true);

    // Create or get existing lesson session
    let sessionId = "";
    try {
      log("🔄 Creating/retrieving lesson session for:", canDoId);
      const sessionResponse = await apiPost<{ session_id: string }>(
        "/api/v1/cando/lessons/session/create",
        { can_do_id: canDoId }
      );
      if (sessionResponse && sessionResponse.session_id) {
        sessionId = sessionResponse.session_id;
        setLessonSessionId(sessionId);
        // Set expiration to 2 hours from now (default TTL)
        sessionExpiresAtRef.current = new Date(Date.now() + 2 * 60 * 60 * 1000);
        log("✅ Session created/retrieved:", sessionId);
      } else {
        throw new Error("No session_id in response");
      }
    } catch (sessionError: any) {
      if (sessionError.name === "AbortError") return;
      logError("⚠️ Failed to create session:", sessionError);
      
      // Handle database errors
      if (isDatabaseError(sessionError)) {
        const dbError = handleDatabaseError(sessionError);
        setError(dbError.message);
        showToast(dbError.message);
      } else {
        handleError(sessionError, {
          toastMessage: `Failed to create lesson session: ${sessionError.message || "Unknown error"}`,
          logPrefix: "Session creation",
        });
      }
      setIsCompilingV2(false);
      return;
    }

    if (!sessionId) {
      setError("Failed to create lesson session");
      setIsCompilingV2(false);
      return;
    }

    try {
      log("🔍 Fetching lesson list for:", canDoId);
      const response = await apiGet<any>(
        `/api/v1/cando/lessons/list?can_do_id=${encodeURIComponent(
          canDoId
        )}&include_latest_content=true`
      );
      log("📋 Lesson list response:", response);

      if (response?.lessons && response.lessons.length > 0) {
        const latestLesson = response.lessons[0];
        log("📚 Using lesson ID:", latestLesson.id);

        let lessonDetail = latestLesson.lesson || latestLesson;
        if (!latestLesson.lesson) {
          log("📥 Lesson content not included, fetching separately...");
          lessonDetail = await apiGet<any>(
            `/api/v1/cando/lessons/fetch/${latestLesson.id}`
          );
        }
        log("✅ Lesson data ready!", lessonDetail);

        const lessonData = parseAndSetLessonData(lessonDetail);
        if (!lessonData || !lessonData.lesson) {
          logError("❌ No lesson data in response");
          setError(
            "No lesson data found - the lesson may be empty or corrupted"
          );
          setIsCompilingV2(false);
          return;
        }

        // Extract pre-lesson kit info from existing lesson metadata
        if (lessonData.lesson?.meta) {
          const meta = lessonData.lesson.meta;
          if (meta.prelesson_kit_available !== undefined) {
            setPrelessonKitAvailable(meta.prelesson_kit_available);
          }
          if (meta.prelesson_kit_usage) {
            setPrelessonKitUsage(meta.prelesson_kit_usage);
          }
        }

        setLessonRootData(lessonData);
        setIsCompilingV2(false);
        return;
      }
      logWarn("⚠️ No lessons found in database");
    } catch (e: any) {
      if (e.name === "AbortError") return;
      logError("❌ Fetch failed:", e);
      
      // Handle database errors
      if (isDatabaseError(e)) {
        const dbError = handleDatabaseError(e);
        setError(dbError.message);
        if (dbError.shouldRefresh) {
          // For 409 conflicts, retry after a short delay
          setTimeout(() => {
            loadLessonV2();
          }, 1000);
        }
      } else {
        const errorMessage =
          e?.response?.data?.detail || e?.message || "Failed to load lesson";
        setError(errorMessage);
        logError("Error details:", errorMessage);
      }
    }

    // Compile new lesson if none exists
    try {
      let userId: string | null = null;
      try {
        const userResponse = await apiGet<any>("/api/v1/auth/me").catch(
          () => null
        );
        if (userResponse?.id) {
          userId = userResponse.id;
          log("👤 User ID for kit integration:", userId);
        }
      } catch (e) {
        logWarn("⚠️ Could not fetch user ID, continuing without kit:", e);
      }

      log("🏗️ Starting compilation for:", canDoId);

      const result = await compileLessonV2Stream(
        canDoId,
        DEFAULT_METALANGUAGE,
        DEFAULT_MODEL,
        (s) => {
          log("🟦 Compile status:", s);
          if (s?.prelesson_kit_available !== undefined) {
            setPrelessonKitAvailable(s.prelesson_kit_available);
          }
          if (s?.step && s?.progress !== undefined && s?.message) {
            setCompilationProgress({
              step: s.step,
              progress: s.progress,
              message: s.message,
              stage: s.stage,
              substep: s.substep,
            });
          }

          // Handle incremental stage completion events
          if (s?.event === "content_ready") {
            log("✅ Content stage ready!", s);
            const newStatus = { ...stageStatusRef.current, content: "complete" };
            setStageStatus(newStatus);
            stageStatusRef.current = newStatus;
            if (s.lesson_id && s.version) {
              setLastLessonId(s.lesson_id);
              setLastVersion(s.version);
              setPollingActive(true);
            }
            if (s.lesson) {
              const lessonData = parseAndSetLessonData(s.lesson);
              if (lessonData) {
                setLessonRootData(lessonData);
                setIsCompilingV2(false);
              }
            }
          }
          if (s?.event === "comprehension_ready") {
            log("✅ Comprehension stage ready!");
            const newStatus = { ...stageStatusRef.current, comprehension: "complete" };
            setStageStatus(newStatus);
            stageStatusRef.current = newStatus;
            refreshLessonDataSafe().catch((e) => logError("Failed to refresh after comprehension_ready:", e));
          }
          if (s?.event === "production_ready") {
            log("✅ Production stage ready!");
            const newStatus = { ...stageStatusRef.current, production: "complete" };
            setStageStatus(newStatus);
            stageStatusRef.current = newStatus;
            refreshLessonDataSafe().catch((e) => logError("Failed to refresh after production_ready:", e));
          }
          if (s?.event === "interaction_ready") {
            log("✅ Interaction stage ready!");
            const newStatus = { ...stageStatusRef.current, interaction: "complete" };
            setStageStatus(newStatus);
            stageStatusRef.current = newStatus;
            setPollingActive(false);
            refreshLessonDataSafe().catch((e) => logError("Failed to refresh after interaction_ready:", e));
          }

          // Handle failed stages
          if (s?.event?.endsWith("_failed")) {
            const stageName = s.event.replace("_failed", "");
            logError(`❌ ${stageName} stage failed:`, s.error);
            const newStatus = {
              ...stageStatusRef.current,
              [stageName]: `failed: ${s.error?.message || "Unknown error"}`,
            };
            setStageStatus(newStatus);
            stageStatusRef.current = newStatus;
            showToast(
              `${stageName.charAt(0).toUpperCase() + stageName.slice(1)} Stage Failed: ${
                s.error?.retryable
                  ? "This error may be temporary. You can retry this stage."
                  : s.error?.message || "An error occurred during generation"
              }`
            );
          }

          // Track stage generation status from lesson metadata
          if (s?.lesson?.lesson?.meta?.generation_status) {
            const status = s.lesson.lesson.meta.generation_status;
            const newStatus = {
              content: status.content || "pending",
              comprehension: status.comprehension || "pending",
              production: status.production || "pending",
              interaction: status.interaction || "pending",
            };
            setStageStatus(newStatus);
            stageStatusRef.current = newStatus;
          }
        },
        userId,
        fastModelOverride,
        true, // Enable incremental mode
        abortControllerRef.current?.signal // Pass AbortSignal
      );

      log("✅ Compilation stream result:", result);

      if (result?.prelesson_kit_usage) {
        setPrelessonKitUsage(result.prelesson_kit_usage);
      }

      await refreshLessonDataSafe();
    } catch (e: any) {
      if (e.name === "AbortError") return;
      logError("💥 Compilation failed:", e);
      
      // Handle database errors
      if (isDatabaseError(e)) {
        const dbError = handleDatabaseError(e);
        setError(dbError.message);
        showToast(dbError.message);
      } else {
        const errorMsg = e.message || "Failed to compile lesson";
        // Provide more helpful error messages
        if (errorMsg.includes("cando_not_found") || errorMsg.includes("CanDo not found") || errorMsg.includes("not found in database")) {
          setError(
            `CanDo descriptor "${canDoId}" not found in database.\n\n` +
            `The CanDo descriptor must exist in Neo4j before a lesson can be created.\n\n` +
            `Please create the CanDo descriptor first using:\n` +
            `• The API endpoint: /api/v1/cando/create\n` +
            `• Or click the "Create CanDo Descriptor" button below`
          );
        } else {
          setError(errorMsg);
        }
      }
    } finally {
      setIsCompilingV2(false);
      setCompilationProgress(null);
    }
  }, [canDoId, parseAndSetLessonData, refreshLessonData, fastModelOverride]);

  // Generate images for the lesson
  const generateImages = async () => {
    setError(null);
    setIsGeneratingImages(true);

    try {
      log("🖼️ Generating images for:", canDoId);
      const result = await apiPost<any>(
        `/api/v1/cando/lessons/generate-images?can_do_id=${encodeURIComponent(
          canDoId
        )}`
      );
      log("✅ Image generation result:", result);

      if (result.images_generated > 0) {
        log(
          `✅ Generated ${result.images_generated} image(s), reloading lesson...`
        );
        showToast(
          `✅ Successfully generated ${result.images_generated} image(s)! Reloading...`
        );
        await new Promise((resolve) => setTimeout(resolve, 1000));
        await loadLessonV2();
      } else if (result.message) {
        log("ℹ️", result.message);
        showToast(`ℹ️ ${result.message}`);
      } else {
        log("ℹ️ No images generated");
        showToast(
          "⚠️ No images were generated. Check if GEMINI_API_KEY is set or images already exist."
        );
      }
    } catch (e: any) {
      logError("💥 Image generation failed:", e);
      const errorMessage =
        e?.response?.data?.detail || e?.message || "Failed to generate images";
      const userMessage = errorMessage.includes("GEMINI_API_KEY")
        ? "❌ Image generation requires GEMINI_API_KEY to be set in backend .env file"
        : `❌ Image generation failed: ${errorMessage}`;
      showToast(userMessage);
      setError(userMessage);
    } finally {
      setIsGeneratingImages(false);
    }
  };

  // Retry a failed stage
  const retryFailedStage = async (
    stage: "comprehension" | "production" | "interaction"
  ) => {
    // Validate lesson ID and version
    if (!lastLessonId || !lastVersion || lastLessonId <= 0 || lastVersion <= 0) {
      showToast("Cannot Retry - Lesson ID not available. Please regenerate the lesson.");
      return;
    }

    try {
      setStageStatus((prev) => ({ ...prev, [stage]: "generating" }));
      showToast(`Regenerating ${stage} stage... This may take a few moments`);

      await regenerateLessonStage(lastLessonId, lastVersion, stage);
      setPollingActive(true);
      showToast(
        `The ${stage} stage is being regenerated. You'll be notified when it's complete.`
      );
    } catch (e: any) {
      logError(`Failed to retry ${stage} stage:`, e);
      const errorMessage = e?.response?.data?.detail || e?.message || "Unknown error";
      const newStatus = {
        ...stageStatusRef.current,
        [stage]: `failed: ${errorMessage}`,
      };
      setStageStatus(newStatus);
      stageStatusRef.current = newStatus;
      handleError(e, {
        toastMessage: `Retry Failed - ${errorMessage}`,
        logPrefix: "Stage retry",
      });
    }
  };

  // Regenerate lesson - force compilation
  const regenerateLesson = async () => {
    // Cancel any existing compilation
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    setError(null);
    setIsCompilingV2(true);
    setLessonSessionId(crypto.randomUUID());
    setPrelessonKitUsage(null);

    try {
      let userId: string | null = null;
      try {
        const userResponse = await apiGet<any>("/api/v1/auth/me").catch(
          () => null
        );
        if (userResponse?.id) {
          userId = userResponse.id;
        }
      } catch (e) {
        logWarn("⚠️ Could not fetch user ID, continuing without kit:", e);
      }

      log("🔄 Force regenerating lesson for:", canDoId);

      const result = await compileLessonV2Stream(
        canDoId,
        DEFAULT_METALANGUAGE,
        DEFAULT_MODEL,
        (s) => {
          log("🟦 Compile status:", JSON.stringify(s, null, 2));

          if (s?.prelesson_kit_available !== undefined) {
            setPrelessonKitAvailable(s.prelesson_kit_available);
          }
          if (s?.step && s?.progress !== undefined && s?.message) {
            setCompilationProgress({
              step: s.step,
              progress: s.progress,
              message: s.message,
              stage: s.stage,
              substep: s.substep,
            });
          }

          // Handle incremental stage completion events
          if (s?.event === "content_ready") {
            log("✅ Content stage ready!", s);
            const newStatus = { ...stageStatusRef.current, content: "complete" };
            setStageStatus(newStatus);
            stageStatusRef.current = newStatus;
            if (s.lesson_id && s.version) {
              setLastLessonId(s.lesson_id);
              setLastVersion(s.version);
              setPollingActive(true);
            }
            if (s.lesson) {
              const lessonData = parseAndSetLessonData(s.lesson);
              if (lessonData) {
                setLessonRootData(lessonData);
                setIsCompilingV2(false);
              }
            }
          }
          if (s?.event === "comprehension_ready") {
            log("✅ Comprehension stage ready!");
            const newStatus = { ...stageStatusRef.current, comprehension: "complete" };
            setStageStatus(newStatus);
            stageStatusRef.current = newStatus;
            refreshLessonDataSafe().catch((e) => logError("Failed to refresh after comprehension_ready:", e));
          }
          if (s?.event === "production_ready") {
            log("✅ Production stage ready!");
            const newStatus = { ...stageStatusRef.current, production: "complete" };
            setStageStatus(newStatus);
            stageStatusRef.current = newStatus;
            refreshLessonDataSafe().catch((e) => logError("Failed to refresh after production_ready:", e));
          }
          if (s?.event === "interaction_ready") {
            log("✅ Interaction stage ready!");
            const newStatus = { ...stageStatusRef.current, interaction: "complete" };
            setStageStatus(newStatus);
            stageStatusRef.current = newStatus;
            setPollingActive(false);
            refreshLessonDataSafe().catch((e) => logError("Failed to refresh after interaction_ready:", e));
          }

          // Handle failed stages
          if (s?.event?.endsWith("_failed")) {
            const stageName = s.event.replace("_failed", "");
            logError(`❌ ${stageName} stage failed:`, s.error);
            const newStatus = {
              ...stageStatusRef.current,
              [stageName]: `failed: ${s.error?.message || "Unknown error"}`,
            };
            setStageStatus(newStatus);
            stageStatusRef.current = newStatus;
            showToast(
              `${stageName.charAt(0).toUpperCase() + stageName.slice(1)} Stage Failed`
            );
          }

          // Track stage generation status from lesson metadata
          if (s?.lesson?.lesson?.meta?.generation_status) {
            const status = s.lesson.lesson.meta.generation_status;
            const newStatus = {
              content: status.content || "pending",
              comprehension: status.comprehension || "pending",
              production: status.production || "pending",
              interaction: status.interaction || "pending",
            };
            setStageStatus(newStatus);
            stageStatusRef.current = newStatus;
          }
        },
        userId,
        fastModelOverride,
        true, // Enable incremental mode
        abortControllerRef.current?.signal // Pass AbortSignal
      );

      log(
        "✅ Regeneration stream result:",
        JSON.stringify(result, null, 2)
      );

      if (result?.prelesson_kit_usage) {
        setPrelessonKitUsage(result.prelesson_kit_usage);
      }

      if (result) {
        showToast(
          `Content Stage Ready - Lesson ID: ${result?.lesson_id || "N/A"}, remaining stages generating...`
        );
      }

      if (result?.lesson) {
        const lessonData = parseAndSetLessonData(result.lesson);
        if (lessonData) {
          setLessonRootData(lessonData);
          return;
        }
      }

      await refreshLessonDataSafe();

      // Validate lesson ID and version before setting
      if (result?.lesson_id && result?.version) {
        const lessonId = Number(result.lesson_id);
        const version = Number(result.version);
        if (lessonId > 0 && version > 0) {
          setLastLessonId(lessonId);
          setLastVersion(version);
          setPollingActive(true);
        } else {
          logWarn("Invalid lesson ID or version from regeneration:", { lessonId, version });
        }
      }
    } catch (e: any) {
      if (e.name === "AbortError") {
        log("Regeneration cancelled");
        return;
      }
      logError("💥 Regeneration failed:", e);
      const errorMessage = e.message || "Failed to regenerate lesson";
      setError(errorMessage);
      handleError(e, {
        toastMessage: `Compilation Failed - ${errorMessage}`,
        logPrefix: "Regeneration",
      });
    } finally {
      setIsCompilingV2(false);
      setCompilationProgress(null);
    }
  };

  // Load progress and evidence summary
  const loadProgress = useCallback(async () => {
    if (!canDoId) return;

    try {
      setLoadingProgress(true);

      const [progressData, evidenceData] = await Promise.all([
        getCanDoProgress(canDoId, lessonSessionId || undefined),
        getCanDoEvidenceSummary(canDoId, 10).catch(() => null),
      ]);
      setProgress(progressData);
      setEvidenceSummary(evidenceData);

      // Set active stage to next recommended or first incomplete
      if (progressData.next_recommended_stage) {
        const recommended = progressData.next_recommended_stage as
          | "content"
          | "comprehension"
          | "production"
          | "interaction";
        setActiveStage(recommended);
      } else if (progressData.stages && !progressData.stages.content?.completed) {
        setActiveStage("content");
      } else if (
        progressData.stages &&
        !progressData.stages.comprehension?.completed
      ) {
        setActiveStage("comprehension");
      } else if (
        progressData.stages &&
        !progressData.stages.production?.completed
      ) {
        setActiveStage("production");
      } else if (
        progressData.stages &&
        !progressData.stages.interaction?.completed
      ) {
        setActiveStage("interaction");
      } else {
        setActiveStage("content");
      }
    } catch (e: any) {
      logError("Failed to load progress:", e);
    } finally {
      setLoadingProgress(false);
    }
  }, [canDoId, lessonSessionId]);

  useEffect(() => {
    loadLessonV2();
  }, [canDoId, loadLessonV2]);

  useEffect(() => {
    if (lessonSessionId && canDoId) {
      loadProgress();
    }
  }, [lessonSessionId, canDoId, loadProgress]);

  // Handle stage complete with optimistic updates
  const handleStageComplete = async (
    stage: "content" | "comprehension" | "production" | "interaction"
  ) => {
    // Optimistic update
    const previousStatus = { ...stageStatusRef.current };
    const newStatus = { ...previousStatus, [stage]: "complete" };
    setStageStatus(newStatus);
    stageStatusRef.current = newStatus;

    try {
      await markStageComplete(canDoId, stage, lessonSessionId || undefined);
      await loadProgress();
      showToast(
        `✅ ${stage.charAt(0).toUpperCase() + stage.slice(1)} stage completed!`
      );
    } catch (e: any) {
      // Revert on error
      setStageStatus(previousStatus);
      stageStatusRef.current = previousStatus;
      logError("Failed to mark stage complete:", e);
      handleError(e, {
        toastMessage: `Failed to mark stage complete: ${e.message}`,
        logPrefix: "Stage completion",
      });
    }
  };

  // Error state
  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-6">
        <Card className="p-8 text-center border-red-500/30 bg-red-500/10">
          <CardHeader>
            <CardTitle className="text-xl mb-2 text-red-600">
              ❌ Error Loading Lesson
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-red-600 mb-4 whitespace-pre-wrap">{error}</p>
            <div className="flex gap-2 justify-center flex-wrap">
              <Button onClick={loadLessonV2} variant="outline">
                🔄 Retry
              </Button>
              {(error.includes("cando_not_found") || error.includes("not found in database") || error.includes("CanDo descriptor") || error.toLowerCase().includes("cando")) && (
                <Button
                  onClick={() => {
                    window.open(`/cando/create?uid=${encodeURIComponent(canDoId)}`, "_blank");
                  }}
                  variant="default"
                >
                  ➕ Create CanDo Descriptor
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // No lesson data state - show generate button if not compiling and no error
  if (!lessonRootData && !isCompilingV2 && !error) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-6">
        <Card className="p-8 text-center">
          <CardHeader>
            <CardTitle className="text-xl mb-2">No Lesson Found</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground mb-6">
              This lesson hasn't been generated yet. Click the button below to create a personalized lesson for this CanDo.
            </p>
            <Button 
              onClick={loadLessonV2} 
              size="lg"
              className="min-w-[200px]"
            >
              🎓 Generate Lesson
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Loading/compiling state with detailed progress
  if (!lessonRootData && isCompilingV2) {
    // Determine current stage and substep from progress
    const currentStage = compilationProgress?.stage || compilationProgress?.step || "planning";
    const substep = compilationProgress?.substep || "";
    const stageNames: Record<string, string> = {
      "planning": "Planning",
      "content": "Content",
      "comprehension": "Comprehension",
      "production": "Production",
      "interaction": "Interaction",
      "finalizing": "Finalizing"
    };
    const substepNames: Record<string, string> = {
      "objective": "Objective",
      "vocabulary": "Vocabulary",
      "grammar": "Grammar",
      "formulaic_expressions": "Formulaic Expressions",
      "dialogue": "Dialogue",
      "culture": "Culture",
      "reading": "Reading",
      "exercises": "Exercises",
      "ai_tutor": "AI Tutor",
      "guided_dialogue": "Guided Dialogue",
      "production_exercises": "Production Exercises",
      "ai_evaluator": "AI Evaluator",
      "interactive_dialogue": "Interactive Dialogue",
      "activities": "Activities",
      "scenario": "AI Scenario"
    };

    return (
      <div className="max-w-7xl mx-auto px-4 py-6">
        <Card className="p-8">
          <div className="space-y-6">
            <div className="text-center">
              <h2 className="text-2xl font-bold mb-2">🚀 Generating Your Lesson</h2>
              {compilationProgress ? (
                <p className="text-foreground font-medium">{compilationProgress.message}</p>
              ) : (
                <p className="text-muted-foreground">
                  Please wait while we generate your personalized lesson...
                </p>
              )}
            </div>
            {compilationProgress && (
              <>
                {/* Overall Progress Bar */}
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Overall Progress</span>
                    <span className="text-muted-foreground font-medium">
                      {compilationProgress.progress}%
                    </span>
                  </div>
                  <div className="w-full bg-muted rounded-full h-3">
                    <div
                      className="bg-primary h-3 rounded-full transition-all duration-300"
                      style={{ width: `${compilationProgress.progress}%` }}
                    ></div>
                  </div>
                </div>
                {/* Stage-by-Stage Progress */}
                <div className="space-y-3">
                  <h3 className="text-sm font-semibold text-foreground">Stage Progress</h3>
                  {['content', 'comprehension', 'production', 'interaction'].map((stage) => {
                    const status = stageStatus[stage as keyof typeof stageStatus];
                    const isActive = currentStage === stage;
                    const isComplete = status === "complete";
                    const isFailed = typeof status === "string" && status.startsWith("failed");
                    const isPending = status === "pending" || status === "generating";
                    return (
                      <div key={stage} className="flex items-center gap-3">
                        <div className="w-32 text-sm capitalize font-medium">
                          {stage === "content"
                            ? "Content"
                            : stage === "comprehension"
                            ? "Comprehension"
                            : stage === "production"
                            ? "Production"
                            : "Interaction"}
                        </div>
                        <div className="flex-1 flex items-center gap-2">
                          {isComplete ? (
                            <>
                              <span className="text-green-600">✓</span>
                              <span className="text-sm text-muted-foreground">Complete</span>
                            </>
                          ) : isFailed ? (
                            <>
                              <span className="text-red-600">✗</span>
                              <span className="text-sm text-red-600">Failed</span>
                            </>
                          ) : isActive ? (
                            <>
                              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>
                              <span className="text-sm text-primary">
                                {substep
                                  ? `Generating ${substepNames[substep] || substep}...`
                                  : "Generating..."}
                              </span>
                            </>
                          ) : isPending ? (
                            <>
                              <div className="h-4 w-4 border-2 border-input rounded-full"></div>
                              <span className="text-sm text-muted-foreground">Waiting...</span>
                            </>
                          ) : (
                            <>
                              <div className="h-4 w-4 border-2 border-input rounded-full"></div>
                              <span className="text-sm text-muted-foreground">Pending</span>
                            </>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </>
            )}
          </div>
        </Card>
      </div>
    );
  }

  // Main render - lessonRootData must be non-null at this point
  if (!lessonRootData) {
    // This should never happen due to earlier checks, but TypeScript needs this
    return null;
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      {/* Pre-Lesson Kit Information */}
      {(prelessonKitAvailable !== null || prelessonKitUsage) && (
        <Card className="mb-6 border-blue-500/30 bg-blue-500/10">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <BookOpen className="w-5 h-5" />
              Pre-Lesson Kit Integration
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {prelessonKitAvailable !== null && (
              <div className="flex items-center gap-2">
                <Badge variant={prelessonKitAvailable ? "default" : "secondary"}>
                  {prelessonKitAvailable ? "✓ Kit Available" : "No Kit Found"}
                </Badge>
                <span className="text-sm text-muted-foreground">
                  {prelessonKitAvailable
                    ? "Pre-lesson kit was integrated into this compilation"
                    : "No pre-lesson kit found in your learning path"}
                </span>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 4-Stage Progress Tabs */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-lg">Learning Stages</CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs
            value={activeStage}
            onValueChange={(v) => setActiveStage(v as any)}
          >
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="content" className="flex items-center gap-2">
                {progress?.stages?.content?.completed ? (
                  <CheckCircle className="w-4 h-4 text-green-600" />
                ) : (
                  <Circle className="w-4 h-4" />
                )}
                <span className="hidden sm:inline">Content</span>
              </TabsTrigger>
              <TabsTrigger
                value="comprehension"
                className="flex items-center gap-2"
              >
                {progress?.stages?.comprehension?.completed ? (
                  <CheckCircle className="w-4 h-4 text-green-600" />
                ) : (
                  <Circle className="w-4 h-4" />
                )}
                <span className="hidden sm:inline">Comprehension</span>
              </TabsTrigger>
              <TabsTrigger
                value="production"
                className="flex items-center gap-2"
              >
                {progress?.stages?.production?.completed ? (
                  <CheckCircle className="w-4 h-4 text-green-600" />
                ) : (
                  <Circle className="w-4 h-4" />
                )}
                <span className="hidden sm:inline">Production</span>
              </TabsTrigger>
              <TabsTrigger
                value="interaction"
                className="flex items-center gap-2"
              >
                {progress?.stages?.interaction?.completed ? (
                  <CheckCircle className="w-4 h-4 text-green-600" />
                ) : (
                  <Circle className="w-4 h-4" />
                )}
                <span className="hidden sm:inline">Interaction</span>
              </TabsTrigger>
            </TabsList>

            {/* Content Stage */}
            <TabsContent value="content" className="mt-6">
              <Card>
                <CardHeader>
                  <CardTitle>Content Stage</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground mb-4">
                    Study the lesson materials: objective, vocabulary, grammar,
                    formulaic expressions, dialogue, and cultural notes.
                  </p>
                  <LessonRootRenderer
                    lessonData={lessonRootData}
                    sessionId={lessonSessionId}
                    onRegenerate={regenerateLesson}
                    stageStatus={stageStatus}
                    onRetryStage={retryFailedStage}
                    onDisplaySettings={() => setShowSettings(true)}
                    onGenerateImages={generateImages}
                    isRegenerating={isCompilingV2}
                    isGeneratingImages={isGeneratingImages}
                    activeStage="content"
                  />
                  {!progress?.stages?.content?.completed && (
                    <Button
                      onClick={() => handleStageComplete("content")}
                      className="mt-4"
                      variant="outline"
                    >
                      Mark Content Stage Complete
                    </Button>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {/* Comprehension Stage */}
            <TabsContent value="comprehension" className="mt-6">
              <Card>
                <CardHeader>
                  <CardTitle>Comprehension Stage</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground mb-4">
                    Practice understanding with input-based tasks: reading
                    comprehension, exercises, and AI-powered Q&A.
                  </p>
                  <LessonRootRenderer
                    lessonData={lessonRootData}
                    sessionId={lessonSessionId}
                    onRegenerate={regenerateLesson}
                    stageStatus={stageStatus}
                    onRetryStage={retryFailedStage}
                    onDisplaySettings={() => setShowSettings(true)}
                    onGenerateImages={generateImages}
                    isRegenerating={isCompilingV2}
                    isGeneratingImages={isGeneratingImages}
                    activeStage="comprehension"
                  />
                  {!progress?.stages?.comprehension?.completed && (
                    <Button
                      onClick={() => handleStageComplete("comprehension")}
                      className="mt-4"
                      variant="outline"
                    >
                      Mark Comprehension Stage Complete
                    </Button>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {/* Production Stage */}
            <TabsContent value="production" className="mt-6">
              <Card>
                <CardHeader>
                  <CardTitle>Production Stage</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground mb-4">
                    Practice producing output: guided dialogue, production
                    exercises, and AI-powered evaluation.
                  </p>
                  <LessonRootRenderer
                    lessonData={lessonRootData}
                    sessionId={lessonSessionId}
                    onRegenerate={regenerateLesson}
                    stageStatus={stageStatus}
                    onRetryStage={retryFailedStage}
                    onDisplaySettings={() => setShowSettings(true)}
                    onGenerateImages={generateImages}
                    isRegenerating={isCompilingV2}
                    isGeneratingImages={isGeneratingImages}
                    activeStage="production"
                  />
                  {!progress?.stages?.production?.completed && (
                    <Button
                      onClick={() => handleStageComplete("production")}
                      className="mt-4"
                      variant="outline"
                    >
                      Mark Production Stage Complete
                    </Button>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {/* Interaction Stage */}
            <TabsContent value="interaction" className="mt-6">
              <Card>
                <CardHeader>
                  <CardTitle>Interaction Stage</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground mb-4">
                    Practice in real-world scenarios: interactive dialogue,
                    role-play activities, and AI scenario management.
                  </p>
                  <LessonRootRenderer
                    lessonData={lessonRootData}
                    sessionId={lessonSessionId}
                    onRegenerate={regenerateLesson}
                    stageStatus={stageStatus}
                    onRetryStage={retryFailedStage}
                    onDisplaySettings={() => setShowSettings(true)}
                    onGenerateImages={generateImages}
                    isRegenerating={isCompilingV2}
                    isGeneratingImages={isGeneratingImages}
                    activeStage="interaction"
                  />
                  {!progress?.stages?.interaction?.completed && (
                    <Button
                      onClick={() => handleStageComplete("interaction")}
                      className="mt-4"
                      variant="outline"
                    >
                      Mark Interaction Stage Complete
                    </Button>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Evidence Summary */}
      {evidenceSummary && evidenceSummary.total_attempts > 0 && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-lg">Progress Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">Total Attempts</p>
                <p className="text-2xl font-bold">
                  {evidenceSummary.total_attempts}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Correct Rate</p>
                <p className="text-2xl font-bold">
                  {(evidenceSummary.correct_rate * 100).toFixed(0)}%
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Mastery Level</p>
                <p className="text-2xl font-bold">
                  {evidenceSummary.mastery_level}/5
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Common Errors</p>
                <p className="text-sm">
                  {evidenceSummary.common_error_tags.slice(0, 3).join(", ") ||
                    "None"}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Display Settings Modal */}
      {showSettings && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-card rounded-lg max-w-2xl w-full mx-4">
            <DisplaySettingsPanel />
            <div className="p-4 border-t">
              <Button onClick={() => setShowSettings(false)} className="w-full">
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Export with ErrorBoundary wrapper
export default function CanDoDetailPageWithErrorBoundary() {
  return (
    <ErrorBoundary>
      <CanDoDetailPage />
    </ErrorBoundary>
  );
}
