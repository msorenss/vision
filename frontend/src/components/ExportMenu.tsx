"use client";

import { useState, useRef, useEffect } from "react";
import { useTranslation } from "@/components/I18nProvider";

interface ExportMenuProps {
    apiBase: string;
    /** File name in the input directory (for demo files) */
    demoFileName?: string;
    /** Whether there is an active inference result */
    hasResult: boolean;
    /** Filter name currently applied */
    filterName?: string;
    /** Whether privacy is available */
    privacyAvailable?: boolean;
}

type ExportMode = "original" | "annotated" | "privacy_only" | "both";

export function ExportMenu({
    apiBase,
    demoFileName,
    hasResult,
    filterName = "default",
    privacyAvailable = false,
}: ExportMenuProps) {
    const { t } = useTranslation();
    const [isOpen, setIsOpen] = useState(false);
    const [busy, setBusy] = useState(false);
    const menuRef = useRef<HTMLDivElement>(null);

    // Close on outside click
    useEffect(() => {
        const handleClick = (e: MouseEvent) => {
            if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
                setIsOpen(false);
            }
        };
        if (isOpen) {
            document.addEventListener("mousedown", handleClick);
            return () => document.removeEventListener("mousedown", handleClick);
        }
    }, [isOpen]);

    if (!hasResult || !demoFileName) return null;

    const doExport = async (mode: ExportMode) => {
        setBusy(true);
        setIsOpen(false);

        try {
            const params = new URLSearchParams({
                name: demoFileName,
                mode,
                filter_name: filterName,
            });

            if (mode === "annotated" || mode === "both") {
                params.set("boxes", "true");
                params.set("labels", "true");
            }
            if (mode === "both" || mode === "privacy_only") {
                params.set("privacy", "true");
            }

            const url = `${apiBase}/api/v1/export/image?${params}`;
            const resp = await fetch(url);

            if (!resp.ok) {
                const err = await resp.json().catch(() => ({ detail: "Export failed" }));
                alert(err.detail || "Export failed");
                return;
            }

            const blob = await resp.blob();
            const downloadUrl = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = downloadUrl;

            const suffix = mode === "original" ? "" : `_${mode}`;
            const ext = "jpeg";
            a.download = `${demoFileName.replace(/\.[^.]+$/, "")}${suffix}.${ext}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(downloadUrl);
        } catch (err) {
            console.error("Export error:", err);
            alert("Export failed");
        } finally {
            setBusy(false);
        }
    };

    const options: { mode: ExportMode; label: string; icon: string }[] = [
        { mode: "original", label: t("export.original"), icon: "📄" },
        { mode: "annotated", label: t("export.annotated"), icon: "🔲" },
    ];

    if (privacyAvailable) {
        options.push(
            { mode: "privacy_only", label: t("export.anonymized"), icon: "🔒" },
            { mode: "both", label: t("export.both"), icon: "🔲🔒" },
        );
    }

    return (
        <div ref={menuRef} style={{ position: "relative", display: "inline-block" }}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                disabled={busy}
                className="btn btn-secondary btn-icon"
                title={t("export.download")}
                style={{ padding: "6px 10px" }}
            >
                {busy ? (
                    <span className="spinner spinner-sm" />
                ) : (
                    <span>⬇️</span>
                )}
            </button>

            {isOpen && (
                <div
                    style={{
                        position: "absolute",
                        top: "100%",
                        right: 0,
                        marginTop: "var(--space-1)",
                        background: "var(--color-bg-card)",
                        border: "1px solid var(--color-border)",
                        borderRadius: "var(--radius-lg)",
                        boxShadow: "var(--shadow-lg)",
                        minWidth: "220px",
                        zIndex: 100,
                        padding: "var(--space-1)",
                    }}
                >
                    <div style={{ padding: "var(--space-2) var(--space-3)", borderBottom: "1px solid var(--color-border)" }}>
                        <span className="text-sm font-semibold">{t("export.exportImage")}</span>
                    </div>
                    {options.map((opt) => (
                        <button
                            key={opt.mode}
                            onClick={() => doExport(opt.mode)}
                            className="btn btn-ghost"
                            style={{
                                width: "100%",
                                justifyContent: "flex-start",
                                padding: "var(--space-2) var(--space-3)",
                                gap: "var(--space-2)",
                                borderRadius: "var(--radius-md)",
                            }}
                        >
                            <span>{opt.icon}</span>
                            <span>{opt.label}</span>
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
}

export default ExportMenu;
