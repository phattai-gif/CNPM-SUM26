import os
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from services.submission_service import SubmissionService

def test_get_submission_ai_report():
    # Setup
    mock_repo = MagicMock()
    
    mock_flag_1 = MagicMock()
    mock_flag_1.id = 1
    mock_flag_1.flag_type = "AI_METADATA"
    mock_flag_1.confidence_score = 0.0
    mock_flag_1.risk_level = "safe"
    mock_flag_1.status = "completed"
    mock_flag_1.reviewed_by = None
    mock_flag_1.reviewed_at = None
    mock_flag_1.review_notes = None
    mock_flag_1.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    mock_flag_1.updated_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    
    mock_report = MagicMock()
    mock_report.raw_details = {"exif_data": {"Make": "Canon"}}
    mock_report.similarity_matched_submission_id = None
    mock_flag_1.analysis_report = mock_report
    
    mock_repo.get_all_ai_flags.return_value = [mock_flag_1]
    
    # Mocking the session query for audit logs and matched submissions
    mock_session = MagicMock()
    mock_repo.session = mock_session
    mock_query = MagicMock()
    mock_session.query.return_value = mock_query
    mock_filter = MagicMock()
    mock_query.filter.return_value = mock_filter
    mock_order = MagicMock()
    mock_filter.order_by.return_value = mock_order
    mock_order.all.return_value = [] # No audit logs
    
    service = SubmissionService(submission_repo=mock_repo)
    
    # Act
    report = service.get_submission_ai_report(submission_id=123)
    
    # Assert
    assert report["submission_id"] == 123
    assert len(report["ai_flags"]) == 1
    
    flag_res = report["ai_flags"][0]
    assert flag_res["id"] == 1
    assert flag_res["flag_type"] == "AI_METADATA"
    assert flag_res["risk_level"] == "safe"
    assert flag_res["raw_details"]["exif_data"]["Make"] == "Canon"
    assert flag_res["history"] == []
