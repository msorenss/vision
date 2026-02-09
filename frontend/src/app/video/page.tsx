"use client";

import type { ChangeEvent, DragEvent } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useTranslation } from "@/components/I18nProvider";
import { ThemeToggle } from "@/components/ThemeToggle";
import { LanguageSelector } from "@/components/LanguageSelector";
import { useToast } from "@/components/Toast";
import { FilterSelector } from "@/components/FilterSelector";
import styles from "./video.module.css";

/* ------------------------------------------------------------------ */
/* Types                                                              */
/* ------------------------------------------------------------------ */

type Detection = {
  class_id: number;
  label: string;
  score: number;
  box: { x1: number; y1: number; x2: number; y2: number };
};

type FrameResult = {
  frame_index: number;
  timestamp_ms: number;
  detections: Detection[];
  privacy_applied: boolean;
  privacy_faces: number;
};

type VideoSummary = {
  total_frames_analysed: number;
  total_detections: number;
  unique_labels: string[];
  label_counts: Record<string, number>;
  privacy_total_faces: number;
};

type VideoInferResponse = {
  job_id: string;
  status: string;
  video_width: number;
  video_height: number;
  fps: number;
  duration_ms: number;
  frame_interval: number;
  frames: FrameResult[];
  summary: VideoSummary;
  error?: string | null;
};

type JobStatus = {
  job_id: string;
  status: string;
  progress: number;
  frames_done: number;
  frames_total: number;
  error?: string | null;
};

/* ------------------------------------------------------------------ */
/* Constants                                                          */
/* ------------------------------------------------------------------ */

const DEFAULT_API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";
const LS_API_BASE_KEY = "vision.apiBase";

const DETECTION_COLORS = [
  "#003057", "#d36000", "#1a8754", "#4a9eff", "#c41230",
  "#004d8c", "#ff8533", "#2ecc71", "#6db3ff", "#e74c3c",
];

/* ------------------------------------------------------------------ */
/* Page                                                               */
/* ------------------------------------------------------------------ */

export default function VideoPage() {
  const { t } = useTranslation();
  const toast = useToast();

  const [apiBase, setApiBase] = useState(DEFAULT_API_BASE);

  // Upload state
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [isDragActive, setIsDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Job state
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [result, setResult] = useState<VideoInferResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Frame navigation
  const [selectedFrame, setSelectedFrame] = useState(0);

  // Filter
  const [activeFilter, setActiveFilter] = useState("default");

  // Export state
  const [exportBoxes, setExportBoxes] = useState(true);
  const [exportLabels, setExportLabels] = useState(true);
  const [exportPrivacy, setExportPrivacy] = useState(true);
  const [rendering, setRendering] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [renderDone, setRenderDone] = useState(false);

  // Load saved API base
  useEffect(() => {
    try {
      const v = window.localStorage.getItem(LS_API_BASE_KEY);
      if (v) setApiBase(v);
    } catch {
      // ignore
    }
  }, []);

  /* ---------------------------------------------------------------- */
  /* Upload video                                                     */
  /* ---------------------------------------------------------------- */

  async function uploadVideo() {
    if (!videoFile) return;
    setBusy(true);
    setError(null);
    setResult(null);
    setJobStatus(null);
    setSelectedFrame(0);
    setPreviewUrl(null);
    setRenderDone(false);

    try {
      const form = new FormData();
      form.append("video", videoFile);

      const filterParam = activeFilter && activeFilter !== "default"
        ? `?filter_name=${encodeURIComponent(activeFilter)}`
        : "";
      const resp = await fetch(`${apiBase}/api/v1/infer/video${filterParam}`, {
        method: "POST",
        body: form,
      });
      const json = await resp.json();
      if (!resp.ok) {
        throw new Error(json?.detail ?? `HTTP ${resp.status}`);
      }
      const jid = json.job_id as string;
      setJobId(jid);
      setJobStatus(json as JobStatus);

      // Start SSE polling
      pollStatus(jid);
    } catch (e) {
      const msg = String(e);
      setError(msg);
      toast.error(msg);
      setBusy(false);
    }
  }

  async function pollStatus(jid: string) {
    try {
      const evtSource = new EventSource(
        `${apiBase}/api/v1/infer/video/status/${jid}`
      );

      evtSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as JobStatus;
          setJobStatus(data);

          if (data.status === "done" || data.status === "error") {
            evtSource.close();
            if (data.status === "done") {
              fetchResult(jid);
            } else {
              setError(data.error ?? t("video.error"));
              toast.error(data.error ?? t("video.error"));
              setBusy(false);
            }
          }
        } catch {
          // ignore parse errors
        }
      };

      evtSource.onerror = () => {
        evtSource.close();
        // Fallback: poll via fetch
        pollFallback(jid);
      };
    } catch {
      pollFallback(jid);
    }
  }

  async function pollFallback(jid: string) {
    const interval = setInterval(async () => {
      try {
        const resp = await fetch(
          `${apiBase}/api/v1/infer/video/result/${jid}`
        );
        if (resp.status === 202) {
          // Still processing – update status
          return;
        }
        clearInterval(interval);
        if (resp.ok) {
          const json = (await resp.json()) as VideoInferResponse;
          setResult(json);
          toast.success(t("video.done"));
        } else {
          const json = await resp.json();
          const msg = json?.detail ?? t("video.error");
          setError(msg);
          toast.error(msg);
        }
        setBusy(false);
      } catch {
        clearInterval(interval);
        setBusy(false);
      }
    }, 1500);
  }

  async function fetchResult(jid: string) {
    try {
      const resp = await fetch(
        `${apiBase}/api/v1/infer/video/result/${jid}`
      );
      if (resp.ok) {
        const json = (await resp.json()) as VideoInferResponse;
        setResult(json);
        toast.success(t("video.done"));
      } else {
        const json = await resp.json();
        setError(json?.detail ?? t("video.error"));
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  /* ---------------------------------------------------------------- */
  /* Export / Render                                                  */
  /* ---------------------------------------------------------------- */

  async function startRender() {
    if (!jobId) return;
    setRendering(true);
    setRenderDone(false);
    setPreviewUrl(null);

    try {
      const params = new URLSearchParams({
        boxes: String(exportBoxes),
        labels: String(exportLabels),
        privacy: String(exportPrivacy),
      });
      const resp = await fetch(
        `${apiBase}/api/v1/infer/video/export/${jobId}?${params}`,
        { method: "POST" },
      );
      if (!resp.ok) {
        const json = await resp.json();
        throw new Error(json?.detail ?? `HTTP ${resp.status}`);
      }
      pollRender(jobId);
    } catch (e) {
      toast.error(String(e));
      setRendering(false);
    }
  }

  async function pollRender(jid: string) {
    const interval = setInterval(async () => {
      try {
        const resp = await fetch(
          `${apiBase}/api/v1/infer/video/export/${jid}`,
        );
        if (!resp.ok) {
          if (resp.status >= 500) {
            clearInterval(interval);
            setRendering(false);
            toast.error(t("video.error"));
          }
          return;
        }
        const ct = resp.headers.get("content-type") || "";
        if (ct.includes("video")) {
          // File is ready
          clearInterval(interval);
          setRendering(false);
          setRenderDone(true);
          setPreviewUrl(
            `${apiBase}/api/v1/infer/video/preview/${jid}`,
          );
          toast.success(t("video.exportReady"));
        } else {
          // JSON status — check for error
          const json = await resp.json();
          if (json.render_status === "error") {
            clearInterval(interval);
            setRendering(false);
            toast.error(json.render_error ?? t("video.error"));
          }
        }
      } catch {
        clearInterval(interval);
        setRendering(false);
      }
    }, 2000);
  }

  function downloadVideo() {
    if (!jobId) return;
    window.open(
      `${apiBase}/api/v1/infer/video/export/${jobId}`,
      "_blank",
    );
  }

  /* ---------------------------------------------------------------- */
  /* Drag & drop                                                      */
  /* ---------------------------------------------------------------- */

  const handleDrag = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDragIn = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer?.items?.length) setIsDragActive(true);
  }, []);

  const handleDragOut = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
  }, []);

  const handleDrop = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
    const files = e.dataTransfer?.files;
    if (files && files.length > 0) {
      const f = files[0];
      if (f.type.startsWith("video/")) {
        setVideoFile(f);
      }
    }
  }, []);

  const handleFileSelect = (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) setVideoFile(f);
  };

  /* ---------------------------------------------------------------- */
  /* Current frame data                                               */
  /* ---------------------------------------------------------------- */

  const currentFrame: FrameResult | null = useMemo(() => {
    if (!result || result.frames.length === 0) return null;
    return result.frames[Math.min(selectedFrame, result.frames.length - 1)];
  }, [result, selectedFrame]);

  const progressPct = useMemo(() => {
    if (!jobStatus) return 0;
    return Math.round(jobStatus.progress * 100);
  }, [jobStatus]);

  /* ---------------------------------------------------------------- */
  /* Render                                                           */
  /* ---------------------------------------------------------------- */

  return (
    <div className="page">
      {/* Header */}
      <header className="header">
        <div className="header-logo">
          <span style={{ fontSize: "1.5rem" }}>🎬</span>
          <span style={{ color: "var(--color-primary)" }}>Video Mode</span>
        </div>

        <nav className="header-nav">
          <Link href="/" className="btn btn-ghost">{t("nav.home")}</Link>
          <Link href="/video" className="btn btn-ghost">{t("video.title")}</Link>
          <Link href="/settings" className="btn btn-ghost">{t("nav.settings")}</Link>
        </nav>

        <div className="header-controls">
          <LanguageSelector />
          <ThemeToggle />
        </div>
      </header>

      {/* Main */}
      <main className={`container ${styles.mainContent}`}>
        <div className="flex items-center justify-between" style={{ marginBottom: "var(--space-6)" }}>
          <h1 style={{ margin: 0 }}>{t("video.title")}</h1>
          <div className={styles.filterWrapper}>
            <FilterSelector
              apiBase={apiBase}
              selectedFilter={activeFilter}
              onFilterChange={setActiveFilter}
            />
          </div>
        </div>

        {/* Upload + Progress row */}
        <div className={`grid-2 ${styles.uploadSection}`}>
          {/* Drop zone */}
          <div
            className={`drop-zone ${isDragActive ? "active" : ""}`}
            onDragEnter={handleDragIn}
            onDragLeave={handleDragOut}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="video/mp4,video/avi,video/quicktime,video/x-matroska,video/webm,.mp4,.avi,.mov,.mkv,.webm"
              onChange={handleFileSelect}
              style={{ display: "none" }}
              aria-label="Upload video file"
            />
            <div className="drop-zone-icon">🎥</div>
            <div style={{ textAlign: "center" }}>
              <p style={{ margin: 0, fontWeight: 500 }}>
                {isDragActive ? t("upload.dragActive") : t("video.dropHere")}
              </p>
              <p className="text-sm text-muted" style={{ marginTop: "var(--space-2)" }}>
                {t("upload.orClick")}
              </p>
            </div>
            <span className="text-xs text-muted">{t("video.supportedFormats")}</span>

            {videoFile && (
              <div className="badge badge-primary" style={{ marginTop: "var(--space-2)" }}>
                {videoFile.name} ({(videoFile.size / 1024 / 1024).toFixed(1)} MB)
              </div>
            )}
          </div>

          {/* Actions + Progress */}
          <div className="card animate-fade-in">
            <h3 style={{ marginBottom: "var(--space-4)" }}>{t("video.upload")}</h3>

            <button
              onClick={uploadVideo}
              disabled={!videoFile || busy}
              className="btn btn-primary w-full"
              style={{ marginBottom: "var(--space-4)" }}
            >
              {busy ? (
                <>
                  <span className="spinner spinner-sm" />
                  {t("video.processing")}
                </>
              ) : (
                t("infer.run")
              )}
            </button>

            {/* Progress bar */}
            {jobStatus && busy && (
              <div className={styles.progressSection}>
                <div className="flex justify-between text-sm">
                  <span>{t("video.progress", { done: jobStatus.frames_done, total: jobStatus.frames_total })}</span>
                  <span>{progressPct}%</span>
                </div>
                <div className="progress" style={{ marginTop: "var(--space-2)" }}>
                  <div
                    className="progress-bar"
                    style={{ width: `${progressPct}%`, transition: "width 0.3s" }}
                  />
                </div>
              </div>
            )}

            {/* Error */}
            {error && (
              <div className={styles.errorBox}>
                {error}
              </div>
            )}
          </div>
        </div>

        {/* Results */}
        {result && (
          <div className={styles.resultsSection}>

            {/* ---- Video Player ---- */}
            {previewUrl && (
              <div className="card animate-slide-up" style={{ marginBottom: "var(--space-6)" }}>
                <h3 style={{ marginBottom: "var(--space-4)" }}>
                  {t("video.preview")}
                </h3>
                <div className={styles.videoPlayerWrapper}>
                  <video
                    key={previewUrl}
                    controls
                    className={styles.videoPlayer}
                    src={previewUrl}
                  >
                    {t("video.noSupport")}
                  </video>
                </div>
              </div>
            )}

            {/* ---- Export Controls ---- */}
            <div className="card animate-slide-up" style={{ marginBottom: "var(--space-6)" }}>
              <h3 style={{ marginBottom: "var(--space-4)" }}>{t("video.export")}</h3>

              <div className={styles.exportControls}>
                <label className={styles.exportOption}>
                  <input
                    type="checkbox"
                    checked={exportBoxes}
                    onChange={(e) => setExportBoxes(e.target.checked)}
                  />
                  <span>{t("video.exportBoxes")}</span>
                </label>
                <label className={styles.exportOption}>
                  <input
                    type="checkbox"
                    checked={exportLabels}
                    onChange={(e) => setExportLabels(e.target.checked)}
                    disabled={!exportBoxes}
                  />
                  <span>{t("video.exportLabels")}</span>
                </label>
                <label className={styles.exportOption}>
                  <input
                    type="checkbox"
                    checked={exportPrivacy}
                    onChange={(e) => setExportPrivacy(e.target.checked)}
                  />
                  <span>{t("video.exportPrivacy")}</span>
                </label>
              </div>

              <div className="flex gap-2" style={{ marginTop: "var(--space-4)" }}>
                <button
                  onClick={startRender}
                  disabled={rendering}
                  className="btn btn-primary"
                >
                  {rendering ? (
                    <>
                      <span className="spinner spinner-sm" />
                      {t("video.rendering")}
                    </>
                  ) : (
                    t("video.renderVideo")
                  )}
                </button>

                {renderDone && (
                  <button
                    onClick={downloadVideo}
                    className="btn btn-secondary"
                  >
                    {t("video.download")}
                  </button>
                )}
              </div>

              {renderDone && (
                <div className={styles.exportHint}>
                  {t("video.exportReady")}
                </div>
              )}
            </div>

            {/* Summary card */}
            <div className="card animate-slide-up" style={{ marginBottom: "var(--space-6)" }}>
              <h3 style={{ marginBottom: "var(--space-4)" }}>{t("video.summary")}</h3>
              <div className={styles.summaryGrid}>
                <div className={styles.summaryItem}>
                  <span className="text-sm text-muted">{t("video.frames", { count: "" })}</span>
                  <span className={styles.summaryValue}>{result.summary.total_frames_analysed}</span>
                </div>
                <div className={styles.summaryItem}>
                  <span className="text-sm text-muted">{t("video.detections", { count: "" })}</span>
                  <span className={styles.summaryValue}>{result.summary.total_detections}</span>
                </div>
                <div className={styles.summaryItem}>
                  <span className="text-sm text-muted">{t("video.uniqueLabels")}</span>
                  <span className={styles.summaryValue}>{result.summary.unique_labels.length}</span>
                </div>
                <div className={styles.summaryItem}>
                  <span className="text-sm text-muted">FPS</span>
                  <span className={styles.summaryValue}>{result.fps.toFixed(1)}</span>
                </div>
              </div>

              {/* Label distribution */}
              {result.summary.unique_labels.length > 0 && (
                <div style={{ marginTop: "var(--space-4)" }}>
                  <div className="flex flex-wrap gap-2">
                    {result.summary.unique_labels.map((label, i) => (
                      <span
                        key={label}
                        className="badge"
                        style={{
                          background: `${DETECTION_COLORS[i % DETECTION_COLORS.length]}20`,
                          color: DETECTION_COLORS[i % DETECTION_COLORS.length],
                          border: `1px solid ${DETECTION_COLORS[i % DETECTION_COLORS.length]}40`,
                        }}
                      >
                        {label}: {result.summary.label_counts[label]}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Frame navigator */}
            <div className="card animate-slide-up">
              <h3 style={{ marginBottom: "var(--space-4)" }}>{t("video.frameNav")}</h3>

              {result.frames.length > 0 ? (
                <>
                  {/* Slider */}
                  <div className={styles.frameSlider}>
                    <input
                      type="range"
                      min={0}
                      max={result.frames.length - 1}
                      value={selectedFrame}
                      onChange={(e) => setSelectedFrame(Number(e.target.value))}
                      className={styles.slider}
                    />
                    <div className="flex justify-between text-sm text-muted">
                      <span>
                        {t("video.frame", { index: currentFrame?.frame_index ?? 0 })}
                      </span>
                      <span>
                        {t("video.timestamp")}: {currentFrame ? (currentFrame.timestamp_ms / 1000).toFixed(2) : 0}s
                      </span>
                      <span>
                        {selectedFrame + 1} / {result.frames.length}
                      </span>
                    </div>
                  </div>

                  {/* Frame detections */}
                  {currentFrame && (
                    <div style={{ marginTop: "var(--space-4)" }}>
                      <div className="flex justify-between items-center" style={{ marginBottom: "var(--space-3)" }}>
                        <span className="font-medium">
                          {t("results.title")}
                        </span>
                        {currentFrame.detections.length > 0 && (
                          <span className="badge badge-success">
                            {t("results.objects", { count: currentFrame.detections.length })}
                          </span>
                        )}
                      </div>

                      {currentFrame.privacy_applied && (
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "var(--space-2)",
                            padding: "var(--space-2) var(--space-3)",
                            marginBottom: "var(--space-3)",
                            background: "var(--color-bg-tertiary)",
                            borderRadius: "var(--radius-md)",
                            borderLeft: "4px solid var(--color-primary)",
                            fontSize: "var(--font-size-sm)",
                          }}
                        >
                          <span>🔒</span>
                          <span>{t("privacy.facesBlurred", { count: currentFrame.privacy_faces })}</span>
                        </div>
                      )}

                      {currentFrame.detections.length > 0 ? (
                        <div className="flex flex-col gap-2">
                          {currentFrame.detections.map((det, idx) => (
                            <div
                              key={idx}
                              style={{
                                padding: "var(--space-3)",
                                background: "var(--color-bg-tertiary)",
                                borderRadius: "var(--radius-md)",
                                borderLeft: `4px solid ${DETECTION_COLORS[idx % DETECTION_COLORS.length]}`,
                              }}
                            >
                              <div className="flex justify-between items-center">
                                <span className="font-medium">{det.label}</span>
                                <span
                                  className="badge"
                                  style={{
                                    background: `${DETECTION_COLORS[idx % DETECTION_COLORS.length]}30`,
                                    color: DETECTION_COLORS[idx % DETECTION_COLORS.length],
                                  }}
                                >
                                  {(det.score * 100).toFixed(1)}%
                                </span>
                              </div>
                              <div className="progress" style={{ marginTop: "var(--space-2)", height: "4px" }}>
                                <div
                                  className="progress-bar"
                                  style={{
                                    width: `${det.score * 100}%`,
                                    background: DETECTION_COLORS[idx % DETECTION_COLORS.length],
                                  }}
                                />
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="text-center text-muted" style={{ padding: "var(--space-4) 0" }}>
                          <p>{t("results.noDetections")}</p>
                        </div>
                      )}
                    </div>
                  )}
                </>
              ) : (
                <div className="text-center text-muted" style={{ padding: "var(--space-8) 0" }}>
                  <div style={{ fontSize: "2rem", marginBottom: "var(--space-2)" }}>🎞️</div>
                  <p>{t("video.noFrames")}</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Empty state */}
        {!result && !busy && (
          <div className="card" style={{ textAlign: "center", padding: "var(--space-8)" }}>
            <div style={{ fontSize: "3rem", marginBottom: "var(--space-2)" }}>🎬</div>
            <p className="text-muted">{t("video.uploadOrDrag")}</p>
          </div>
        )}
      </main>
    </div>
  );
}
