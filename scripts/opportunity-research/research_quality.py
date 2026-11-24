"""Shared coverage and regression checks, independent of source page layout.

Unknown is a valid answer for optional vendor information. Identity, application
availability and a future source deadline remain mandatory before publication.
"""
from datetime import datetime
from zoneinfo import ZoneInfo
from category_rules import price_rows,question_options

FIELDS=('identity','availability','categories','costs','requirements','deadline')

def build_quality(result,app,requirements=''):
 c=result['candidate'];facts=result.get('category_evidence',{}).get('categories',{})
 app_url=c['application_url'];source=c['source_url'];checked=result['checked_at']
 fields={}
 def field(key,status,summary,url=app_url):
  fields[key]={'status':status,'summary':summary,'source_url':url,'checked_at':checked}
 field('identity','confirmed','Official event, location and application identity were checked.',source)
 field('availability','confirmed','Application controls and status were checked; category space is not guaranteed.')
 category_sources=sorted({fact.get('source_url',source) for fact in facts.values() if fact.get('status')=='eligible'})
 field('categories','partial' if facts else 'unconfirmed','Specific source-listed products are grouped for searching; other products in each group are unconfirmed.' if facts else 'Product eligibility is unconfirmed. Ask the organizer.',category_sources[0] if category_sources else source)
 known_cost=any(c.get(k) is not None for k in ('booth_fee','application_fee','deposit'))
 field('costs','partial' if known_cost else 'unconfirmed','Some published prices were found; confirm the complete cost and required add-ons.' if known_cost else 'Specific prices are unconfirmed. Ask the organizer.',source)
 field('requirements','partial' if requirements else 'unconfirmed','Some explicit requirements were found; read the full official terms.' if requirements else 'Specific attendance, setup and cancellation requirements remain unconfirmed.')
 cutoff=datetime.fromisoformat(c['deadline']) if c.get('deadline') else None
 scope=cutoff.astimezone(ZoneInfo('America/New_York')).date().isoformat() if cutoff and cutoff.tzinfo else None
 field('deadline','confirmed' if scope and scope<c['starts_on'] else 'unconfirmed',
       'A dated application cutoff was found.' if scope and scope<c['starts_on'] else 'Confirm the event-specific cutoff: the published deadline may cover a series or fall on the event date.')
 prices=list(price_rows(app));table_pair='Table options:' in c.get('fee_notes','')
 return {'version':1,'application_url':app_url,'source_url':source,'starts_on':c['starts_on'],'ends_on':c['ends_on'],'checked_at':checked,
  'fields':fields,'signals':{'price_options':len(prices)+(2 if table_pair else 0),'category_choices':len(question_options(app)),
  'category_keys':sorted(facts),'requirements_found':bool(requirements)}}

def regression_issues(previous,current):
 if not previous:return []
 issues=[]
 for key in ('categories','costs','requirements','deadline'):
  old=previous.get('fields',{}).get(key,{}).get('status');new=current['fields'][key]['status']
  if old in {'confirmed','partial'} and new=='unconfirmed':issues.append(key+' information previously found is no longer confirmed')
 a=previous.get('signals',{});b=current['signals']
 for key in ('price_options','category_choices'):
  if a.get(key,0)>0 and b.get(key,0)==0:issues.append(key.replace('_',' ')+' section previously readable is missing')
 missing=set(a.get('category_keys',[]))-set(b.get('category_keys',[]))
 if missing:issues.append('previous category evidence disappeared: '+', '.join(sorted(missing)))
 return issues

def apply_quality_gate(item,result):
 if result.get('decision')!='publish':return result
 q=result.get('research_quality');c=result.get('candidate',{})
 if not q or c.get('availability') not in {'open','limited','waitlist'} or not c.get('deadline'):
  return {**result,'decision':'review','reason':'Research quality receipt or critical application facts are missing.'}
 issues=regression_issues((item or {}).get('previous_quality'),q)
 if issues:return {**result,'decision':'review','reason':'Source change needs review: '+'; '.join(issues),'quality_issues':issues}
 return result


def add_review_suggestions(item,result):
 """Keep collected facts available if publication is deferred by either layer."""
 c=result.get('candidate',{})
 if not item or result.get('policy')!='makrs-eventeny-v5-quality' or not c or not result.get('checked_at') or not result.get('source_hash'):return result
 if c.get('application_url')!=item.get('application_url') or c.get('starts_on')!=item.get('starts_on') or c.get('ends_on')!=item.get('ends_on'):return result
 fields={k:c[k] for k in ('booth_fee','application_fee','deposit','deadline','fee_notes','eligibility') if c.get(k) is not None and c[k]!=''}
 return {**result,'research_suggestions':{'application_url':c['application_url'],'starts_on':c['starts_on'],'ends_on':c['ends_on'],
  'source_url':c['source_url'],'source_hash':result['source_hash'],'checked_at':result['checked_at'],'fields':fields,
  'notes':result.get('reason') or 'Research collected. Confirm any remaining source warnings before publishing.',
  'form_readable':True,'complete':result.get('decision')=='publish'}}
