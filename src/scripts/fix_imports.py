import os
from pathlib import Path

src_dir = Path('src')
replacements = [
    ('from ...databases.base', 'from infrastructure.databases.base'),
    ('from ...domain.models.', 'from domain.models.'),
    ('from ...domain.', 'from domain.'),
    ('from ...infrastructure.', 'from infrastructure.'),
    ('from ..databases.', 'from infrastructure.databases.'),
    ('from ..models.app', 'from infrastructure.models.app'),
    ('from ..infrastructure.', 'from infrastructure.'),
]

count = 0
for py_file in src_dir.rglob('*.py'):
    content = py_file.read_text(encoding='utf-8')
    original = content
    
    for old, new in replacements:
        content = content.replace(old, new)
    
    if content != original:
        py_file.write_text(content, encoding='utf-8')
        print(f"Fixed: {py_file.relative_to(Path('.'))}")
        count += 1

print(f"\nTotal files fixed: {count}")
