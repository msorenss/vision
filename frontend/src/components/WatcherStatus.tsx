"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "@/components/I18nProvider";

interface WatcherStatusData {
    enabled: boolean;
    input_dir: string;
    output_dir: string;
    processed_dir: string | null;
    mode: string;
    pending_files: number;
    processed_today: number;
    last_processed: string | null;
}

interface WatcherStatusProps {
    apiBase: string;
}

export function WatcherStatusCard({ apiBase }: WatcherStatusProps) {
    const { t } = useTranslation();
    const [status, setStatus] = useState<WatcherStatusData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const loadStatus = useCallback(async () => {
        try {
            const res = await fetch(`${apiBase}/api/v1/watcher/status`);
            if (res.ok) {
                const data = await res.json();
                setStatus(data);
                setError(null);
            } else {
                setError("Failed to load watcher status");
            }
        } catch (e) {
            setError("Connection error");
        } finally {
            setLoading(false);
        }
    }, [apiBase]);

    useEffect(() => {
        loadStatus();
        // Poll every 10 seconds
        const interval = setInterval(loadStatus, 10000);
        return () => clearInterval(interval);
    }, [loadStatus]);

    if (loading) {
        return (
            <div className="card" style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                <div className="spinner spinner-sm" />
                <span className="text-muted">{t("watcher.loading")}</span>
            </div>
        );
    }

    if (error || !status) {
        return (
            <div className="card" style={{ opacity: 0.6 }}>
                <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                    <span className="status-dot status-dot-error" />
                    <span className="text-muted">{t("watcher.unavailable")}</span>
                </div>
            </div>
        );
    }

    return (
        <div className="card animate-fade-in">
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "var(--space-4)" }}>
                <h3 style={{ margin: 0, display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                        <circle cx="12" cy="12" r="3" />
                    </svg>
                    {t("watcher.title")}
                </h3>
                <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                    <span
                        className={`status-dot ${status.enabled ? "status-dot-ok" : "status-dot-error"}`}
                    />
                    <span className="text-sm">
                        {status.enabled ? t("watcher.active") : t("watcher.inactive")}
                    </span>
                </div>
            </div>

            {status.enabled && (
                <>
                    {/* Stats Grid */}
                    <div
                        style={{
                            display: "grid",
                            gridTemplateColumns: "repeat(2, 1fr)",
                            gap: "var(--space-4)",
                            marginBottom: "var(--space-4)",
                        }}
                    >
                        {/* Pending */}
                        <div
                            style={{
                                background: "var(--color-bg-tertiary)",
                                padding: "var(--space-4)",
                                borderRadius: "var(--radius-lg)",
                                textAlign: "center",
                            }}
                        >
                            <div
                                style={{
                                    fontSize: "var(--font-size-2xl)",
                                    fontWeight: "var(--font-weight-bold)",
                                    color: status.pending_files > 0 ? "var(--color-warning)" : "var(--color-text-primary)",
                                }}
                            >
                                {status.pending_files}
                            </div>
                            <div className="text-sm text-muted">{t("watcher.pending")}</div>
                        </div>

                        {/* Processed Today */}
                        <div
                            style={{
                                background: "var(--color-bg-tertiary)",
                                padding: "var(--space-4)",
                                borderRadius: "var(--radius-lg)",
                                textAlign: "center",
                            }}
                        >
                            <div
                                style={{
                                    fontSize: "var(--font-size-2xl)",
                                    fontWeight: "var(--font-weight-bold)",
                                    color: "var(--color-success)",
                                }}
                            >
                                {status.processed_today}
                            </div>
                            <div className="text-sm text-muted">{t("watcher.processedToday")}</div>
                        </div>
                    </div>

                    {/* Mode Badge */}
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)" }}>
                        <span className="badge badge-primary">
                            {t("watcher.mode")}: {status.mode}
                        </span>
                        {status.processed_dir && (
                            <span className="badge badge-success">
                                {t("watcher.autoMove")}
                            </span>
                        )}
                    </div>

                    {/* Folder Info (collapsed) */}
                    <details style={{ marginTop: "var(--space-4)" }}>
                        <summary className="text-sm text-muted" style={{ cursor: "pointer" }}>
                            {t("watcher.folders")}
                        </summary>
                        <div
                            style={{
                                marginTop: "var(--space-2)",
                                padding: "var(--space-3)",
                                background: "var(--color-bg-tertiary)",
                                borderRadius: "var(--radius-md)",
                                fontSize: "var(--font-size-xs)",
                            }}
                        >
                            <div><strong>Input:</strong> {status.input_dir}</div>
                            <div><strong>Output:</strong> {status.output_dir}</div>
                            {status.processed_dir && (
                                <div><strong>Processed:</strong> {status.processed_dir}</div>
                            )}
                        </div>
                    </details>
                </>
            )}

            {!status.enabled && (
                <div className="text-muted text-sm">
                    {t("watcher.enableHint")}
                </div>
            )}
        </div>
    );
}

export default WatcherStatusCard;
