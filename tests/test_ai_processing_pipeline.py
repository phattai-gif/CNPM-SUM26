import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from services.submission_service import SubmissionService

def test_submission_creates_pending_ai_flags_and_starts_thread():
    """
    Test that create_submission initializes AI flags as 'pending'
    and starts a background thread for AI Processing Pipeline.
    """
    mock_repo = MagicMock()
    mock_submission = MagicMock()
    mock_submission.id = 123
    mock_repo.create_submission.return_value = mock_submission
    
    mock_storage = MagicMock()
    mock_storage.upload_image.return_value = {
        "hd_url": "http://example.com/hd.jpg",
        "thumbnail_url": "http://example.com/thumb.jpg",
        "sha256": "fakehash",
        "width": 800,
        "height": 600,
        "file_size": 1024
    }
    
    service = SubmissionService(submission_repo=mock_repo, storage_service=mock_storage)
    
    with patch("threading.Thread") as mock_thread_class:
        mock_thread_instance = MagicMock()
        mock_thread_class.return_value = mock_thread_instance
        
        result = service.create_submission(
            round_id=1,
            user_id=1,
            title="Test Pipeline",
            file_bytes=b"fake image data",
            filename="test.jpg",
            status="submitted",
            film_metadata={"film_stock": "Kodak Portra 400"}
        )
        
        # 1. Ensure submission is returned
        assert result.id == 123
        
        # 2. Verify pending flags were saved
        save_calls = mock_repo.save_ai_flag.call_args_list
        assert len(save_calls) == 2, "Should create 2 initial pending flags"
        
        flag_types = [call.kwargs.get("flag_type") for call in save_calls]
        assert "AI_METADATA" in flag_types
        assert "duplicate_similarity" in flag_types
        
        for call in save_calls:
            assert call.kwargs.get("status") == "pending", "Initial AI flag status must be pending"
            assert call.kwargs.get("submission_id") == 123
        
        # 3. Verify thread was initialized and started
        mock_thread_class.assert_called_once()
        mock_thread_instance.start.assert_called_once()
        
        # Check thread arguments
        args, kwargs = mock_thread_class.call_args
        assert kwargs.get("target") is not None, "Thread target should be provided"
        thread_args = kwargs.get("args")
        assert thread_args[0] == 123  # submission_id
        assert thread_args[1] == "http://example.com/hd.jpg"  # hd_url
        assert thread_args[2] == b"fake image data"  # file_bytes
        
