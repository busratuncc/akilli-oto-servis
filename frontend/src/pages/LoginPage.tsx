import { FormEvent, useState } from "react";
import {
  ArrowLeft,
  Building2,
  CheckCircle2,
  ClipboardList,
  KeyRound,
  Languages,
  Mail,
  Moon,
  Phone,
  Search,
  ShieldCheck,
  Sun,
  UserPlus,
  Wrench,
} from "lucide-react";

import { api } from "../api";
import { useI18n } from "../i18n";
import { useTheme } from "../theme";
import type { AuthUser, RegistrationPayload } from "../types";

type Props = {
  onAuthenticated: (user: AuthUser) => void;
};

type Step = "register" | "login" | "code";

const COUNTRY_CODES = [
  { code: "+90", label: "TR +90" },
  { code: "+49", label: "DE +49" },
  { code: "+31", label: "NL +31" },
  { code: "+33", label: "FR +33" },
  { code: "+44", label: "GB +44" },
  { code: "+1", label: "US/CA +1" },
  { code: "+43", label: "AT +43" },
  { code: "+32", label: "BE +32" },
  { code: "+994", label: "AZ +994" },
  { code: "+359", label: "BG +359" },
  { code: "+30", label: "GR +30" },
  { code: "+7", label: "RU +7" },
];

const emptyRegistration = {
  full_name: "",
  workshop_name: "",
  email: "",
  phone_country_code: "+90",
  phone_number: "",
  privacy_accepted: false,
  terms_accepted: false,
  marketing_consent: false,
};

export function LoginPage({ onAuthenticated }: Props) {
  const { language, setLanguage, t } = useI18n();
  const { theme, toggleTheme } = useTheme();
  const [step, setStep] = useState<Step>("register");
  const [registration, setRegistration] = useState(emptyRegistration);
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [localCode, setLocalCode] = useState("111111");
  const [registeredNow, setRegisteredNow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [phoneError, setPhoneError] = useState("");

  function switchStep(next: Step) {
    setStep(next);
    setError("");
    setCode("");
    setRegisteredNow(false);
  }

  function updatePhone(value: string) {
    if (value && !/^\d+$/.test(value)) {
      setPhoneError(t("auth.phoneDigitsOnly"));
      return;
    }
    setPhoneError("");
    setRegistration((current) => ({ ...current, phone_number: value }));
  }

  async function register(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const privacyAccepted = formData.has("privacy_accepted");
    const termsAccepted = formData.has("terms_accepted");
    const phoneNumber = String(formData.get("phone_number") ?? "").trim();

    if (!privacyAccepted || !termsAccepted) {
      setError(t("auth.consentRequired"));
      return;
    }
    if (!/^\d{6,15}$/.test(phoneNumber)) {
      setPhoneError(t("auth.phoneDigitsOnly"));
      return;
    }
    setPhoneError("");
    setBusy(true);
    setError("");
    try {
      const payload: RegistrationPayload = {
        full_name: String(formData.get("full_name") ?? "").trim(),
        workshop_name: String(formData.get("workshop_name") ?? "").trim() || null,
        email: String(formData.get("email") ?? "").trim(),
        phone_country_code: String(formData.get("phone_country_code") ?? "+90"),
        phone_number: phoneNumber,
        preferred_language: language,
        privacy_accepted: true,
        terms_accepted: true,
        marketing_consent: formData.has("marketing_consent"),
      };
      await api.register(payload);
      const result = await api.requestOtp(payload.email, language);
      setEmail(payload.email);
      setLocalCode(result.local_code ?? "111111");
      setRegisteredNow(true);
      setStep("code");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : t("common.connectionError"));
    } finally {
      setBusy(false);
    }
  }

  async function continueLogin(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await api.requestOtp(email, language);
      setLocalCode(result.local_code ?? "111111");
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
    <main className="login-page registration-page">
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

      <section className="login-shell registration-shell">
        <aside className="login-visual">
          <div className="login-brand"><span className="brand-mark"><Wrench size={22} /></span><strong>{t("app.name")}</strong></div>
          <div className="login-visual-copy">
            <span className="section-kicker">{t("login.kicker")}</span>
            <h1>{t("auth.heroTitle")}</h1>
            <p>{t("auth.heroSubtitle")}</p>
            <div className="login-features">
              <span><ClipboardList size={18} /> {t("login.feature1")}</span>
              <span><KeyRound size={18} /> {t("login.feature2")}</span>
              <span><Search size={18} /> {t("login.feature3")}</span>
            </div>
          </div>
          <div className="login-security"><ShieldCheck size={18} /><span>{t("auth.privacyTitle")}</span></div>
        </aside>

        <section className={`login-card ${step === "register" ? "registration-card" : ""}`}>
          <div className="auth-tabs" role="tablist">
            <button role="tab" aria-selected={step === "register"} className={step === "register" ? "active" : ""} type="button" onClick={() => switchStep("register")}><UserPlus size={16} /> {t("auth.createAccount")}</button>
            <button role="tab" aria-selected={step !== "register"} className={step !== "register" ? "active" : ""} type="button" onClick={() => { setEmail((current) => current || registration.email); switchStep("login"); }}><KeyRound size={16} /> {t("auth.signIn")}</button>
          </div>
          <div className="login-card-icon">
            {step === "register" ? <UserPlus size={25} /> : step === "login" ? <Mail size={25} /> : <KeyRound size={25} />}
          </div>

          {step === "register" && (
            <>
              <span className="section-kicker">{t("auth.registerKicker")}</span>
              <h2>{t("auth.registerTitle")}</h2>
              <p className="auth-subtitle">{t("auth.registerSubtitle")}</p>
              <form className="login-form registration-form" onSubmit={register}>
                <div className="auth-form-grid">
                  <label>{t("auth.fullName")}<input name="full_name" required minLength={2} maxLength={120} autoComplete="name" value={registration.full_name} onChange={(event) => setRegistration({ ...registration, full_name: event.target.value })} placeholder={t("auth.fullNamePlaceholder")} /></label>
                  <label><span className="field-label-row">{t("auth.workshopName")} <small>({t("auth.optional")})</small></span><span className="input-with-icon"><Building2 size={16} /><input name="workshop_name" maxLength={160} autoComplete="organization" value={registration.workshop_name} onChange={(event) => setRegistration({ ...registration, workshop_name: event.target.value })} placeholder={t("auth.workshopPlaceholder")} /></span></label>
                  <label className="span-2">{t("login.email")}<input name="email" required type="email" autoComplete="email" value={registration.email} onChange={(event) => setRegistration({ ...registration, email: event.target.value })} placeholder={t("login.emailPlaceholder")} /></label>
                  <label className="span-2">{t("auth.phone")}<span className="phone-input-row"><select name="phone_country_code" aria-label={t("auth.phone")} value={registration.phone_country_code} onChange={(event) => setRegistration({ ...registration, phone_country_code: event.target.value })}>{COUNTRY_CODES.map((country) => <option value={country.code} key={country.code}>{country.label}</option>)}</select><span className="input-with-icon"><Phone size={16} /><input name="phone_number" required type="tel" inputMode="numeric" autoComplete="tel-national" minLength={6} maxLength={15} pattern="[0-9]+" value={registration.phone_number} onChange={(event) => updatePhone(event.target.value)} onBlur={(event) => updatePhone(event.currentTarget.value.trim())} placeholder={t("auth.phonePlaceholder")} /></span></span><small className={phoneError ? "field-error" : "field-help"}>{phoneError || t("auth.phoneHelp")}</small></label>
                </div>

                <div className="consent-details">
                  <details><summary>{t("auth.privacyTitle")}</summary><p>{t("auth.privacyText")}</p></details>
                  <details><summary>{t("auth.termsTitle")}</summary><p>{t("auth.termsText")}</p></details>
                </div>

                <label className="consent-check"><input name="privacy_accepted" required type="checkbox" checked={registration.privacy_accepted} onChange={(event) => setRegistration({ ...registration, privacy_accepted: event.target.checked })} /><span>{t("auth.privacyAccept")}</span></label>
                <label className="consent-check"><input name="terms_accepted" required type="checkbox" checked={registration.terms_accepted} onChange={(event) => setRegistration({ ...registration, terms_accepted: event.target.checked })} /><span>{t("auth.termsAccept")}</span></label>
                <label className="consent-check optional-consent"><input name="marketing_consent" type="checkbox" checked={registration.marketing_consent} onChange={(event) => setRegistration({ ...registration, marketing_consent: event.target.checked })} /><span>{t("auth.marketingAccept")}</span></label>

                <button className="primary-button full-button" disabled={busy}>{busy ? t("auth.registering") : t("auth.register")}</button>
                <p className="auth-switch">{t("auth.haveAccount")} <button type="button" onClick={() => { setEmail(registration.email); switchStep("login"); }}>{t("auth.signIn")}</button></p>
              </form>
            </>
          )}

          {step === "login" && (
            <>
              <span className="section-kicker">{t("login.kicker")}</span>
              <h2>{t("auth.signIn")}</h2>
              <form className="login-form" onSubmit={continueLogin}>
                <label>{t("auth.emailLookup")}<input required type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder={t("login.emailPlaceholder")} /></label>
                <button className="primary-button full-button" disabled={busy}>{busy ? t("auth.checking") : t("auth.continue")}</button>
                <p className="auth-switch">{t("auth.noAccount")} <button type="button" onClick={() => switchStep("register")}>{t("auth.createAccount")}</button></p>
              </form>
            </>
          )}

          {step === "code" && (
            <>
              <span className="section-kicker">{t("auth.localCodeTitle")}</span>
              <h2>{t("auth.enterCode")}</h2>
              <form className="login-form" onSubmit={verifyCode}>
                {registeredNow && <div className="login-sent"><CheckCircle2 size={18} /><span>{t("auth.registered")}</span></div>}
                <div className="local-code-box"><span>{t("auth.localCodeHelp")}</span><strong>{localCode}</strong></div>
                <label>{t("login.code")}<input className="otp-input" required inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, ""))} placeholder="000000" autoFocus /></label>
                <button className="primary-button full-button" disabled={busy || code.length !== 6}>{busy ? t("login.verifying") : t("login.verify")}</button>
                <button className="text-button" type="button" onClick={() => switchStep("login")}><ArrowLeft size={15} /> {t("login.back")}</button>
              </form>
            </>
          )}

          {error && <div className="login-error">{error}</div>}
        </section>
      </section>
    </main>
  );
}
