import { FormEvent, useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  AudioLines,
  Bot,
  BrainCircuit,
  Mic,
  Search,
  ShieldAlert,
  Sparkles,
  Square,
  UploadCloud,
  Wrench,
} from "lucide-react";

import { api } from "../api";
import { StatusBadge } from "../components/StatusBadge";
import { useI18n } from "../i18n";
import type { AIRuntimeStatus, CaseSearchResult, ExtractionPreview, TranscriptionResult } from "../types";
import { formatNumber, orderCode } from "../utils";
import type { IntakeDraft } from "./WorkOrdersPage";

type Props = {
  onUseDraft: (draft: IntakeDraft) => void;
  notify: (message: string) => void;
  reportError: (message: string) => void;
};

export function AssistantPage({ onUseDraft, notify, reportError }: Props) {
  const { language, t } = useI18n();
  const [text, setText] = useState("");
  const [preview, setPreview] = useState<ExtractionPreview | null>(null);
  const [extracting, setExtracting] = useState(false);
  const [recording, setRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [audioUrl, setAudioUrl] = useState("");
  const [transcribing, setTranscribing] = useState(false);
  const [transcription, setTranscription] = useState<TranscriptionResult | null>(null);
  const [runtime, setRuntime] = useState<AIRuntimeStatus | null>(null);
  const [query, setQuery] = useState("");
  const [dtcCode, setDtcCode] = useState("");
  const [searchMode, setSearchMode] = useState<"hybrid" | "keyword" | "semantic">("hybrid");
  const [results, setResults] = useState<CaseSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    void api.aiStatus().then(setRuntime).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!audioBlob) {
      setAudioUrl("");
      return;
    }
    const nextUrl = URL.createObjectURL(audioBlob);
    setAudioUrl(nextUrl);
    return () => URL.revokeObjectURL(nextUrl);
  }, [audioBlob]);

  useEffect(() => () => mediaStreamRef.current?.getTracks().forEach((track) => track.stop()), []);

  async function startRecording() {
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      reportError(t("assistant.browserUnsupported"));
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      const mimeType = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus"]
        .find((candidate) => MediaRecorder.isTypeSupported(candidate));
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];
      setAudioBlob(null);
      setTranscription(null);
      recorder.ondataavailable = (event) => {
        if (event.data.size) chunksRef.current.push(event.data);
      };
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        setAudioBlob(blob);
        stream.getTracks().forEach((track) => track.stop());
        mediaStreamRef.current = null;
      };
      recorder.start();
      setRecording(true);
    } catch (error) {
      reportError(error instanceof Error ? error.message : t("assistant.microphoneError"));
    }
  }

  function stopRecording() {
    if (mediaRecorderRef.current?.state === "recording") mediaRecorderRef.current.stop();
    setRecording(false);
  }

  async function transcribeRecording() {
    if (!audioBlob) return;
    setTranscribing(true);
    try {
      const result = await api.transcribeAudio(audioBlob);
      setTranscription(result);
      setText(result.transcript);
      notify(t("assistant.transcribed"));
      setRuntime(await api.aiStatus());
    } catch (error) {
      reportError(error instanceof Error ? error.message : t("assistant.transcribeError"));
    } finally {
      setTranscribing(false);
    }
  }

  async function extract(event: FormEvent) {
    event.preventDefault();
    setExtracting(true);
    try {
      const result = await api.extractionPreview(text);
      setPreview(result);
      notify(t("assistant.structured"));
    } catch (error) {
      reportError(error instanceof Error ? error.message : t("assistant.analyzeError"));
    } finally {
      setExtracting(false);
    }
  }

  async function search(event: FormEvent) {
    event.preventDefault();
    setSearching(true);
    try {
      setResults(await api.searchCases(query, dtcCode, searchMode));
    } catch (error) {
      reportError(error instanceof Error ? error.message : t("assistant.searchError"));
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
        <div><span className="section-kicker">{t("assistant.kicker")}</span><h2>{t("assistant.title")}</h2><p>{t("assistant.subtitle")}</p></div>
        <span className="research-chip"><BrainCircuit size={17} /> {runtime?.whisper_loaded ? t("assistant.ready") : `Whisper ${runtime?.whisper_model ?? "small"}`}</span>
      </section>

      <section className="assistant-grid">
        <article className="panel assistant-input-panel">
          <div className="assistant-icon"><Bot size={25} /></div>
          <span className="section-kicker">{t("assistant.intake")}</span>
          <h3>{t("assistant.structure")}</h3>
          <p className="panel-copy">{t("assistant.structureHelp")}</p>
          <div className={`recorder-box ${recording ? "recording" : ""}`}>
            <div className="recorder-status">
              <span className="record-dot" />
              <div><strong>{recording ? t("assistant.recording") : audioBlob ? t("assistant.audioReady") : t("assistant.voiceIntake")}</strong><small>{t("assistant.audioPrivacy")}</small></div>
            </div>
            <div className="recorder-actions">
              {!recording ? <button type="button" className="record-button" onClick={() => void startRecording()}><Mic size={17} /> {t("assistant.start")}</button> : <button type="button" className="stop-button" onClick={stopRecording}><Square size={15} /> {t("assistant.stop")}</button>}
              {!recording && <label className="ghost-button upload-button"><UploadCloud size={16} /> {t("assistant.chooseFile")}<input hidden type="file" accept="audio/webm,audio/wav,audio/mpeg,audio/mp4,audio/ogg,audio/flac" onChange={(event) => { const file = event.target.files?.[0]; if (file) { setAudioBlob(file); setTranscription(null); } }} /></label>}
            </div>
            {audioUrl && <audio className="audio-player" controls src={audioUrl} />}
            {audioBlob && <button type="button" className="secondary-button full-button" disabled={transcribing} onClick={() => void transcribeRecording()}><AudioLines size={17} /> {transcribing ? t("assistant.transcribing") : t("assistant.transcribe")}</button>}
            {transcription && <div className="transcription-meta"><span>{transcription.provider}</span><span>{transcription.duration_seconds.toFixed(1)} s</span><span>{transcription.language.toUpperCase()} %{Math.round(transcription.language_probability * 100)}</span></div>}
          </div>
          <form onSubmit={extract}>
            <label>{t("assistant.text")}<textarea rows={9} required minLength={5} value={text} onChange={(event) => setText(event.target.value)} placeholder={t("assistant.textPlaceholder")} /></label>
            <button className="primary-button full-button" disabled={extracting}><Sparkles size={17} /> {extracting ? t("assistant.analyzing") : t("assistant.analyze")}</button>
          </form>
        </article>

        <article className="panel extraction-panel">
          <div className="panel-heading"><div><span className="section-kicker">{t("assistant.preview")}</span><h3>{t("assistant.review")}</h3></div>{preview && <span className="provider-chip">{preview.provider}</span>}</div>
          {preview ? (
            <>
              <div className="extraction-metrics">
                <div><span>{t("assistant.mileage")}</span><strong>{formatNumber(preview.mileage, language)} km</strong></div>
                <div><span>{t("assistant.dtcCount")}</span><strong>{preview.dtc_codes.length}</strong></div>
              </div>
              <div className="extraction-section"><span>{t("assistant.detectedSymptoms")}</span><div className="tag-row">{Array.isArray(preview.probable_fields.symptoms) && preview.probable_fields.symptoms.length ? preview.probable_fields.symptoms.map((item) => <span className="soft-tag" key={String(item)}>{String(item)}</span>) : <span className="muted-text">{t("assistant.noSymptoms")}</span>}</div></div>
              <div className="extraction-section"><span>{t("assistant.knowledgeBase")}</span><div className="dtc-detail-list">{preview.dtc_details.map((item) => <div key={item.code}><strong>{item.code}</strong><p>{item.description || t("assistant.noDescription")}</p></div>)}{preview.dtc_details.length === 0 && <span className="muted-text">{t("assistant.noDetectedDtc")}</span>}</div></div>
              <div className="warning-box"><ShieldAlert size={19} /><span>{preview.warnings.join(" ")}</span></div>
              <button className="secondary-button full-button" onClick={usePreview}>{t("assistant.useDraft")} <ArrowRight size={17} /></button>
            </>
          ) : (
            <div className="empty-state tall-empty"><Sparkles size={32} /><p>{t("assistant.noPreview")}</p><small>{t("assistant.disclaimer")}</small></div>
          )}
        </article>
      </section>

      <section className="panel">
        <div className="panel-heading"><div><span className="section-kicker">{t("assistant.serviceMemory")}</span><h3>{t("assistant.searchVerified")}</h3></div></div>
        <form className="case-search-form" onSubmit={search}>
          <label className="search-input"><Search size={17} /><input required minLength={2} value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t("assistant.searchPlaceholder")} /></label>
          <input value={dtcCode} onChange={(event) => setDtcCode(event.target.value.toUpperCase())} maxLength={5} placeholder="P0299" />
          <select value={searchMode} onChange={(event) => setSearchMode(event.target.value as "hybrid" | "keyword" | "semantic")}><option value="hybrid">{t("assistant.modeHybrid")}</option><option value="semantic">{t("assistant.modeSemantic")}</option><option value="keyword">{t("assistant.modeKeyword")}</option></select>
          <button className="primary-button" disabled={searching}>{searching ? t("assistant.searching") : t("assistant.search")}</button>
        </form>
        <div className="case-result-grid">
          {results.map((result) => (
            <article className="case-card" key={result.work_order.id}>
              <div className="case-head"><span className="case-icon"><Wrench size={18} /></span><StatusBadge status={result.work_order.status} /></div>
              <span className="section-kicker">{orderCode(result.work_order.id)}</span>
              <h4>{result.vehicle.brand} {result.vehicle.model}</h4>
              <p>{result.work_order.customer_complaint}</p>
              <div className="tag-row">{result.work_order.dtc_codes.map((item) => <span className="dtc-chip" key={item.code}>{item.code}</span>)}</div>
              <div className="match-footer"><small>{result.match_reason}</small>{result.similarity_score != null && <strong>%{Math.round(result.similarity_score * 100)}</strong>}</div>
            </article>
          ))}
          {results.length === 0 && <div className="empty-state wide-empty"><Search size={28} /><p>{t("assistant.resultsPlaceholder")}</p></div>}
        </div>
      </section>
    </div>
  );
}
