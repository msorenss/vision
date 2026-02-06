"use client";

import { useTranslation } from "./I18nProvider";
import { localeFlags, localeNames, type Locale } from "@/i18n/translations";
import styles from "./LanguageSelector.module.css";

export function LanguageSelector() {
    const { locale, setLocale, t } = useTranslation();

    const toggleLocale = () => {
        const locales = Object.keys(localeNames) as Locale[];
        const currentIndex = locales.indexOf(locale);
        const nextIndex = (currentIndex + 1) % locales.length;
        setLocale(locales[nextIndex]);
    };

    return (
        <button
            onClick={toggleLocale}
            className={`btn btn-ghost btn-icon ${styles.languageButton}`}
            title={`${t("settings.language")}: ${localeNames[locale]}`}
            aria-label="Change language"
        >
            {localeFlags[locale]}
        </button>
    );
}

export function LanguageDropdown() {
    const { locale, setLocale, t } = useTranslation();

    return (
        <div className={styles.dropdownContainer}>
            <select
                value={locale}
                onChange={(e) => setLocale(e.target.value as Locale)}
                className={`input select ${styles.languageSelect}`}
                aria-label={t("settings.language")}
            >
                {Object.entries(localeNames).map(([key, name]) => (
                    <option key={key} value={key}>
                        {localeFlags[key as Locale]} {name}
                    </option>
                ))}
            </select>
        </div>
    );
}
