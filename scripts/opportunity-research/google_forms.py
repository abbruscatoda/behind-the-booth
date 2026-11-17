"""Read public Google Forms without accounts, cookies, submissions or script execution.

Source adapters bind a form to an organizer and occurrence. This parser reads
published descriptions/questions/options, never respondent answers. Partial or
multi-page forms remain review-only; finding an Apply link is not verification.
"""
import re
from decimal import Decimal
from category_rules import visible_text,nodes_with_parents
from verifier import Uncertain,clean

MONEY=r'\$\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)'
BLOCK=r'must sign in|sign in to continue|allow google forms access|can.t access this content|request access|you need permission'

def published_blocks(doc):
 nodes=list(nodes_with_parents(doc.root));out=[]
 # Semantic role/Google descriptive classes, not unstable whole-document text.
 for n,parents in nodes:
  classes=set(n.attrs.get('class','').split())
  if n.attrs.get('role') in {'heading','listitem'} or classes & {'cBGGJ','M7eMe','OIC90c','Cb9Z7'}:
   text=clean(visible_text(n))
   if text and text not in out:out.append(text)
 if not out:
  out=[clean(visible_text(n)) for n,_ in nodes if n.tag in {'h1','h2','h3','p','legend','label'} and visible_text(n)]
 return list(dict.fromkeys(out))

def read_public_form(doc):
 text=visible_text(doc.root)
 if re.search(BLOCK,text,re.I):raise Uncertain('Google Form requires sign-in, cookie access, or permission; a public worker cannot read the application.')
 if re.search(r'no longer accepting responses|form .{0,40}closed|applications? (?:are )?closed',text,re.I):
  return {'closed':True,'complete':False,'blocks':published_blocks(doc),'fee_notes':'','eligibility':'','booth_fee':None,'application_fee':None,'deposit':None}
 blocks=published_blocks(doc)
 if not blocks:raise Uncertain('Google Form has no readable organizer descriptions or questions.')
 active=[]
 for n,parents in nodes_with_parents(doc.root):
  if n.tag=='button' or n.attrs.get('role')=='button' or (n.tag=='input' and n.attrs.get('type')=='submit'):
   label=clean(visible_text(n) or n.attrs.get('value',''))
   if label.lower() in {'submit','next'}:active.append(label.lower())
 # Next means not all sections have been read; do not submit/answer to advance.
 complete='submit' in active and 'next' not in active
 # Preserve whole fee/condition blocks. Never flatten a category-specific price
 # into the universal booth price or treat a refundable deposit as an app fee.
 fee_blocks=[];requirements=[];prices={key:set() for key in ('booth_fee','application_fee','deposit')}
 labels={'booth_fee':r'(?:standard )?(?:booth|table|space) (?:fee|cost|price)',
         'application_fee':r'(?:non-refundable )?application fee', 'deposit':r'(?:refundable )?deposit'}
 issues=[]
 for block in blocks:
  if '$' in block or re.search(r'\b(?:fees?|deposits?|refunds?|commission|electricity)\b',block,re.I):fee_blocks.append(block)
  if re.search(r'\b(?:must|required|requirement|shall|prohibited|not (?:allowed|permitted)|no refunds|nonrefundable|insurance|permit|weights|setup|set-up|load-in|cleanliness|photo|selection|approval)\b',block,re.I):requirements.append(block)
  for key,label in labels.items():
   # Only exact, unconditional labels. Conditional tiers stay in fee notes.
   match=re.fullmatch(label+r'\s*[:–-]\s*'+MONEY+r'\s*\.?',block,re.I)
   if match:prices[key].add(str(Decimal(match[1].replace(',',''))))
 for key,values in prices.items():
  if len(values)>1:issues.append('Conflicting '+key.replace('_',' ')+' values require review.')
 def bounded(values,limit):
  text='\n'.join(dict.fromkeys(values))
  if len(text)>limit:issues.append('Published terms exceed the editor limit; full source review required.');return ''
  return text
 return {'closed':False,'complete':complete,'blocks':blocks,'fee_notes':bounded(fee_blocks,2000),
  'eligibility':bounded(requirements,2000),'issues':issues,
  **{k:float(next(iter(v))) if len(v)==1 else None for k,v in prices.items()}}
