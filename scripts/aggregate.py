"""Aggregate priced PRAISE/ATTACK posts -> headline, table, aggregate blocks. Writes report.json + report.md."""
import json
from statistics import mean, median

MEDIA = {'WBD', 'CMCSA', 'PARA', 'FOXA', 'NYT', 'DIS'}  # news/broadcast companies

def avg(xs):
    xs = [x for x in xs if x is not None]
    return round(mean(xs), 3) if xs else None

def med(xs):
    xs = [x for x in xs if x is not None]
    return round(median(xs), 3) if xs else None

def block(rows, win_dir):
    """win_dir: 'up' for praise (win=up), 'down' for attack (win=stock fell)."""
    nd = [r['nd_ret'] for r in rows if r['nd_ret'] is not None]
    wk = [r['wk_ret'] for r in rows if r['wk_ret'] is not None]
    if win_dir == 'up':
        wins = sum(1 for x in nd if x > 0)
    else:
        wins = sum(1 for x in nd if x < 0)
    # direction-neutral: biggest up move and biggest down move (labels don't imply "success")
    up = max(rows, key=lambda r: r['nd_ret']) if nd else None
    down = min(rows, key=lambda r: r['nd_ret']) if nd else None
    return {
        'n': len(rows),
        'n_nextday': len(nd),
        'n_1wk': len(wk),
        'avg_nextday_pct': avg(nd),
        'med_nextday_pct': med(nd),
        'avg_1wk_pct': avg(wk),
        'med_1wk_pct': med(wk),
        'win_rate_pct': round(100 * wins / len(nd), 1) if nd else None,
        'win_dir': win_dir,
        'biggest_up': {'company': up['company'], 'date': up['entry_date'], 'nd': up['nd_ret']} if up else None,
        'biggest_down': {'company': down['company'], 'date': down['entry_date'], 'nd': down['nd_ret']} if down else None,
    }

def main():
    rows = json.load(open('priced.json', encoding='utf-8'))
    praise = [r for r in rows if r['sentiment'] == 'PRAISE']
    attack = [r for r in rows if r['sentiment'] == 'ATTACK']

    report = {
        'praise_all': block(praise, 'up'),
        'attack_all': block(attack, 'down'),
        'praise_substantive': block([r for r in praise if r.get('substantive')], 'up'),
        'attack_substantive': block([r for r in attack if r.get('substantive')], 'down'),
        'praise_ex_djt': block([r for r in praise if r['ticker'] != 'DJT'], 'up'),
        'attack_media': block([r for r in attack if r['ticker'] in MEDIA], 'down'),
        'attack_nonmedia': block([r for r in attack if r['ticker'] not in MEDIA], 'down'),
        'praise_inhours': block([r for r in praise if r.get('inhours')], 'up'),
        'praise_outhours': block([r for r in praise if not r.get('inhours')], 'up'),
        'attack_inhours': block([r for r in attack if r.get('inhours')], 'down'),
        'attack_outhours': block([r for r in attack if not r.get('inhours')], 'down'),
    }
    # per-company
    percomp = {}
    for sent, rs in (('PRAISE', praise), ('ATTACK', attack)):
        for r in rs:
            k = (r['company'], r['ticker'], sent)
            percomp.setdefault(k, []).append(r)
    percomp_out = []
    for (comp, tk, sent), rs in sorted(percomp.items(), key=lambda x: -len(x[1])):
        nd = [r['nd_ret'] for r in rs if r['nd_ret'] is not None]
        percomp_out.append({
            'company': comp, 'ticker': tk, 'sentiment': sent, 'n': len(rs),
            'avg_nextday_pct': avg(nd),
            'avg_1wk_pct': avg([r['wk_ret'] for r in rs if r['wk_ret'] is not None]),
        })
    report['per_company'] = percomp_out

    # full table
    table = sorted(rows, key=lambda r: r['et_time'])
    report['table'] = [{
        'date': r['et_time'][:10], 'time_et': r['et_time'][11:], 'ticker': r['ticker'],
        'company': r['company'], 'sentiment': r['sentiment'], 'substantive': r.get('substantive'),
        'nd_ret': r['nd_ret'], 'wk_ret': r['wk_ret'], 'quote': r.get('quote', ''),
    } for r in table]
    json.dump(report, open('report.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    # headline
    pa, aa = report['praise_all'], report['attack_all']
    print('=== HEADLINE ===')
    print(f"Across {pa['n']} PRAISE posts: avg {pa['avg_nextday_pct']}% next-day / {pa['avg_1wk_pct']}% 1-week (win {pa['win_rate_pct']}% up).")
    print(f"Across {aa['n']} ATTACK posts: avg {aa['avg_nextday_pct']}% next-day / {aa['avg_1wk_pct']}% 1-week (fell {aa['win_rate_pct']}% of the time).")
    print()
    print('=== PRAISE (all) ===', json.dumps(pa, indent=1))
    print('=== ATTACK (all) ===', json.dumps(aa, indent=1))
    print('=== PRAISE substantive ===', json.dumps(report['praise_substantive'], indent=1))
    print('=== ATTACK substantive ===', json.dumps(report['attack_substantive'], indent=1))
    print()
    print('=== PER COMPANY ===')
    for c in percomp_out:
        print(f"{c['sentiment']:6s} {c['ticker']:6s} {c['company']:22s} n={c['n']:3d} nd={c['avg_nextday_pct']} wk={c['avg_1wk_pct']}")

if __name__ == '__main__':
    main()
