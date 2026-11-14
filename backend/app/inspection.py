from collections.abc import Iterable
from typing import Protocol


class InspectionItemLike(Protocol):
    condition: str
    resolved: bool


TEMPLATE_ITEMS = (
    ("safety", "brake_pads", "Fren balataları"),
    ("safety", "brake_discs", "Fren diskleri"),
    ("safety", "brake_fluid", "Fren hidroliği"),
    ("safety", "parking_brake", "El freni"),
    ("tires", "tire_condition", "Lastik genel durumu"),
    ("tires", "tire_pressure", "Lastik basınçları"),
    ("tires", "tread_depth", "Diş derinliği"),
    ("tires", "spare_tire", "Stepne / tamir kiti"),
    ("fluids", "engine_oil", "Motor yağı"),
    ("fluids", "coolant", "Soğutma sıvısı"),
    ("fluids", "transmission_fluid", "Şanzıman yağı"),
    ("fluids", "washer_fluid", "Cam suyu"),
    ("fluids", "fluid_leaks", "Sıvı kaçakları"),
    ("electrical", "battery", "Akü ve şarj sistemi"),
    ("electrical", "headlights", "Farlar ve aydınlatma"),
    ("electrical", "warning_lights", "Gösterge uyarı lambaları"),
    ("electrical", "horn", "Korna"),
    ("electrical", "wipers", "Silecekler"),
    ("body", "windshield", "Ön cam"),
    ("body", "mirrors", "Aynalar"),
    ("body", "body_damage", "Kaporta hasarı"),
    ("body", "underbody", "Alt takım görsel kontrolü"),
)

CONDITION_WEIGHTS = {"good": 100, "attention": 55, "critical": 0}


def summarize(items: Iterable[InspectionItemLike]) -> dict[str, int]:
    item_list = list(items)
    checked = [item for item in item_list if item.condition in CONDITION_WEIGHTS]
    health_score = (
        round(sum(CONDITION_WEIGHTS[item.condition] for item in checked) / len(checked))
        if checked
        else 0
    )
    critical = [item for item in item_list if item.condition == "critical"]
    return {
        "health_score": health_score,
        "checked_count": len(checked),
        "total_count": len(item_list),
        "attention_count": sum(item.condition == "attention" for item in item_list),
        "critical_count": len(critical),
        "unresolved_critical_count": sum(not item.resolved for item in critical),
    }


def completion_errors(items: Iterable[InspectionItemLike], mechanic_approved: bool) -> list[str]:
    summary = summarize(items)
    errors: list[str] = []
    if summary["checked_count"] != summary["total_count"]:
        errors.append("Kontrol formundaki tüm maddeler değerlendirilmelidir")
    if summary["unresolved_critical_count"]:
        errors.append("Kritik bulgular çözüldü olarak işaretlenmelidir")
    if not mechanic_approved:
        errors.append("Form tamamlanmadan önce usta onayı gereklidir")
    return errors
