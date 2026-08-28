import io
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from PIL import Image, ImageDraw, ImageFont

from config import Config
from infrastructure.databases.factory_database import FactoryDatabase
from infrastructure.models.app import (
    ContestModel,
    RoundModel,
    SubmissionFileModel,
    SubmissionModel,
    SubmissionReviewModel,
    UserModel,
)


class CertificateService:
    """
    Service for winner certificates and social sharing.

    FE06.4 responsibilities:
        1. Get approved winner information.
        2. Determine winner rank and award.
        3. Build certificate metadata.
        4. Generate certificate PDF.
        5. Provide social sharing metadata.
    """

    DEFAULT_AWARDS = {
        1: "First Prize",
        2: "Second Prize",
        3: "Third Prize",
        4: "Honorable Mention",
        5: "Honorable Mention",
    }

    PRIVILEGED_ROLES = {
        "admin",
        "organizer",
    }

    def __init__(self, session=None):
        """
        Initialize the certificate service.

        A session can be injected for testing.
        If no session is provided, load the PostgreSQL
        session from FactoryDatabase.
        """
        if session is not None:
            self.session = session
            return

        try:
            database = FactoryDatabase.get_database("POSTGREE")
            self.session = database.session
        except Exception:
            self.session = None

    # ============================================================
    # IDENTIFIER
    # ============================================================

    def _extract_submission_id(
        self,
        identifier: Any,
    ) -> Optional[int]:
        """
        Convert a certificate identifier into a submission ID.

        Supported formats:
            123
            "123"
            "cert-123"
            "cert_123"
            "certificate-123"
            "certificate_123"
        """
        if isinstance(identifier, bool):
            return None

        if isinstance(identifier, int):
            return identifier if identifier > 0 else None

        if not isinstance(identifier, str):
            return None

        value = identifier.strip().lower()

        prefixes = (
            "certificate-",
            "certificate_",
            "cert-",
            "cert_",
        )

        for prefix in prefixes:
            if value.startswith(prefix):
                value = value[len(prefix):]
                break

        try:
            submission_id = int(value)
        except (TypeError, ValueError):
            return None

        return submission_id if submission_id > 0 else None

    # ============================================================
    # DATABASE
    # ============================================================

    def _get_submission_details(
        self,
        submission_id: int,
    ) -> Tuple[
        Optional[Any],
        Optional[Any],
        Optional[Any],
        Optional[Any],
        Optional[Any],
    ]:
        """
        Load submission and related certificate information.

        Returns:
            (
                submission,
                user,
                round_obj,
                contest,
                main_image_file,
            )
        """
        if self.session is None:
            return None, None, None, None, None

        submission = (
            self.session
            .query(SubmissionModel)
            .filter_by(id=submission_id)
            .first()
        )

        if not submission:
            return None, None, None, None, None

        user = (
            self.session
            .query(UserModel)
            .filter_by(id=submission.user_id)
            .first()
        )

        round_obj = (
            self.session
            .query(RoundModel)
            .filter_by(id=submission.round_id)
            .first()
        )

        contest = None

        if round_obj:
            contest = (
                self.session
                .query(ContestModel)
                .filter_by(id=round_obj.contest_id)
                .first()
            )

        main_image_file = self._get_main_image_file(
            submission.id
        )

        return (
            submission,
            user,
            round_obj,
            contest,
            main_image_file,
        )

    def _get_main_image_file(
        self,
        submission_id: int,
    ) -> Optional[Any]:
        """
        Get the primary image file of a submission.

        File priority:
            1. Explicit main_image.
            2. File with image_hd_url.
            3. File with thumbnail_url.

        The method intentionally does not fall back to an arbitrary
        file because a submission may contain:
            - main_image
            - negative
            - contact_sheet
            - proof files
        """
        if self.session is None:
            return None

        files = (
            self.session
            .query(SubmissionFileModel)
            .filter_by(submission_id=submission_id)
            .all()
        )

        if not files:
            return None

        # --------------------------------------------------------
        # 1. Explicit main image
        # --------------------------------------------------------

        for file in files:
            file_type = str(
                getattr(file, "file_type", "")
                or getattr(file, "type", "")
            ).strip().lower()

            if file_type == "main_image":
                return file

        # --------------------------------------------------------
        # 2. Image with HD URL
        # --------------------------------------------------------

        for file in files:
            image_hd_url = getattr(
                file,
                "image_hd_url",
                None,
            )

            if image_hd_url:
                return file

        # --------------------------------------------------------
        # 3. Image with thumbnail URL
        # --------------------------------------------------------

        for file in files:
            thumbnail_url = getattr(
                file,
                "thumbnail_url",
                None,
            )

            if thumbnail_url:
                return file

        return None

    # ============================================================
    # AWARDS
    # ============================================================

    def _get_awards(
        self,
        contest,
    ) -> List[Dict[str, Any]]:
        """
        Read and normalize contest award configuration.

        Supported formats:
            - list
            - dict
            - JSON string
        """
        if not contest:
            return []

        awards = getattr(
            contest,
            "awards_json",
            None,
        )

        if not awards:
            return []

        if isinstance(awards, str):
            try:
                awards = json.loads(awards)
            except (TypeError, ValueError):
                return []

        if isinstance(awards, dict):
            awards = [awards]

        if not isinstance(awards, list):
            return []

        return [
            award
            for award in awards
            if isinstance(award, dict)
        ]

    def _get_award_name(
        self,
        rank: int,
        contest,
    ) -> str:
        """
        Get the configured award name for a rank.

        If the contest does not configure an award for the rank,
        use the default award name.
        """
        for award in self._get_awards(contest):
            try:
                award_rank = int(
                    award.get("rank")
                )
            except (TypeError, ValueError):
                continue

            if award_rank != rank:
                continue

            name = (
                award.get("name")
                or award.get("title")
            )

            if name:
                return str(name)

        return (
            self.DEFAULT_AWARDS.get(rank)
            or f"Rank {rank} Award"
        )

    def _get_configured_winner_ranks(
        self,
        contest,
    ) -> Set[int]:
        """
        Get winner ranks configured by the contest.
        """
        configured_ranks: Set[int] = set()

        for award in self._get_awards(contest):
            try:
                rank = int(
                    award.get("rank")
                )
            except (TypeError, ValueError):
                continue

            if rank > 0:
                configured_ranks.add(rank)

        return configured_ranks

    # ============================================================
    # WINNER / RANKING
    # ============================================================

    def _get_round_submissions(
        self,
        round_id: int,
    ) -> List[Any]:
        """
        Get submissions participating in ranking.

        Draft submissions are excluded.
        """
        if self.session is None:
            return []

        return (
            self.session
            .query(SubmissionModel)
            .filter_by(round_id=round_id)
            .filter(
                SubmissionModel.status != "draft"
            )
            .all()
        )

    @staticmethod
    def _get_score(
        submission,
    ) -> float:
        """
        Normalize a submission final score to float.

        Missing or invalid scores are treated as 0.0.
        """
        score = getattr(
            submission,
            "final_score",
            None,
        )

        if score is None:
            return 0.0

        try:
            return float(score)
        except (TypeError, ValueError):
            return 0.0

    def _get_submission_rank(
        self,
        submission,
        round_obj,
    ) -> int:
        """
        Calculate competition ranking based on final score.

        Higher scores receive better ranks.

        Equal scores receive the same rank.

        Example:
            100 -> rank 1
            100 -> rank 1
            90  -> rank 3
            80  -> rank 4

        No arbitrary tie-break is applied.
        """
        if (
            not submission
            or not round_obj
            or self.session is None
        ):
            return 0

        submissions = self._get_round_submissions(
            round_obj.id
        )

        if not submissions:
            return 0

        target_score = self._get_score(
            submission
        )

        higher_score_count = sum(
            1
            for item in submissions
            if self._get_score(item) > target_score
        )

        return higher_score_count + 1

    def _determine_winner_rank(
        self,
        submission,
        round_obj,
        contest,
    ) -> Tuple[bool, int, str]:
        """
        Determine whether a submission is a winner.

        Winner logic:
            1. Use configured award ranks when available.
            2. Otherwise, top 3 ranks are winners.
            3. An explicit status of "winner" is also accepted.

        Equal scores receive equal ranks.
        """
        if (
            not submission
            or not round_obj
            or self.session is None
        ):
            return False, 0, ""

        rank = self._get_submission_rank(
            submission,
            round_obj,
        )

        if rank <= 0:
            return False, 0, ""

        configured_ranks = (
            self._get_configured_winner_ranks(
                contest
            )
        )

        submission_status = str(
            getattr(
                submission,
                "status",
                "",
            )
        ).strip().lower()

        # Only an exact "winner" status is treated as
        # an explicit winner.
        explicit_winner = (
            submission_status == "winner"
        )

        if configured_ranks:
            is_winner = (
                rank in configured_ranks
                or explicit_winner
            )
        else:
            is_winner = (
                rank <= 3
                or explicit_winner
            )

        if not is_winner:
            return False, rank, ""

        award_name = self._get_award_name(
            rank,
            contest,
        )

        return True, rank, award_name

    # ============================================================
    # APPROVAL
    # ============================================================

    def _is_submission_approved(
        self,
        submission_id: int,
        submission,
    ) -> bool:
        """
        Check whether a submission has been approved.

        Approval sources:
            1. Submission.status == "approved"
            2. Latest SubmissionReview.review_status == "approved"
        """
        if submission:
            submission_status = str(
                getattr(
                    submission,
                    "status",
                    "",
                )
            ).strip().lower()

            if submission_status == "approved":
                return True

        if self.session is None:
            return False

        review = (
            self.session
            .query(SubmissionReviewModel)
            .filter_by(
                submission_id=submission_id
            )
            .order_by(
                SubmissionReviewModel.id.desc()
            )
            .first()
        )

        if not review:
            return False

        review_status = str(
            getattr(
                review,
                "review_status",
                "",
            )
        ).strip().lower()

        return review_status == "approved"

    # ============================================================
    # USER / CONTEST
    # ============================================================

    def _get_winner_name(
        self,
        user,
        user_id: Any,
    ) -> str:
        """
        Get the display name of the winner.

        Priority:
            1. full_name
            2. username
            3. fallback identifier
        """
        if user:
            full_name = getattr(
                user,
                "full_name",
                None,
            )

            if full_name:
                return str(full_name)

            username = getattr(
                user,
                "username",
                None,
            )

            if username:
                return str(username)

        return f"Winner #{user_id}"

    def _get_contest_name(
        self,
        contest,
    ) -> str:
        """
        Get the contest display name.
        """
        if contest:
            title = getattr(
                contest,
                "title",
                None,
            )

            if title:
                return str(title)

        return "Film Contest"

    def _get_award_date(
        self,
        submission,
        round_obj,
        contest,
    ) -> str:
        """
        Determine the certificate award date.

        Priority:
            1. Round end date.
            2. Contest end date.
            3. Submission updated date.
            4. Submission created date.
            5. Current UTC date.
        """
        award_date = None

        if round_obj:
            award_date = getattr(
                round_obj,
                "end_date",
                None,
            )

        if not award_date and contest:
            award_date = getattr(
                contest,
                "end_date",
                None,
            )

        if not award_date and submission:
            award_date = getattr(
                submission,
                "updated_at",
                None,
            )

        if not award_date and submission:
            award_date = getattr(
                submission,
                "created_at",
                None,
            )

        if isinstance(
            award_date,
            datetime,
        ):
            return award_date.strftime(
                "%Y-%m-%d"
            )

        if award_date:
            return str(award_date)[:10]

        return datetime.utcnow().strftime(
            "%Y-%m-%d"
        )

    # ============================================================
    # URL
    # ============================================================

    def _get_base_url(self) -> str:
        """
        Get the application base URL.
        """
        base_url = getattr(
            Config,
            "BASE_URL",
            None,
        )

        if not base_url:
            base_url = "http://localhost:9999"

        return str(base_url).rstrip("/")

    def _get_certificate_urls(
        self,
        submission_id: int,
    ) -> Tuple[str, str]:
        """
        Build certificate download and sharing URLs.
        """
        base_url = self._get_base_url()

        download_url = (
            f"{base_url}"
            f"/api/certificates/"
            f"{submission_id}"
            f"/download"
        )

        share_url = (
            f"{base_url}"
            f"/certificates/"
            f"{submission_id}"
        )

        return download_url, share_url

    # ============================================================
    # IMAGE
    # ============================================================

    def _get_submission_image_url(
        self,
        main_image_file,
    ) -> Optional[str]:
        """
        Get the best image URL from the primary submission file.

        Priority:
            1. image_hd_url
            2. thumbnail_url
        """
        if not main_image_file:
            return None

        image_hd_url = getattr(
            main_image_file,
            "image_hd_url",
            None,
        )

        if image_hd_url:
            return str(image_hd_url)

        thumbnail_url = getattr(
            main_image_file,
            "thumbnail_url",
            None,
        )

        if thumbnail_url:
            return str(thumbnail_url)

        return None

    # ============================================================
    # CERTIFICATE DATA
    # ============================================================

    def get_certificate_by_id(
        self,
        identifier: Any,
        current_user_id: Optional[int] = None,
        user_role: Optional[str] = None,
    ) -> Tuple[
        Optional[Dict[str, Any]],
        Optional[str],
    ]:
        """
        Get certificate information for an approved winner.
        """
        submission_id = (
            self._extract_submission_id(
                identifier
            )
        )

        if not submission_id:
            return None, "invalid_identifier"

        (
            submission,
            user,
            round_obj,
            contest,
            main_image_file,
        ) = self._get_submission_details(
            submission_id
        )

        if not submission:
            return None, "submission_not_found"

        # --------------------------------------------------------
        # Permission
        # --------------------------------------------------------

        if current_user_id is not None:
            normalized_role = str(
                user_role or ""
            ).strip().lower()

            is_privileged = (
                normalized_role
                in self.PRIVILEGED_ROLES
            )

            is_owner = (
                submission.user_id
                == current_user_id
            )

            if not is_privileged and not is_owner:
                return None, "forbidden"

        # --------------------------------------------------------
        # Winner
        # --------------------------------------------------------

        (
            is_winner,
            rank,
            award_name,
        ) = self._determine_winner_rank(
            submission,
            round_obj,
            contest,
        )

        if not is_winner:
            return None, "not_a_winner"

        # --------------------------------------------------------
        # Approval
        # --------------------------------------------------------

        if not self._is_submission_approved(
            submission_id,
            submission,
        ):
            return None, "winner_not_approved"

        # --------------------------------------------------------
        # Certificate information
        # --------------------------------------------------------

        winner_name = self._get_winner_name(
            user,
            submission.user_id,
        )

        contest_name = self._get_contest_name(
            contest
        )

        award_date = self._get_award_date(
            submission,
            round_obj,
            contest,
        )

        certificate_id = (
            f"cert-{submission.id}"
        )

        (
            download_url,
            share_url,
        ) = self._get_certificate_urls(
            submission.id
        )

        image_url = (
            self._get_submission_image_url(
                main_image_file
            )
        )

        data = {
            "certificate_id": certificate_id,
            "winner": {
                "user_id": submission.user_id,
                "name": winner_name,
            },
            "contest": {
                "id": (
                    contest.id
                    if contest
                    else None
                ),
                "name": contest_name,
            },
            "award": {
                "name": award_name,
                "rank": rank,
            },
            "award_date": award_date,
            "submission": {
                "id": submission.id,
                "title": getattr(
                    submission,
                    "title",
                    None,
                ),
                "image_url": image_url,
            },
            "certificate_url": download_url,
            "share_url": share_url,
        }

        return data, None

    # ============================================================
    # PDF GENERATION
    # ============================================================

    def _load_font(
        self,
        size: int,
    ):
        """
        Load a commonly available font.

        Windows Arial is preferred, with DejaVu Sans as
        a Linux-compatible fallback.
        """
        font_candidates = (
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/ARIAL.TTF",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        )

        for font_path in font_candidates:
            try:
                return ImageFont.truetype(
                    font_path,
                    size,
                )
            except (OSError, IOError):
                continue

        return ImageFont.load_default()

    @staticmethod
    def _draw_centered_text(
        draw,
        text: str,
        y: int,
        font,
        fill,
        canvas_width: int,
    ) -> None:
        """
        Draw text centered horizontally.
        """
        bbox = draw.textbbox(
            (0, 0),
            text,
            font=font,
        )

        text_width = (
            bbox[2] - bbox[0]
        )

        x = (
            canvas_width - text_width
        ) // 2

        draw.text(
            (x, y),
            text,
            font=font,
            fill=fill,
        )

    def generate_certificate_file(
        self,
        identifier: Any,
        current_user_id: Optional[int] = None,
        user_role: Optional[str] = None,
    ) -> Tuple[
        Optional[bytes],
        Optional[str],
    ]:
        """
        Generate the winner certificate as a PDF.
        """
        cert_data, error = (
            self.get_certificate_by_id(
                identifier,
                current_user_id=current_user_id,
                user_role=user_role,
            )
        )

        if error:
            return None, error

        if not cert_data:
            return None, "generation_failed"

        winner_name = str(
            cert_data["winner"]["name"]
        )

        contest_name = str(
            cert_data["contest"]["name"]
        )

        award_name = str(
            cert_data["award"]["name"]
        ).upper()

        rank = cert_data["award"]["rank"]

        award_date = str(
            cert_data["award_date"]
        )

        # --------------------------------------------------------
        # Canvas
        # --------------------------------------------------------

        width = 1600
        height = 1100

        image = Image.new(
            "RGB",
            (width, height),
            color=(252, 250, 245),
        )

        draw = ImageDraw.Draw(image)

        # --------------------------------------------------------
        # Colors
        # --------------------------------------------------------

        gold = (184, 134, 11)
        dark = (30, 30, 30)
        gray = (90, 90, 90)

        # --------------------------------------------------------
        # Borders
        # --------------------------------------------------------

        draw.rectangle(
            [
                35,
                35,
                width - 35,
                height - 35,
            ],
            outline=gold,
            width=6,
        )

        draw.rectangle(
            [
                55,
                55,
                width - 55,
                height - 55,
            ],
            outline=gold,
            width=2,
        )

        # --------------------------------------------------------
        # Fonts
        # --------------------------------------------------------

        font_title = self._load_font(72)
        font_subtitle = self._load_font(34)
        font_winner = self._load_font(64)
        font_award = self._load_font(48)
        font_contest = self._load_font(42)
        font_normal = self._load_font(30)
        font_small = self._load_font(26)

        # --------------------------------------------------------
        # Certificate content
        # --------------------------------------------------------

        self._draw_centered_text(
            draw,
            "CERTIFICATE OF ACHIEVEMENT",
            130,
            font_title,
            gold,
            width,
        )

        self._draw_centered_text(
            draw,
            "This certificate is proudly presented to",
            250,
            font_subtitle,
            gray,
            width,
        )

        self._draw_centered_text(
            draw,
            winner_name,
            330,
            font_winner,
            dark,
            width,
        )

        self._draw_centered_text(
            draw,
            "for outstanding achievement",
            445,
            font_subtitle,
            gray,
            width,
        )

        self._draw_centered_text(
            draw,
            award_name,
            515,
            font_award,
            gold,
            width,
        )

        self._draw_centered_text(
            draw,
            f"Rank #{rank}",
            595,
            font_normal,
            dark,
            width,
        )

        self._draw_centered_text(
            draw,
            "in",
            665,
            font_subtitle,
            gray,
            width,
        )

        self._draw_centered_text(
            draw,
            contest_name,
            725,
            font_contest,
            dark,
            width,
        )

        self._draw_centered_text(
            draw,
            f"Award Date: {award_date}",
            850,
            font_normal,
            gray,
            width,
        )

        self._draw_centered_text(
            draw,
            "Film Contest Achievement",
            925,
            font_small,
            gray,
            width,
        )

        # --------------------------------------------------------
        # Export PDF
        # --------------------------------------------------------

        pdf_buffer = io.BytesIO()

        try:
            image.save(
                pdf_buffer,
                format="PDF",
                resolution=150.0,
            )

            pdf_bytes = pdf_buffer.getvalue()

        except Exception:
            return None, "generation_failed"

        finally:
            pdf_buffer.close()

        if not pdf_bytes:
            return None, "generation_failed"

        return pdf_bytes, None

    # ============================================================
    # SOCIAL SHARING
    # ============================================================

    def get_social_sharing_metadata(
        self,
        identifier: Any,
    ) -> Tuple[
        Optional[Dict[str, Any]],
        Optional[str],
    ]:
        """
        Get public metadata for social sharing.

        Returned metadata includes:
            title
            description
            image
            url
            contest_name
            winner_name
            award_name
            rank
            award_date
            certificate_url
            submission_id
        """
        submission_id = (
            self._extract_submission_id(
                identifier
            )
        )

        if not submission_id:
            return None, "invalid_identifier"

        (
            submission,
            user,
            round_obj,
            contest,
            main_image_file,
        ) = self._get_submission_details(
            submission_id
        )

        if not submission:
            return None, "submission_not_found"

        # --------------------------------------------------------
        # Winner
        # --------------------------------------------------------

        (
            is_winner,
            rank,
            award_name,
        ) = self._determine_winner_rank(
            submission,
            round_obj,
            contest,
        )

        if not is_winner:
            return None, "not_a_winner"

        # --------------------------------------------------------
        # Approval
        # --------------------------------------------------------

        if not self._is_submission_approved(
            submission_id,
            submission,
        ):
            return None, "winner_not_approved"

        # --------------------------------------------------------
        # Basic information
        # --------------------------------------------------------

        winner_name = self._get_winner_name(
            user,
            submission.user_id,
        )

        contest_name = self._get_contest_name(
            contest
        )

        award_date = self._get_award_date(
            submission,
            round_obj,
            contest,
        )

        (
            download_url,
            share_url,
        ) = self._get_certificate_urls(
            submission.id
        )

        image_url = (
            self._get_submission_image_url(
                main_image_file
            )
        )

        # --------------------------------------------------------
        # Social content
        # --------------------------------------------------------

        title = (
            f"{winner_name} won "
            f"{award_name} at "
            f"{contest_name}"
        )

        description = (
            f"Congratulations to "
            f"{winner_name} for winning "
            f"{award_name} at "
            f"{contest_name}."
        )

        metadata = {
            "title": title,
            "description": description,
            "image": image_url,
            "url": share_url,
            "contest_name": contest_name,
            "winner_name": winner_name,
            "award_name": award_name,
            "rank": rank,
            "award_date": award_date,
            "certificate_url": download_url,
            "submission_id": submission.id,
        }

        return metadata, None