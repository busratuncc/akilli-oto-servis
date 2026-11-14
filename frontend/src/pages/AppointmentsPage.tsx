import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  BellRing,
  CalendarDays,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Plus,
  ShieldCheck,
  UserCog,
} from "lucide-react";

import { api } from "../api";
import { useI18n } from "../i18n";
import type {
  Appointment,
  AppointmentStatus,
  MaintenanceReminder,
  ReminderStatus,
  ScheduleSummary,
  Vehicle,
} from "../types";

type Props = {
  vehicles: Vehicle[];
  notify: (message: string) => void;
  reportError: (message: string) => void;
};

const appointmentStatuses: AppointmentStatus[] = [
  "scheduled", "confirmed", "checked_in", "in_service", "completed", "cancelled", "no_show",
];

function pad(value: number) {
  return String(value).padStart(2, "0");
}

function localInputValue(date: Date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function initialTimes() {
  const start = new Date();
  start.setMinutes(0, 0, 0);
  start.setHours(start.getHours() + 1);
  const end = new Date(start.getTime() + 60 * 60 * 1000);
  return { start: localInputValue(start), end: localInputValue(end) };
}

function mondayOf(date: Date) {
  const result = new Date(date);
  result.setHours(0, 0, 0, 0);
  const day = result.getDay() || 7;
  result.setDate(result.getDate() - day + 1);
  return result;
}

function dateKey(date: Date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function AppointmentsPage({ vehicles, notify, reportError }: Props) {
  const { language, t } = useI18n();
  const locale = language === "tr" ? "tr-TR" : "en-US";
  const times = useMemo(initialTimes, []);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [reminders, setReminders] = useState<MaintenanceReminder[]>([]);
  const [summary, setSummary] = useState<ScheduleSummary | null>(null);
  const [weekStart, setWeekStart] = useState(() => mondayOf(new Date()));
  const [showAppointmentForm, setShowAppointmentForm] = useState(false);
  const [showReminderForm, setShowReminderForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [appointmentForm, setAppointmentForm] = useState({
    vehicle_id: "",
    service_type: "",
    customer_complaint: "",
    scheduled_start: times.start,
    scheduled_end: times.end,
    assigned_technician: "",
    notes: "",
  });
  const [reminderForm, setReminderForm] = useState({
    vehicle_id: "",
    title: "",
    due_date: "",
    due_mileage: "",
    notes: "",
  });

  const loadSchedule = useCallback(async () => {
    try {
      const [appointmentData, reminderData, summaryData] = await Promise.all([
        api.listAppointments(),
        api.listMaintenanceReminders(),
        api.scheduleSummary(),
      ]);
      setAppointments(appointmentData);
      setReminders(reminderData);
      setSummary(summaryData);
    } catch (error) {
      reportError(error instanceof Error ? error.message : t("schedule.loadError"));
    } finally {
      setLoading(false);
    }
  }, [reportError, t]);

  useEffect(() => { void loadSchedule(); }, [loadSchedule]);

  useEffect(() => {
    const firstVehicle = vehicles[0]?.id ?? "";
    if (firstVehicle) {
      setAppointmentForm((current) => ({ ...current, vehicle_id: current.vehicle_id || firstVehicle }));
      setReminderForm((current) => ({ ...current, vehicle_id: current.vehicle_id || firstVehicle }));
    }
  }, [vehicles]);

  const vehicleMap = useMemo(
    () => new Map(vehicles.map((vehicle) => [vehicle.id, vehicle])),
    [vehicles],
  );
  const weekDays = useMemo(
    () => Array.from({ length: 7 }, (_, index) => {
      const day = new Date(weekStart);
      day.setDate(day.getDate() + index);
      return day;
    }),
    [weekStart],
  );
  const groupedAppointments = useMemo(() => {
    const groups = new Map<string, Appointment[]>();
    appointments.forEach((appointment) => {
      const key = dateKey(new Date(appointment.scheduled_start));
      const current = groups.get(key) ?? [];
      current.push(appointment);
      groups.set(key, current);
    });
    groups.forEach((items) => items.sort((a, b) => a.scheduled_start.localeCompare(b.scheduled_start)));
    return groups;
  }, [appointments]);
  const sortedReminders = useMemo(() => {
    const order = { overdue: 0, due_soon: 1, upcoming: 2, completed: 3, dismissed: 4 };
    return [...reminders].sort((a, b) => order[a.due_state] - order[b.due_state]);
  }, [reminders]);

  function vehicleLabel(vehicleId: string) {
    const vehicle = vehicleMap.get(vehicleId);
    return vehicle ? `${vehicle.anonymous_code} · ${vehicle.brand} ${vehicle.model}` : t("common.unknownVehicle");
  }

  async function createAppointment(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      await api.createAppointment({
        vehicle_id: appointmentForm.vehicle_id,
        service_type: appointmentForm.service_type.trim(),
        customer_complaint: appointmentForm.customer_complaint.trim(),
        scheduled_start: new Date(appointmentForm.scheduled_start).toISOString(),
        scheduled_end: new Date(appointmentForm.scheduled_end).toISOString(),
        assigned_technician: appointmentForm.assigned_technician.trim() || null,
        notes: appointmentForm.notes.trim() || null,
      });
      const resetTimes = initialTimes();
      setAppointmentForm((current) => ({
        ...current,
        service_type: "",
        customer_complaint: "",
        scheduled_start: resetTimes.start,
        scheduled_end: resetTimes.end,
        assigned_technician: "",
        notes: "",
      }));
      setShowAppointmentForm(false);
      notify(t("schedule.appointmentCreated"));
      await loadSchedule();
    } catch (error) {
      reportError(error instanceof Error ? error.message : t("schedule.saveError"));
    } finally {
      setSaving(false);
    }
  }

  async function updateAppointmentStatus(id: string, status: AppointmentStatus) {
    try {
      await api.updateAppointment(id, { status });
      notify(t("schedule.appointmentUpdated"));
      await loadSchedule();
    } catch (error) {
      reportError(error instanceof Error ? error.message : t("schedule.saveError"));
    }
  }

  async function createReminder(event: FormEvent) {
    event.preventDefault();
    if (!reminderForm.due_date && !reminderForm.due_mileage) {
      reportError(t("schedule.reminderTargetRequired"));
      return;
    }
    setSaving(true);
    try {
      await api.createMaintenanceReminder({
        vehicle_id: reminderForm.vehicle_id,
        title: reminderForm.title.trim(),
        due_date: reminderForm.due_date || null,
        due_mileage: reminderForm.due_mileage ? Number(reminderForm.due_mileage) : null,
        notes: reminderForm.notes.trim() || null,
      });
      setReminderForm((current) => ({ ...current, title: "", due_date: "", due_mileage: "", notes: "" }));
      setShowReminderForm(false);
      notify(t("schedule.reminderCreated"));
      await loadSchedule();
    } catch (error) {
      reportError(error instanceof Error ? error.message : t("schedule.saveError"));
    } finally {
      setSaving(false);
    }
  }

  async function updateReminderStatus(id: string, status: ReminderStatus) {
    try {
      await api.updateMaintenanceReminder(id, { status });
      notify(t(status === "completed" ? "schedule.reminderCompleted" : "schedule.reminderDismissed"));
      await loadSchedule();
    } catch (error) {
      reportError(error instanceof Error ? error.message : t("schedule.saveError"));
    }
  }

  function moveWeek(days: number) {
    setWeekStart((current) => {
      const next = new Date(current);
      next.setDate(next.getDate() + days);
      return next;
    });
  }

  if (loading) return <div className="loading-card">{t("schedule.loading")}</div>;

  return (
    <div className="page-stack schedule-page">
      <div className="page-title-row">
        <div><span className="section-kicker">{t("schedule.kicker")}</span><h2>{t("schedule.title")}</h2><p>{t("schedule.subtitle")}</p></div>
        <button className="primary-button" disabled={vehicles.length === 0} onClick={() => setShowAppointmentForm((value) => !value)}><Plus size={17} /> {t("schedule.newAppointment")}</button>
      </div>

      {vehicles.length === 0 && <div className="inline-warning"><AlertTriangle size={17} /> {t("schedule.vehicleRequired")}</div>}

      <div className="metric-grid schedule-metrics">
        <div className="metric-card"><span className="metric-icon orange"><CalendarDays size={21} /></span><div><strong>{summary?.today_appointments ?? 0}</strong><span>{t("schedule.today")}</span></div></div>
        <div className="metric-card"><span className="metric-icon blue"><Clock3 size={21} /></span><div><strong>{summary?.upcoming_appointments ?? 0}</strong><span>{t("schedule.nextSevenDays")}</span></div></div>
        <div className="metric-card"><span className="metric-icon green"><UserCog size={21} /></span><div><strong>{summary?.active_appointments ?? 0}</strong><span>{t("schedule.activeAppointments")}</span></div></div>
        <div className="metric-card"><span className="metric-icon purple"><BellRing size={21} /></span><div><strong>{summary?.overdue_reminders ?? 0}</strong><span>{t("schedule.overdueMaintenance")}</span></div></div>
      </div>

      {showAppointmentForm && <form className="panel form-panel" onSubmit={createAppointment}>
        <div className="panel-heading"><div><span className="section-kicker">{t("schedule.appointmentFormKicker")}</span><h3>{t("schedule.appointmentFormTitle")}</h3></div><ShieldCheck size={22} /></div>
        <div className="privacy-note"><ShieldCheck size={17} /><span>{t("schedule.privacyNote")}</span></div>
        <div className="form-grid schedule-form-grid">
          <label>{t("schedule.vehicle")}<select required value={appointmentForm.vehicle_id} onChange={(event) => setAppointmentForm({ ...appointmentForm, vehicle_id: event.target.value })}><option value="">{t("common.select")}</option>{vehicles.map((vehicle) => <option key={vehicle.id} value={vehicle.id}>{vehicleLabel(vehicle.id)}</option>)}</select></label>
          <label>{t("schedule.serviceType")}<input required minLength={2} value={appointmentForm.service_type} onChange={(event) => setAppointmentForm({ ...appointmentForm, service_type: event.target.value })} placeholder={t("schedule.servicePlaceholder")} /></label>
          <label>{t("schedule.technician")}<input value={appointmentForm.assigned_technician} onChange={(event) => setAppointmentForm({ ...appointmentForm, assigned_technician: event.target.value })} placeholder={t("schedule.technicianPlaceholder")} /></label>
          <label>{t("schedule.start")}<input type="datetime-local" required value={appointmentForm.scheduled_start} onChange={(event) => setAppointmentForm({ ...appointmentForm, scheduled_start: event.target.value })} /></label>
          <label>{t("schedule.end")}<input type="datetime-local" required min={appointmentForm.scheduled_start} value={appointmentForm.scheduled_end} onChange={(event) => setAppointmentForm({ ...appointmentForm, scheduled_end: event.target.value })} /></label>
          <label className="span-2">{t("schedule.complaint")}<textarea required minLength={3} rows={3} value={appointmentForm.customer_complaint} onChange={(event) => setAppointmentForm({ ...appointmentForm, customer_complaint: event.target.value })} placeholder={t("schedule.complaintPlaceholder")} /></label>
          <label>{t("schedule.notes")}<textarea rows={3} value={appointmentForm.notes} onChange={(event) => setAppointmentForm({ ...appointmentForm, notes: event.target.value })} /></label>
          <div className="form-actions span-2"><button type="button" className="ghost-button" onClick={() => setShowAppointmentForm(false)}>{t("common.cancel")}</button><button className="primary-button" disabled={saving}>{saving ? t("common.saving") : t("schedule.createAppointment")}</button></div>
        </div>
      </form>}

      <section className="panel calendar-panel">
        <div className="panel-heading calendar-toolbar">
          <div><span className="section-kicker">{t("schedule.weeklyPlan")}</span><h3>{weekDays[0].toLocaleDateString(locale, { day: "numeric", month: "long" })} — {weekDays[6].toLocaleDateString(locale, { day: "numeric", month: "long", year: "numeric" })}</h3></div>
          <div className="calendar-actions"><button className="icon-button" title={t("schedule.previousWeek")} onClick={() => moveWeek(-7)}><ChevronLeft size={18} /></button><button className="ghost-button" onClick={() => setWeekStart(mondayOf(new Date()))}>{t("schedule.thisWeek")}</button><button className="icon-button" title={t("schedule.nextWeek")} onClick={() => moveWeek(7)}><ChevronRight size={18} /></button></div>
        </div>
        <div className="schedule-calendar">
          {weekDays.map((day) => {
            const items = groupedAppointments.get(dateKey(day)) ?? [];
            const today = dateKey(day) === dateKey(new Date());
            return <div className={`calendar-day ${today ? "today" : ""}`} key={dateKey(day)}>
              <div className="calendar-day-head"><span>{day.toLocaleDateString(locale, { weekday: "short" })}</span><strong>{day.getDate()}</strong><small>{items.length}</small></div>
              <div className="calendar-day-body">{items.length === 0 ? <span className="day-empty">{t("schedule.noAppointment")}</span> : items.map((item) => <article className={`appointment-card appointment-${item.status}`} key={item.id}>
                <div className="appointment-time"><Clock3 size={13} /> {new Date(item.scheduled_start).toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit" })}–{new Date(item.scheduled_end).toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit" })}</div>
                <strong>{item.service_type}</strong><span>{vehicleLabel(item.vehicle_id)}</span>
                {item.assigned_technician && <small><UserCog size={12} /> {item.assigned_technician}</small>}
                <select aria-label={t("schedule.status")} value={item.status} onChange={(event) => void updateAppointmentStatus(item.id, event.target.value as AppointmentStatus)}>{appointmentStatuses.map((status) => <option key={status} value={status}>{t(`schedule.status.${status}`)}</option>)}</select>
              </article>)}</div>
            </div>;
          })}
        </div>
      </section>

      <section className="panel reminder-panel">
        <div className="panel-heading"><div><span className="section-kicker">{t("schedule.maintenanceKicker")}</span><h3>{t("schedule.maintenanceTitle")}</h3><p className="panel-copy">{t("schedule.maintenanceHelp")}</p></div><button className="secondary-button" disabled={vehicles.length === 0} onClick={() => setShowReminderForm((value) => !value)}><Plus size={16} /> {t("schedule.newReminder")}</button></div>
        {showReminderForm && <form className="reminder-form" onSubmit={createReminder}>
          <label>{t("schedule.vehicle")}<select required value={reminderForm.vehicle_id} onChange={(event) => setReminderForm({ ...reminderForm, vehicle_id: event.target.value })}><option value="">{t("common.select")}</option>{vehicles.map((vehicle) => <option key={vehicle.id} value={vehicle.id}>{vehicleLabel(vehicle.id)}</option>)}</select></label>
          <label>{t("schedule.reminderTitle")}<input required minLength={2} value={reminderForm.title} onChange={(event) => setReminderForm({ ...reminderForm, title: event.target.value })} placeholder={t("schedule.reminderPlaceholder")} /></label>
          <label>{t("schedule.dueDate")}<input type="date" value={reminderForm.due_date} onChange={(event) => setReminderForm({ ...reminderForm, due_date: event.target.value })} /></label>
          <label>{t("schedule.dueMileage")}<input type="number" min="0" value={reminderForm.due_mileage} onChange={(event) => setReminderForm({ ...reminderForm, due_mileage: event.target.value })} placeholder="50000" /></label>
          <label>{t("schedule.notes")}<input value={reminderForm.notes} onChange={(event) => setReminderForm({ ...reminderForm, notes: event.target.value })} /></label>
          <button className="primary-button" disabled={saving}>{saving ? t("common.saving") : t("schedule.createReminder")}</button>
        </form>}
        <div className="reminder-list">{sortedReminders.length === 0 ? <div className="empty-state"><BellRing size={30} /><p>{t("schedule.noReminders")}</p><small>{t("schedule.noRemindersHelp")}</small></div> : sortedReminders.map((reminder) => <article className={`reminder-row reminder-${reminder.due_state}`} key={reminder.id}>
          <span className="reminder-icon">{reminder.due_state === "overdue" ? <AlertTriangle size={19} /> : reminder.due_state === "completed" ? <CheckCircle2 size={19} /> : <BellRing size={19} />}</span>
          <div className="reminder-main"><div><strong>{reminder.title}</strong><span className={`due-state due-${reminder.due_state}`}>{t(`schedule.dueState.${reminder.due_state}`)}</span></div><span>{vehicleLabel(reminder.vehicle_id)}</span><small>{[reminder.due_date ? new Date(`${reminder.due_date}T12:00:00`).toLocaleDateString(locale) : null, reminder.due_mileage !== null ? `${reminder.due_mileage.toLocaleString(locale)} km` : null].filter(Boolean).join(" · ")}</small></div>
          {reminder.status === "pending" && <div className="reminder-actions"><button className="secondary-button" onClick={() => void updateReminderStatus(reminder.id, "completed")}><CheckCircle2 size={15} /> {t("schedule.complete")}</button><button className="ghost-button" onClick={() => void updateReminderStatus(reminder.id, "dismissed")}>{t("schedule.dismiss")}</button></div>}
        </article>)}</div>
      </section>
    </div>
  );
}
