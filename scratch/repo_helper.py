def get_ai_analysis_report_full(self, submission_id: int) -> dict:
        flags = self.get_all_ai_flags(submission_id)
        
        from infrastructure.models.app.app_audit_log_model import AuditLogModel
        from infrastructure.models.app.app_submission_model import SubmissionModel
        
        result = []
        for flag in flags:
            flag_dict = {
                "id": flag.id,
                "flag_type": flag.flag_type,
                "confidence_score": float(flag.confidence_score),
                "risk_level": flag.risk_level,
                "status": flag.status,
                "reviewed_by": flag.reviewed_by,
                "reviewed_at": flag.reviewed_at.isoformat() if flag.reviewed_at else None,
                "review_notes": flag.review_notes,
                "created_at": flag.created_at.isoformat() if flag.created_at else None,
                "updated_at": flag.updated_at.isoformat() if flag.updated_at else None,
                "raw_details": None,
                "similarity_matched_submission": None,
                "history": []
            }
            
            if flag.analysis_report:
                flag_dict["raw_details"] = flag.analysis_report.raw_details
                matched_id = flag.analysis_report.similarity_matched_submission_id
                if matched_id:
                    matched_sub = self.session.query(SubmissionModel).filter(SubmissionModel.id == matched_id).first()
                    if matched_sub:
                        flag_dict["similarity_matched_submission"] = {
                            "id": matched_sub.id,
                            "title": matched_sub.title
                        }
            
            # Fetch history
            audit_logs = self.session.query(AuditLogModel).filter(
                AuditLogModel.entity_name == "ai_flags",
                AuditLogModel.entity_id == flag.id
            ).order_by(AuditLogModel.created_at.asc()).all()
            
            for log in audit_logs:
                flag_dict["history"].append({
                    "id": log.id,
                    "action": log.action,
                    "old_value": log.old_value,
                    "new_value": log.new_value,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                    "user_id": log.user_id
                })
                
            result.append(flag_dict)
            
        return {"submission_id": submission_id, "ai_flags": result}
