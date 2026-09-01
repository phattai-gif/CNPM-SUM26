import pytest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from unittest.mock import MagicMock
from infrastructure.models.app.app_contest_settings_model import ContestSettingsModel


def test_contest_settings_model_has_ai_thresholds():
    """
    Test that ContestSettingsModel has the new AI threshold fields
    and they default to 70.0 as required by the task.
    """
    settings = ContestSettingsModel(contest_id=1)
    
    assert hasattr(settings, 'ai_duplicate_threshold'), "Missing ai_duplicate_threshold"
    assert hasattr(settings, 'ai_risk_threshold'), "Missing ai_risk_threshold"
    
    # Check default values from the model column definition
    assert ContestSettingsModel.ai_duplicate_threshold.default.arg == 70.0
    assert ContestSettingsModel.ai_risk_threshold.default.arg == 70.0

def test_ai_thresholds_can_be_customized():
    """
    Test that the Organizer can customize the thresholds for their contest.
    """
    settings = ContestSettingsModel(
        contest_id=2,
        ai_duplicate_threshold=85.5,
        ai_risk_threshold=60.0
    )
    
    assert settings.ai_duplicate_threshold == 85.5
    assert settings.ai_risk_threshold == 60.0
