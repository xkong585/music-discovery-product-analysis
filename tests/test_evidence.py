from pathlib import Path
import json,pytest,numpy as np
R=Path(__file__).resolve().parents[1]
def load(n):return json.loads((R/'evidence'/n).read_text())
def test_author_archive_verified():
 m=load('source_manifest.json');assert m['md5']=='a79a6808f54f73354789a9fb02cb1e41';assert m['archive_bytes']==672741554
def test_all_parsed_rows_accounted():
 q=load('quality.json');assert q['raw_rows']==q['valid_events']+q['invalid_required_fields']+q['ambiguous_missing_id_excluded']+q['outside_administrative_window'];assert q['parser_rejects']==0
def test_event_and_user_estimands_independently_reconcile():
 r=load('reconciliation.json');assert abs(r['sql_event_rate']-r['pandas_event_rate'])<1e-12;assert abs(r['sql_user_rate']-r['pandas_user_rate'])<1e-12
def test_daily_counts_reconcile():assert load('reconciliation.json')['artist_day_reconciles']
def test_future_information_not_used_for_exploration():assert load('reconciliation.json')['past_feature_positive_denominator']
def test_public_groups_have_support():
 for v in load('summary.json'):
  for r in v['overall']+v['segments']:assert r['users']>=20 and r['events']>=r['users']
def test_intervals_and_rates():
 for v in load('summary.json'):
  for r in v['overall']+v['segments']:assert 0<=r['ci_low']<=r['repeat7_user_mean']<=r['ci_high']<=1
def test_followup_is_a_subset():
 q=load('quality.json');assert 0<q['eligible_events28']<=q['eligible_events7'];assert q['eligible_users28']<=q['eligible_users7']
def test_public_export_has_no_identifiers():
 d=json.loads((R/'site/data.json').read_text());assert 'uid' not in json.dumps(d) and 'user_000' not in json.dumps(d)
def test_strict_real_timestamp_boundaries():
 import duckdb,pandas as pd
 path=R/'data/private/analysis.duckdb'
 if not path.exists():pytest.skip('Private full-data audit requires downloaded source')
 db=duckdb.connect(str(path),read_only=True)
 sample=db.execute('select uid,artist_key,d,repeat7 from cohort order by hash(uid,artist_key) limit 40').fetchdf()
 for _,r in sample.iterrows():
  days=db.execute('select day from artist_day where uid=? and artist_key=?',[r.uid,r.artist_key]).fetchdf().day
  assert days.min()==r.d
  expected=((days>=r.d+pd.Timedelta(days=1))&(days<r.d+pd.Timedelta(days=8))).any()
  assert bool(expected)==bool(r.repeat7)
 db.close()
