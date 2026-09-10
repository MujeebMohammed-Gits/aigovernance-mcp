import os
with open('project-prompt.md', 'rb') as f:
    content = f.read()
with open('prompt_utf8.txt', 'w', encoding='utf-8') as out:
    out.write(content.decode('utf-8', errors='replace'))
print('Done')

exec(\x27open('read_prompt.py').read()\x27)