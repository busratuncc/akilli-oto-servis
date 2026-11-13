import { FormEvent, useState } from "react";
import { ArrowRight, Bot, BrainCircuit, Search, ShieldAlert, Sparkles, Wrench } from "lucide-react";

import { api } from "../api";
import { StatusBadge } from "../components/StatusBadge";
import type { CaseSearchResult, ExtractionPreview } from "../types";
import { formatNumber, orderCode } from "../utils";
import type { IntakeDraft } from "./WorkOrdersPage";

type Props = {
  onUseDraft: (draft: IntakeDraft) => void;
  notify: (message: string) => void;
  reportError: (message: string) => void;
};

export function AssistantPage({ onUseDraft, notify, reportError }: Props) {
  const [text, setText] = useState("");
  const [preview, setPreview] = useState<ExtractionPreview | null>(null);
  const [extracting, setExtracting] = useState(false);
  const [query, setQuery] = useState("");
  const [dtcCode, setDtcCode] = useState("");
  const [results, setResults] = useState<CaseSearchResult[]>([]);
  const [searching, setSearching] = useState(false);

  async function extract(event: FormEvent) {
    event.preventDefault();
    setExtracting(true);
    try {
      const result = await api.extractionPreview(text);
      setPreview(result);
      notify("Servis anlatımı yapılandırıldı; usta kontrolüne hazır.");
    } catch (error) {
      reportError(error instanceof Error ? error.message : "Metin çözümlenemedi.");
    } finally {
      setExtracting(false);
    }
  }

  async function search(event: FormEvent) {
    event.preventDefault();
    setSearching(true);
    try {
      setResults(await api.searchCases(query, dtcCode));
    } catch (error) {
      reportError(error instanceof Error ? error.message : "Vaka araması yapılamadı.");
    } finally {
      setSearching(false);
    }
  }

  function usePreview() {
    if (!preview) return;
    const symptoms = Array.isArray(preview.probable_fields.symptoms)
      ? preview.probable_fields.symptoms.join(", ")
      : "";
    const actions = Array.isArray(preview.probable_fields.actions)
      ? preview.probable_fields.actions.join(". ")
      : "";
    onUseDraft({
      customer_complaint: preview.raw_text,
      symptoms,
      actions,
      dtc_code: preview.dtc_codes.join(", "),
      voice_transcript: preview.raw_text,
    });
  }

  return (
    <div className="page-stack">
      <section className="page-title-row">
        <div><span className="section-kicker">Karar desteği</span><h2>Akıllı servis asistanı</h2><p>Usta anlatımını düzenli kayda dönüştürün ve doğrulanmış geçmiş vakaları bulun.</p></div>
        <span className="research-chip"><BrainCircuit size={17} /> Kural motoru v2</span>
      </section>

      <section className="assistant-grid">
        <article className="panel assistant-input-panel">
          <div className="assistant-icon"><Bot size={25} /></div>
          <span className="section-kicker">Akıllı kabul</span>
          <h3>Ustanın anlatımını yapılandır</h3>
          <p className="panel-copy">Konuşma metnini girin; sistem kilometreyi, belirtileri ve OBD-II kodlarını ayırsın.</p>
          <form onSubmit={extract}>
            <label>Servis anlatımı<textarea rows={9} required minLength={5} value={text} onChange={(event) => setText(event.target.value)} placeholder="Araç 182 bin kilometrede. Düşük devirde çekişten düşüyor ve P0299 kodu veriyor. Turbo hortumu kontrol edildi…" /></label>
            <button className="primary-button full-button" disabled={extracting}><Sparkles size={17} /> {extracting ? "Çözümleniyor…" : "Anlatımı çözümle"}</button>
          </form>
        </article>

        <article className="panel extraction-panel">
          <div className="panel-heading"><div><span className="section-kicker">Yapılandırılmış ön izleme</span><h3>Usta kontrolü</h3></div>{preview && <span className="provider-chip">{preview.provider}</span>}</div>
          {preview ? (
            <>
              <div className="extraction-metrics">
                <div><span>Kilometre</span><strong>{formatNumber(preview.mileage)} km</strong></div>
                <div><span>OBD kodu</span><strong>{preview.dtc_codes.length}</strong></div>
              </div>
              <div className="extraction-section"><span>Algılanan belirtiler</span><div className="tag-row">{Array.isArray(preview.probable_fields.symptoms) && preview.probable_fields.symptoms.length ? preview.probable_fields.symptoms.map((item) => <span className="soft-tag" key={String(item)}>{String(item)}</span>) : <span className="muted-text">Belirti sınıflandırılamadı.</span>}</div></div>
              <div className="extraction-section"><span>OBD-II bilgi tabanı</span><div className="dtc-detail-list">{preview.dtc_details.map((item) => <div key={item.code}><strong>{item.code}</strong><p>{item.description || "Yerel açıklama bulunamadı."}</p></div>)}{preview.dtc_details.length === 0 && <span className="muted-text">Kod bulunamadı.</span>}</div></div>
              <div className="warning-box"><ShieldAlert size={19} /><span>{preview.warnings.join(" ")}</span></div>
              <button className="secondary-button full-button" onClick={usePreview}>İş emrine aktar <ArrowRight size={17} /></button>
            </>
          ) : (
            <div className="empty-state tall-empty"><Sparkles size={32} /><p>Çözümlenen alanlar burada görünecek.</p><small>Çıktı kesin teşhis değildir ve usta onayı gerektirir.</small></div>
          )}
        </article>
      </section>

      <section className="panel">
        <div className="panel-heading"><div><span className="section-kicker">Servis hafızası</span><h3>Benzer doğrulanmış vaka ara</h3></div></div>
        <form className="case-search-form" onSubmit={search}>
          <label className="search-input"><Search size={17} /><input required minLength={2} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Örn. çekiş düşüklüğü turbo" /></label>
          <input value={dtcCode} onChange={(event) => setDtcCode(event.target.value.toUpperCase())} maxLength={5} placeholder="P0299" />
          <button className="primary-button" disabled={searching}>{searching ? "Aranıyor…" : "Vakaları ara"}</button>
        </form>
        <div className="case-result-grid">
          {results.map((result) => (
            <article className="case-card" key={result.work_order.id}>
              <div className="case-head"><span className="case-icon"><Wrench size={18} /></span><StatusBadge status={result.work_order.status} /></div>
              <span className="section-kicker">{orderCode(result.work_order.id)}</span>
              <h4>{result.vehicle.brand} {result.vehicle.model}</h4>
              <p>{result.work_order.customer_complaint}</p>
              <div className="tag-row">{result.work_order.dtc_codes.map((item) => <span className="dtc-chip" key={item.code}>{item.code}</span>)}</div>
              <small>{result.match_reason}</small>
            </article>
          ))}
          {results.length === 0 && <div className="empty-state wide-empty"><Search size={28} /><p>Arama yaptığınızda benzer servis kayıtları burada listelenecek.</p></div>}
        </div>
      </section>
    </div>
  );
}
