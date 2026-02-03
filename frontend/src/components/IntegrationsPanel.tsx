"use client";

import { useState } from "react";
import { useTranslation } from "@/components/I18nProvider";

type OpcUaStatus = {
    available: boolean;
    enabled: boolean;
    running: boolean;
    endpoint: string | null;
    port: number;
    namespace: string;
    update_interval_ms: number;
};

type MqttStatus = {
    available: boolean;
    configured: boolean;
    broker: string | null;
    port: number;
    topic: string;
    username: string | null;
};

type WebhookStatus = {
    configured: boolean;
    url: string | null;
    has_custom_headers: boolean;
};

type IntegrationsStatus = {
    opcua: OpcUaStatus;
    mqtt: MqttStatus;
    webhook: WebhookStatus;
};

type IntegrationsPanelProps = {
    apiBase: string;
    onUpdate?: () => void;
};

export function IntegrationsPanel({ apiBase, onUpdate }: IntegrationsPanelProps) {
    const { t } = useTranslation();

    const [integrations, setIntegrations] = useState<IntegrationsStatus | null>(null);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    // OPC UA form state
    const [opcuaEnabled, setOpcuaEnabled] = useState(false);
    const [opcuaPort, setOpcuaPort] = useState(4840);
    const [opcuaInterval, setOpcuaInterval] = useState(0);

    // MQTT form state
    const [mqttBroker, setMqttBroker] = useState("");
    const [mqttPort, setMqttPort] = useState(1883);
    const [mqttTopic, setMqttTopic] = useState("vision/results");
    const [mqttUsername, setMqttUsername] = useState("");
    const [mqttPassword, setMqttPassword] = useState("");

    // Webhook form state
    const [webhookUrl, setWebhookUrl] = useState("");
    const [webhookHeaders, setWebhookHeaders] = useState("{}");

    // Expanded sections
    const [expandedSection, setExpandedSection] = useState<string | null>(null);

    async function refreshIntegrations() {
        setBusy(true);
        setError(null);
        try {
            const r = await fetch(`${apiBase}/api/v1/integrations`);
            if (!r.ok) {
                const j = await r.json();
                setError(j?.detail ?? `Request failed: ${r.status}`);
                return;
            }
            const j = (await r.json()) as IntegrationsStatus;
            setIntegrations(j);

            // Populate form state
            setOpcuaEnabled(j.opcua.enabled);
            setOpcuaPort(j.opcua.port);
            setOpcuaInterval(j.opcua.update_interval_ms);

            setMqttBroker(j.mqtt.broker ?? "");
            setMqttPort(j.mqtt.port);
            setMqttTopic(j.mqtt.topic);
            setMqttUsername(j.mqtt.username ?? "");

            setWebhookUrl(j.webhook.url ?? "");
        } catch (e) {
            setError(String(e));
        } finally {
            setBusy(false);
        }
    }

    async function updateIntegrations(payload: Record<string, unknown>) {
        setBusy(true);
        setError(null);
        setSuccess(null);
        try {
            const r = await fetch(`${apiBase}/api/v1/integrations`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            const j = await r.json();
            if (!r.ok) {
                setError(j?.detail ?? `Request failed: ${r.status}`);
                return;
            }
            setIntegrations(j as IntegrationsStatus);
            setSuccess("Settings updated");
            onUpdate?.();
        } catch (e) {
            setError(String(e));
        } finally {
            setBusy(false);
        }
    }

    async function testWebhook() {
        setBusy(true);
        setError(null);
        setSuccess(null);
        try {
            const r = await fetch(`${apiBase}/api/v1/integrations/test/webhook`, {
                method: "POST",
            });
            const j = await r.json();
            if (!r.ok) {
                setError(j?.detail ?? `Test failed: ${r.status}`);
                return;
            }
            setSuccess("Webhook test sent successfully");
        } catch (e) {
            setError(String(e));
        } finally {
            setBusy(false);
        }
    }

    async function testMqtt() {
        setBusy(true);
        setError(null);
        setSuccess(null);
        try {
            const r = await fetch(`${apiBase}/api/v1/integrations/test/mqtt`, {
                method: "POST",
            });
            const j = await r.json();
            if (!r.ok) {
                setError(j?.detail ?? `Test failed: ${r.status}`);
                return;
            }
            setSuccess("MQTT test message published");
        } catch (e) {
            setError(String(e));
        } finally {
            setBusy(false);
        }
    }

    // Load on mount
    useState(() => {
        void refreshIntegrations();
    });

    function toggleSection(section: string) {
        setExpandedSection(expandedSection === section ? null : section);
    }

    return (
        <section className="card animate-fade-in" style={{ animationDelay: "150ms" }}>
            <div className="flex justify-between items-center" style={{ marginBottom: "var(--space-4)" }}>
                <h2 style={{ margin: 0 }}>🔌 {t("settings.integrations") ?? "Integrations"}</h2>
                <button onClick={() => void refreshIntegrations()} disabled={busy} className="btn btn-secondary">
                    {t("settings.refresh")}
                </button>
            </div>

            {error && (
                <div className="badge badge-error" style={{ marginBottom: "var(--space-4)", display: "block", padding: "var(--space-2)" }}>
                    {error}
                </div>
            )}

            {success && (
                <div className="badge badge-success" style={{ marginBottom: "var(--space-4)", display: "block", padding: "var(--space-2)" }}>
                    {success}
                </div>
            )}

            {integrations && (
                <div className="flex flex-col gap-4">
                    {/* OPC UA */}
                    <div
                        className="card"
                        style={{
                            padding: "var(--space-4)",
                            border: integrations.opcua.running
                                ? "2px solid var(--color-success)"
                                : "1px solid var(--color-border)",
                        }}
                    >
                        <div
                            className="flex justify-between items-center"
                            style={{ cursor: "pointer" }}
                            onClick={() => toggleSection("opcua")}
                        >
                            <div className="flex items-center gap-2">
                                <span className="font-semibold">OPC UA Server</span>
                                {integrations.opcua.running ? (
                                    <span className="badge badge-success">Running</span>
                                ) : integrations.opcua.enabled ? (
                                    <span className="badge badge-warning">Enabled</span>
                                ) : (
                                    <span className="badge badge-secondary">Disabled</span>
                                )}
                                {!integrations.opcua.available && (
                                    <span className="badge badge-error">Library not installed</span>
                                )}
                            </div>
                            <span>{expandedSection === "opcua" ? "▲" : "▼"}</span>
                        </div>

                        {expandedSection === "opcua" && (
                            <div style={{ marginTop: "var(--space-4)" }}>
                                <div className="text-sm text-muted" style={{ marginBottom: "var(--space-3)" }}>
                                    Namespace: <code>{integrations.opcua.namespace}</code>
                                </div>

                                <div className="grid-2" style={{ gap: "var(--space-4)" }}>
                                    <label className="flex items-center gap-2">
                                        <input
                                            type="checkbox"
                                            className="checkbox"
                                            checked={opcuaEnabled}
                                            onChange={(e) => setOpcuaEnabled(e.target.checked)}
                                            disabled={!integrations.opcua.available}
                                        />
                                        <span>Enable OPC UA Server</span>
                                    </label>

                                    <div>
                                        <label className="label">Port</label>
                                        <input
                                            type="number"
                                            className="input"
                                            value={opcuaPort}
                                            onChange={(e) => setOpcuaPort(Number(e.target.value))}
                                            min={1}
                                            max={65535}
                                            style={{ maxWidth: "120px" }}
                                        />
                                    </div>

                                    <div>
                                        <label className="label">Update Interval (ms)</label>
                                        <input
                                            type="number"
                                            className="input"
                                            value={opcuaInterval}
                                            onChange={(e) => setOpcuaInterval(Number(e.target.value))}
                                            min={0}
                                            style={{ maxWidth: "120px" }}
                                        />
                                        <div className="text-sm text-muted">0 = immediate</div>
                                    </div>
                                </div>

                                <button
                                    onClick={() => void updateIntegrations({
                                        opcua_enabled: opcuaEnabled,
                                        opcua_port: opcuaPort,
                                        opcua_update_interval_ms: opcuaInterval,
                                    })}
                                    disabled={busy || !integrations.opcua.available}
                                    className="btn btn-primary"
                                    style={{ marginTop: "var(--space-4)" }}
                                >
                                    Apply OPC UA Settings
                                </button>

                                <details style={{ marginTop: "var(--space-4)" }}>
                                    <summary className="text-sm text-muted" style={{ cursor: "pointer" }}>
                                        📖 OPC UA Node Structure
                                    </summary>
                                    <pre style={{
                                        marginTop: "var(--space-2)",
                                        padding: "var(--space-3)",
                                        background: "var(--color-bg-tertiary)",
                                        borderRadius: "var(--radius-md)",
                                        fontSize: "var(--font-size-sm)",
                                    }}>
                                        {`VisionSystem (Object)
├── ActiveModel (String)
├── State (Int32)
│   0=Off, 1=Ready, 2=Processing, 3=Error
└── Results (Object)
    ├── LastResult (String/JSON)
    └── DisplayCount (UInt32)`}
                                    </pre>
                                </details>
                            </div>
                        )}
                    </div>

                    {/* MQTT */}
                    <div
                        className="card"
                        style={{
                            padding: "var(--space-4)",
                            border: integrations.mqtt.configured
                                ? "2px solid var(--color-primary)"
                                : "1px solid var(--color-border)",
                        }}
                    >
                        <div
                            className="flex justify-between items-center"
                            style={{ cursor: "pointer" }}
                            onClick={() => toggleSection("mqtt")}
                        >
                            <div className="flex items-center gap-2">
                                <span className="font-semibold">MQTT Client</span>
                                {integrations.mqtt.configured ? (
                                    <span className="badge badge-primary">Configured</span>
                                ) : (
                                    <span className="badge badge-secondary">Not configured</span>
                                )}
                                {!integrations.mqtt.available && (
                                    <span className="badge badge-error">Library not installed</span>
                                )}
                            </div>
                            <span>{expandedSection === "mqtt" ? "▲" : "▼"}</span>
                        </div>

                        {expandedSection === "mqtt" && (
                            <div style={{ marginTop: "var(--space-4)" }}>
                                <div className="grid-2" style={{ gap: "var(--space-4)" }}>
                                    <div>
                                        <label className="label">Broker</label>
                                        <input
                                            type="text"
                                            className="input"
                                            value={mqttBroker}
                                            onChange={(e) => setMqttBroker(e.target.value)}
                                            placeholder="mqtt.example.com"
                                        />
                                    </div>

                                    <div>
                                        <label className="label">Port</label>
                                        <input
                                            type="number"
                                            className="input"
                                            value={mqttPort}
                                            onChange={(e) => setMqttPort(Number(e.target.value))}
                                            min={1}
                                            max={65535}
                                            style={{ maxWidth: "120px" }}
                                        />
                                    </div>

                                    <div>
                                        <label className="label">Topic</label>
                                        <input
                                            type="text"
                                            className="input"
                                            value={mqttTopic}
                                            onChange={(e) => setMqttTopic(e.target.value)}
                                            placeholder="vision/results"
                                        />
                                    </div>

                                    <div>
                                        <label className="label">Username (optional)</label>
                                        <input
                                            type="text"
                                            className="input"
                                            value={mqttUsername}
                                            onChange={(e) => setMqttUsername(e.target.value)}
                                        />
                                    </div>

                                    <div>
                                        <label className="label">Password (optional)</label>
                                        <input
                                            type="password"
                                            className="input"
                                            value={mqttPassword}
                                            onChange={(e) => setMqttPassword(e.target.value)}
                                        />
                                    </div>
                                </div>

                                <div className="flex gap-2" style={{ marginTop: "var(--space-4)" }}>
                                    <button
                                        onClick={() => void updateIntegrations({
                                            mqtt_broker: mqttBroker || null,
                                            mqtt_port: mqttPort,
                                            mqtt_topic: mqttTopic,
                                            mqtt_username: mqttUsername || null,
                                            mqtt_password: mqttPassword || null,
                                        })}
                                        disabled={busy || !integrations.mqtt.available}
                                        className="btn btn-primary"
                                    >
                                        Apply MQTT Settings
                                    </button>

                                    <button
                                        onClick={() => void testMqtt()}
                                        disabled={busy || !integrations.mqtt.configured}
                                        className="btn btn-secondary"
                                    >
                                        🧪 Test
                                    </button>
                                </div>

                                <details style={{ marginTop: "var(--space-4)" }}>
                                    <summary className="text-sm text-muted" style={{ cursor: "pointer" }}>
                                        📖 MQTT Payload Format
                                    </summary>
                                    <pre style={{
                                        marginTop: "var(--space-2)",
                                        padding: "var(--space-3)",
                                        background: "var(--color-bg-tertiary)",
                                        borderRadius: "var(--radius-md)",
                                        fontSize: "var(--font-size-sm)",
                                    }}>
                                        {`{
  "image": "filename.jpg",
  "timestamp": "2024-01-01T12:00:00Z",
  "detections": [
    {
      "class_id": 0,
      "label": "person",
      "score": 0.95,
      "box": {"x1": 10, "y1": 20, "x2": 100, "y2": 200}
    }
  ]
}`}
                                    </pre>
                                </details>
                            </div>
                        )}
                    </div>

                    {/* Webhook */}
                    <div
                        className="card"
                        style={{
                            padding: "var(--space-4)",
                            border: integrations.webhook.configured
                                ? "2px solid var(--color-accent)"
                                : "1px solid var(--color-border)",
                        }}
                    >
                        <div
                            className="flex justify-between items-center"
                            style={{ cursor: "pointer" }}
                            onClick={() => toggleSection("webhook")}
                        >
                            <div className="flex items-center gap-2">
                                <span className="font-semibold">Webhook</span>
                                {integrations.webhook.configured ? (
                                    <span className="badge badge-accent">Configured</span>
                                ) : (
                                    <span className="badge badge-secondary">Not configured</span>
                                )}
                            </div>
                            <span>{expandedSection === "webhook" ? "▲" : "▼"}</span>
                        </div>

                        {expandedSection === "webhook" && (
                            <div style={{ marginTop: "var(--space-4)" }}>
                                <div className="flex flex-col gap-4">
                                    <div>
                                        <label className="label">URL</label>
                                        <input
                                            type="url"
                                            className="input"
                                            value={webhookUrl}
                                            onChange={(e) => setWebhookUrl(e.target.value)}
                                            placeholder="https://api.example.com/webhook"
                                            style={{ width: "100%" }}
                                        />
                                    </div>

                                    <div>
                                        <label className="label">Custom Headers (JSON)</label>
                                        <textarea
                                            className="input"
                                            value={webhookHeaders}
                                            onChange={(e) => setWebhookHeaders(e.target.value)}
                                            placeholder='{"Authorization": "Bearer token"}'
                                            rows={3}
                                            style={{ width: "100%", fontFamily: "monospace" }}
                                        />
                                    </div>
                                </div>

                                <div className="flex gap-2" style={{ marginTop: "var(--space-4)" }}>
                                    <button
                                        onClick={() => void updateIntegrations({
                                            webhook_url: webhookUrl || null,
                                            webhook_headers: webhookHeaders,
                                        })}
                                        disabled={busy}
                                        className="btn btn-primary"
                                    >
                                        Apply Webhook Settings
                                    </button>

                                    <button
                                        onClick={() => void testWebhook()}
                                        disabled={busy || !integrations.webhook.configured}
                                        className="btn btn-secondary"
                                    >
                                        🧪 Test
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {!integrations && !error && (
                <div className="text-center text-muted" style={{ padding: "var(--space-8)" }}>
                    Loading integrations...
                </div>
            )}
        </section>
    );
}
