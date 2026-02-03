"use client";

import { useState, useRef } from "react";
import { useTranslation } from "@/components/I18nProvider";

interface ModelUploadProps {
    apiBase: string;
    onUploadSuccess?: () => void;
}

export function ModelUpload({ apiBase, onUploadSuccess }: ModelUploadProps) {
    const { t } = useTranslation();
    const [modelFile, setModelFile] = useState<File | null>(null);
    const [labelsFile, setLabelsFile] = useState<File | null>(null);
    const [bundleName, setBundleName] = useState("");
    const [version, setVersion] = useState("v1");
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    const modelInputRef = useRef<HTMLInputElement>(null);
    const labelsInputRef = useRef<HTMLInputElement>(null);

    const canUpload = modelFile && labelsFile && bundleName.trim();

    const handleUpload = async () => {
        if (!canUpload) return;

        setUploading(true);
        setError(null);
        setSuccess(null);

        try {
            const formData = new FormData();
            formData.append("model", modelFile);
            formData.append("labels", labelsFile);

            const url = `${apiBase}/api/v1/models/upload?name=${encodeURIComponent(bundleName.trim())}&version=${encodeURIComponent(version.trim() || "v1")}`;

            const res = await fetch(url, {
                method: "POST",
                body: formData,
            });

            if (res.ok) {
                const data = await res.json();
                setSuccess(`Modell uppladdad: ${data.name}/${data.version} (${data.labels_count} etiketter)`);
                setModelFile(null);
                setLabelsFile(null);
                setBundleName("");
                setVersion("v1");
                if (modelInputRef.current) modelInputRef.current.value = "";
                if (labelsInputRef.current) labelsInputRef.current.value = "";
                if (onUploadSuccess) onUploadSuccess();
            } else {
                const data = await res.json();
                setError(data.detail || "Uppladdning misslyckades");
            }
        } catch (e) {
            setError("Nätverksfel vid uppladdning");
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="card">
            <h3 style={{ marginBottom: "var(--space-4)", display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="17,8 12,3 7,8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                </svg>
                {t("settings.uploadModel") || "Ladda upp modell"}
            </h3>

            {/* Model File */}
            <div style={{ marginBottom: "var(--space-4)" }}>
                <label className="label">{t("settings.modelFile") || "ONNX-modell (.onnx)"}</label>
                <div
                    style={{
                        border: "2px dashed var(--color-border)",
                        borderRadius: "var(--radius-lg)",
                        padding: "var(--space-4)",
                        textAlign: "center",
                        cursor: "pointer",
                        background: modelFile ? "var(--color-success-bg)" : "var(--color-bg-tertiary)",
                    }}
                    onClick={() => modelInputRef.current?.click()}
                >
                    {modelFile ? (
                        <div>
                            <span style={{ color: "var(--color-success)" }}>✓</span> {modelFile.name}
                            <div className="text-xs text-muted">{(modelFile.size / 1024 / 1024).toFixed(1)} MB</div>
                        </div>
                    ) : (
                        <div className="text-muted">
                            <div>📦 Klicka för att välja .onnx-fil</div>
                        </div>
                    )}
                </div>
                <input
                    ref={modelInputRef}
                    type="file"
                    accept=".onnx"
                    style={{ display: "none" }}
                    onChange={(e) => setModelFile(e.target.files?.[0] || null)}
                />
            </div>

            {/* Labels File */}
            <div style={{ marginBottom: "var(--space-4)" }}>
                <label className="label">{t("settings.labelsFile") || "Etiketter (labels.txt)"}</label>
                <div
                    style={{
                        border: "2px dashed var(--color-border)",
                        borderRadius: "var(--radius-lg)",
                        padding: "var(--space-4)",
                        textAlign: "center",
                        cursor: "pointer",
                        background: labelsFile ? "var(--color-success-bg)" : "var(--color-bg-tertiary)",
                    }}
                    onClick={() => labelsInputRef.current?.click()}
                >
                    {labelsFile ? (
                        <div>
                            <span style={{ color: "var(--color-success)" }}>✓</span> {labelsFile.name}
                        </div>
                    ) : (
                        <div className="text-muted">
                            <div>📝 Klicka för att välja labels.txt</div>
                        </div>
                    )}
                </div>
                <input
                    ref={labelsInputRef}
                    type="file"
                    accept=".txt"
                    style={{ display: "none" }}
                    onChange={(e) => setLabelsFile(e.target.files?.[0] || null)}
                />
            </div>

            {/* Bundle Name & Version */}
            <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "var(--space-3)", marginBottom: "var(--space-4)" }}>
                <div>
                    <label className="label">{t("settings.bundleName") || "Bundle-namn"}</label>
                    <input
                        type="text"
                        className="input"
                        placeholder="custom_model"
                        value={bundleName}
                        onChange={(e) => setBundleName(e.target.value)}
                    />
                </div>
                <div>
                    <label className="label">{t("common.version") || "Version"}</label>
                    <input
                        type="text"
                        className="input"
                        placeholder="v1"
                        value={version}
                        onChange={(e) => setVersion(e.target.value)}
                    />
                </div>
            </div>

            {/* Error/Success Messages */}
            {error && (
                <div
                    style={{
                        padding: "var(--space-3)",
                        background: "var(--color-error-bg)",
                        borderRadius: "var(--radius-md)",
                        color: "var(--color-error)",
                        marginBottom: "var(--space-4)",
                    }}
                >
                    {error}
                </div>
            )}
            {success && (
                <div
                    style={{
                        padding: "var(--space-3)",
                        background: "var(--color-success-bg)",
                        borderRadius: "var(--radius-md)",
                        color: "var(--color-success)",
                        marginBottom: "var(--space-4)",
                    }}
                >
                    {success}
                </div>
            )}

            {/* Upload Button */}
            <button
                className="btn btn-primary w-full"
                onClick={handleUpload}
                disabled={!canUpload || uploading}
            >
                {uploading ? (
                    <>
                        <span className="spinner spinner-sm" />
                        {t("common.loading") || "Laddar..."}
                    </>
                ) : (
                    <>{t("settings.uploadModel") || "Ladda upp modell"}</>
                )}
            </button>

            {/* Help Text */}
            <div className="text-xs text-muted" style={{ marginTop: "var(--space-3)" }}>
                <p>Modellen måste vara en YOLOv8 ONNX-fil med inbyggd NMS.</p>
                <p>labels.txt ska innehålla en etikett per rad.</p>
            </div>
        </div>
    );
}

export default ModelUpload;
