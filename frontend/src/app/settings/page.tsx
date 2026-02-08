"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "@/components/I18nProvider";
import { ThemeToggle } from "@/components/ThemeToggle";
import { LanguageSelector, LanguageDropdown } from "@/components/LanguageSelector";
import { useTheme } from "@/components/ThemeProvider";
import { useToast } from "@/components/Toast";
import { ModelUpload } from "@/components/ModelUpload";
import { IntegrationsPanel } from "@/components/IntegrationsPanel";
import styles from "./settings.module.css";

type SettingsInfo = {
  demo_input_dir: string;
  save_uploads: boolean;
  save_uploads_subdir: string;
  demo_allow_mutations: boolean;
  allow_runtime_settings: boolean;
  input_file_count: number | null;
  uploads_file_count: number | null;
  total_input_size_bytes: number | null;
};

type BundleInfo = {
  name: string;
  version: string;
  path: string;
  input_size: number[] | null;
  export_info: Record<string, unknown> | null;
  is_active: boolean;
};

type RegistryResponse = {
  models_dir: string;
  bundles: BundleInfo[];
  active_model_path: string | null;
};

type PrivacyStatus = {
  enabled: boolean;
  model_loaded: boolean;
  model_path: string | null;
  min_score: number;
  mode: string;
  is_ulfd: boolean;
};

const LS_API_BASE_KEY = "vision.apiBase";
const DEFAULT_API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export default function SettingsPage() {
  const { t } = useTranslation();
  const { theme, setTheme } = useTheme();
  const toast = useToast();

  const [apiBase, setApiBase] = useState(DEFAULT_API_BASE);

  const [backend, setBackend] = useState<SettingsInfo | null>(null);
  const [busy, setBusy] = useState(false);

  // Local draft settings
  const [saveUploads, setSaveUploads] = useState(false);
  const [saveUploadsSubdir, setSaveUploadsSubdir] = useState("_uploads");
  const [allowMutations, setAllowMutations] = useState(false);

  // Model registry
  const [registry, setRegistry] = useState<RegistryResponse | null>(null);

  // Privacy status
  const [privacy, setPrivacy] = useState<PrivacyStatus | null>(null);

  const canMutate = backend?.demo_allow_mutations ?? false;

  useEffect(() => {
    try {
      const v = window.localStorage.getItem(LS_API_BASE_KEY);
      if (v) setApiBase(v);
    } catch {
      // ignore
    }
  }, []);

  async function refreshBackend() {
    try {
      const r = await fetch(`${apiBase}/api/v1/settings`);
      const j = (await r.json()) as SettingsInfo;
      if (!r.ok) {
        toast.error((j as any)?.detail ?? t("notify.requestFailed", { status: r.status }));
        return;
      }
      setBackend(j);
      setSaveUploads(j.save_uploads);
      setSaveUploadsSubdir(j.save_uploads_subdir);
      setAllowMutations(j.demo_allow_mutations);
    } catch (e) {
      toast.error(String(e));
    }
  }

  async function refreshRegistry() {
    try {
      const r = await fetch(`${apiBase}/api/v1/registry`);
      if (r.ok) {
        const j = (await r.json()) as RegistryResponse;
        setRegistry(j);
      }
    } catch {
      // Ignore registry errors
    }
  }

  async function refreshPrivacy() {
    try {
      const r = await fetch(`${apiBase}/api/v1/privacy`);
      if (r.ok) {
        const j = (await r.json()) as PrivacyStatus;
        setPrivacy(j);
      }
    } catch {
      // Ignore privacy errors
    }
  }

  async function updatePrivacy(update: { enabled?: boolean; mode?: string; min_score?: number }) {
    setBusy(true);
    try {
      const r = await fetch(`${apiBase}/api/v1/privacy`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(update),
      });
      const j = await r.json();
      if (!r.ok) {
        toast.error(j?.detail ?? t("notify.requestFailed", { status: r.status }));
        return;
      }
      setPrivacy(j as PrivacyStatus);
      toast.success(t("notify.settingsApplied"));
    } catch (e) {
      toast.error(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function activateModel(name: string, version: string) {
    setBusy(true);
    try {
      const r = await fetch(
        `${apiBase}/api/v1/registry/activate?name=${name}&version=${version}`,
        { method: "POST" }
      );
      const j = await r.json();
      if (!r.ok) {
        toast.error(j?.detail ?? t("notify.requestFailed", { status: r.status }));
        return;
      }
      toast.success(t("notify.modelActivated", { name: `${name}/${version}` }));
      await refreshRegistry();
    } catch (e) {
      toast.error(String(e));
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void refreshBackend();
    void refreshRegistry();
    void refreshPrivacy();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiBase]);

  const envSnippet = useMemo(() => {
    const lines = [
      `VISION_SAVE_UPLOADS=${saveUploads ? "1" : "0"}`,
      `VISION_SAVE_UPLOADS_SUBDIR=${saveUploadsSubdir || "_uploads"}`,
      `VISION_DEMO_ALLOW_MUTATIONS=${allowMutations ? "1" : "0"}`,
      "# Optional: allow this UI to update the running backend via /api/v1/settings",
      "VISION_ALLOW_RUNTIME_SETTINGS=1"
    ];
    return lines.join("\n") + "\n";
  }, [saveUploads, saveUploadsSubdir, allowMutations]);

  async function saveApiBase() {
    try {
      window.localStorage.setItem(LS_API_BASE_KEY, apiBase);
      toast.success(t("notify.apiBaseSaved"));
    } catch (e) {
      toast.error(String(e));
    }
  }

  async function applyToBackendRuntime() {
    setBusy(true);

    try {
      const resp = await fetch(`${apiBase}/api/v1/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          save_uploads: saveUploads,
          save_uploads_subdir: saveUploadsSubdir,
          demo_allow_mutations: allowMutations
        })
      });
      const json = await resp.json();
      if (!resp.ok) {
        toast.error(json?.detail ?? t("notify.requestFailed", { status: resp.status }));
        return;
      }
      setBackend(json as SettingsInfo);
      toast.success(t("notify.settingsApplied"));
    } catch (e) {
      toast.error(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function clearInput(scope: "uploads" | "all") {
    setBusy(true);

    try {
      if (!canMutate) {
        toast.error("Backend mutations are disabled. Enable VISION_DEMO_ALLOW_MUTATIONS=1.");
        return;
      }

      if (scope === "all") {
        const token = window.prompt(t("settings.clearConfirm"));
        if (token !== "CLEAR") {
          toast.info(t("settings.cancelled"));
          return;
        }
      } else {
        const ok = window.confirm("Delete all files under /input/_uploads?");
        if (!ok) {
          toast.info(t("settings.cancelled"));
          return;
        }
      }

      const resp = await fetch(`${apiBase}/api/v1/demo/clear?scope=${scope}`, {
        method: "POST"
      });
      const json = await resp.json();
      if (!resp.ok) {
        toast.error(json?.detail ?? t("notify.requestFailed", { status: resp.status }));
        return;
      }

      const df = json?.deleted_files ?? 0;
      const dd = json?.deleted_dirs ?? 0;
      toast.success(t("notify.cleared", { scope, files: df, dirs: dd }));

      await refreshBackend();
    } catch (e) {
      toast.error(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function copyEnvSnippet() {
    try {
      await navigator.clipboard.writeText(envSnippet);
      toast.success(t("notify.copiedEnv"));
    } catch (e) {
      toast.error(String(e));
    }
  }

  return (
    <div className="page">
      {/* Header */}
      <header className="header">
        <div className="header-logo">
          {/* Volvo Iron Mark */}
          <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
            <circle cx="16" cy="16" r="14" stroke="currentColor" strokeWidth="2.5" fill="none" />
            <path d="M8 16h16M22 10l-6 6 6 6" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
          </svg>
          <span className={styles.logoText}>
            Volvo Cars Vision
          </span>
        </div>

        <nav className="header-nav">
          <Link href="/" className="btn btn-ghost">{t("nav.home")}</Link>
          <Link href="/settings" className="btn btn-ghost">{t("nav.settings")}</Link>
        </nav>

        <div className="header-controls">
          <LanguageSelector />
          <ThemeToggle />
        </div>
      </header>

      <main className={`container ${styles.mainContent}`}>
        <div className={styles.pageHeader}>
          <h1 className={styles.pageTitle}>{t("settings.title")}</h1>
          <p className="text-muted">{t("settings.savedInBrowser")}</p>
        </div>

        {/* UI Settings */}
        <section className={`card animate-fade-in ${styles.section}`}>
          <h2 className={styles.sectionHeader}>{t("settings.ui")}</h2>

          <div className={`grid-2 ${styles.gridWithGap}`}>
            {/* API Base */}
            <div>
              <label className="label">{t("settings.apiBase")}</label>
              <div className="flex gap-2">
                <input
                  value={apiBase}
                  onChange={(e) => setApiBase(e.target.value)}
                  className="input"
                  placeholder={t("settings.apiBasePlaceholder")}
                />
                <button onClick={saveApiBase} disabled={busy} className="btn btn-primary">
                  {t("settings.saveApiBase")}
                </button>
              </div>
            </div>

            {/* Theme */}
            <div>
              <label className="label">{t("settings.theme")}</label>
              <div className="flex gap-2">
                <button
                  onClick={() => setTheme("light")}
                  className={`btn ${theme === "light" ? "btn-primary" : "btn-secondary"}`}
                >
                  ☀️ {t("settings.themeLight")}
                </button>
                <button
                  onClick={() => setTheme("dark")}
                  className={`btn ${theme === "dark" ? "btn-primary" : "btn-secondary"}`}
                >
                  🌙 {t("settings.themeDark")}
                </button>
                <button
                  onClick={() => setTheme("system")}
                  className={`btn ${theme === "system" ? "btn-primary" : "btn-secondary"}`}
                >
                  💻 {t("settings.themeSystem")}
                </button>
              </div>
            </div>

            {/* Language */}
            <div>
              <label className="label">{t("settings.language")}</label>
              <LanguageDropdown />
            </div>
          </div>
        </section>

        {/* Backend Settings */}
        <section className={`card animate-fade-in ${styles.sectionAnimated100}`}>
          <div className={`flex justify-between items-center ${styles.sectionHeader}`}>
            <h2 className={styles.sectionTitle}>{t("settings.backend")}</h2>
            <button onClick={() => void refreshBackend()} disabled={busy} className="btn btn-secondary">
              {t("settings.refresh")}
            </button>
          </div>

          {backend && (
            <>
              {/* Stats */}
              <div className={`grid-3 ${styles.statsBox}`}>
                <div className="text-center">
                  <div className={`text-2xl font-bold ${styles.statPrimary}`}>
                    {backend.input_file_count ?? 0}
                  </div>
                  <div className="text-sm text-muted">{t("settings.inputFiles")}</div>
                </div>
                <div className="text-center">
                  <div className={`text-2xl font-bold ${styles.statAccent}`}>
                    {backend.uploads_file_count ?? 0}
                  </div>
                  <div className="text-sm text-muted">{t("settings.uploads")}</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold">
                    {backend.total_input_size_bytes != null
                      ? (backend.total_input_size_bytes / (1024 * 1024)).toFixed(1) + " MB"
                      : "—"}
                  </div>
                  <div className="text-sm text-muted">{t("settings.totalSize")}</div>
                </div>
              </div>

              {/* Settings Form */}
              <div className="flex flex-col gap-4">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    className="checkbox"
                    checked={saveUploads}
                    onChange={(e) => setSaveUploads(e.target.checked)}
                  />
                  <span>{t("settings.saveUploads")}</span>
                </label>

                <div>
                  <label className="label">{t("settings.uploadsSubdir")}</label>
                  <input
                    value={saveUploadsSubdir}
                    onChange={(e) => setSaveUploadsSubdir(e.target.value)}
                    className={`input ${styles.inputSmall}`}
                    placeholder="_uploads"
                  />
                </div>

                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    className="checkbox"
                    checked={allowMutations}
                    onChange={(e) => setAllowMutations(e.target.checked)}
                  />
                  <span>{t("settings.allowMutations")}</span>
                  <span className="badge badge-warning">{t("settings.allowMutationsWarning")}</span>
                </label>

                <div className={`flex gap-2 ${styles.formActions}`}>
                  <button onClick={applyToBackendRuntime} disabled={busy} className="btn btn-primary">
                    {t("settings.applyRuntime")}
                  </button>
                  <button onClick={copyEnvSnippet} disabled={busy} className="btn btn-secondary">
                    📋 {t("settings.copyEnv")}
                  </button>
                </div>

                <div className="text-sm text-muted">
                  {t("settings.runtimeSettings")}:{" "}
                  <span className={backend.allow_runtime_settings ? "badge badge-success" : "badge badge-error"}>
                    {backend.allow_runtime_settings ? t("settings.runtimeEnabled") : t("settings.runtimeDisabled")}
                  </span>
                </div>

                <pre className={styles.codeBlock}>
                  {envSnippet}
                </pre>
              </div>
            </>
          )}
        </section>

        {/* Models */}
        <section className={`card animate-fade-in ${styles.sectionAnimated200}`}>
          <div className={`flex justify-between items-center ${styles.sectionHeader}`}>
            <h2 className={styles.sectionTitle}>{t("settings.models")}</h2>
            <button onClick={() => void refreshRegistry()} disabled={busy} className="btn btn-secondary">
              {t("settings.refresh")}
            </button>
          </div>

          {registry && (
            <>
              <div className={`text-sm text-muted ${styles.modelsInfo}`}>
                {t("settings.modelsDir")}: <code>{registry.models_dir}</code>
              </div>

              {registry.bundles.length === 0 ? (
                <div className="text-center text-muted" style={{ padding: "var(--space-8)" }}>
                  {t("settings.noModels")}
                </div>
              ) : (
                <div className="grid-auto">
                  {registry.bundles.map((b) => (
                    <div
                      key={`${b.name}/${b.version}`}
                      className="card"
                      style={{
                        padding: "var(--space-4)",
                        border: b.is_active ? "2px solid var(--color-success)" : "1px solid var(--color-border)"
                      }}
                    >
                      <div className={`flex justify-between items-center ${styles.modelItem}`}>
                        <span className="font-semibold">{b.name}</span>
                        {b.is_active && (
                          <span className="badge badge-success">{t("settings.active")}</span>
                        )}
                      </div>
                      <div className={`text-sm text-muted ${styles.modelItem}`}>
                        {t("common.version")}: {b.version}
                      </div>
                      <div className={`text-sm text-muted ${styles.modelItemSmall}`}>
                        {t("settings.inputSize")}:{" "}
                        {b.input_size ? `${b.input_size[0]}×${b.input_size[1]}` : "—"}
                      </div>
                      {!b.is_active && (
                        <button
                          onClick={() => void activateModel(b.name, b.version)}
                          disabled={busy || !backend?.allow_runtime_settings}
                          className="btn btn-secondary w-full"
                        >
                          {t("settings.activate")}
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </section>

        {/* Model Upload */}
        <section className={styles.section}>
          <ModelUpload apiBase={apiBase} onUploadSuccess={() => void refreshRegistry()} />
        </section>

        {/* Privacy & Anonymization */}
        <section className={`card animate-fade-in ${styles.sectionAnimated300}`}>
          <div className={`flex justify-between items-center ${styles.sectionHeader}`}>
            <h2 className={styles.sectionTitle}>🔒 {t("privacy.title")}</h2>
            <button onClick={() => void refreshPrivacy()} disabled={busy} className="btn btn-secondary">
              {t("settings.refresh")}
            </button>
          </div>

          {privacy ? (
            <>
              <div className={`grid-3 ${styles.statsBox}`}>
                <div className="text-center">
                  <div className={`text-2xl font-bold ${privacy.enabled ? styles.statPrimary : ""}`}>
                    {privacy.enabled ? "✅" : "❌"}
                  </div>
                  <div className="text-sm text-muted">{t("privacy.status")}</div>
                </div>
                <div className="text-center">
                  <div className={`text-2xl font-bold ${privacy.model_loaded ? styles.statAccent : ""}`}>
                    {privacy.model_loaded ? "✅" : "❌"}
                  </div>
                  <div className="text-sm text-muted">{t("privacy.modelLoaded")}</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold">
                    {privacy.mode === "blur" ? "🫧" : "🟦"}
                  </div>
                  <div className="text-sm text-muted">{t("privacy.mode")}</div>
                </div>
              </div>

              <div className="flex flex-col gap-4">
                <div className="text-sm">
                  <strong>{t("privacy.model")}:</strong>{" "}
                  <code>{privacy.model_path ?? "—"}</code>
                  {privacy.is_ulfd && (
                    <span className="badge badge-info" style={{ marginLeft: "var(--space-2)" }}>ULFD</span>
                  )}
                </div>

                {/* Toggle enabled */}
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    className="checkbox"
                    checked={privacy.enabled}
                    onChange={(e) => void updatePrivacy({ enabled: e.target.checked })}
                    disabled={busy || !backend?.allow_runtime_settings}
                  />
                  <span>{t("privacy.enableLabel")}</span>
                </label>

                {/* Mode selector */}
                <div>
                  <label className="label">{t("privacy.modeLabel")}</label>
                  <div className="flex gap-2">
                    <button
                      onClick={() => void updatePrivacy({ mode: "blur" })}
                      disabled={busy || !backend?.allow_runtime_settings}
                      className={`btn ${privacy.mode === "blur" ? "btn-primary" : "btn-secondary"}`}
                    >
                      🫧 {t("privacy.blur")}
                    </button>
                    <button
                      onClick={() => void updatePrivacy({ mode: "pixelate" })}
                      disabled={busy || !backend?.allow_runtime_settings}
                      className={`btn ${privacy.mode === "pixelate" ? "btn-primary" : "btn-secondary"}`}
                    >
                      🟦 {t("privacy.pixelate")}
                    </button>
                  </div>
                </div>

                {/* Min score slider */}
                <div>
                  <label className="label">
                    {t("privacy.minScore")}: {(privacy.min_score * 100).toFixed(0)}%
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={Math.round(privacy.min_score * 100)}
                    onChange={(e) => void updatePrivacy({ min_score: parseInt(e.target.value) / 100 })}
                    disabled={busy || !backend?.allow_runtime_settings}
                    style={{ width: "100%", maxWidth: "300px" }}
                  />
                </div>
              </div>

              {!backend?.allow_runtime_settings && (
                <p className="text-sm text-muted" style={{ marginTop: "var(--space-3)" }}>
                  {t("privacy.runtimeDisabled")}
                </p>
              )}
            </>
          ) : (
            <div className="text-center text-muted" style={{ padding: "var(--space-4)" }}>
              {t("common.loading")}
            </div>
          )}
        </section>

        {/* Integrations */}
        <section className={styles.section}>
          <IntegrationsPanel apiBase={apiBase} />
        </section>

        {/* Danger Zone */}
        <section className={`card animate-fade-in ${styles.dangerSection}`}>
          <h2 className={styles.dangerTitle}>
            ⚠️ {t("settings.dangerZone")}
          </h2>

          <div className="flex gap-2">
            <button
              onClick={() => void clearInput("uploads")}
              disabled={busy || !canMutate}
              className="btn btn-secondary"
            >
              🗑️ {t("settings.clearUploads")}
            </button>
            <button
              onClick={() => void clearInput("all")}
              disabled={busy || !canMutate}
              className="btn btn-danger"
            >
              ⚠️ {t("settings.clearAll")}
            </button>
          </div>

          {!canMutate && (
            <p className={`text-sm text-muted ${styles.dangerNote}`}>
              Enable <code>VISION_DEMO_ALLOW_MUTATIONS=1</code> to use these actions.
            </p>
          )}
        </section>
      </main>
    </div>
  );
}
