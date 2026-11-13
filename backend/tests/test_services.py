import pytest
from pydantic import ValidationError

from app.schemas import DtcCodeCreate
from app.services import extract_preview


def test_extracts_dtc_and_mileage() -> None:
    preview = extract_preview("Araç 182 bin kilometrede, P0401 ve p0299 kodu verdi.")

    assert preview.dtc_codes == ["P0299", "P0401"]
    assert preview.mileage == 182000
    assert preview.provider == "turkish-rules-v2"
    assert preview.dtc_details[0].description


def test_warns_when_dtc_is_missing() -> None:
    preview = extract_preview("Araç düşük devirde çekişten düşüyor.")

    assert preview.dtc_codes == []
    assert any("OBD-II" in warning for warning in preview.warnings)


def test_extracts_structured_symptoms_actions_and_dotted_mileage() -> None:
    preview = extract_preview(
        "Araç 182.000 km'de. Çekişten düşüyor, siyah duman atıyor. EGR temizlendi."
    )

    assert preview.mileage == 182000
    assert "çekiş düşüklüğü" in preview.probable_fields["symptoms"]
    assert "egzoz dumanı" in preview.probable_fields["symptoms"]
    assert preview.probable_fields["actions"] == ["EGR temizlendi"]


def test_accepts_hexadecimal_obd_codes() -> None:
    assert DtcCodeCreate(code="p0a80").code == "P0A80"

    with pytest.raises(ValidationError):
        DtcCodeCreate(code="X1234")

