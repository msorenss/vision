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
    const [activeTab, setActiveTab] = useState<"opcua" | "mqtt" | "webhook">("opcua");

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
    const [useInternalMqtt, setUseInternalMqtt] = useState(true);

    // Webhook form state
    const [webhookUrl, setWebhookUrl] = useState("");
    const [webhookHeaders, setWebhookHeaders] = useState("{}");

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

            const isInternal = j.mqtt.broker === "mqtt" || j.mqtt.broker === null;
            setUseInternalMqtt(isInternal);
            setMqttBroker(isInternal ? "mqtt" : (j.mqtt.broker ?? ""));
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

    const TabButton = ({ id, label, icon }: { id: typeof activeTab, label: string, icon: string }) => (
        <button
            onClick={() => setActiveTab(id)}
            className={`btn btn-sm ${activeTab === id ? 'btn-neutral' : 'btn-ghost'}`}
            style={{ borderRadius: "var(--radius-md)" }}
        >
            {icon} {label}
        </button>
    );

    return (
        <section className="card animate-fade-in" style={{ animationDelay: "150ms" }}>
            <div className="flex justify-between items-center" style={{ marginBottom: "var(--space-4)" }}>
                <h2 style={{ margin: 0 }}>🏭 Industrial Integrations</h2>
                <button onClick={() => void refreshIntegrations()} disabled={busy} className="btn btn-secondary btn-sm">
                    {t("settings.refresh")}
                </button>
            </div>

            {/* Tabs */}
            <div className="flex gap-2 p-1 bg-base-200 rounded-lg" style={{
                marginBottom: "var(--space-4)",
                background: "var(--color-bg-secondary)",
                padding: "var(--space-1)"
            }}>
                <TabButton id="opcua" label="OPC UA" icon="🔌" />
                <TabButton id="mqtt" label="MQTT" icon="📡" />
                <TabButton id="webhook" label="Webhook" icon="🔗" />
            </div>

            {error && (
                <div className="badge badge-error w-full mb-4 p-2">
                    {error}
                </div>
            )}

            {success && (
                <div className="badge badge-success w-full mb-4 p-2">
                    {success}
                </div>
            )}

            {integrations && (
                <div className="animate-fade-in">
                    {/* OPC UA Tab */}
                    {activeTab === "opcua" && (
                        <div className="flex flex-col gap-4">
                            <div className="p-4 border rounded-lg bg-base-100" style={{
                                borderColor: integrations.opcua.running ? "var(--color-success)" : "var(--color-border)"
                            }}>
                                <div className="flex justify-between items-center mb-4">
                                    <div className="flex items-center gap-2">
                                        <span className="font-bold">OPC UA Status</span>
                                        {integrations.opcua.running ? (
                                            <span className="badge badge-success">Running</span>
                                        ) : integrations.opcua.enabled ? (
                                            <span className="badge badge-warning">Enabled</span>
                                        ) : (
                                            <span className="badge badge-secondary">Disabled</span>
                                        )}
                                    </div>
                                    <code className="text-sm bg-base-200 px-2 py-1 rounded">
                                        {integrations.opcua.endpoint || "opc.tcp://..."}
                                    </code>
                                </div>

                                <div className="grid-2 gap-4">
                                    <label className="flex items-center gap-2 cursor-pointer p-2 hover:bg-base-200 rounded">
                                        <input
                                            type="checkbox"
                                            className="checkbox"
                                            checked={opcuaEnabled}
                                            onChange={(e) => setOpcuaEnabled(e.target.checked)}
                                            disabled={!integrations.opcua.available}
                                        />
                                        <span className="font-medium">Enable Server</span>
                                    </label>

                                    <div>
                                        <label className="label text-sm font-medium">Port</label>
                                        <input
                                            type="number"
                                            className="input input-sm w-full"
                                            value={opcuaPort}
                                            onChange={(e) => setOpcuaPort(Number(e.target.value))}
                                        />
                                    </div>

                                    <div>
                                        <label className="label text-sm font-medium">Update Interval (ms)</label>
                                        <input
                                            type="number"
                                            className="input input-sm w-full"
                                            value={opcuaInterval}
                                            onChange={(e) => setOpcuaInterval(Number(e.target.value))}
                                        />
                                    </div>
                                </div>

                                <div className="mt-4 flex justify-end">
                                    <button
                                        onClick={() => void updateIntegrations({
                                            opcua_enabled: opcuaEnabled,
                                            opcua_port: opcuaPort,
                                            opcua_update_interval_ms: opcuaInterval,
                                        })}
                                        disabled={busy || !integrations.opcua.available}
                                        className="btn btn-primary"
                                    >
                                        Apply OPC UA Settings
                                    </button>
                                </div>
                            </div>

                            <div className="text-sm text-muted">
                                <p><strong>Compliance:</strong> Partially compliant with OPC 40100 (Machine Vision).</p>
                                <p><strong>Namespace:</strong> <code>http://opcfoundation.org/UA/MachineVision</code> (and legacy <code>http://volvocars.com/vision</code>)</p>
                            </div>
                        </div>
                    )}

                    {/* MQTT Tab */}
                    {activeTab === "mqtt" && (
                        <div className="flex flex-col gap-4">
                            <div className="flex gap-4 mb-2">
                                <button
                                    className={`btn btn-sm ${useInternalMqtt ? 'btn-primary' : 'btn-outline'}`}
                                    onClick={() => { setUseInternalMqtt(true); setMqttBroker("mqtt"); }}
                                >
                                    Internal Broker
                                </button>
                                <button
                                    className={`btn btn-sm ${!useInternalMqtt ? 'btn-primary' : 'btn-outline'}`}
                                    onClick={() => setUseInternalMqtt(false)}
                                >
                                    External Broker
                                </button>
                            </div>

                            <div className="p-4 border rounded-lg bg-base-100">
                                {useInternalMqtt ? (
                                    <div className="text-center py-4">
                                        <div className="text-4xl mb-2">📦</div>
                                        <h3 className="font-bold">Embedded Mosquitto Broker</h3>
                                        <p className="text-muted text-sm">Running locally on port 1883</p>
                                        <div className="mt-4 p-2 bg-base-200 rounded text-left text-xs font-mono">
                                            Host: mqtt<br />
                                            Port: 1883<br />
                                            Auth: Anonymous
                                        </div>
                                    </div>
                                ) : (
                                    <div className="grid-2 gap-4">
                                        <div>
                                            <label className="label text-sm">Broker Host</label>
                                            <input
                                                type="text"
                                                className="input input-sm w-full"
                                                value={mqttBroker}
                                                onChange={(e) => setMqttBroker(e.target.value)}
                                                placeholder="mqtt.example.com"
                                            />
                                        </div>
                                        <div>
                                            <label className="label text-sm">Port</label>
                                            <input
                                                type="number"
                                                className="input input-sm w-full"
                                                value={mqttPort}
                                                onChange={(e) => setMqttPort(Number(e.target.value))}
                                            />
                                        </div>
                                        <div>
                                            <label className="label text-sm">Username</label>
                                            <input
                                                type="text"
                                                className="input input-sm w-full"
                                                value={mqttUsername}
                                                onChange={(e) => setMqttUsername(e.target.value)}
                                            />
                                        </div>
                                        <div>
                                            <label className="label text-sm">Password</label>
                                            <input
                                                type="password"
                                                className="input input-sm w-full"
                                                value={mqttPassword}
                                                onChange={(e) => setMqttPassword(e.target.value)}
                                            />
                                        </div>
                                    </div>
                                )}

                                <div className="mt-4 border-t pt-4">
                                    <label className="label text-sm font-bold">Topic</label>
                                    <input
                                        type="text"
                                        className="input input-sm w-full"
                                        value={mqttTopic}
                                        onChange={(e) => setMqttTopic(e.target.value)}
                                        placeholder="vision/results"
                                    />
                                </div>

                                <div className="mt-4 flex justify-between">
                                    <button
                                        onClick={() => void testMqtt()}
                                        disabled={busy || !integrations.mqtt.configured}
                                        className="btn btn-ghost btn-sm"
                                    >
                                        🧪 Test Connection
                                    </button>
                                    <button
                                        onClick={() => void updateIntegrations({
                                            mqtt_broker: useInternalMqtt ? "mqtt" : (mqttBroker || null),
                                            mqtt_port: mqttPort,
                                            mqtt_topic: mqttTopic,
                                            mqtt_username: useInternalMqtt ? null : (mqttUsername || null),
                                            mqtt_password: useInternalMqtt ? null : (mqttPassword || null),
                                        })}
                                        disabled={busy}
                                        className="btn btn-primary"
                                    >
                                        Save Configuration
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Webhook Tab */}
                    {activeTab === "webhook" && (
                        <div className="flex flex-col gap-4">
                            <div className="p-4 border rounded-lg bg-base-100">
                                <div>
                                    <label className="label text-sm font-medium">Webhook URL</label>
                                    <input
                                        type="url"
                                        className="input input-sm w-full"
                                        value={webhookUrl}
                                        onChange={(e) => setWebhookUrl(e.target.value)}
                                        placeholder="https://api.example.com/webhook"
                                    />
                                </div>
                                <div className="mt-4">
                                    <label className="label text-sm font-medium">Custom Headers (JSON)</label>
                                    <textarea
                                        className="input w-full font-mono text-sm"
                                        value={webhookHeaders}
                                        onChange={(e) => setWebhookHeaders(e.target.value)}
                                        rows={3}
                                        placeholder='{"Authorization": "Bearer key"}'
                                    />
                                </div>

                                <div className="mt-4 flex justify-between">
                                    <button
                                        onClick={() => void testWebhook()}
                                        disabled={busy || !integrations.webhook.configured}
                                        className="btn btn-ghost btn-sm"
                                    >
                                        🧪 Send Test Event
                                    </button>
                                    <button
                                        onClick={() => void updateIntegrations({
                                            webhook_url: webhookUrl || null,
                                            webhook_headers: webhookHeaders,
                                        })}
                                        disabled={busy}
                                        className="btn btn-primary"
                                    >
                                        Save Webhook
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </section>
    );
}
