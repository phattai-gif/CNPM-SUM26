import io
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from app import create_app

app = create_app()
client = app.test_client()

PNG_BYTES = b'\x89PNG\r\n\x1a\n' + b'\x00' * 20

org_payload = {
    'username': 'demo_org_flow_1',
    'email': 'demo_org_flow_1@example.com',
    'password': 'Pass1234!',
    'passwordconfirm': 'Pass1234!',
    'full_name': 'Demo Organizer',
    'role': 'organizer'
}
org_resp = client.post('/auth/signup', json=org_payload)
print('ORG_SIGNUP', org_resp.status_code, org_resp.get_json())
assert org_resp.status_code == 201, org_resp.get_data(as_text=True)
org_token = org_resp.get_json().get('token')

contest_payload = {
    'title': 'Demo Contest 2026',
    'slug': 'demo-contest-2026',
    'description': 'Contest for end to end validation',
    'rules': 'Submit image and follow requirements',
    'status': 'active',
}
contest_resp = client.post('/organizer/contests', json=contest_payload, headers={'Authorization': f'Bearer {org_token}'})
print('CREATE_CONTEST', contest_resp.status_code, contest_resp.get_json())
assert contest_resp.status_code == 201, contest_resp.get_data(as_text=True)
contest_id = contest_resp.get_json()['contest']['id']

round_payload = {
    'title': 'Round 1',
    'description': 'Initial round',
    'status': 'ongoing',
    'start_date': '2026-08-01T00:00:00',
    'end_date': '2026-08-30T00:00:00',
    'weight': 1.0,
    'round_number': 1,
    'criteria': []
}
round_resp = client.post(f'/organizer/contests/{contest_id}/rounds', json=round_payload, headers={'Authorization': f'Bearer {org_token}'})
print('CREATE_ROUND', round_resp.status_code, round_resp.get_json())
assert round_resp.status_code == 201, round_resp.get_data(as_text=True)
round_id = round_resp.get_json()['round']['id']

part_payload = {
    'username': 'demo_part_flow_1',
    'email': 'demo_part_flow_1@example.com',
    'password': 'Pass1234!',
    'passwordconfirm': 'Pass1234!',
    'full_name': 'Demo Participant',
    'role': 'participant'
}
part_resp = client.post('/auth/signup', json=part_payload)
print('PART_SIGNUP', part_resp.status_code, part_resp.get_json())
assert part_resp.status_code == 201, part_resp.get_data(as_text=True)
part_token = part_resp.get_json().get('token')

img = (io.BytesIO(PNG_BYTES), 'sample.png', 'image/png')
draft_data = {
    'round_id': str(round_id),
    'title': 'Draft Photo',
    'story_description': 'This is a draft submission',
    'film_stock': 'Kodak Portra 400',
    'camera_body': 'Canon AE-1',
    'lens': '50mm',
    'film_iso': '400',
    'lab_name': 'Lab Demo',
    'scanner_info': 'Scanner Demo',
    'development_process': 'C-41',
    'taken_at_location': 'Hanoi',
    'status': 'draft'
}
draft_resp = client.post('/submissions', data={'file': img, **draft_data}, headers={'Authorization': f'Bearer {part_token}'}, content_type='multipart/form-data')
print('DRAFT_SUBMIT', draft_resp.status_code, draft_resp.get_json())
assert draft_resp.status_code == 201, draft_resp.get_data(as_text=True)

final_img = (io.BytesIO(PNG_BYTES), 'final.png', 'image/png')
final_data = {
    'round_id': str(round_id),
    'title': 'Final Photo',
    'story_description': 'This is a final submission',
    'film_stock': 'Kodak Portra 400',
    'camera_body': 'Canon AE-1',
    'lens': '50mm',
    'film_iso': '400',
    'lab_name': 'Lab Demo',
    'scanner_info': 'Scanner Demo',
    'development_process': 'C-41',
    'taken_at_location': 'Hanoi',
    'status': 'submitted'
}
final_resp = client.post('/submissions', data={'file': final_img, **final_data}, headers={'Authorization': f'Bearer {part_token}'}, content_type='multipart/form-data')
print('FINAL_SUBMIT', final_resp.status_code, final_resp.get_json())
assert final_resp.status_code == 201, final_resp.get_data(as_text=True)
print('END_TO_END_OK')
