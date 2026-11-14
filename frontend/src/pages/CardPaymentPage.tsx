import { FormEvent, useEffect, useState } from "react";
import { ArrowLeft, CreditCard, LockKeyhole, ShieldCheck } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";

import { api } from "../api";
import { useI18n } from "../i18n";
import type { Invoice } from "../types";
import { formatCurrency } from "../utils";

type Props = {
  reportError: (message: string) => void;
};

function formatCardNumber(value: string) {
  return value.replace(/\D/g, "").slice(0, 19).replace(/(.{4})/g, "$1 ").trim();
}

function validLuhn(value: string) {
  const digits = value.replace(/\D/g, "");
  if (digits.length < 13 || digits.length > 19) return false;
  let sum = 0;
  let double = false;
  for (let index = digits.length - 1; index >= 0; index -= 1) {
    let digit = Number(digits[index]);
    if (double) {
      digit *= 2;
      if (digit > 9) digit -= 9;
    }
    sum += digit;
    double = !double;
  }
  return sum % 10 === 0;
}

function validExpiry(value: string) {
  const match = /^(0[1-9]|1[0-2])\/(\d{2})$/.exec(value);
  if (!match) return false;
  const month = Number(match[1]);
  const year = 2000 + Number(match[2]);
  const now = new Date();
  return year > now.getFullYear() || (year === now.getFullYear() && month >= now.getMonth() + 1);
}

export function CardPaymentPage({ reportError }: Props) {
  const { invoiceId = "" } = useParams();
  const navigate = useNavigate();
  const { language, t } = useI18n();
  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [holder, setHolder] = useState("");
  const [cardNumber, setCardNumber] = useState("");
  const [expiry, setExpiry] = useState("");
  const [cvv, setCvv] = useState("");
  const [amount, setAmount] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let active = true;
    void api.getInvoice(invoiceId)
      .then((result) => {
        if (!active) return;
        setInvoice(result);
        setAmount(result.balance_due);
      })
      .catch((requestError) => {
        if (active) reportError(requestError instanceof Error ? requestError.message : t("card.loadError"));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [invoiceId, reportError, t]);

  function updateExpiry(value: string) {
    const digits = value.replace(/\D/g, "").slice(0, 4);
    setExpiry(digits.length > 2 ? `${digits.slice(0, 2)}/${digits.slice(2)}` : digits);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!invoice) return;
    const digits = cardNumber.replace(/\D/g, "");
    if (holder.trim().length < 3) {
      setError(t("card.holderError"));
      return;
    }
    if (!validLuhn(digits)) {
      setError(t("card.numberError"));
      return;
    }
    if (!validExpiry(expiry)) {
      setError(t("card.expiryError"));
      return;
    }
    if (!/^\d{3,4}$/.test(cvv)) {
      setError(t("card.cvvError"));
      return;
    }
    if (Number(amount) <= 0 || Number(amount) > Number(invoice.balance_due)) {
      setError(t("card.amountError"));
      return;
    }

    setError("");
    setSubmitting(true);
    try {
      // Only the amount and last four test-card digits leave this page.
      const result = await api.startTestCardPayment(invoice.id, amount, digits.slice(-4));
      window.location.assign(result.redirect_url);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : t("card.startError"));
      setSubmitting(false);
    }
  }

  if (loading) return <div className="loading-card">{t("card.loading")}</div>;
  if (!invoice) return <div className="empty-state tall-empty"><CreditCard size={32} /><p>{t("card.loadError")}</p></div>;

  return (
    <div className="page-stack card-payment-page">
      <button className="text-button back-payment" onClick={() => navigate("/finance")}><ArrowLeft size={17} /> {t("card.back")}</button>
      <section className="page-title-row"><div><span className="section-kicker">{t("card.kicker")}</span><h2>{t("card.title")}</h2><p>{t("card.subtitle")}</p></div></section>

      <div className="card-payment-layout">
        <section className="panel card-form-panel">
          <div className="test-mode-banner"><ShieldCheck size={19} /><span><strong>{t("card.testMode")}</strong>{t("card.testModeHelp")}</span></div>
          <form className="card-form" onSubmit={submit} autoComplete="off">
            <label>{t("card.amount")}<input type="number" required min="0.01" max={invoice.balance_due} step="0.01" value={amount} onChange={(event) => setAmount(event.target.value)} /></label>
            <label>{t("card.holder")}<input required value={holder} onChange={(event) => setHolder(event.target.value.toUpperCase())} placeholder="BÜŞRA TUNÇ" autoComplete="off" /></label>
            <label>{t("card.number")}<div className="input-with-icon"><CreditCard size={18} /><input required inputMode="numeric" value={cardNumber} onChange={(event) => setCardNumber(formatCardNumber(event.target.value))} placeholder="4242 4242 4242 4242" autoComplete="off" /></div></label>
            <div className="card-short-fields"><label>{t("card.expiry")}<input required inputMode="numeric" value={expiry} onChange={(event) => updateExpiry(event.target.value)} placeholder="12/30" autoComplete="off" /></label><label>{t("card.cvv")}<input required inputMode="numeric" maxLength={4} value={cvv} onChange={(event) => setCvv(event.target.value.replace(/\D/g, ""))} placeholder="123" autoComplete="off" /></label></div>
            {error && <div className="card-form-error">{error}</div>}
            <button className="primary-button full-button" disabled={submitting}><LockKeyhole size={17} /> {submitting ? t("card.redirecting") : t("card.pay")}</button>
          </form>
          <div className="card-data-note"><LockKeyhole size={17} /><span>{t("card.dataNote")}</span></div>
        </section>

        <aside className="card-preview-column">
          <div className="demo-card">
            <div className="demo-card-top"><span>{t("card.testCard")}</span><CreditCard size={28} /></div>
            <strong>{cardNumber || "•••• •••• •••• 4242"}</strong>
            <div><span><small>{t("card.holder")}</small>{holder || "TEST USER"}</span><span><small>{t("card.expiry")}</small>{expiry || "12/30"}</span></div>
          </div>
          <div className="payment-order-card"><span>{t("card.invoice")}</span><strong>{invoice.invoice_number}</strong><span>{t("finance.balance")}</span><strong>{formatCurrency(invoice.balance_due, language)}</strong></div>
          <div className="test-card-values"><strong>{t("card.testValues")}</strong><span>{t("card.sampleCard")}: <code>4242 4242 4242 4242</code></span><span>{t("card.sampleExpiry")}: <code>12/30</code></span><span>{t("card.sampleCvv")}: <code>123</code></span><span>{t("card.sample3d")}: <code>123456</code></span></div>
        </aside>
      </div>
    </div>
  );
}
