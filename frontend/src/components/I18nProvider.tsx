"use client";

import { createContext, useContext, useEffect, useState, useCallback, useMemo, type ReactNode } from "react";
import { translations, defaultLocale, type Locale, type TranslationKey } from "@/i18n/translations";

const LS_LOCALE_KEY = "vision.locale";

type I18nContextType = {
    locale: Locale;
    setLocale: (locale: Locale) => void;
    t: (key: TranslationKey, params?: Record<string, string | number>) => string;
};

const I18nContext = createContext<I18nContextType | null>(null);

function detectBrowserLocale(): Locale {
    if (typeof navigator === "undefined") return defaultLocale;

    const browserLang = navigator.language.split("-")[0].toLowerCase();
    if (browserLang === "sv" || browserLang === "se") return "sv";
    if (browserLang === "en") return "en";

    return defaultLocale;
}

export function I18nProvider({ children }: { children: ReactNode }) {
    const [locale, setLocaleState] = useState<Locale>(defaultLocale);
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        // Try to load from localStorage, fallback to browser detection
        try {
            const stored = window.localStorage.getItem(LS_LOCALE_KEY) as Locale | null;
            if (stored && (stored === "sv" || stored === "en")) {
                setLocaleState(stored);
            } else {
                setLocaleState(detectBrowserLocale());
            }
        } catch {
            setLocaleState(detectBrowserLocale());
        }
        setMounted(true);
    }, []);

    const setLocale = useCallback((newLocale: Locale) => {
        setLocaleState(newLocale);
        try {
            window.localStorage.setItem(LS_LOCALE_KEY, newLocale);
        } catch {
            // Ignore storage errors
        }
        // Update html lang attribute
        document.documentElement.lang = newLocale;
    }, []);

    // Use the actual locale for translations (always use current state)
    const effectiveLocale = mounted ? locale : defaultLocale;

    const t = useCallback((key: TranslationKey, params?: Record<string, string | number>): string => {
        let text: string = translations[effectiveLocale][key] ?? translations[defaultLocale][key] ?? key;

        // Replace {param} placeholders with values
        if (params) {
            for (const [paramKey, value] of Object.entries(params)) {
                text = text.replace(new RegExp(`\\{${paramKey}\\}`, "g"), String(value));
            }
        }

        return text;
    }, [effectiveLocale]);

    // Memoize context value to prevent unnecessary re-renders of children
    const contextValue = useMemo<I18nContextType>(() => ({
        locale: effectiveLocale,
        setLocale: mounted ? setLocale : () => { },
        t,
    }), [effectiveLocale, mounted, setLocale, t]);

    return (
        <I18nContext.Provider value={contextValue}>
            {children}
        </I18nContext.Provider>
    );
}

export function useTranslation() {
    const context = useContext(I18nContext);
    if (!context) {
        throw new Error("useTranslation must be used within I18nProvider");
    }
    return context;
}

export function useLocale() {
    const { locale, setLocale } = useTranslation();
    return { locale, setLocale };
}
