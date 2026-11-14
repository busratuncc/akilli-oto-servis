import { FormEvent, useEffect, useMemo, useState } from "react";
import { CheckCircle2, Clock3, LockKeyhole, ShieldCheck, XCircle } from "lucide-react";

import { api } from "../api";
import { useI18n } from "../i18n";
import type { CardChallenge, CardChallengeStatus } from "../types";
import { formatCurrency } from "../utils";

const BANK_THEMES = [
  { name: "Nova Test Bank", short: "NT", theme: "nova" },
  { name: "Marmara Test Bank", short: "MT", theme: "marmara" },
  { name: "Anka Test Bank", short: "AT", theme: "anka" },
];

export function TestBank3DPage() {
  const { language, t } = useI18n();
  const challengeId = new URLSearchParams(window.location.search).get("challenge_id") ?? "";
  const token = new URLSearchParams(window.location.hash.slice(1)).get("token") ?? "";
  const [challenge, setChallenge] = useState<CardChallenge | null>(null);
  const [code, setCode] = useState("");
  const [status, setStatus] = useState<CardChallengeStatus>("pending");
  const [message, setMessage] = useState("");
  const [attempts, setAttempts] = useState(0);
  const [secondsLeft, setSecondsLeft] = useState(0);
  const [loading, setLoading] = useState(true);
  const [verifying, setVerifying] = useState(false);

  const bank = useMemo(() => {
    const score = [...challengeId].reduce((sum, character) => sum + character.charCodeAt(0), 0);
    return BANK_THEMES[score % BANK_THEMES.length];
  }, [challengeId]);

  useEffect(() => {
    let active = true;
    if (!challengeId || !token) {
      setMessage(t("bank.invalidLink"));
      setStatus("failed");
      setLoading(false);
      return () => { active = false; };
    }
    void api.testCardChallengeDetails(challengeId, token)
      .then((result) => {
        if (!active) return;
        setChallenge(result);
        setStatus(result.status);
        setAttempts(result.attempts_remaining);
        setSecondsLeft(Math.max(0, Math.floor((new Date(result.expires_at).getTime() - Date.now()) / 1000)));
      })
      .catch((error) => {
        if (!active) return;
        setMessage(error instanceof Error ? error.message : t("bank.invalidLink"));
        setStatus("failed");
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [challengeId, t, token]);

  useEffect(() => {
    if (!challenge || status !== "pending") return;
    const timer = window.setInterval(() => {
      const remaining = Math.max(0, Math.floor((new Date(challenge.expires_at).getTime() - Date.now()) / 1000));
      setSecondsLeft(remaining);
      if (remaining === 0) setStatus("expired");
    }, 1000);
    return () => window.clearInterval(timer);
  }, [challenge, status]);

  async function verify(event: FormEvent) {
    event.preventDefault();
    if (code.length !== 6) return;
    setVerifying(true);
    setMessage("");
    try {
      const result = await api.verifyTestCardChallenge(challengeId, token, code);
      setStatus(result.status);
      setMessage(result.message);
      setAttempts(result.attempts_remaining);
      setCode("");
      if (result.status === "succeeded" && result.redirect_url) {
        window.setTimeout(() => window.location.assign(result.redirect_url!), 1400);
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : t("bank.verifyError"));
    } finally {
      setVerifying(false);
    }
  }

  const minutes = String(Math.floor(secondsLeft / 60)).padStart(2, "0");
  const seconds = String(secondsLeft % 60).padStart(2, "0");

  return (
    <main className={`test-bank-page bank-${bank.theme}`}>
      <section className="test-bank-shell">
        <header className="test-bank-header"><div className="test-bank-logo">{bank.short}</div><div><strong>{bank.name}</strong><small>{t("bank.testEnvironment")}</small></div><ShieldCheck size={27} /></header>
        <div className="bank-security-strip"><LockKeyhole size={16} /> {t("bank.securePayment")}</div>

        {loading ? <div className="bank-state"><Clock3 className="spin" size={34} /><p>{t("bank.loading")}</p></div> : status === "succeeded" ? <div className="bank-state success"><CheckCircle2 size={52} /><h2>{t("bank.successTitle")}</h2><p>{message || t("bank.successText")}</p></div> : status === "failed" || status === "expired" ? <div className="bank-state failed"><XCircle size={52} /><h2>{status === "expired" ? t("bank.expiredTitle") : t("bank.failedTitle")}</h2><p>{message || (status === "expired" ? t("bank.expiredText") : t("bank.failedText"))}</p><button onClick={() => window.location.assign("/finance")}>{t("bank.return")}</button></div> : challenge && <>
          <div className="bank-transaction"><span>{t("bank.merchant")}<strong>{t("app.name")}</strong></span><span>{t("bank.invoice")}<strong>{challenge.invoice_number}</strong></span><span>{t("bank.card")}<strong>•••• •••• •••• {challenge.card_last4}</strong></span><span>{t("bank.amount")}<strong>{formatCurrency(challenge.amount, language)}</strong></span></div>
          <div className="bank-challenge-copy"><LockKeyhole size={34} /><h2>{t("bank.confirmTitle")}</h2><p>{t("bank.confirmText")}</p></div>
          <form className="bank-code-form" onSubmit={verify}><label>{t("bank.code")}<input autoFocus inputMode="numeric" maxLength={6} value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, ""))} placeholder="••••••" /></label><div className="bank-code-meta"><span><Clock3 size={15} /> {minutes}:{seconds}</span><span>{t("bank.attempts", { count: attempts })}</span></div>{message && <div className="bank-code-error"><XCircle size={16} /> {message}</div>}<button disabled={verifying || code.length !== 6}>{verifying ? t("bank.verifying") : t("bank.confirm")}</button></form>
          <div className="bank-test-hint">{t("bank.testCodeHint")} <code>123456</code></div>
        </>}
        <footer>{t("bank.footer")}</footer>
      </section>
    </main>
  );
}
