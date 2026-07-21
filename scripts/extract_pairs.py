"""Prefilter posts for company mentions -> pairs.jsonl (one row per (post,company))."""
import csv, re, json, sys
from companies import COMPANIES

def fix_mojibake(s):
    # File double-encodes UTF-8 as latin-1 (curly quotes show as â...).
    try:
        return s.encode('latin-1').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s

def norm(s):
    s = fix_mojibake(s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def main():
    rows = list(csv.DictReader(open('truth_archive.csv', encoding='utf-8')))
    pats = {c: [re.compile(p, re.I) for p in v[1]] for c, v in COMPANIES.items()}
    seen_text = {}  # dedupe near-identical text per company
    out = []
    for r in rows:
        raw = r['content']
        if not raw.strip():
            continue
        t = norm(raw)
        low = t.lower()
        for c, pl in pats.items():
            if any(p.search(low) for p in pl):
                ticker = COMPANIES[c][0]
                key = (c, low[:120])
                if key in seen_text:
                    continue
                seen_text[key] = True
                out.append({
                    "id": r['id'],
                    "created_at": r['created_at'],  # UTC ISO Z
                    "company": c,
                    "ticker": ticker,
                    "text": t[:1500],
                })
    with open('pairs.jsonl', 'w', encoding='utf-8') as f:
        for o in out:
            f.write(json.dumps(o, ensure_ascii=False) + '\n')
    print('wrote', len(out), 'pairs')

if __name__ == '__main__':
    main()
