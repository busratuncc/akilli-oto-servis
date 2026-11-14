from dataclasses import dataclass

from app import inspection


@dataclass
class Item:
    condition: str
    resolved: bool = False


def test_summarizes_health_and_findings():
    summary = inspection.summarize(
        [
            Item("good"),
            Item("good"),
            Item("attention"),
            Item("critical"),
            Item("not_checked"),
        ]
    )

    assert summary == {
        "health_score": 64,
        "checked_count": 4,
        "total_count": 5,
        "attention_count": 1,
        "critical_count": 1,
        "unresolved_critical_count": 1,
    }


def test_completion_requires_every_item_critical_resolution_and_approval():
    errors = inspection.completion_errors(
        [Item("good"), Item("not_checked"), Item("critical")],
        mechanic_approved=False,
    )

    assert len(errors) == 3
    assert any("tüm maddeler" in error for error in errors)
    assert any("Kritik" in error for error in errors)
    assert any("usta onayı" in error for error in errors)


def test_completed_form_has_no_validation_errors():
    errors = inspection.completion_errors(
        [Item("good"), Item("attention"), Item("critical", resolved=True)],
        mechanic_approved=True,
    )

    assert errors == []


def test_template_has_stable_unique_keys_and_positions():
    keys = [item_key for _, item_key, _ in inspection.TEMPLATE_ITEMS]

    assert len(keys) >= 20
    assert len(keys) == len(set(keys))
