from flask import Blueprint, request, jsonify
from api.role_required import token_required
from services.notification_service import NotificationService
from infrastructure.repositories.notification_repository import NotificationRepository

notification_bp = Blueprint('notification', __name__, url_prefix='/notifications')
notification_service = NotificationService(NotificationRepository())


@notification_bp.route('', methods=['GET'])
@token_required
def get_notifications(current_user):
    """
    Get all notifications for the current user
    ---
    get:
      summary: Get user notifications (unread and read)
      tags:
        - Notifications
      security:
        - Bearer: []
      parameters:
        - in: query
          name: unread_only
          schema:
            type: boolean
          description: Filter only unread notifications
      responses:
        200:
          description: List of notifications
        401:
          description: Unauthorized
    """
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'
    notifications = notification_service.get_user_notifications(current_user.id, unread_only=unread_only)
    
    return jsonify({
        'count': len(notifications),
        'notifications': [
            {
                'id': n.id,
                'title': n.title,
                'body': n.body,
                'type': n.notification_type,
                'contest_id': n.contest_id,
                'is_read': n.is_read,
                'created_at': n.created_at.isoformat() if n.created_at else None,
            }
            for n in notifications
        ]
    }), 200


@notification_bp.route('/<int:notification_id>', methods=['GET'])
@token_required
def get_notification(current_user, notification_id):
    """
    Get a specific notification
    ---
    get:
      summary: Retrieve a single notification by ID
      tags:
        - Notifications
      security:
        - Bearer: []
      parameters:
        - in: path
          name: notification_id
          schema:
            type: integer
          required: true
      responses:
        200:
          description: Notification details
        404:
          description: Notification not found
    """
    notification = notification_service.repository.get_by_id(notification_id)
    if not notification or notification.user_id != current_user.id:
        return jsonify({'message': 'Notification not found'}), 404
    
    return jsonify({
        'id': notification.id,
        'title': notification.title,
        'body': notification.body,
        'type': notification.notification_type,
        'contest_id': notification.contest_id,
        'is_read': notification.is_read,
        'created_at': notification.created_at.isoformat() if notification.created_at else None,
    }), 200


@notification_bp.route('/<int:notification_id>/mark-read', methods=['POST'])
@token_required
def mark_notification_read(current_user, notification_id):
    """
    Mark a notification as read
    ---
    post:
      summary: Mark notification as read
      tags:
        - Notifications
      security:
        - Bearer: []
      parameters:
        - in: path
          name: notification_id
          schema:
            type: integer
          required: true
      responses:
        200:
          description: Notification marked as read
        404:
          description: Notification not found
    """
    notification = notification_service.repository.get_by_id(notification_id)
    if not notification or notification.user_id != current_user.id:
        return jsonify({'message': 'Notification not found'}), 404
    
    updated = notification_service.mark_notification_read(notification_id)
    return jsonify({
        'id': updated.id,
        'is_read': updated.is_read,
        'message': 'Notification marked as read'
    }), 200
