"use client";

import type { ChangeEvent, DragEvent } from "react";
import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import Link from "next/link";
import { useTranslation } from "@/components/I18nProvider";
import { ThemeToggle } from "@/components/ThemeToggle";
import { LanguageSelector } from "@/components/LanguageSelector";
import { useToast } from "@/components/Toast";
import { FilterSelector } from "@/components/FilterSelector";
import { WatcherStatusCard } from "@/components/WatcherStatus";
import styles from "./page.module.css";

type Detection = {
  class_id: number;
  label: string;
  score: number;
  box: { x1: number; y1: number; x2: number; y2: number };
};

type InferResponse = {
  model_path: string | null;
  image_width: number;
  image_height: number;
  detections: Detection[];
  filter_applied?: string | null;
  privacy_applied?: boolean | null;
  privacy_faces?: number | null;
};

const DEFAULT_API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";
const LS_API_BASE_KEY = "vision.apiBase";

// Volvo Cars color palette for detection boxes
const DETECTION_COLORS = [
  "#003057", "#d36000", "#1a8754", "#4a9eff", "#c41230",
  "#004d8c", "#ff8533", "#2ecc71", "#6db3ff", "#e74c3c"
];

export default function HomePage() {
  const { t } = useTranslation();
  const toast = useToast();

  const [apiBase, setApiBase] = useState(DEFAULT_API_BASE);
  const [health, setHealth] = useState<null | { ok: boolean }>(null);
  const [modelInfo, setModelInfo] = useState<null | {
    configured_model_path: string | null;
    loaded: boolean;
    detail?: string | null;
  }>(null);

  const [demoFiles, setDemoFiles] = useState<string[]>([]);
  const [selectedDemo, setSelectedDemo] = useState<string>("");

  const [file, setFile] = useState<File | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [result, setResult] = useState<InferResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [isDragActive, setIsDragActive] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [activeFilter, setActiveFilter] = useState("default");

  const imgRef = useRef<HTMLImageElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    try {
      const v = window.localStorage.getItem(LS_API_BASE_KEY);
      if (v) setApiBase(v);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    if (!file) return;
    const url = URL.createObjectURL(file);
    setImageUrl(url);
    setResult(null);
    setError(null);
    setZoom(1);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const refreshDemoFiles = useCallback(async () => {
    try {
      const r = await fetch(`${apiBase}/api/v1/demo/files`);
      const j = await r.json();
      const files = (j?.files ?? []) as string[];
      setDemoFiles(files);
      if (!files.includes(selectedDemo)) {
        setSelectedDemo(files[0] ?? "");
      }
    } catch {
      setDemoFiles([]);
    }
  }, [apiBase, selectedDemo]);

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${apiBase}/health`);
        const j = await r.json();
        setHealth(j);
      } catch {
        setHealth(null);
      }
    })();

    (async () => {
      try {
        const r = await fetch(`${apiBase}/api/v1/models`);
        const j = await r.json();
        setModelInfo(j);
      } catch {
        setModelInfo(null);
      }
    })();

    refreshDemoFiles();
  }, [apiBase, refreshDemoFiles]);

  // Auto-refresh demo file list
  useEffect(() => {
    if (busy) return;
    const id = window.setInterval(() => void refreshDemoFiles(), 5000);
    return () => window.clearInterval(id);
  }, [busy, refreshDemoFiles]);

  const canInfer = useMemo(() => !!file && !busy, [file, busy]);

  async function runInference() {
    if (!file) return;
    setBusy(true);
    setError(null);
    setResult(null);

    try {
      const form = new FormData();
      form.append("image", file);

      // Always use filtered endpoint to apply filter settings (including default min_confidence)
      const endpoint = `${apiBase}/api/v1/infer/filtered?filter_name=${encodeURIComponent(activeFilter)}`;

      const resp = await fetch(endpoint, {
        method: "POST",
        body: form
      });

      const json = await resp.json();
      if (!resp.ok) {
        const errMsg = json?.detail ?? t("notify.requestFailed", { status: resp.status });
        setError(errMsg);
        toast.error(errMsg);
        return;
      }
      setResult(json as InferResponse);
      // If privacy was applied, swap preview to anonymized image
      if (json.privacy_applied && file) {
        try {
          const anonForm = new FormData();
          anonForm.append("image", file);
          const anonResp = await fetch(
            `${apiBase}/api/v1/privacy/anonymize`,
            { method: "POST", body: anonForm }
          );
          if (anonResp.ok) {
            const blob = await anonResp.blob();
            setImageUrl(URL.createObjectURL(blob));
          }
        } catch {
          // Keep original preview on error
        }
      }
      toast.success(t("notify.inferenceComplete", { count: json.detections?.length ?? 0 }));
    } catch (e) {
      const errMsg = String(e);
      setError(errMsg);
      toast.error(errMsg);
    } finally {
      setBusy(false);
    }
  }

  async function runDemoInference() {
    if (!selectedDemo) return;
    setBusy(true);
    setError(null);
    setResult(null);

    try {
      // Always use filtered endpoint to apply filter settings (including default min_confidence)
      const endpoint = `${apiBase}/api/v1/demo/infer/filtered?name=${encodeURIComponent(selectedDemo)}&filter_name=${encodeURIComponent(activeFilter)}`;

      const resp = await fetch(endpoint);
      const json = await resp.json();
      if (!resp.ok) {
        const errMsg = json?.detail ?? t("notify.requestFailed", { status: resp.status });
        setError(errMsg);
        toast.error(errMsg);
        return;
      }

      setImageUrl(
        json.privacy_applied
          ? `${apiBase}/api/v1/demo/image/anonymized?name=${encodeURIComponent(selectedDemo)}`
          : `${apiBase}/api/v1/demo/image?name=${encodeURIComponent(selectedDemo)}`
      );
      setFile(null);
      setResult(json as InferResponse);
      setZoom(1);
      toast.success(t("notify.inferenceComplete", { count: json.detections?.length ?? 0 }));
    } catch (e) {
      const errMsg = String(e);
      setError(errMsg);
      toast.error(errMsg);
    } finally {
      setBusy(false);
    }
  }

  // Drag and drop handlers
  const handleDrag = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDragIn = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer?.items?.length) {
      setIsDragActive(true);
    }
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
      const droppedFile = files[0];
      if (droppedFile.type.startsWith("image/")) {
        setFile(droppedFile);
      }
    }
  }, []);

  const handleFileSelect = (e: ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected) {
      setFile(selected);
    }
  };

  // Draw detection boxes
  const draw = useCallback(() => {
    const img = imgRef.current;
    const canvas = canvasRef.current;
    if (!img || !canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const w = img.clientWidth;
    const h = img.clientHeight;
    canvas.width = w;
    canvas.height = h;

    ctx.clearRect(0, 0, w, h);

    if (!result) return;

    const sx = w / result.image_width;
    const sy = h / result.image_height;

    ctx.lineWidth = 2;
    ctx.font = "600 13px Inter, system-ui, sans-serif";

    result.detections.forEach((det, idx) => {
      const color = DETECTION_COLORS[idx % DETECTION_COLORS.length];

      const x1 = det.box.x1 * sx;
      const y1 = det.box.y1 * sy;
      const x2 = det.box.x2 * sx;
      const y2 = det.box.y2 * sy;

      const bw = x2 - x1;
      const bh = y2 - y1;

      // Box
      ctx.strokeStyle = color;
      ctx.fillStyle = `${color}20`;
      ctx.strokeRect(x1, y1, bw, bh);
      ctx.fillRect(x1, y1, bw, bh);

      // Label background
      const label = `${det.label} ${(det.score * 100).toFixed(0)}%`;
      const pad = 6;
      const tw = ctx.measureText(label).width;
      const th = 20;

      const labelY = Math.max(0, y1 - th - 2);

      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.roundRect(x1, labelY, tw + pad * 2, th, 4);
      ctx.fill();

      // Label text
      ctx.fillStyle = "#000";
      ctx.fillText(label, x1 + pad, labelY + 14);
    });
  }, [result]);

  useEffect(() => {
    draw();
  }, [result, imageUrl, zoom, draw]);

  return (
    <div className="page">
      {/* Header */}
      <header className="header">
        <div className="header-logo">
          {/* Logo */}
          <span className={styles.logoIcon}>👁️</span>
          <span className={styles.logoText}>
            Vision System
          </span>
        </div>

        <nav className="header-nav">
          <Link href="/" className="btn btn-ghost">{t("nav.home")}</Link>
          <Link href="/datasets" className="btn btn-ghost">Datasets</Link>
          <Link href="/training" className="btn btn-ghost">Training</Link>
          <Link href="/settings" className="btn btn-ghost">{t("nav.settings")}</Link>
        </nav>

        <div className="header-controls">
          <div className={`flex items-center gap-2 ${styles.statusWrapper}`}>
            <span
              className={`status-dot ${health?.ok ? "status-dot-ok" : "status-dot-error"}`}
              title={health?.ok ? t("status.connected") : t("status.disconnected")}
            />
            <span className="text-sm text-muted">
              {modelInfo?.loaded ? t("status.modelLoaded") : t("status.modelNotLoaded")}
            </span>
          </div>
          <LanguageSelector />
          <ThemeToggle />
        </div>
      </header>

      {/* Main Content */}
      <main className={`container ${styles.mainContent}`}>
        {/* Upload Section */}
        <div className={`grid-2 ${styles.uploadSection}`}>
          {/* Drop Zone */}
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
              accept="image/*"
              onChange={handleFileSelect}
              className={styles.hiddenInput}
              aria-label="Upload image file"
            />
            <div className="drop-zone-icon">📷</div>
            <div className={styles.dropzoneText}>
              <p className={styles.dropzoneTitle}>
                {isDragActive ? t("upload.dragActive") : t("upload.dropHere")}
              </p>
              <p className={`text-sm text-muted ${styles.dropzoneSubtitle}`}>
                {t("upload.orClick")}
              </p>
            </div>
            <span className="text-xs text-muted">{t("upload.supportedFormats")}</span>

            {file && (
              <div className={`badge badge-primary ${styles.fileBadge}`}>
                {file.name}
              </div>
            )}
          </div>

          {/* Demo Files & Actions */}
          <div className="card animate-fade-in">
            <h3 className={styles.sectionTitle}>{t("demo.title")}</h3>

            <div className={styles.formGroup}>
              <label htmlFor="demo-file-select" className="label">{t("demo.selectFile")}</label>
              <div className="flex gap-2">
                <select
                  id="demo-file-select"
                  value={selectedDemo}
                  onChange={(e: ChangeEvent<HTMLSelectElement>) =>
                    setSelectedDemo(e.target.value)
                  }
                  className={`input select ${styles.selectFlex}`}
                >
                  <option value="">{t("demo.noFiles")}</option>
                  {demoFiles.map((f: string) => (
                    <option value={f} key={f}>
                      {f}
                    </option>
                  ))}
                </select>
                <button
                  onClick={() => void refreshDemoFiles()}
                  disabled={busy}
                  className="btn btn-secondary btn-icon"
                  title={t("demo.refresh")}
                >
                  🔄
                </button>
              </div>
              {demoFiles.length > 0 && (
                <span className={`text-xs text-muted ${styles.helperText}`}>
                  {t("demo.fileCount", { count: demoFiles.length })}
                </span>
              )}
            </div>

            <div className="flex flex-col gap-2">
              {/* Filter Selector */}
              <div className={styles.filterWrapper}>
                <FilterSelector
                  apiBase={apiBase}
                  selectedFilter={activeFilter}
                  onFilterChange={setActiveFilter}
                />
              </div>
              <button
                onClick={runInference}
                disabled={!canInfer}
                className="btn btn-primary w-full"
              >
                {busy ? (
                  <>
                    <span className="spinner spinner-sm" />
                    {t("infer.running")}
                  </>
                ) : (
                  t("infer.runUpload")
                )}
              </button>
              <button
                onClick={runDemoInference}
                disabled={!selectedDemo || busy}
                className="btn btn-secondary w-full"
              >
                {busy ? t("infer.running") : t("infer.runDemo")}
              </button>
            </div>

            {/* Watcher Status */}
            <WatcherStatusCard apiBase={apiBase} />
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className={`card animate-slide-up ${styles.errorCard}`}>
            <p className={styles.errorText}>{error}</p>
          </div>
        )}

        {/* Preview & Results */}
        <div className="grid-2">
          {/* Image Preview */}
          <div className={`card ${styles.previewCard}`}>
            <div className={styles.previewHeader}>
              <h3 className={styles.previewHeaderTitle}>{t("preview.title")}</h3>
              {imageUrl && (
                <div className="flex gap-2">
                  <button
                    onClick={() => setZoom(1)}
                    className="btn btn-ghost btn-icon text-sm"
                    title={t("preview.fit")}
                  >
                    ⊡
                  </button>
                  <button
                    onClick={() => setZoom((z) => Math.max(0.5, z - 0.25))}
                    className="btn btn-ghost btn-icon text-sm"
                    title={t("preview.zoomOut")}
                  >
                    −
                  </button>
                  <span className={`text-sm text-muted ${styles.zoomText}`}>
                    {Math.round(zoom * 100)}%
                  </span>
                  <button
                    onClick={() => setZoom((z) => Math.min(3, z + 0.25))}
                    className="btn btn-ghost btn-icon text-sm"
                    title={t("preview.zoomIn")}
                  >
                    +
                  </button>
                </div>
              )}
            </div>

            <div className={styles.previewContainer}>
              {imageUrl ? (
                <div style={{ position: "relative", transform: `scale(${zoom})`, transformOrigin: "center" }}>
                  <img
                    ref={imgRef}
                    src={imageUrl}
                    alt="preview"
                    onLoad={draw}
                    style={{
                      maxWidth: "100%",
                      height: "auto",
                      display: "block",
                      borderRadius: "var(--radius-md)"
                    }}
                  />
                  <canvas
                    ref={canvasRef}
                    style={{
                      position: "absolute",
                      top: 0,
                      left: 0,
                      pointerEvents: "none",
                      borderRadius: "var(--radius-md)"
                    }}
                  />
                </div>
              ) : (
                <div className="text-center text-muted">
                  <div className={styles.emptyIcon}>🖼️</div>
                  <p>{t("preview.noImage")}</p>
                </div>
              )}

              {busy && (
                <div className={styles.loadingOverlay}>
                  <div className="spinner spinner-lg" />
                </div>
              )}
            </div>
          </div>

          {/* Detection Results */}
          <div className="card">
            <h3 style={{ marginBottom: "var(--space-4)" }}>
              {t("results.title")}
              {result && result.detections.length > 0 && (
                <span className="badge badge-success" style={{ marginLeft: "var(--space-2)" }}>
                  {t("results.objects", { count: result.detections.length })}
                </span>
              )}
            </h3>

            {result ? (
              <>
                <div className={`text-sm text-muted ${styles.resultsInfo}`}>
                  Model: <code>{result.model_path?.split("/").pop() ?? "—"}</code>
                </div>

                {result.privacy_applied && (
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
                      fontSize: "var(--font-size-sm)"
                    }}
                  >
                    <span>🔒</span>
                    <span>{t("privacy.facesBlurred", { count: result.privacy_faces ?? 0 })}</span>
                  </div>
                )}

                {result.detections.length > 0 ? (
                  <div className="flex flex-col gap-2">
                    {result.detections.map((det, idx) => (
                      <div
                        key={idx}
                        className="animate-slide-up"
                        style={{
                          padding: "var(--space-3)",
                          background: "var(--color-bg-tertiary)",
                          borderRadius: "var(--radius-md)",
                          borderLeft: `4px solid ${DETECTION_COLORS[idx % DETECTION_COLORS.length]}`,
                          animationDelay: `${idx * 50}ms`
                        }}
                      >
                        <div className="flex justify-between items-center">
                          <span className="font-medium">{det.label}</span>
                          <span
                            className="badge"
                            style={{
                              background: `${DETECTION_COLORS[idx % DETECTION_COLORS.length]}30`,
                              color: DETECTION_COLORS[idx % DETECTION_COLORS.length]
                            }}
                          >
                            {(det.score * 100).toFixed(1)}%
                          </span>
                        </div>
                        <div className={`progress ${styles.progressSmall}`}>
                          <div
                            className="progress-bar"
                            style={{
                              width: `${det.score * 100}%`,
                              background: DETECTION_COLORS[idx % DETECTION_COLORS.length]
                            }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className={`text-center text-muted ${styles.emptyState}`}>
                    <div className={styles.emptyIconSmall}>🔍</div>
                    <p>{t("results.noDetections")}</p>
                  </div>
                )}
              </>
            ) : (
              <div className={`text-center text-muted ${styles.emptyState}`}>
                <div className={styles.emptyIconSmall}>✨</div>
                <p>{t("results.noResults")}</p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
