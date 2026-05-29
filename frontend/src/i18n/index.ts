import i18n from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import { initReactI18next } from "react-i18next";

import en from "./locales/en.json";
import fr from "./locales/fr.json";
import sw from "./locales/sw.json";
import rw from "./locales/rw.json";
import ar from "./locales/ar.json";
import es from "./locales/es.json";
import pt from "./locales/pt.json";

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: { en: { translation: en }, fr: { translation: fr }, sw: { translation: sw }, rw: { translation: rw }, ar: { translation: ar }, es: { translation: es }, pt: { translation: pt } },
    fallbackLng: "en",
    interpolation: { escapeValue: false },
  });

export default i18n;
