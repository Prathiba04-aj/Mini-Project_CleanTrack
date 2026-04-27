/**
 * 🌍 Clean Track i18n Engine
 * Handles dynamic language switching without page reload
 */

const i18n = {
    currentLang: localStorage.getItem('clean_track_lang') || 'en',
    translations: {},

    async init() {
        await this.loadTranslations(this.currentLang);
        this.applyTranslations();
        
        // Add listener to selector if it exists
        const selector = document.getElementById('lang-selector');
        if (selector) {
            selector.value = this.currentLang;
            selector.addEventListener('change', (e) => this.switchLanguage(e.target.value));
        }
    },

    async loadTranslations(lang) {
        try {
            const resp = await fetch(`/static/locales/${lang}.json`);
            this.translations = await resp.json();
        } catch (err) {
            console.error("Failed to load translations for", lang);
        }
    },

    async switchLanguage(lang) {
        this.currentLang = lang;
        localStorage.setItem('clean_track_lang', lang);
        await this.loadTranslations(lang);
        this.applyTranslations();
    },

    applyTranslations() {
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            if (this.translations[key]) {
                // If it's an input with placeholder
                if (el.tagName === 'INPUT' && el.placeholder) {
                    el.placeholder = this.translations[key];
                } else {
                    el.innerText = this.translations[key];
                }
            }
        });
        
        // Update document title if needed
        if (this.translations['nav_home']) {
            const siteName = "Clean Track";
            document.title = `${this.translations['nav_home']} | ${siteName}`;
        }
    }
};

// Initialize on page load
window.addEventListener('DOMContentLoaded', () => i18n.init());
