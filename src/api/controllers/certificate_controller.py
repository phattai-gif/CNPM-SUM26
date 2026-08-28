from flask import Blueprint, Response, jsonify, request

from api.role_required import token_required
from services.certificate_service import CertificateService


certificate_bp = Blueprint(
    "certificate",
    __name__,
    url_prefix="/api/certificates",
)

certificate_service = CertificateService()


def _get_current_user():
    """
    Get current authenticated user information.

    token_required is responsible for setting request.user.
    """
    user = getattr(request, "user", None) or {}

    return (
        user.get("user_id"),
        user.get("role"),
    )


def _certificate_error_response(error):
    """
    Convert service errors into HTTP responses.
    """

    if error == "submission_not_found":
        return jsonify({
            "success": False,
            "message": "Submission not found",
        }), 404

    if error == "forbidden":
        return jsonify({
            "success": False,
            "message": (
                "You do not have permission to access this certificate"
            ),
        }), 403

    if error == "not_a_winner":
        return jsonify({
            "success": False,
            "message": (
                "Certificate is not available for this submission"
            ),
        }), 404

    if error == "winner_not_approved":
        return jsonify({
            "success": False,
            "message": "Winner has not been approved yet",
        }), 403

    if error == "invalid_identifier":
        return jsonify({
            "success": False,
            "message": "Invalid certificate identifier",
        }), 400

    return jsonify({
        "success": False,
        "message": "An error occurred",
    }), 500


# ============================================================
# GET CERTIFICATE INFORMATION
# ============================================================

@certificate_bp.route("/<identifier>", methods=["GET"])
@token_required
def get_certificate(identifier):
    """
    Get certificate information for an approved winner.

    Example:
        GET /api/certificates/123

    Response contains:
        - certificate_id
        - winner
        - contest
        - award
        - award_date
        - certificate_url
    """

    user_id, user_role = _get_current_user()

    data, error = certificate_service.get_certificate_by_id(
        identifier=identifier,
        current_user_id=user_id,
        user_role=user_role,
    )

    if error:
        return _certificate_error_response(error)

    return jsonify({
        "success": True,
        "data": data,
    }), 200


# ============================================================
# DOWNLOAD CERTIFICATE
# ============================================================

@certificate_bp.route("/<identifier>/download", methods=["GET"])
@token_required
def download_certificate(identifier):
    """
    Generate and download certificate as PDF.

    Example:
        GET /api/certificates/123/download
    """

    user_id, user_role = _get_current_user()

    pdf_bytes, error = certificate_service.generate_certificate_file(
        identifier=identifier,
        current_user_id=user_id,
        user_role=user_role,
    )

    if error:
        return _certificate_error_response(error)

    if not pdf_bytes:
        return jsonify({
            "success": False,
            "message": "Failed to generate certificate",
        }), 500

    clean_id = str(identifier).strip()

    # Prevent unsafe characters from being used in filename.
    clean_id = (
        clean_id
        .replace("/", "_")
        .replace("\\", "_")
        .replace(" ", "_")
    )

    filename = f"certificate-{clean_id}.pdf"

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            )
        },
        status=200,
    )


# ============================================================
# SOCIAL SHARING METADATA
# ============================================================

@certificate_bp.route("/<identifier>/share", methods=["GET"])
def get_social_sharing(identifier):
    """
    Get public metadata used by frontend for social sharing.

    This endpoint does not require authentication because
    a public sharing link must be accessible by social platforms.

    Example:
        GET /api/certificates/123/share

    Returns:
        - title
        - description
        - image
        - url
        - winner_name
        - contest_name
        - award_name
        - award_date
        - certificate_url
    """

    data, error = certificate_service.get_social_sharing_metadata(
        identifier=identifier,
    )

    if error:
        return _certificate_error_response(error)

    return jsonify({
        "success": True,
        "data": data,
    }), 200