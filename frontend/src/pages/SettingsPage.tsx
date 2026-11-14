import { FormEvent, useEffect, useState } from "react";
import {
  Building2,
  Database,
  History,
  KeyRound,
  Phone,
  Save,
  ShieldCheck,
  UserRound,
} from "lucide-react";

import { api } from "../api";
import { COUNTRY_CODES } from "../countryCodes";
import { useI18n } from "../i18n";
import type { AuditEvent, AuthUser } from "../types";
import { formatDate } from "../utils";

type Props = {
  user: AuthUser;
  onUserUpdated: (user: AuthUser) => void;
  notify: (message: string) => void;
  reportError: (message: string) => void;
};

const EVENT_LABEL_KEYS: Record<string, string> = {
  "account.registered": "settings.eventRegistered",
  "account.profile_updated": "settings.eventProfileUpdated",
  "account.language_updated": "settings.eventLanguageUpdated",
  "auth.login": "settings.eventLogin",
  "auth.logout": "settings.eventLogout",
  "vehicle.created": "settings.eventVehicleCreated",
  "vehicle.updated": "settings.eventVehicleUpdated",
  "work_order.created": "settings.eventOrderCreated",
  "work_order.updated": "settings.eventOrderUpdated",
  "invoice.created": "settings.eventInvoiceCreated",
  "payment.recorded": "settings.eventPaymentRecorded",
  "inventory.part_created": "settings.eventPartCreated",
  "inventory.part_updated": "settings.eventPartUpdated",
  "inventory.stock_moved": "settings.eventStockMoved",
  "card_payment.challenge_started": "settings.eventCardChallengeStarted",
  "card_payment.challenge_failed": "settings.eventCardChallengeFailed",
  "card_payment.succeeded": "settings.eventCardPaymentSucceeded",
  "evaluation.query_created": "settings.eventEvaluationQueryCreated",
  "evaluation.query_deleted": "settings.eventEvaluationQueryDeleted",
  "evaluation.run_completed": "settings.eventEvaluationRunCompleted",
  "appointment.created": "settings.eventAppointmentCreated",
  "appointment.updated": "settings.eventAppointmentUpdated",
  "maintenance_reminder.created": "settings.eventReminderCreated",
  "maintenance_reminder.updated": "settings.eventReminderUpdated",
  "inspection.created": "settings.eventInspectionCreated",
  "inspection.updated": "settings.eventInspectionUpdated",
  "estimate.created": "settings.eventEstimateCreated",
  "estimate.updated": "settings.eventEstimateUpdated",
  "estimate.sent": "settings.eventEstimateSent",
  "estimate.approved": "settings.eventEstimateApproved",
  "estimate.rejected": "settings.eventEstimateRejected",
  "estimate.converted": "settings.eventEstimateConverted",
};

export function SettingsPage({ user, onUserUpdated, notify, reportError }: Props) {
  const { language, t } = useI18n();
  const [form, setForm] = useState({
    full_name: user.full_name,
    workshop_name: user.workshop_name ?? "",
    phone_country_code: user.phone_country_code,
    phone_number: user.phone_number,
    marketing_consent: user.marketing_consent,
  });
  const [activity, setActivity] = useState<AuditEvent[]>([]);
  const [saving, setSaving] = useState(false);
  const [phoneError, setPhoneError] = useState("");

  useEffect(() => {
    void api.accountActivity().then(setActivity).catch(() => undefined);
  }, []);

  function updatePhone(value: string) {
    if (value && !/^\d+$/.test(value)) {
      setPhoneError(t("auth.phoneDigitsOnly"));
      return;
    }
    setPhoneError("");
    setForm((current) => ({ ...current, phone_number: value }));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!/^\d{6,15}$/.test(form.phone_number)) {
      setPhoneError(t("auth.phoneDigitsOnly"));
      return;
    }
    setSaving(true);
    try {
      const result = await api.updateProfile({
        full_name: form.full_name,
        workshop_name: form.workshop_name || null,
        phone_country_code: form.phone_country_code,
        phone_number: form.phone_number,
        marketing_consent: form.marketing_consent,
      });
      onUserUpdated(result.user);
      setActivity(await api.accountActivity());
      notify(t("settings.saved"));
    } catch (error) {
      reportError(error instanceof Error ? error.message : t("settings.saveError"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="page-stack">
      <section className="page-title-row">
        <div><span className="section-kicker">{t("settings.kicker")}</span><h2>{t("settings.title")}</h2><p>{t("settings.subtitle")}</p></div>
        <span className="research-chip"><ShieldCheck size={17} /> {t("settings.accountProtected")}</span>
      </section>

      <section className="settings-grid">
        <article className="panel form-panel">
          <div className="panel-heading"><div><span className="section-kicker">{t("settings.profile")}</span><h3>{t("settings.profileInfo")}</h3></div><UserRound size={21} /></div>
          <form className="settings-form" onSubmit={submit}>
            <label>{t("auth.fullName")}<input required minLength={2} maxLength={120} value={form.full_name} onChange={(event) => setForm({ ...form, full_name: event.target.value })} /></label>
            <label>{t("auth.workshopName")}<span className="input-with-icon"><Building2 size={16} /><input maxLength={160} value={form.workshop_name} onChange={(event) => setForm({ ...form, workshop_name: event.target.value })} /></span></label>
            <label>{t("login.email")}<input value={user.email} disabled /><small className="field-help">{t("settings.emailReadonly")}</small></label>
            <label>{t("auth.phone")}<span className="phone-input-row"><select value={form.phone_country_code} onChange={(event) => setForm({ ...form, phone_country_code: event.target.value })}>{COUNTRY_CODES.map((country) => <option value={country.code} key={country.code}>{country.label}</option>)}</select><span className="input-with-icon"><Phone size={16} /><input required inputMode="numeric" minLength={6} maxLength={15} pattern="[0-9]+" value={form.phone_number} onChange={(event) => updatePhone(event.target.value)} /></span></span><small className={phoneError ? "field-error" : "field-help"}>{phoneError || t("auth.phoneHelp")}</small></label>
            <label className="consent-check settings-consent"><input type="checkbox" checked={form.marketing_consent} onChange={(event) => setForm({ ...form, marketing_consent: event.target.checked })} /><span>{t("auth.marketingAccept")}</span></label>
            <button className="primary-button" disabled={saving}><Save size={17} /> {saving ? t("common.saving") : t("settings.save")}</button>
          </form>
        </article>

        <div className="settings-side-stack">
          <article className="panel security-card">
            <div className="settings-card-icon"><KeyRound size={20} /></div>
            <div><span className="section-kicker">{t("settings.security")}</span><h3>{t("settings.localAccess")}</h3><p>{t("settings.localAccessHelp")}</p></div>
            <strong className="settings-code">111111</strong>
          </article>
          <article className="panel security-card">
            <div className="settings-card-icon green"><Database size={20} /></div>
            <div><span className="section-kicker">{t("settings.database")}</span><h3>{t("settings.dataOwnership")}</h3><p>{t("settings.dataOwnershipHelp")}</p></div>
            <div className="settings-meta"><span>{t("settings.accountCreated")}</span><strong>{formatDate(user.created_at, language)}</strong><span>{t("settings.consents")}</span><strong>{formatDate(user.privacy_accepted_at, language)}</strong></div>
          </article>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading"><div><span className="section-kicker">{t("settings.audit")}</span><h3>{t("settings.activity")}</h3></div><History size={21} /></div>
        <div className="activity-list">
          {activity.map((event) => (
            <div className="activity-row" key={event.id}>
              <span className="activity-dot" />
              <div><strong>{t(EVENT_LABEL_KEYS[event.event_type] ?? "settings.eventOther")}</strong><small>{formatDate(event.created_at, language)}</small></div>
            </div>
          ))}
          {activity.length === 0 && <div className="empty-state"><History size={28} /><p>{t("settings.noActivity")}</p></div>}
        </div>
      </section>
    </div>
  );
}
