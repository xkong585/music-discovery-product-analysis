from pathlib import Path
import json,hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
A=Path(__file__).resolve().parents[1]
d=json.loads((A/'site/data.json').read_text());q=d['quality'];vs=d['versions'];o=vs[0]['overall'][0]
plt.rcParams.update({'font.family':'DejaVu Sans','axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'#f6f4ee','axes.facecolor':'#f6f4ee','axes.labelcolor':'#193e36','text.color':'#193e36','font.size':10})
assets=A/'docs/assets';assets.mkdir(exist_ok=True)
fig,ax=plt.subplots(figsize=(9,3.6));labs=['Source rows','Inside analysis window','Eligible first-artist events'];vals=[q['raw_rows'],q['valid_events'],q['eligible_events7']];ax.barh(labs,vals,color=['#bac9bd','#397664','#b95d32']);ax.invert_yaxis();ax.set_xlabel('Rows / events (different grains explicitly labeled)');ax.ticklabel_format(style='plain',axis='x');
for i,v in enumerate(vals):ax.text(v*.98,i,f'{v:,}',va='center',ha='right',color='white',fontweight='bold')
ax.set_title('From original listening records to eligible first-artist events',loc='left',pad=18);fig.tight_layout();fig.savefig(assets/'sample_flow.png',dpi=160);plt.close(fig)
fig,ax=plt.subplots(figsize=(9,3.8));segs=vs[0]['segments'];ys=list(range(len(segs)))
for i,r in enumerate(segs):ax.errorbar(r['repeat7_user_mean']*100,i,xerr=[[(r['repeat7_user_mean']-r['ci_low'])*100],[(r['ci_high']-r['repeat7_user_mean'])*100]],fmt='o',color='#397664',capsize=5)
ax.set_yticks(ys,[r['exploration']+' / '+r['activity'] for r in segs]);ax.invert_yaxis();ax.set_xlabel('Observed 7-day artist repeat, user mean (%) with 95% interval');ax.set_title('Past behavior states: descriptive differences, not causal effects',loc='left',pad=18);fig.tight_layout();fig.savefig(assets/'segments.png',dpi=160);plt.close(fig)
fig,ax=plt.subplots(figsize=(8,3.5));names={'main60':'60-day history','wash90':'90-day history','reliable_id':'Reliable ID subset','common28':'Common 28-day cohort'}
for i,v in enumerate(vs):
 r=v['overall'][0];ax.errorbar(r['repeat7_user_mean']*100,i,xerr=[[(r['repeat7_user_mean']-r['ci_low'])*100],[(r['ci_high']-r['repeat7_user_mean'])*100]],fmt='o',color='#b95d32',capsize=5)
ax.set_yticks(range(4),[names[v['version']] for v in vs]);ax.invert_yaxis();ax.set_xlabel('User-weighted observed artist repeat (%)');ax.set_title('Definition sensitivity changes the population being summarized',loc='left',pad=18);fig.tight_layout();fig.savefig(assets/'sensitivity.png',dpi=160);plt.close(fig)
table='\n'.join(f"| {names[v['version']]} | {v['overall'][0]['users']:,} | {v['overall'][0]['events']:,} | {v['overall'][0]['repeat7_user_mean']:.2%} | {v['overall'][0]['ci_low']:.2%}–{v['overall'][0]['ci_high']:.2%} |" for v in vs)
memo=f'''# Product decision memo

## Recommendation

Prioritize a small, concrete user-research study before committing engineering effort to recent-discovery retrieval. Compare it against active exploration and familiar-content access. Historical listening patterns provide a research context; they do not establish retrieval friction or rank the causal value of these features.

## What the data establishes

Parsed all **{q['raw_rows']:,}** original author-published records with zero parser rejects. The conservative analysis window retains **{q['valid_events']:,}** records and **{q['users']:,}** listeners. There are **{q['eligible_events7']:,}** eligible first-artist events from **{q['eligible_users7']:,}** users. Main user-weighted observed 7-day artist repeat is **{o['repeat7_user_mean']:.2%}**, 95% user-cluster bootstrap interval **{o['ci_low']:.2%}–{o['ci_high']:.2%}**. The event-weighted proportion is **{o['repeat7_event_mean']:.2%}**; heavier explorers influence that different estimand more.

| Cohort | Users | First-artist events | User mean | 95% interval |
|---|---:|---:|---:|---:|
{table}

![Past behavior groups](assets/segments.png)

Read group proportions alongside new-artist volume and active days. A lower repeated fraction can arise mechanically when more new artists enter the denominator. The same user may appear in different states; groups are not randomized and differences do not establish that changing exploration changes future use.

## What remains unknown

The file contains **{q['outside_administrative_window']:,}** records at or after the conservative exclusive 2009-05-05 cutoff, including June 2009 and two timestamps in 2010/2013. Preserve the full raw span in QC; do not use the extreme maximum to imply full observation. Timestamp anomalies, missing synchronization and artist identity can alter interpretation.

No recommendation exposure, intent, retrieval attempts, bookmarks, subscriptions, skips or duration are available. One-time listening could represent satisfied exploration, dislike, failed retrieval, or missing logs. No participant, usability, revenue or feature-lift result has been measured.

## Next evidence and investment gate

Ask consenting listeners about the last artist they wanted to hear again: what they remembered, the path they used, whether it worked, and when one listen was enough. Keep counterexamples. If concrete retrieval-friction episodes recur, test one narrow recent-discovery entry point against a baseline information layout. Measure task success, time and mistakes. If that need is unsupported, retain simpler discovery/familiar-content experiences or improve measurement first.

For a future real experiment, add exposure, entry point, click, play start, feedback and errors; randomize eligible users and keep zero-discovery users in the primary denominator. Do not reuse the conditional first-artist repeat proportion as an unqualified causal KPI.
'''
(A/'docs/decision_memo.md').write_text(memo)
readme=f'''# Music Discovery and Repeat Listening

**Product question:** Should a music product prioritize active exploration, familiar-content access, or retrieval of recent discoveries?

**Decision:** research the need before building a retrieval feature. Real historical logs support behavior measurement, not user intent or causal feature lift.

[Interactive research](https://xkong585.github.io/music-discovery-product-analysis/) · [Product memo](docs/decision_memo.md) · [Metric contract](docs/product_brief.md) · [Source and QC](evidence/source_manifest.json)

![Behavior segments with uncertainty](docs/assets/segments.png)

## Verified results

- **{q['raw_rows']:,} original records**, author MD5 verified; **0 parser rejects**. No generated listening data.
- **{q['valid_events']:,}** records retained before conservative exclusive May 5, 2009 cutoff; **{q['outside_administrative_window']:,}** later timestamps audited and excluded.
- **{q['eligible_users7']:,} users / {q['eligible_events7']:,} eligible first-artist events**; user-weighted observed 7-day repeat **{o['repeat7_user_mean']:.2%}** (95% interval **{o['ci_low']:.2%}–{o['ci_high']:.2%}**).
- Four cohort definitions, past-only behavioral segments, 2,000 user-cluster resamples, independent DuckDB/pandas reconciliation and executable tests.

![Scope and sample flow](docs/assets/sample_flow.png)

## Reproduce

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python src/download.py
python src/analyze.py --archive data/raw/lastfm-dataset-1K.tar.gz
pytest tests -q
python -m http.server 8766 --directory site
```

Full source download is 672.7 MB and expands to a multi-GB TSV; the pipeline uses DuckDB with a 3 GB memory limit and disk-backed intermediates. Raw logs, profiles, individual IDs and private analytic tables are git-ignored. Public exports are aggregate-only. Build output under `site/` is committed so the dashboard works without rerunning the full pipeline.

## Analysis flow

Original archive → checksum → TSV/field audit → artist identity resolution → user-artist-day → full-history first appearances → past-28-day features → administratively complete outcomes → user-weighted summaries → product memo.

![Cohort sensitivity](docs/assets/sensitivity.png)

## Data provenance and boundaries

Original dataset: **Òscar Celma / Music Technology Group, UPF**, [Zenodo 6090214](https://zenodo.org/records/6090214), with required attribution to [Last.fm](https://www.last.fm/). Publisher terms: non-commercial use. The data is author-published listening history, not Amazon data or a representative current listener sample. Data terms are separate from repository code licensing; no raw-data redistribution is included.

The checksum-verified file extends beyond the publisher-described date. The actual minimum/maximum and exclusions are published in [QC](evidence/quality.json). Identical tuple candidates are retained rather than treating every repeated play as an error. Name-only identities are marked; reliable-ID sensitivity is available.

No exposure, subscription, skip, intent, true listening duration, interviews, production users or experimental assignment is invented. First appearance is observed history, not first-ever discovery. No synchronization does not prove non-use. Current Amazon Music retention, commercial ROI and optimal recommendation mix cannot be estimated here.

## Portfolio wording

Analyzed {q['raw_rows']:,} author-published listening records with SQL/Python; constructed {q['eligible_events7']:,} eligible first-artist observations across {q['eligible_users7']:,} users using past-only features and audited follow-up windows.

Compared four cohort definitions with user-clustered uncertainty and independent reconciliation; delivered an interactive dashboard and product memo separating behavioral evidence from unvalidated user needs.
'''
(A/'README.md').write_text(readme)
