"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

type Theme = "light" | "dark" | "system";
type ResolvedTheme = "light" | "dark";

const LS_THEME_KEY = "vision.theme";

type ThemeContextType = {
    theme: Theme;
    resolvedTheme: ResolvedTheme;
    setTheme: (theme: Theme) => void;
};

const ThemeContext = createContext<ThemeContextType | null>(null);

function getSystemTheme(): ResolvedTheme {
    if (typeof window === "undefined") return "light";
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function ThemeProvider({ children }: { children: ReactNode }) {
    const [theme, setThemeState] = useState<Theme>("system");
    const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>("light");
    const [mounted, setMounted] = useState(false);

    // Apply theme to document
    const applyTheme = (resolved: ResolvedTheme) => {
        document.documentElement.setAttribute("data-theme", resolved);
        setResolvedTheme(resolved);
    };

    useEffect(() => {
        // Load saved theme
        try {
            const stored = window.localStorage.getItem(LS_THEME_KEY) as Theme | null;
            if (stored && ["light", "dark", "system"].includes(stored)) {
                setThemeState(stored);
                if (stored === "system") {
                    applyTheme(getSystemTheme());
                } else {
                    applyTheme(stored);
                }
            } else {
                // Default to system
                applyTheme(getSystemTheme());
            }
        } catch {
            applyTheme(getSystemTheme());
        }
        setMounted(true);
    }, []);

    // Listen for system theme changes
    useEffect(() => {
        if (theme !== "system") return;

        const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
        const handleChange = () => {
            applyTheme(mediaQuery.matches ? "dark" : "light");
        };

        mediaQuery.addEventListener("change", handleChange);
        return () => mediaQuery.removeEventListener("change", handleChange);
    }, [theme]);

    const setTheme = (newTheme: Theme) => {
        setThemeState(newTheme);
        try {
            window.localStorage.setItem(LS_THEME_KEY, newTheme);
        } catch {
            // Ignore storage errors
        }

        if (newTheme === "system") {
            applyTheme(getSystemTheme());
        } else {
            applyTheme(newTheme);
        }
    };

    // Prevent flash by returning minimal shell before mount
    if (!mounted) {
        return (
            <ThemeContext.Provider value={{ theme: "system", resolvedTheme: "light", setTheme: () => { } }}>
                {children}
            </ThemeContext.Provider>
        );
    }

    return (
        <ThemeContext.Provider value={{ theme, resolvedTheme, setTheme }}>
            {children}
        </ThemeContext.Provider>
    );
}

export function useTheme() {
    const context = useContext(ThemeContext);
    if (!context) {
        throw new Error("useTheme must be used within ThemeProvider");
    }
    return context;
}
