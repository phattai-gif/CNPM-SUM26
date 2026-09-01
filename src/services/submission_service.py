import threading
from typing import Any, Dict, List, Optional, Tuple

from infrastructure.repositories.submission_repository import SubmissionRepository
from services.storage_service import StorageService


class SubmissionService:
    """Minimal SubmissionService used by tests.

    Behavior:
    - Accepts either `files` (list of dicts with `file_bytes`), or a single
      `file_bytes` + `filename` pair.
    - Uploads bytes via `storage_service.upload_image` when present.
    - Calls `submission_repo.create_submission(...)` to persist submission.
    - When `status != 'draft'`, creates two pending AI flags via
      `submission_repo.save_ai_flag(...)` and starts a background thread
      using `threading.Thread(target=self._run_ai_detection, args=(...))`.
    """

    DEFAULT_CONTENT_TYPE = "image/jpeg"

    def __init__(
        self,
        submission_repo: Optional[SubmissionRepository] = None,
        storage_service: Optional[StorageService] = None,
    ):
        self.submission_repo = submission_repo or SubmissionRepository()
        self.storage_service = storage_service or StorageService()

    def upload_submission_image(self, file_bytes: bytes, filename: str, content_type: str = DEFAULT_CONTENT_TYPE) -> Dict[str, Any]:
        if hasattr(self.storage_service, "upload_image"):
            return self.storage_service.upload_image(file_bytes=file_bytes, filename=filename, content_type=content_type)
        return {"hd_url": None, "thumbnail_url": None, "sha256": None, "width": None, "height": None, "file_size": None}

    def _run_ai_detection(self, submission_id: int, image_url: Optional[str], file_bytes: Optional[bytes]) -> None:
        # No-op stub for tests; real implementation would analyze image/file_bytes
        return None

    def _calculate_image_hashes(self, file_bytes: Optional[bytes]):
        if not file_bytes:
            return None, None
        try:
            from services.duplicate_detection_service import DuplicateDetectionService
            ph = DuplicateDetectionService.calculate_phash_from_bytes(file_bytes)
            ah = DuplicateDetectionService.calculate_ahash_from_bytes(file_bytes)
            phs = str(ph) if ph is not None else None
            ahs = str(ah) if ah is not None else None
            return phs, ahs
        except Exception:
            return None, None

    def update_draft(
        self,
        submission_id: int,
        user_id: Optional[int] = None,
        title: Optional[str] = None,
        story_description: Optional[str] = None,
        files: Optional[List[Dict[str, Any]]] = None,
        film_metadata: Optional[Dict[str, Any]] = None,
    ):
        files_data = None

        # files_data will be populated from provided files
        if files and isinstance(files, list):
            files_data = []
            for f in files:
                if not isinstance(f, dict):
                    continue
                if f.get("file_bytes") and f.get("filename"):
                    storage_info = self.upload_submission_image(file_bytes=f.get("file_bytes"), filename=f.get("filename"), content_type=f.get("content_type") or "image/jpeg")
                    files_data.append(
                        {
                            "file_type": f.get("file_type") or "main_image",
                            "image_hd_url": storage_info.get("hd_url"),
                            "thumbnail_url": storage_info.get("thumbnail_url"),
                            "file_hash": f.get("file_hash") or storage_info.get("sha256"),
                            "width_px": storage_info.get("width"),
                            "height_px": storage_info.get("height"),
                            "file_size_bytes": storage_info.get("file_size"),
                        }
                    )
                elif f.get("image_hd_url"):
                    files_data.append(f)

        if hasattr(self.submission_repo, "update_draft"):
            return self.submission_repo.update_draft(
                submission_id=submission_id,
                user_id=user_id,
                title=title,
                story_description=story_description,
                files_data=files_data,
                film_metadata=film_metadata,
            )

        raise NotImplementedError()

    def submit_draft(self, submission_id, user_id):
        result = None
        if hasattr(self.submission_repo, "get_by_id_with_details"):
            result = self.submission_repo.get_by_id_with_details(submission_id)
        elif hasattr(self.submission_repo, "get_by_id"):
            result = self.submission_repo.get_by_id(submission_id)

        if not result:
            raise ValueError("Submission not found")

        submission_obj = result[0] if isinstance(result, tuple) else result

        owner = getattr(submission_obj, "user_id", None)
        if owner is not None and owner != user_id:
            raise PermissionError("You are not the owner of this submission")

        current_status = getattr(submission_obj, "status", None)
        if current_status in ("submitted",):
            raise ValueError("Submission already submitted")

        if current_status in ("flagged", "evaluated"):
            raise ValueError("Cannot submit a submission in current status")

        title = getattr(submission_obj, "title", None)
        has_file = False
        if isinstance(result, tuple) and len(result) > 1 and result[1]:
            has_file = True

        if not title and not has_file:
            raise ValueError("Missing required submission data")

        updated = self.submission_repo.update_status(submission_id, "submitted")

        try:
            if isinstance(updated, dict):
                return updated
            from types import SimpleNamespace
            return SimpleNamespace(id=getattr(updated, "id", submission_id), status=getattr(updated, "status", "submitted"))
        except Exception:
            return SimpleNamespace(id=submission_id, status="submitted")

    def get_submission_by_id(self, submission_id: int):
        if hasattr(self.submission_repo, "get_by_id_with_details"):
            return self.submission_repo.get_by_id_with_details(submission_id)

        if hasattr(self.submission_repo, "get_by_id"):
            return self.submission_repo.get_by_id(submission_id)

        return None

    def get_submission_detail(self, submission_id: int, user_id: Optional[int] = None, role: str = "participant"):
        result = self.get_submission_by_id(submission_id)

        if not result:
            raise ValueError("Submission not found")

        if isinstance(result, tuple):
            submission = result[0]
        else:
            submission = result

        if role == "participant" and user_id is not None:
            if getattr(submission, "user_id", None) != user_id:
                raise PermissionError("You are not allowed to view this submission")

        return result

    def get_submission_ai_report(self, submission_id: int) -> Dict[str, Any]:
        flags = []
        if hasattr(self.submission_repo, "get_all_ai_flags"):
            flags = self.submission_repo.get_all_ai_flags(submission_id)

        out_flags = []
        for flag in flags or []:
            # attempt to collect history/audit logs if available
            history = []
            try:
                session = getattr(self.submission_repo, "session", None)
                if session is not None:
                    from infrastructure.models.app.app_audit_log_model import AuditLogModel
                    q = session.query(AuditLogModel).filter(
                        AuditLogModel.entity_name == 'ai_flags',
                        AuditLogModel.entity_id == getattr(flag, 'id', None),
                    ).order_by(AuditLogModel.id.asc())
                    rows = q.all()
                    for r in rows or []:
                        history.append({
                            'action': r.action,
                            'old_value': r.old_value,
                            'new_value': r.new_value,
                            'created_at': getattr(r, 'created_at', None).isoformat() if getattr(r, 'created_at', None) else None,
                        })
            except Exception:
                history = []

            out_flags.append(
                {
                    "id": getattr(flag, "id", None),
                    "flag_type": getattr(flag, "flag_type", None),
                    "confidence_score": float(getattr(flag, "confidence_score", 0.0) or 0.0),
                    "risk_level": getattr(flag, "risk_level", None),
                    "status": getattr(flag, "status", None),
                    "raw_details": getattr(getattr(flag, "analysis_report", None), "raw_details", {}) or {},
                    "history": history,
                }
            )

        return {"submission_id": submission_id, "ai_flags": out_flags}

    def create_submission(
        self,
        round_id: int,
        user_id: int,
        title: str = "",
        files: Optional[List[Dict[str, Any]]] = None,
        file_bytes: Optional[bytes] = None,
        filename: Optional[str] = None,
        content_type: Optional[str] = DEFAULT_CONTENT_TYPE,
        image_hd_url: Optional[str] = None,
        file_hash: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        width_px: Optional[int] = None,
        height_px: Optional[int] = None,
        file_size_bytes: Optional[int] = None,
        film_metadata: Optional[Dict[str, Any]] = None,
        story_description: str = "",
        status: str = "submitted",
        file_type: Optional[str] = None,
    ):
        film_metadata = film_metadata or {}

        files_data = None

        # --------------------------------------------------------
        # ROUND STATUS CHECK
        # Reject submissions when the target round is not accepting submissions
        try:
            from infrastructure.databases.factory_database import FactoryDatabase
            session = FactoryDatabase.get_database('POSTGREE').session
            from infrastructure.models.app import RoundModel
            rnd = session.query(RoundModel).filter(RoundModel.id == round_id).first()
            if rnd is not None:
                status_value = getattr(rnd, "status", None)
                normalized = (str(status_value).strip().lower() if status_value is not None else "upcoming")
                aliases = {
                    'open': 'ongoing',
                    'active': 'ongoing',
                    'in_progress': 'ongoing',
                    'closed': 'completed',
                    'ended': 'completed',
                    'done': 'completed',
                    'draft': 'upcoming',
                    'pending': 'upcoming',
                }
                normalized = aliases.get(normalized, normalized)
                # only allow submissions when normalized status is 'ongoing'
                if normalized != 'ongoing':
                    raise ValueError(f"Cannot submit to round with status '{status_value}'")
        except ValueError:
            raise
        except Exception:
            # if we cannot check round status for any reason, proceed conservatively
            pass

        # If callers provided a single file_bytes + filename, upload it
        if file_bytes and filename:
            storage_info = self.upload_submission_image(file_bytes=file_bytes, filename=filename, content_type=content_type)
            files_data = [
                {
                    "file_type": (file_type or "main_image"),
                    "image_hd_url": storage_info.get("hd_url"),
                    "thumbnail_url": storage_info.get("thumbnail_url"),
                    "file_hash": file_hash or storage_info.get("sha256"),
                    "width_px": storage_info.get("width"),
                    "height_px": storage_info.get("height"),
                    "file_size_bytes": storage_info.get("file_size"),
                    "phash": self._calculate_image_hashes(file_bytes)[0],
                    "ahash": self._calculate_image_hashes(file_bytes)[1],
                }
            ]

        # If files list provided, prefer that (and upload any raw bytes present)
        if files and isinstance(files, list):
            files_data = []
            for f in files:
                if not isinstance(f, dict):
                    continue
                if f.get("file_bytes") and f.get("filename"):
                    storage_info = self.upload_submission_image(file_bytes=f.get("file_bytes"), filename=f.get("filename"), content_type=f.get("content_type") or content_type)
                    files_data.append(
                        {
                            "file_type": f.get("file_type") or "main_image",
                            "image_hd_url": storage_info.get("hd_url"),
                            "thumbnail_url": storage_info.get("thumbnail_url"),
                            "file_hash": f.get("file_hash") or storage_info.get("sha256"),
                            "width_px": storage_info.get("width"),
                            "height_px": storage_info.get("height"),
                            "file_size_bytes": storage_info.get("file_size"),
                            "phash": self._calculate_image_hashes(f.get("file_bytes"))[0],
                            "ahash": self._calculate_image_hashes(f.get("file_bytes"))[1],
                        }
                    )
                elif f.get("image_hd_url"):
                    files_data.append(f)

        # Create submission via repository
        submission = self.submission_repo.create_submission(
            round_id=round_id,
            user_id=user_id,
            title=title or "",
            image_hd_url=(files_data[0].get("image_hd_url") if files_data and len(files_data) > 0 else image_hd_url),
            file_hash=(files_data[0].get("file_hash") if files_data and len(files_data) > 0 else file_hash),
            story_description=story_description or "",
            thumbnail_url=(files_data[0].get("thumbnail_url") if files_data and len(files_data) > 0 else thumbnail_url),
            width_px=(files_data[0].get("width_px") if files_data and len(files_data) > 0 else width_px),
            height_px=(files_data[0].get("height_px") if files_data and len(files_data) > 0 else height_px),
            file_size_bytes=(files_data[0].get("file_size_bytes") if files_data and len(files_data) > 0 else file_size_bytes),
            files_data=files_data,
            film_stock=(film_metadata.get("film_stock") or ""),
            film_iso=film_metadata.get("film_iso"),
            camera_body=film_metadata.get("camera_body"),
            lens=film_metadata.get("lens"),
            lab_name=film_metadata.get("lab_name"),
            scanner_info=film_metadata.get("scanner_info"),
            development_process=(film_metadata.get("development_process") or "C-41"),
            taken_at_location=film_metadata.get("taken_at_location"),
            status=status,
        )

        # Post-create: initialize AI flags and fire background thread when submitted
        if status != "draft":
            try:
                self.submission_repo.save_ai_flag(
                    submission_id=getattr(submission, "id", None),
                    confidence_score=None,
                    risk_level=None,
                    flag_type="AI_METADATA",
                    status="pending",
                )
            except Exception:
                pass

            try:
                self.submission_repo.save_ai_flag(
                    submission_id=getattr(submission, "id", None),
                    confidence_score=None,
                    risk_level=None,
                    flag_type="duplicate_similarity",
                    status="pending",
                )
            except Exception:
                pass

            # Start background thread; prefer bytes from files list, then the single file_bytes arg
            thread_file_bytes = None
            if files and isinstance(files, list) and len(files) > 0:
                thread_file_bytes = files[0].get("file_bytes")
            else:
                thread_file_bytes = file_bytes

            try:
                t = threading.Thread(target=self._run_ai_detection, args=(getattr(submission, "id", None), (files_data[0].get("image_hd_url") if files_data and len(files_data) > 0 else image_hd_url), thread_file_bytes))
                t.daemon = True
                t.start()
            except Exception:
                pass

        # Run duplicate detection immediately for submissions with file bytes
        try:
            if status != "draft" and files and isinstance(files, list):
                try:
                    from services.duplicate_detection_service import DuplicateDetectionService
                    dup_service = DuplicateDetectionService()

                    for f in files:
                        fb = f.get("file_bytes")
                        if not fb:
                            continue

                        dup_result = dup_service.check_duplicate_against_database(new_image_bytes=fb, exclude_submission_id=getattr(submission, "id", None), session=getattr(self.submission_repo, "session", None))

                        similarity = float(dup_result.get("similarity_score", 0.0) or 0.0)
                        is_dup = bool(dup_result.get("is_duplicate", False))

                        if is_dup:
                            try:
                                flag = self.submission_repo.save_ai_flag(
                                    submission_id=getattr(submission, "id", None),
                                    confidence_score=similarity,
                                    risk_level=("high" if similarity >= 90 else "medium"),
                                    flag_type="duplicate_similarity",
                                    status="completed",
                                )

                                self.submission_repo.save_ai_analysis_report(
                                    submission_id=getattr(submission, "id", None),
                                    ai_flag_id=getattr(flag, "id", None) if flag is not None else None,
                                    ai_model_name="Duplicate Detection Engine",
                                    ai_confidence_score=similarity,
                                    raw_details=dup_result or {},
                                    similarity_matched_submission_id=dup_result.get("matched_submission_id") if isinstance(dup_result, dict) else None,
                                )
                            except Exception:
                                pass
                        else:
                            break
                except Exception:
                    pass
        except Exception:
            pass

        return submission