from app.services import extract_preview


def test_extracts_dtc_and_mileage() -> None:
    preview = extract_preview("Araç 182 bin kilometrede, P0401 ve p0299 kodu verdi.")

    assert preview.dtc_codes == ["P0299", "P0401"]
    assert preview.mileage == 182000
    assert preview.provider == "demo-rules-v1"


def test_warns_when_dtc_is_missing() -> None:
    preview = extract_preview("Araç düşük devirde çekişten düşüyor.")

    assert preview.dtc_codes == []
    assert any("OBD-II" in warning for warning in preview.warnings)

