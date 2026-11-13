import { FormEvent, useState } from "react";
import {
  ArrowLeft,
  CheckCircle2,
  ClipboardList,
  ExternalLink,
  KeyRound,
  Languages,
  Mail,
  Moon,
  Search,
  ShieldCheck,
  Sun,
  Wrench,
} from "lucide-react";

import { api } from "../api";
import { useI18n } from "../i18n";
import { useTheme } from "../theme";
import type { AuthUser } from "../types";

type Props = {
  onAuthenticated: (user: AuthUser) => void;
};

export function LoginPage({ onAuthenticated }: Props) {
  const { language, setLanguage, t } = useI18n();
  const { theme, toggleTheme } = useTheme();
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [step, setStep] = useState<"email" | "code">("email");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [mailpitUrl, setMailpitUrl] = useState("http://localhost:8026");

  async function sendCode(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await api.requestOtp(email, language);
      if (result.mailpit_url) setMailpitUrl(result.mailpit_url);
      setStep("code");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : t("common.connectionError"));
    } finally {
      setBusy(false);
    }
  }

  async function verifyCode(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await api.verifyOtp(email, code, language);
      onAuthenticated(result.user);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : t("common.connectionError"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login-page">
      <div className="login-toolbar">
        <label className="compact-select" title={t("common.language")}>
          <Languages size={16} />
          <select value={language} onChange={(event) => setLanguage(event.target.value as "tr" | "en")}>
            <option value="tr">TR</option>
            <option value="en">EN</option>
          </select>
        </label>
        <button className="icon-button" type="button" onClick={toggleTheme} title={theme === "dark" ? t("common.light") : t("common.dark")}>
          {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
        </button>
      </div>

      <section className="login-shell">
        <aside className="login-visual">
          <div className="login-brand"><span className="brand-mark"><Wrench size={22} /></span><strong>{t("app.name")}</strong></div>
          <div className="login-visual-copy">
            <span className="section-kicker">{t("login.kicker")}</span>
            <h1>{t("login.title")}</h1>
            <p>{t("login.subtitle")}</p>
            <div className="login-features">
              <span><ClipboardList size={18} /> {t("login.feature1")}</span>
              <span><KeyRound size={18} /> {t("login.feature2")}</span>
              <span><Search size={18} /> {t("login.feature3")}</span>
            </div>
          </div>
          <div className="login-security"><ShieldCheck size={18} /><span>{t("login.secure")}</span></div>
        </aside>

        <section className="login-card">
          <div className="login-card-icon">{step === "email" ? <Mail size={25} /> : <KeyRound size={25} />}</div>
          <span className="section-kicker">{t("login.kicker")}</span>
          <h2>{step === "email" ? t("login.email") : t("login.code")}</h2>

          {step === "email" ? (
            <form className="login-form" onSubmit={sendCode}>
              <label>{t("login.email")}<input required type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder={t("login.emailPlaceholder")} /></label>
              <button className="primary-button full-button" disabled={busy}>{busy ? t("login.sending") : t("login.send")}</button>
            </form>
          ) : (
            <form className="login-form" onSubmit={verifyCode}>
              <div className="login-sent"><CheckCircle2 size={18} /><span>{t("login.sent", { email })}</span></div>
              <label>{t("login.code")}<input className="otp-input" required inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, ""))} placeholder="000000" autoFocus /></label>
              <button className="primary-button full-button" disabled={busy || code.length !== 6}>{busy ? t("login.verifying") : t("login.verify")}</button>
              <button className="text-button" type="button" onClick={() => { setStep("email"); setCode(""); setError(""); }}><ArrowLeft size={15} /> {t("login.back")}</button>
            </form>
          )}

          {error && <div className="login-error">{error}</div>}

          {step === "code" && (
            <div className="mailpit-note">
              <p>{t("login.localHint")}</p>
              <a href={mailpitUrl} target="_blank" rel="noreferrer">{t("login.localInbox")} <ExternalLink size={14} /></a>
            </div>
          )}
        </section>
      </section>
    </main>
  );
}
