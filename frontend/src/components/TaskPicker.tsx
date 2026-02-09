"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "@/components/I18nProvider";

interface TaskInfo {
    name: string;
    description: string;
    icon: string;
    model_name: string | null;
    model_path: string | null;
    classes: string[];
    available: boolean;
}

interface TaskPickerProps {
    apiBase: string;
    onTaskChange?: (taskName: string) => void;
    selectedTask: string;
}

const LS_TASK_KEY = "vision_active_task";

export function TaskPicker({
    apiBase,
    onTaskChange,
    selectedTask,
}: TaskPickerProps) {
    const { t } = useTranslation();
    const [tasks, setTasks] = useState<TaskInfo[]>([]);

    // Restore from localStorage on mount
    useEffect(() => {
        try {
            const stored = window.localStorage.getItem(LS_TASK_KEY);
            if (stored && stored !== selectedTask && onTaskChange) {
                onTaskChange(stored);
            }
        } catch {
            // ignore
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const loadTasks = useCallback(async () => {
        try {
            const res = await fetch(`${apiBase}/api/v1/tasks`);
            if (res.ok) {
                const data = await res.json();
                setTasks(data.tasks || []);
            }
        } catch (e) {
            console.error("Failed to load tasks:", e);
        }
    }, [apiBase]);

    useEffect(() => {
        loadTasks();
    }, [loadTasks]);

    const handleTaskSelect = (name: string) => {
        if (onTaskChange) {
            onTaskChange(name);
        }
        try {
            window.localStorage.setItem(LS_TASK_KEY, name);
        } catch {
            // ignore
        }
    };

    if (tasks.length === 0) return null;

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
            <label className="text-xs text-muted font-semibold" style={{ textTransform: "uppercase", letterSpacing: "0.5px" }}>
                {t("tasks.title")}
            </label>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-1)" }}>
                {tasks.map((task) => {
                    const isActive = selectedTask === task.name;
                    return (
                        <button
                            key={task.name}
                            onClick={() => handleTaskSelect(task.name)}
                            disabled={!task.available}
                            className={`btn ${isActive ? "btn-primary" : "btn-secondary"}`}
                            title={task.description}
                            style={{
                                padding: "4px 12px",
                                fontSize: "var(--font-size-sm)",
                                borderRadius: "var(--radius-full, 999px)",
                                display: "flex",
                                alignItems: "center",
                                gap: "4px",
                                opacity: task.available ? 1 : 0.5,
                            }}
                        >
                            <span>{task.icon}</span>
                            <span>{task.description}</span>
                        </button>
                    );
                })}
            </div>

            {/* Show classes for selected task */}
            {tasks.find((t) => t.name === selectedTask)?.classes &&
                tasks.find((t) => t.name === selectedTask)!.classes.length > 0 &&
                tasks.find((t) => t.name === selectedTask)!.classes.length <= 10 && (
                    <div className="text-xs text-muted" style={{ display: "flex", flexWrap: "wrap", gap: "4px", alignItems: "center" }}>
                        <span>{t("filters.activeClasses")}:</span>
                        {tasks.find((t) => t.name === selectedTask)!.classes.map((cls) => (
                            <span
                                key={cls}
                                className="badge"
                                style={{
                                    fontSize: "10px",
                                    padding: "2px 6px",
                                    background: "var(--color-bg-tertiary)",
                                    borderRadius: "var(--radius-full, 999px)",
                                }}
                            >
                                {cls}
                            </span>
                        ))}
                    </div>
                )}
        </div>
    );
}

export default TaskPicker;
