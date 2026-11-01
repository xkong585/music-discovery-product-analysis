"""Real Last.fm archive -> auditable cohorts -> aggregate-only product evidence."""
from pathlib import Path
import argparse,hashlib,json,tarfile,shutil,datetime
import duckdb,numpy as np,pandas as pd

ROOT=Path(__file__).resolve().parents[1]
SOURCE='https://zenodo.org/records/6090214'
MD5='a79a6808f54f73354789a9fb02cb1e41'
def hashfile(path,algorithm='sha256'):
 h=hashlib.new(algorithm)
 with open(path,'rb') as f:
  while b:=f.read(8*1024*1024):h.update(b)
 return h.hexdigest()

def run(archive):
 raw=ROOT/'data/raw';private=ROOT/'data/private';evidence=ROOT/'evidence'
 for p in [raw,private,evidence,ROOT/'site']:p.mkdir(parents=True,exist_ok=True)
 assert hashfile(archive,'md5')==MD5,'Author MD5 mismatch'
 tsv=raw/'listens.tsv'
 with tarfile.open(archive) as t:
  member=next(m for m in t.getmembers() if m.name.endswith('userid-timestamp-artid-artname-traid-traname.tsv'))
  if not tsv.exists():
   with t.extractfile(member) as f,tsv.open('wb') as g:shutil.copyfileobj(f,g)
  readme=next(m for m in t.getmembers() if m.name.endswith('README.txt'))
  (raw/'publisher_readme.txt').write_bytes(t.extractfile(readme).read())
 manifest={'source':SOURCE,'download_url':SOURCE+'/files/lastfm-dataset-1K.tar.gz?download=1','retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'archive_bytes':Path(archive).stat().st_size,'md5':MD5,'sha256':hashfile(archive),'tsv_sha256':hashfile(tsv),'license':'Non-commercial use; cite Last.fm (https://www.last.fm/) and author Òscar Celma / MTG-UPF. Raw logs and profiles excluded from public outputs.'}
 (evidence/'source_manifest.json').write_text(json.dumps(manifest,indent=2))
 db=duckdb.connect(str(private/'analysis.duckdb'));db.execute("SET threads=4; SET memory_limit='3GB'")
 def q(sql):return db.execute(sql)
 def scalar(sql):return q(sql).fetchone()[0]
 def stage(msg):print(msg,flush=True)
 stage('Reading original TSV')
 q(f"""CREATE OR REPLACE TABLE raw AS SELECT * FROM read_csv('{tsv}', delim='\t',header=false,
 columns={{'uid':'VARCHAR','stamp':'VARCHAR','mbid':'VARCHAR','artist':'VARCHAR','track_id':'VARCHAR','track':'VARCHAR'}},
 quote='',escape='',null_padding=true,strict_mode=false,ignore_errors=true,store_rejects=true)""")
 rejects=scalar('SELECT count(*) FROM reject_errors'); raw_rows=scalar('SELECT count(*) FROM raw')
 q("CREATE OR REPLACE TABLE parsed AS SELECT uid,try_cast(stamp AS TIMESTAMP) ts, lower(trim(mbid)) mbid, lower(regexp_replace(trim(artist),'\\s+',' ','g')) norm FROM raw")
 q("CREATE OR REPLACE TABLE names AS SELECT norm,count(DISTINCT mbid) n,min(mbid) resolved FROM parsed WHERE mbid IS NOT NULL GROUP BY norm")
 q("""CREATE OR REPLACE TABLE clean AS SELECT p.uid,p.ts,cast(p.ts AS DATE) AS day,
 CASE WHEN p.mbid IS NOT NULL THEN 'id:'||p.mbid WHEN n.n=1 THEN 'id:'||n.resolved
 WHEN n.n IS NULL THEN 'name:'||p.norm END artist_key,
 p.mbid IS NOT NULL reliable_id,
 CASE WHEN p.mbid IS NOT NULL THEN 'original_id' WHEN n.n=1 THEN 'unique_name_to_id' WHEN n.n IS NULL THEN 'name_only' ELSE 'ambiguous_missing_id' END key_method
 FROM parsed p LEFT JOIN names n USING(norm)
 WHERE uid IS NOT NULL AND ts IS NOT NULL AND norm IS NOT NULL""")
 q("CREATE OR REPLACE TABLE events AS SELECT * FROM clean WHERE artist_key IS NOT NULL AND day<DATE '2009-05-05'")
 stage('Building user-artist-day and full-history first appearances')
 q('CREATE OR REPLACE TABLE artist_day AS SELECT uid,artist_key,day,count(*) plays,bool_and(reliable_id) all_id FROM events GROUP BY ALL')
 q('CREATE OR REPLACE TABLE first_artist AS SELECT uid,artist_key,min(day) d,bool_and(all_id) all_id FROM artist_day GROUP BY ALL')
 q('CREATE OR REPLACE TABLE user_bounds AS SELECT uid,min(day) start_day,max(day) last_day FROM events GROUP BY uid')
 cutoff=datetime.date(2009,5,5) # Conservative publisher-described boundary, exclusive. Later timestamps audited, not used to extend follow-up.
 stage(f'Exclusive administrative cutoff {cutoff}')
 q("CREATE OR REPLACE TABLE daily AS SELECT uid,day,count(*) plays,count(DISTINCT artist_key) artists FROM events GROUP BY ALL")
 q("CREATE OR REPLACE TABLE new_daily AS SELECT uid,d AS day,count(*) new_artists FROM first_artist GROUP BY ALL")
 q(f"""CREATE OR REPLACE TABLE calendar_grid AS SELECT b.uid,cast(r.day AS DATE) AS day
 FROM user_bounds b CROSS JOIN LATERAL generate_series(b.start_day,DATE '{cutoff}'-INTERVAL 1 DAY,INTERVAL 1 DAY) r(day)""".replace('\n+','\n'))
 q("""CREATE OR REPLACE TABLE calendar AS SELECT g.uid,g.day,coalesce(d.plays,0) plays,coalesce(n.new_artists,0) new_artists
 FROM calendar_grid g LEFT JOIN daily d USING(uid,day) LEFT JOIN new_daily n USING(uid,day)""")
 q("""CREATE OR REPLACE TABLE history AS SELECT *,
 sum(CASE WHEN plays>0 THEN 1 ELSE 0 END) OVER w active28,
 sum(plays) OVER w plays28,sum(new_artists) OVER w new28
 FROM calendar WINDOW w AS (PARTITION BY uid ORDER BY day ROWS BETWEEN 28 PRECEDING AND 1 PRECEDING)""")
 q(f"""CREATE OR REPLACE TABLE anchors AS SELECT f.*,date_diff('day',b.start_day,f.d) history_days,
 h.active28,h.plays28,h.new28, f.d+INTERVAL 29 DAY<=DATE '{cutoff}' eligible28
 FROM first_artist f JOIN user_bounds b USING(uid) JOIN history h ON f.uid=h.uid AND f.d=h.day
 WHERE f.d>=b.start_day+INTERVAL 60 DAY AND f.d+INTERVAL 8 DAY<=DATE '{cutoff}' AND h.plays28>0""")
 # Compute one past-only feature per unique user-date, not once per new artist.
 stage('Computing historical distinct-artist denominators')
 q("""CREATE OR REPLACE TABLE historical_distinct AS SELECT a.uid,a.d,count(DISTINCT p.artist_key) distinct28
 FROM (SELECT DISTINCT uid,d FROM anchors) a JOIN artist_day p ON a.uid=p.uid AND p.day>=a.d-INTERVAL 28 DAY AND p.day<a.d GROUP BY ALL""")
 q("""CREATE OR REPLACE TABLE outcomes AS SELECT a.uid,a.artist_key,a.d,
 count(p.day) FILTER(WHERE p.day>=a.d+INTERVAL 1 DAY AND p.day<a.d+INTERVAL 8 DAY)>0 repeat7
 FROM anchors a LEFT JOIN artist_day p ON a.uid=p.uid AND a.artist_key=p.artist_key AND p.day>=a.d+INTERVAL 1 DAY AND p.day<a.d+INTERVAL 8 DAY GROUP BY ALL""")
 q("""CREATE OR REPLACE TABLE future_activity AS SELECT a.uid,a.d,
 count(p.day) FILTER(WHERE p.plays>0 AND p.day>=a.d+INTERVAL 1 DAY AND p.day<a.d+INTERVAL 29 DAY) active_future28,
 count(p.day) FILTER(WHERE p.plays>0 AND p.day>=a.d+INTERVAL 8 DAY AND p.day<a.d+INTERVAL 29 DAY) active_future8_28
 FROM (SELECT DISTINCT uid,d FROM anchors WHERE eligible28) a LEFT JOIN daily p ON a.uid=p.uid AND p.day>=a.d+INTERVAL 1 DAY AND p.day<a.d+INTERVAL 29 DAY GROUP BY ALL""")
 q("""CREATE OR REPLACE TABLE cohort AS SELECT a.*,h.distinct28,a.new28/h.distinct28 exploration28,
 CASE WHEN a.new28/h.distinct28>=0.5 THEN 'higher exploration' ELSE 'lower exploration' END exploration,
 CASE WHEN a.active28>=14 THEN 'higher activity' ELSE 'lower activity' END activity,
 o.repeat7,f.active_future28,f.active_future8_28
 FROM anchors a JOIN historical_distinct h USING(uid,d) JOIN outcomes o USING(uid,artist_key,d)
 LEFT JOIN future_activity f USING(uid,d)""")
 q(f"COPY cohort TO '{private/'cohort.parquet'}' (FORMAT PARQUET)")
 stage('Summarizing per-user means and clustered intervals')
 qc={'raw_rows':raw_rows,'parser_rejects':rejects,'valid_events':scalar('select count(*) from events'),'users':scalar('select count(distinct uid) from events'),'raw_min_timestamp':str(scalar('select min(ts) from parsed')),'raw_max_timestamp':str(scalar('select max(ts) from parsed')),'outside_administrative_window':scalar("select count(*) from clean where artist_key is not null and day>=DATE '2009-05-05'"),'cutoff_note':'Conservative exclusive 2009-05-05 boundary from publisher description; real file contains later records through June 2009 and two timestamps in 2010/2013. Full raw span is audited; later records do not extend follow-up.','exclusive_cutoff_utc':str(cutoff),'ambiguous_missing_id_excluded':scalar("select count(*) from clean where artist_key is null"),'invalid_required_fields':raw_rows-scalar('select count(*) from clean'),'artist_day_rows':scalar('select count(*) from artist_day'),'first_artist_pairs':scalar('select count(*) from first_artist'),'eligible_events7':scalar('select count(*) from cohort'),'eligible_users7':scalar('select count(distinct uid) from cohort'),'eligible_events28':scalar('select count(*) from cohort where eligible28'),'eligible_users28':scalar('select count(distinct uid) from cohort where eligible28'),'key_methods':q('select key_method,count(*) n from clean group by 1').fetchdf().to_dict('records'),'exact_duplicate_candidates':scalar('select count(*) from (select uid,ts,artist_key,count(*) n from events group by all having count(*)>1)')}
 (evidence/'quality.json').write_text(json.dumps(qc,indent=2))
 # No raw IDs exported: user averages remain private; only sufficiently large aggregate groups exported.
 def summarize(where='true',group=True):
  keys='exploration,activity,' if group else "'all' exploration,'all' activity,"
  df=q(f"""SELECT {keys}uid,count(*) n,avg(cast(repeat7 AS DOUBLE)) repeat_rate,
 avg(distinct28) historical_artists,avg(new28) new_artists,avg(active28) historical_active_days,
 avg(active_future28) future_active28,avg(active_future8_28) future_active8_28,
 count(DISTINCT d) anchor_days FROM cohort WHERE {where} GROUP BY ALL""").fetchdf()
  out=[];rng=np.random.default_rng(20261101)
  for (exploration,activity),g in df.groupby(['exploration','activity']):
   if len(g)<20:continue
   a=g.repeat_rate.to_numpy();boots=np.mean(rng.choice(a,size=(2000,len(a)),replace=True),axis=1)
   out.append({'exploration':exploration,'activity':activity,'users':len(g),'events':int(g.n.sum()),'repeat7_user_mean':float(a.mean()),'ci_low':float(np.quantile(boots,.025)),'ci_high':float(np.quantile(boots,.975)),'repeat7_event_mean':float(np.average(a,weights=g.n)),'mean_new_artists_per_anchor':float(g.new_artists.mean()),'mean_historical_artists':float(g.historical_artists.mean()),'mean_active_days28':float(g.historical_active_days.mean()),'mean_future_active28':None if g.future_active28.isna().all() else float(g.future_active28.mean()),'mean_future_active8_28':None if g.future_active8_28.isna().all() else float(g.future_active8_28.mean())})
  return out
 summaries=[]
 for name,where in [('main60','true'),('wash90','history_days>=90'),('reliable_id','all_id'),('common28','eligible28')]:
  summaries.append({'version':name,'overall':summarize(where,False),'segments':summarize(where,True)})
 (evidence/'summary.json').write_text(json.dumps(summaries,indent=2,allow_nan=False))
 # Independent pandas reconciliation of headline event rate and user-weighted rate.
 small=q('select uid,repeat7 from cohort').fetchdf()
 checks={'sql_event_rate':float(scalar('select avg(cast(repeat7 as double)) from cohort')),'pandas_event_rate':float(small.repeat7.mean()),'sql_user_rate':float(scalar('select avg(r) from (select uid,avg(cast(repeat7 as double)) r from cohort group by uid)')),'pandas_user_rate':float(small.groupby('uid').repeat7.mean().mean()),'artist_day_reconciles':scalar('select sum(plays) from artist_day')==qc['valid_events'],'past_feature_positive_denominator':scalar('select count(*) from cohort where distinct28<=0 or new28>distinct28')==0,'d0_excluded':True}
 assert abs(checks['sql_event_rate']-checks['pandas_event_rate'])<1e-12
 assert abs(checks['sql_user_rate']-checks['pandas_user_rate'])<1e-12
 assert checks['artist_day_reconciles'] and checks['past_feature_positive_denominator']
 (evidence/'reconciliation.json').write_text(json.dumps(checks,indent=2))
 result={'source':manifest,'quality':qc,'versions':summaries,'reconciliation':checks,'generated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 (ROOT/'site/data.json').write_text(json.dumps(result,indent=2,allow_nan=False))
 stage(json.dumps(qc,indent=2));db.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);args=p.parse_args();run(args.archive)
