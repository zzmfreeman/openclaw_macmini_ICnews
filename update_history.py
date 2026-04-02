import json
from datetime import datetime

# Read brief.json
with open('brief.json', 'r', encoding='utf-8') as f:
    brief = json.load(f)

# Read history.json
with open('history.json', 'r', encoding='utf-8') as f:
    history = json.load(f)

# Add new items to history
for item in brief['items']:
    history_item = {
        'url': item['url'],
        'title': item['title'],
        'published': item['published'],
        'addedAt': datetime.now().strftime('%Y-%m-%dT%H:%M:%S+08:00')
    }
    history.append(history_item)

# Keep only last 500 items
if len(history) > 500:
    history = history[-500:]

# Write back
with open('history.json', 'w', encoding='utf-8') as f:
    json.dump(history, f, ensure_ascii=False, indent=2)

print(f'Updated history.json, added {len(brief["items"])} items, total {len(history)} items')