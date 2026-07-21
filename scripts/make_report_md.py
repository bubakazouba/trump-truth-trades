import json
r = json.load(open('report.json', encoding='utf-8'))

def bw(b):
    u, d = b.get('biggest_up'), b.get('biggest_down')
    if not u:
        return ""
    return (f" | biggest up move {u['company']} {u['nd']:+.1f}% ({u['date']}), "
            f"biggest down move {d['company']} {d['nd']:+.1f}% ({d['date']})")

def line(b):
    return (f"n={b['n']} | next-day avg {b['avg_nextday_pct']}% (median {b['med_nextday_pct']}%) | "
            f"1-week avg {b['avg_1wk_pct']}% (median {b['med_1wk_pct']}%) | "
            f"win {b['win_rate_pct']}% ({'up' if b['win_dir']=='up' else 'down'})" + bw(b))

pa, pex, aa, am, an = (r['praise_all'], r['praise_ex_djt'], r['attack_all'],
                       r['attack_media'], r['attack_nonmedia'])
L = []
L.append("# Trump Truth Social — Company Praise/Attack Returns Analysis\n")
L.append("## Bottom line")
L.append(f"- **PRAISE (all, n={pa['n']}):** buying at the post's entry close returned avg "
         f"**{pa['avg_nextday_pct']}%** next-day / **{pa['avg_1wk_pct']}%** 1-week; stock rose only **{pa['win_rate_pct']}%** of the time.")
L.append(f"- **PRAISE excluding DJT (his own stock, n={pex['n']}):** avg **{pex['avg_nextday_pct']}%** next-day / "
         f"**{pex['avg_1wk_pct']}%** 1-week; up **{pex['win_rate_pct']}%** of the time — essentially a coin flip.")
L.append(f"- **ATTACK (all, n={aa['n']}):** the targeted stock moved avg **{aa['avg_nextday_pct']}%** next-day and "
         f"fell only **{aa['win_rate_pct']}%** of the time — i.e. it rose more often than it fell after a Trump attack.\n")
L.append("## Aggregate blocks")
for name, b in [("PRAISE — all", pa), ("PRAISE — excluding DJT", pex),
                ("PRAISE — substantive only", r['praise_substantive']),
                ("PRAISE — in market hours", r['praise_inhours']),
                ("PRAISE — out of hours", r['praise_outhours']),
                ("ATTACK — all", aa), ("ATTACK — media companies", am),
                ("ATTACK — non-media", an), ("ATTACK — substantive only", r['attack_substantive']),
                ("ATTACK — in market hours", r['attack_inhours']),
                ("ATTACK — out of hours", r['attack_outhours'])]:
    L.append(f"- **{name}:** {line(b)}")
L.append("")
L.append("## Per-company")
L.append("| Sentiment | Ticker | Company | n | avg +1d % | avg +1wk % |")
L.append("|---|---|---|---|---|---|")
for c in r['per_company']:
    L.append(f"| {c['sentiment']} | {c['ticker']} | {c['company']} | {c['n']} | {c['avg_nextday_pct']} | {c['avg_1wk_pct']} |")
L.append("")
L.append("## Full labeled table")
L.append("| Date | Time ET | Ticker | Sentiment | Sub | +1d % | +1wk % | Quote |")
L.append("|---|---|---|---|---|---|---|---|")
for t in r['table']:
    q = t['quote'].replace('|', '/')[:70]
    L.append(f"| {t['date']} | {t['time_et']} | {t['ticker']} | {t['sentiment']} | "
             f"{'Y' if t['substantive'] else 'n'} | {t['nd_ret']} | {t['wk_ret']} | {q} |")
open('REPORT.md', 'w', encoding='utf-8').write('\n'.join(L))
print('wrote REPORT.md', len(r['table']), 'table rows')
