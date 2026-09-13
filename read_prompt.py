"""
Reads project-prompt.md and writes a UTF‑8 safe version.
"""

import os

with open('project-prompt.md', 'rb') as f:
    content = f.read()

with open('prompt_utf8.txt', 'w', encoding='utf-8') as out:
    out.write(content.decode('utf-8', errors='replace'))

print('Done')
