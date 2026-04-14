import re

content = open('main.py', encoding='utf-8').read()

new_func = '''def clean_text(text: str) -> str:
    """Removes only genuine LIVE/UPDATE ticker prefixes, NOT regular headlines."""
    if not text:
        return ""
    # Only strip if prefix ends in LIVE, UPDATE, BREAKING, or ALERT followed by colon or dash
    # Correct: "FTSE 100 LIVE: Stocks..." -> "Stocks..."
    # Correct: "BREAKING: Markets..." -> "Markets..."
    # Safe:    "Iran Talks" stays as "Iran Talks"
    # Safe:    "Oil Falls as IEA..." stays intact
    prefix_pattern = r"^(?:[\\w\\s]{1,40}?\\s+(?:LIVE|UPDATE|BREAKING|ALERT)|(?:BREAKING|UPDATE|LIVE|ALERT))\\s*[:\\-\\u2014]\\s+"
    cleaned = re.sub(prefix_pattern, text if not re.match(prefix_pattern, text, re.IGNORECASE) else "", text, flags=re.IGNORECASE).strip()
    cleaned = re.sub(prefix_pattern, "", text, flags=re.IGNORECASE).strip()
    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned'''

# Find and replace the existing clean_text function
pattern = r'def clean_text\(text: str\) -> str:.*?return cleaned\n'
if re.search(pattern, content, re.DOTALL):
    content = re.sub(pattern, new_func + '\n', content, flags=re.DOTALL)
    open('main.py', 'w', encoding='utf-8').write(content)
    print('SUCCESS - clean_text updated')
else:
    print('PATTERN NOT FOUND')
    # Show lines 24-50 for debugging
    for i, line in enumerate(content.split('\n')[23:50], start=24):
        print(f'{i}: {repr(line[:80])}')
