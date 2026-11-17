from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from app.config import Thresholds, load_thresholds

YAML = Path(__file__).resolve().parent.parent / "config" / "thresholds.yaml"


def test_loads_shipped_thresholds():
    cfg = load_thresholds(YAML)
    assert cfg.formula_version == "0.3"
    assert cfg.min_sample.sells == 10
    assert cfg.fees.broker_tiers[-1][0] == float("inf")
    assert cfg.risk_tiers.balanced.score == (10, 14)
    assert cfg.herding.include_next_session is True


def test_missing_key_fails_validation(tmp_path):
    data = yaml.safe_load(YAML.read_text(encoding="utf-8"))
    del data["concentration"]["hhi_warn"]
    with pytest.raises(ValidationError):
        Thresholds.model_validate(data)


def test_unknown_key_fails_validation():
    data = yaml.safe_load(YAML.read_text(encoding="utf-8"))
    data["typo_section"] = {"x": 1}
    with pytest.raises(ValidationError):
        Thresholds.model_validate(data)
