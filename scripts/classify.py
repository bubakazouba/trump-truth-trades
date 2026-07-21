"""LLM classification pass over (post,company) pairs via `claude -p` (Sonnet).
Per pair: stance toward THAT company -> PRAISE | ATTACK | NEUTRAL, + substantive bool + verbatim quote.
Resume-safe: appends to classified.jsonl, skips already-done (id,company)."""
import json, subprocess, os, re, sys

PAIRS = 'pairs.jsonl'
SHARD = int(os.environ.get('SHARD', '0'))
NSHARD = int(os.environ.get('NSHARD', '1'))
OUT = f'classified_shard{SHARD}.jsonl' if NSHARD > 1 else 'classified.jsonl'
BATCH = 25

PROMPT_HEADER = """You are labeling Donald Trump Truth Social posts for financial-sentiment analysis.
Each item gives a CANDIDATE COMPANY (with ticker) and the post TEXT. The post mentions that company.
Judge Trump's STANCE TOWARD THAT SPECIFIC COMPANY (its business, stock, products, or leadership) in this post.

Label each item:
- "PRAISE": positive/promotional/supportive of the company, its product, stock, or leadership.
- "ATTACK": negative/critical/hostile toward the company, its product, stock, or leadership (e.g. "Fake News CNN, failing, nobody watches", "Boycott X", threatening tariffs/investigation against it).
- "NEUTRAL": merely names it, cites it as a news source/example, or the mention is incidental with no clear stance toward the company (e.g. "as reported by CNN", "President DJT" signoff, naming a person who happens to work there).

Also set "substantive": true if the post is materially ABOUT this company (a claim/stance directed at its business/product/leadership), false if it is a passing epithet or incidental name-drop (e.g. a reflexive "Fake News CNN!" tag on an unrelated post).

Give "quote": a SHORT excerpt (<=15 words) from the text that best shows the stance. For NEUTRAL, quote the phrase where the company is named. IMPORTANT: in the quote field do NOT use double-quote characters at all; if the text has quotes, replace them with single quotes so the JSON stays valid.

Return ONLY a JSON array, one object per item, no prose, no markdown fences:
[{"i": <index>, "sentiment": "PRAISE|ATTACK|NEUTRAL", "substantive": true|false, "quote": "..."}]

ITEMS:
"""

def load_done():
    done = set()
    if os.path.exists(OUT):
        for line in open(OUT, encoding='utf-8'):
            line = line.strip()
            if not line:
                continue
            o = json.loads(line)
            done.add((o['id'], o['company']))
    return done

def call_claude(prompt):
    p = subprocess.run(['claude', '-p'], input=prompt, capture_output=True,
                       text=True, encoding='utf-8', timeout=600)
    return p.stdout

def extract_json_array(s):
    start = s.find('[')
    end = s.rfind(']')
    if start == -1 or end == -1:
        return None
    frag = s[start:end+1]
    try:
        return json.loads(frag)
    except json.JSONDecodeError:
        pass
    # Tolerant fallback: pull each {...} object, salvage what parses.
    out = []
    for m in re.finditer(r'\{[^{}]*\}', frag):
        chunk = m.group(0)
        try:
            out.append(json.loads(chunk))
            continue
        except json.JSONDecodeError:
            pass
        # Salvage fields via regex even if quote has stray quotes.
        im = re.search(r'"i"\s*:\s*(\d+)', chunk)
        sm = re.search(r'"sentiment"\s*:\s*"(PRAISE|ATTACK|NEUTRAL)"', chunk)
        bm = re.search(r'"substantive"\s*:\s*(true|false)', chunk)
        if im and sm:
            out.append({'i': int(im.group(1)), 'sentiment': sm.group(1),
                        'substantive': (bm.group(1) == 'true') if bm else False,
                        'quote': ''})
    return out or None

def main():
    pairs = [json.loads(l) for l in open(PAIRS, encoding='utf-8') if l.strip()]
    pairs = [p for i, p in enumerate(pairs) if i % NSHARD == SHARD]
    done = load_done()
    todo = [p for p in pairs if (p['id'], p['company']) not in done]
    print(f'{len(pairs)} pairs, {len(done)} done, {len(todo)} todo', flush=True)
    fout = open(OUT, 'a', encoding='utf-8')
    for bstart in range(0, len(todo), BATCH):
        batch = todo[bstart:bstart+BATCH]
        lines = []
        for i, p in enumerate(batch):
            lines.append(f'[{i}] COMPANY={p["company"]} (${p["ticker"]}) TEXT: {p["text"]}')
        prompt = PROMPT_HEADER + '\n'.join(lines)
        try:
            resp = call_claude(prompt)
        except subprocess.TimeoutExpired:
            print(f'batch {bstart} TIMEOUT', flush=True)
            continue
        arr = extract_json_array(resp)
        if arr is None:
            print(f'batch {bstart} PARSE FAIL; resp head: {resp[:200]!r}', flush=True)
            continue
        by_i = {o.get('i'): o for o in arr if isinstance(o, dict)}
        wrote = 0
        for i, p in enumerate(batch):
            o = by_i.get(i)
            if o is None:
                continue
            rec = dict(p)
            rec['sentiment'] = o.get('sentiment', 'NEUTRAL')
            rec['substantive'] = bool(o.get('substantive', False))
            rec['quote'] = o.get('quote', '')
            fout.write(json.dumps(rec, ensure_ascii=False) + '\n')
            wrote += 1
        fout.flush()
        print(f'batch {bstart}-{bstart+len(batch)} -> wrote {wrote}/{len(batch)}', flush=True)
    fout.close()
    print('DONE', flush=True)

if __name__ == '__main__':
    main()
