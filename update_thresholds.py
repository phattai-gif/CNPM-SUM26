import os

file_path = 'd:/UTH/CNPM/CNPM-SUM26/src/services/submission_service.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

inject_settings = '''                from infrastructure.repositories.submission_repository import SubmissionRepository
                repo = SubmissionRepository()
                
                # Fetch settings for thresholds
                duplicate_threshold = 70.0
                ai_risk_threshold = 70.0
                try:
                    from infrastructure.models.app import SubmissionModel, ContestSettingsModel
                    sub_for_settings = repo.session.query(SubmissionModel).filter_by(id=sub_id).first()
                    if sub_for_settings and sub_for_settings.round and sub_for_settings.round.contest:
                        c_id = sub_for_settings.round.contest.id
                        c_settings = repo.session.query(ContestSettingsModel).filter_by(contest_id=c_id).first()
                        if c_settings:
                            duplicate_threshold = float(c_settings.ai_duplicate_threshold)
                            ai_risk_threshold = float(c_settings.ai_risk_threshold)
                except Exception as e:
                    print(f"Failed to fetch contest settings for AI thresholds: {e}")
'''
content = content.replace(
    '                from infrastructure.repositories.submission_repository import SubmissionRepository\n                repo = SubmissionRepository()\n',
    inject_settings
)

# Now update AI Detection risk evaluation
ai_eval_old = '''                        risk_level = "safe"
                        if "high" in [base_risk, comp_risk]:
                            risk_level = "high"
                        elif "medium" in [base_risk, comp_risk]:
                            risk_level = "medium"'''

ai_eval_new = '''                        risk_level = "safe"
                        if ai_score >= ai_risk_threshold:
                            risk_level = "high"
                        elif "high" in [base_risk, comp_risk]:
                            risk_level = "high"
                        elif "medium" in [base_risk, comp_risk]:
                            risk_level = "medium"'''
content = content.replace(ai_eval_old, ai_eval_new)

# Include in raw details
ai_raw_details_old = '''                            raw_details={
                                "exif_data": ai_result.get("exif_data", {}),
                                "raw_exif": ai_result.get("raw_exif", {}),
                                "metadata_comparison": comparison_result,
                            },'''
ai_raw_details_new = '''                            raw_details={
                                "exif_data": ai_result.get("exif_data", {}),
                                "raw_exif": ai_result.get("raw_exif", {}),
                                "metadata_comparison": comparison_result,
                                "applied_thresholds": {
                                    "ai_risk": ai_risk_threshold
                                }
                            },'''
content = content.replace(ai_raw_details_old, ai_raw_details_new)


# Now update Duplicate Detection risk evaluation
dup_eval_old = '''                        risk_level = "safe"
                        if is_dup:
                            risk_level = "high"
                        elif similarity >= 70.0:
                            risk_level = "medium"'''

dup_eval_new = '''                        risk_level = "safe"
                        if is_dup:
                            risk_level = "high"
                        elif similarity >= duplicate_threshold:
                            risk_level = "medium"'''
content = content.replace(dup_eval_old, dup_eval_new)

# Include in dup details
dup_raw_details_old = '''                            raw_details=dup_result,'''
dup_raw_details_new = '''                            raw_details={
                                **dup_result,
                                "applied_thresholds": {
                                    "duplicate": duplicate_threshold
                                }
                            },'''
content = content.replace(dup_raw_details_old, dup_raw_details_new)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated submission_service.py with thresholds!")
