"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "@/components/I18nProvider";

interface FilterConfig {
    name: string;
    enabled: boolean;
    include_classes: string[];
    exclude_classes: string[];
    min_confidence: number;
}

interface FilterSelectorProps {
    apiBase: string;
    onFilterChange?: (filterName: string) => void;
    selectedFilter: string;
}

export function FilterSelector({
    apiBase,
    onFilterChange,
    selectedFilter,
}: FilterSelectorProps) {
    const { t } = useTranslation();
    const [filters, setFilters] = useState<FilterConfig[]>([]);
    const [labels, setLabels] = useState<string[]>([]);
    const [isOpen, setIsOpen] = useState(false);
    const [isEditing, setIsEditing] = useState(false);
    const [editingFilter, setEditingFilter] = useState<FilterConfig | null>(null);
    const [newFilterName, setNewFilterName] = useState("");

    const loadFilters = useCallback(async () => {
        try {
            const res = await fetch(`${apiBase}/api/v1/filters`);
            if (res.ok) {
                const data = await res.json();
                setFilters(data.filters || []);
            }
        } catch (e) {
            console.error("Failed to load filters:", e);
        }
    }, [apiBase]);

    const loadLabels = useCallback(async () => {
        try {
            const res = await fetch(`${apiBase}/api/v1/models/labels`);
            if (res.ok) {
                const data = await res.json();
                setLabels(data.labels || []);
            }
        } catch (e) {
            console.error("Failed to load labels:", e);
        }
    }, [apiBase]);

    useEffect(() => {
        loadFilters();
        loadLabels();
    }, [loadFilters, loadLabels]);

    const handleFilterSelect = (name: string) => {
        if (onFilterChange) {
            onFilterChange(name);
        }
        setIsOpen(false);
    };

    const handleCreateFilter = () => {
        if (!newFilterName.trim()) return;
        setEditingFilter({
            name: newFilterName.trim(),
            enabled: true,
            include_classes: [],
            exclude_classes: [],
            min_confidence: 0.5,
        });
        setNewFilterName("");
        setIsEditing(true);
    };

    const handleSaveFilter = async () => {
        if (!editingFilter) return;

        try {
            const res = await fetch(`${apiBase}/api/v1/filters`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name: editingFilter.name,
                    include_classes: editingFilter.include_classes,
                    exclude_classes: editingFilter.exclude_classes,
                    min_confidence: editingFilter.min_confidence,
                }),
            });

            if (res.ok) {
                await loadFilters();
                setIsEditing(false);
                setEditingFilter(null);
            } else {
                const data = await res.json();
                alert(data.detail || "Failed to save filter. Make sure VISION_ALLOW_RUNTIME_SETTINGS=1 is set.");
            }
        } catch (e) {
            console.error("Failed to save filter:", e);
            alert("Network error saving filter");
        }
    };

    const handleDeleteFilter = async (name: string) => {
        if (name === "default") return;

        try {
            const res = await fetch(`${apiBase}/api/v1/filters/${name}`, {
                method: "DELETE",
            });

            if (res.ok) {
                await loadFilters();
                if (selectedFilter === name) {
                    handleFilterSelect("default");
                }
            }
        } catch (e) {
            console.error("Failed to delete filter:", e);
        }
    };

    const toggleClass = (className: string, type: "include" | "exclude") => {
        if (!editingFilter) return;

        const list =
            type === "include"
                ? editingFilter.include_classes
                : editingFilter.exclude_classes;
        const otherList =
            type === "include"
                ? editingFilter.exclude_classes
                : editingFilter.include_classes;

        let newList: string[];
        if (list.includes(className)) {
            newList = list.filter((c) => c !== className);
        } else {
            newList = [...list, className];
        }

        // Remove from other list if added to this one
        const newOtherList = otherList.filter((c) => c !== className);

        setEditingFilter({
            ...editingFilter,
            include_classes: type === "include" ? newList : newOtherList,
            exclude_classes: type === "exclude" ? newList : newOtherList,
        });
    };

    const selectedFilterObj = filters.find((f) => f.name === selectedFilter);

    return (
        <div style={{ position: "relative" }}>
            {/* Filter Button */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="btn btn-secondary"
                style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "var(--space-2)",
                    minWidth: "140px",
                }}
            >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M22 3H2l8 9.46V19l4 2v-8.54L22 3z" />
                </svg>
                <span>{selectedFilter || "default"}</span>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M6 9l6 6 6-6" />
                </svg>
            </button>

            {/* Dropdown */}
            {isOpen && !isEditing && (
                <div
                    style={{
                        position: "absolute",
                        top: "100%",
                        left: 0,
                        marginTop: "var(--space-2)",
                        background: "var(--color-bg-card)",
                        border: "1px solid var(--color-border)",
                        borderRadius: "var(--radius-lg)",
                        boxShadow: "var(--shadow-lg)",
                        minWidth: "280px",
                        zIndex: 100,
                        padding: "var(--space-2)",
                    }}
                >
                    <div style={{ padding: "var(--space-2)", borderBottom: "1px solid var(--color-border)" }}>
                        <span className="text-sm font-semibold">{t("filters.title")}</span>
                    </div>

                    {/* Filter List */}
                    {filters.map((filter) => (
                        <div
                            key={filter.name}
                            style={{
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "space-between",
                                padding: "var(--space-2) var(--space-3)",
                                borderRadius: "var(--radius-md)",
                                cursor: "pointer",
                                background:
                                    selectedFilter === filter.name
                                        ? "var(--color-primary-light)"
                                        : "transparent",
                            }}
                            onClick={() => handleFilterSelect(filter.name)}
                        >
                            <div>
                                <div className="font-medium">{filter.name}</div>
                                <div className="text-xs text-muted">
                                    {filter.include_classes.length > 0
                                        ? `${t("filters.include")}: ${filter.include_classes.join(", ")}`
                                        : filter.min_confidence > 0.5
                                            ? `Min: ${(filter.min_confidence * 100).toFixed(0)}%`
                                            : t("filters.allClasses")}
                                </div>
                            </div>
                            {filter.name !== "default" && (
                                <div style={{ display: "flex", gap: "var(--space-1)" }}>
                                    <button
                                        className="btn btn-ghost btn-icon"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            setEditingFilter(filter);
                                            setIsEditing(true);
                                        }}
                                    >
                                        ✏️
                                    </button>
                                    <button
                                        className="btn btn-ghost btn-icon"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            handleDeleteFilter(filter.name);
                                        }}
                                    >
                                        🗑️
                                    </button>
                                </div>
                            )}
                        </div>
                    ))}

                    {/* Create New Filter */}
                    <div
                        style={{
                            borderTop: "1px solid var(--color-border)",
                            padding: "var(--space-3)",
                            marginTop: "var(--space-2)",
                        }}
                    >
                        <div style={{ display: "flex", gap: "var(--space-2)" }}>
                            <input
                                type="text"
                                className="input"
                                placeholder={t("filters.newName")}
                                value={newFilterName}
                                onChange={(e) => setNewFilterName(e.target.value)}
                                style={{ flex: 1 }}
                            />
                            <button
                                className="btn btn-primary"
                                onClick={handleCreateFilter}
                                disabled={!newFilterName.trim()}
                            >
                                +
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Edit Modal */}
            {isEditing && editingFilter && (
                <div
                    style={{
                        position: "fixed",
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        background: "rgba(0,0,0,0.5)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        zIndex: 200,
                    }}
                    onClick={() => setIsEditing(false)}
                >
                    <div
                        className="card"
                        style={{
                            width: "90%",
                            maxWidth: "500px",
                            maxHeight: "80vh",
                            overflow: "auto",
                        }}
                        onClick={(e) => e.stopPropagation()}
                    >
                        <h3 style={{ marginBottom: "var(--space-4)" }}>
                            {t("filters.edit")}: {editingFilter.name}
                        </h3>

                        {/* Confidence Slider */}
                        <div style={{ marginBottom: "var(--space-4)" }}>
                            <label className="label">
                                {t("filters.minConfidence")}: {(editingFilter.min_confidence * 100).toFixed(0)}%
                            </label>
                            <input
                                type="range"
                                min="0"
                                max="100"
                                value={editingFilter.min_confidence * 100}
                                onChange={(e) =>
                                    setEditingFilter({
                                        ...editingFilter,
                                        min_confidence: parseInt(e.target.value) / 100,
                                    })
                                }
                                style={{ width: "100%" }}
                            />
                        </div>

                        {/* Class Selection */}
                        <div style={{ marginBottom: "var(--space-4)" }}>
                            <label className="label">{t("filters.classes")}</label>
                            <div
                                style={{
                                    maxHeight: "200px",
                                    overflow: "auto",
                                    border: "1px solid var(--color-border)",
                                    borderRadius: "var(--radius-md)",
                                    padding: "var(--space-2)",
                                }}
                            >
                                {labels.length === 0 ? (
                                    <div className="text-muted text-sm">{t("filters.noLabels")}</div>
                                ) : (
                                    labels.map((label) => (
                                        <div
                                            key={label}
                                            style={{
                                                display: "flex",
                                                alignItems: "center",
                                                gap: "var(--space-2)",
                                                padding: "var(--space-1) var(--space-2)",
                                                borderRadius: "var(--radius-sm)",
                                            }}
                                        >
                                            <span style={{ flex: 1 }}>{label}</span>
                                            <button
                                                className={`btn btn-icon ${editingFilter.include_classes.includes(label)
                                                    ? "btn-primary"
                                                    : "btn-ghost"
                                                    }`}
                                                onClick={() => toggleClass(label, "include")}
                                                title={t("filters.include")}
                                                style={{ padding: "4px 8px", fontSize: "12px" }}
                                            >
                                                ✓
                                            </button>
                                            <button
                                                className={`btn btn-icon ${editingFilter.exclude_classes.includes(label)
                                                    ? "btn-danger"
                                                    : "btn-ghost"
                                                    }`}
                                                onClick={() => toggleClass(label, "exclude")}
                                                title={t("filters.exclude")}
                                                style={{ padding: "4px 8px", fontSize: "12px" }}
                                            >
                                                ✕
                                            </button>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>

                        {/* Summary */}
                        <div
                            style={{
                                background: "var(--color-bg-tertiary)",
                                padding: "var(--space-3)",
                                borderRadius: "var(--radius-md)",
                                marginBottom: "var(--space-4)",
                            }}
                        >
                            {editingFilter.include_classes.length > 0 && (
                                <div className="text-sm">
                                    <strong>{t("filters.include")}:</strong>{" "}
                                    {editingFilter.include_classes.join(", ")}
                                </div>
                            )}
                            {editingFilter.exclude_classes.length > 0 && (
                                <div className="text-sm">
                                    <strong>{t("filters.exclude")}:</strong>{" "}
                                    {editingFilter.exclude_classes.join(", ")}
                                </div>
                            )}
                            {editingFilter.include_classes.length === 0 &&
                                editingFilter.exclude_classes.length === 0 && (
                                    <div className="text-sm text-muted">{t("filters.allClasses")}</div>
                                )}
                        </div>

                        {/* Actions */}
                        <div style={{ display: "flex", gap: "var(--space-2)", justifyContent: "flex-end" }}>
                            <button className="btn btn-secondary" onClick={() => setIsEditing(false)}>
                                {t("common.cancel")}
                            </button>
                            <button className="btn btn-primary" onClick={handleSaveFilter}>
                                {t("common.save")}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Filter Badge */}
            {selectedFilterObj &&
                selectedFilter !== "default" &&
                (selectedFilterObj.include_classes.length > 0 ||
                    selectedFilterObj.min_confidence > 0.5) && (
                    <div
                        className="badge badge-primary"
                        style={{
                            position: "absolute",
                            top: "-8px",
                            right: "-8px",
                            fontSize: "10px",
                        }}
                    >
                        {selectedFilterObj.include_classes.length || "F"}
                    </div>
                )}
        </div>
    );
}

export default FilterSelector;
