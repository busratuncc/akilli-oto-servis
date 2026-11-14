import { useEffect, useState } from "react";
import {
  CheckCircle2,
  Clock3,
  FileCheck2,
  LoaderCircle,
  ShieldCheck,
  Wrench,
  XCircle,
} from "lucide-react";
import { useParams, useSearchParams } from "react-router-dom";

import { api } from "../api";
import { useI18n } from "../i18n";
import type { PublicEstimate } from "../types";
import { formatCurrency, formatDateOnly } from "../utils";

export function EstimateApprovalPage() {
  const { language, t } = useI18n();
  const { estimateId = "" } = useParams();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [estimate, setEstimate] = useState<PublicEstimate | null>(null);
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!estimateId || !token) {
      setError(t("publicEstimate.invalid"));
      setLoading(false);
      return;
    }
    void api.publicEstimateDetails(estimateId, token)
      .then(setEstimate)
      .catch((requestError) => setError(requestError instanceof Error ? requestError.message : t("publicEstimate.invalid")))
      .finally(() => setLoading(false));
  }, [estimateId, t, token]);

  async function decide(decision: "approved" | "rejected") {
    setSubmitting(true);
    setError("");
    try {
      setEstimate(await api.publicEstimateDecision(estimateId, token, decision, note.trim() || null));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : t("publicEstimate.decisionError"));
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <div className="public-estimate-page"><div className="public-estimate-loading"><LoaderCircle className="spin" size={30} /><strong>{t("publicEstimate.loading")}</strong></div></div>;

  if (error && !estimate) return <div className="public-estimate-page"><div className="public-estimate-error"><XCircle size={42} /><h2>{t("publicEstimate.unavailable")}</h2><p>{error}</p></div></div>;

  if (!estimate) return null;
  const decided = ["approved", "rejected", "converted"].includes(estimate.status);
  const actionable = estimate.status === "sent";

  return <div className="public-estimate-page">
    <div className="public-estimate-shell">
      <header className="public-estimate-header"><span className="brand-mark"><Wrench size={21} /></span><div><strong>{estimate.workshop_name}</strong><small>{t("publicEstimate.secureApproval")}</small></div><span className="public-security"><ShieldCheck size={16} /> {t("publicEstimate.privateLink")}</span></header>

      <main className="public-estimate-content">
        {decided && <div className={`decision-banner decision-${estimate.status}`}>
          {estimate.status === "rejected" ? <XCircle size={24} /> : <CheckCircle2 size={24} />}
          <span><strong>{t(`publicEstimate.result.${estimate.status}`)}</strong><small>{estimate.status === "converted" ? t("publicEstimate.convertedHelp") : t("publicEstimate.decisionRecorded")}</small></span>
        </div>}
        {estimate.status === "expired" && <div className="decision-banner decision-expired"><Clock3 size={24} /><span><strong>{t("publicEstimate.result.expired")}</strong><small>{t("publicEstimate.expiredHelp")}</small></span></div>}

        <section className="public-estimate-title"><div><span className="section-kicker">{estimate.estimate_number}</span><h1>{t("publicEstimate.title")}</h1><p>{estimate.vehicle_code} · {estimate.vehicle_description}</p></div><div className="public-total"><small>{t("publicEstimate.total")}</small><strong>{formatCurrency(estimate.total_amount, language)}</strong><span>{t("publicEstimate.taxIncluded")}</span></div></section>

        <section className="public-estimate-context"><span><FileCheck2 size={16} /><span><small>{t("publicEstimate.reportedIssue")}</small><strong>{estimate.complaint}</strong></span></span><span><Clock3 size={16} /><span><small>{t("publicEstimate.validUntil")}</small><strong>{formatDateOnly(estimate.valid_until, language)}</strong></span></span></section>

        <section className="public-estimate-lines"><div className="public-line public-line-head"><span>{t("publicEstimate.service")}</span><span>{t("publicEstimate.quantity")}</span><span>{t("publicEstimate.unitPrice")}</span><span>{t("publicEstimate.amount")}</span></div>{estimate.line_items.map((item) => <div className="public-line" key={item.id}><span><strong>{item.description}</strong><small>{t(`finance.${item.item_type}`)}</small></span><span>{item.quantity}</span><span>{formatCurrency(item.unit_price, language)}</span><strong>{formatCurrency(item.line_total, language)}</strong></div>)}</section>

        <section className="public-estimate-totals"><span>{t("finance.subtotal")}<strong>{formatCurrency(estimate.subtotal, language)}</strong></span>{Number(estimate.discount_amount) > 0 && <span>{t("finance.discount")}<strong>-{formatCurrency(estimate.discount_amount, language)}</strong></span>}<span>{t("finance.tax")} ({estimate.tax_rate}%)<strong>{formatCurrency(estimate.tax_amount, language)}</strong></span><span className="public-grand-total">{t("publicEstimate.total")}<strong>{formatCurrency(estimate.total_amount, language)}</strong></span></section>

        {estimate.notes && <section className="public-estimate-note"><strong>{t("publicEstimate.workshopNote")}</strong><p>{estimate.notes}</p></section>}
        {estimate.response_note && <section className="public-estimate-note response"><strong>{t("publicEstimate.yourNote")}</strong><p>{estimate.response_note}</p></section>}

        {actionable && <section className="public-decision"><div><span className="section-kicker">{t("publicEstimate.decisionKicker")}</span><h3>{t("publicEstimate.decisionTitle")}</h3><p>{t("publicEstimate.decisionHelp")}</p></div><label>{t("publicEstimate.optionalNote")}<textarea rows={3} maxLength={1000} value={note} onChange={(event) => setNote(event.target.value)} placeholder={t("publicEstimate.notePlaceholder")} /></label>{error && <div className="card-form-error">{error}</div>}<div className="public-decision-actions"><button className="reject-button" disabled={submitting} onClick={() => void decide("rejected")}><XCircle size={18} /> {t("publicEstimate.reject")}</button><button className="approve-button" disabled={submitting} onClick={() => void decide("approved")}><CheckCircle2 size={18} /> {submitting ? t("common.saving") : t("publicEstimate.approve")}</button></div><small className="public-legal"><ShieldCheck size={14} /> {t("publicEstimate.legalNote")}</small></section>}
      </main>
    </div>
  </div>;
}
