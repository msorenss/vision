"use client";

import { useTranslation } from "./I18nProvider";
import { localeFlags, type Locale } from "@/i18n/translations";

export function LanguageSelector() {
    const { locale, setLocale, t } = useTranslation();

    const toggleLocale = () => {
        setLocale(locale === "sv" ? "en" : "sv");
    };

    return (
        <button
            onClick={toggleLocale}
            className="btn btn-ghost btn-icon"
            title={`${t("settings.language")}: ${locale === "sv" ? "Svenska" : "English"}`}
            aria-label="Change language"
            style={{ fontSize: "1.25rem" }}
        >
            {localeFlags[locale]}
        </button>
    );
}

export function LanguageDropdown() {
    const { locale, setLocale, t } = useTranslation();

    return (
        <div style={{ position: "relative", display: "inline-block" }}>
            <select
                value={locale}
                onChange={(e) => setLocale(e.target.value as Locale)}
                className="input select"
                style={{
                    padding: "var(--space-2) var(--space-8) var(--space-2) var(--space-3)",
                    fontSize: "var(--font-size-sm)",
                    minWidth: "120px"
                }}
                aria-label={t("settings.language")}
            >
                <option value="sv">🇸🇪 Svenska</option>
                <option value="en">🇬🇧 English</option>
            </select>
        </div>
    );
}
