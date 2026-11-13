import hashlib
import logging
import math
import re
import threading
from dataclasses import dataclass
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

EMBEDDING_DIMENSION = 384

_embedding_model = None
_whisper_model = None
_embedding_error: str | None = None
_whisper_error: str | None = None
_embedding_lock = threading.Lock()
_whisper_lock = threading.Lock()


class TranscriptionUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    language: str
    language_probability: float
    duration_seconds: float
    provider: str


def _cache_directory(name: str) -> Path:
    path = Path(settings.model_cache_dir) / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def _get_embedding_model():
    global _embedding_model, _embedding_error
    if _embedding_model is not None:
        return _embedding_model

    with _embedding_lock:
        if _embedding_model is not None:
            return _embedding_model
        try:
            from fastembed import TextEmbedding
            from fastembed.common.model_description import PoolingType, ModelSource

            supported_models = {
                item["model"] for item in TextEmbedding.list_supported_models()
            }
            if settings.embedding_model not in supported_models:
                TextEmbedding.add_custom_model(
                    model=settings.embedding_model,
                    pooling=PoolingType.MEAN,
                    normalization=True,
                    sources=ModelSource(hf=settings.embedding_model),
                    dim=EMBEDDING_DIMENSION,
                    model_file="onnx/model.onnx",
                )

            _embedding_model = TextEmbedding(
                model_name=settings.embedding_model,
                cache_dir=str(_cache_directory("fastembed")),
            )
            _embedding_error = None
        except Exception as exc:  # pragma: no cover - depends on model/network availability
            _embedding_error = str(exc)
            logger.exception("Embedding modeli yüklenemedi; deterministik yedek kullanılacak")
            return None
    return _embedding_model


def _hashing_embedding(text: str) -> list[float]:
    """Offline-safe lexical fallback; it is not presented as a semantic model."""
    vector = [0.0] * EMBEDDING_DIMENSION
    normalized = re.sub(r"\s+", " ", text.casefold()).strip()
    features = re.findall(r"[\wçğıöşü]+", normalized)
    features.extend(
        normalized[index : index + 3]
        for index in range(max(0, len(normalized) - 2))
        if " " not in normalized[index : index + 3]
    )

    for feature in features:
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        bucket = int.from_bytes(digest[:4], "little") % EMBEDDING_DIMENSION
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[bucket] += sign

    norm = math.sqrt(sum(value * value for value in vector))
    if norm:
        vector = [value / norm for value in vector]
    return vector


def embed_text(text: str, *, kind: str = "passage") -> tuple[list[float], str]:
    prefix = "query" if kind == "query" else "passage"
    prepared = f"{prefix}: {text.strip()}"
    model = _get_embedding_model()
    if model is None:
        return _hashing_embedding(prepared), "hashing-fallback-v1"

    try:
        vector = next(iter(model.embed([prepared])))
        return [float(value) for value in vector], settings.embedding_model
    except Exception as exc:  # pragma: no cover - runtime/model-specific failure
        global _embedding_error
        _embedding_error = str(exc)
        logger.exception("Embedding üretilemedi; deterministik yedek kullanılacak")
        return _hashing_embedding(prepared), "hashing-fallback-v1"


def _get_whisper_model():
    global _whisper_model, _whisper_error
    if _whisper_model is not None:
        return _whisper_model

    with _whisper_lock:
        if _whisper_model is not None:
            return _whisper_model
        try:
            from faster_whisper import WhisperModel

            _whisper_model = WhisperModel(
                settings.whisper_model,
                device=settings.whisper_device,
                compute_type=settings.whisper_compute_type,
                download_root=str(_cache_directory("whisper")),
            )
            _whisper_error = None
        except Exception as exc:  # pragma: no cover - depends on model/network availability
            _whisper_error = str(exc)
            logger.exception("Whisper modeli yüklenemedi")
            raise TranscriptionUnavailableError(
                "Whisper modeli yüklenemedi. Model önbelleğini ve ağ bağlantısını kontrol edin."
            ) from exc
    return _whisper_model


def transcribe_audio(path: Path) -> TranscriptionResult:
    model = _get_whisper_model()
    try:
        segments, info = model.transcribe(
            str(path),
            language="tr",
            beam_size=5,
            vad_filter=True,
            condition_on_previous_text=False,
        )
        completed_segments = list(segments)
    except Exception as exc:  # pragma: no cover - codec/model-specific failure
        global _whisper_error
        _whisper_error = str(exc)
        raise TranscriptionUnavailableError("Ses dosyası çözümlenemedi.") from exc

    transcript = " ".join(segment.text.strip() for segment in completed_segments).strip()
    duration = float(
        getattr(info, "duration", 0.0)
        or (completed_segments[-1].end if completed_segments else 0.0)
    )
    return TranscriptionResult(
        text=transcript,
        language=str(getattr(info, "language", "tr")),
        language_probability=float(getattr(info, "language_probability", 0.0)),
        duration_seconds=duration,
        provider=f"faster-whisper/{settings.whisper_model}",
    )


def runtime_status() -> dict[str, str | bool | None]:
    return {
        "embedding_model": settings.embedding_model,
        "embedding_loaded": _embedding_model is not None,
        "embedding_error": _embedding_error,
        "whisper_model": settings.whisper_model,
        "whisper_loaded": _whisper_model is not None,
        "whisper_error": _whisper_error,
    }
