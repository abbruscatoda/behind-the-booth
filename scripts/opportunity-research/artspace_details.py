"""Public table prices and conditions from the already identity-verified form."""
import re
from category_rules import nodes_with_parents,visible_text

class ConflictingTablePrices(ValueError):pass

def form_details(doc):
 # Jotform's descriptive blocks contain the event terms. Never parse a hidden
 # script or a user's field value as a published organizer instruction.
 blocks=[visible_text(n) for n,_ in nodes_with_parents(doc.root) if 'form-html' in n.attrs.get('class','').split()]
 if not blocks:
  blocks=[visible_text(n) for n,_ in nodes_with_parents(doc.root) if n.tag=='p']
 text=' '.join(blocks)
 prices={'half':set(),'full':set()}
 for m in re.finditer(r'Table Fee:\s*\$([\d,]+(?:\.\d{1,2})?)\s+for\s+half\s+(?:a\s+)?table.{0,160}?\bor\s+\$([\d,]+(?:\.\d{1,2})?)\s+for\s+(?:a\s+)?full\b',text,re.I):
  for key,value in zip(('half','full'),m.groups()):prices[key].add(float(value.replace(',','')))
 # Cross-check enabled options for THIS question, not unrelated radio prices.
 for label,parents in nodes_with_parents(doc.root):
  if label.tag not in {'label','legend','span'}:continue
  if re.sub('[^a-z]','',visible_text(label).lower())!='whichspaceareyouapplyingfor':continue
  group=next((p for p in reversed(parents) if p.tag in {'li','fieldset'} or 'form-line' in p.attrs.get('class','').split()),None)
  if group is None:continue
  for node,_ in nodes_with_parents(group):
   if node.tag!='input' or node.attrs.get('type')!='radio':continue
   option=node.attrs.get('value','');match=re.search(r'\b(half|full) table\b.{0,140}?\$([\d,]+(?:\.\d{1,2})?)',option,re.I)
   if match:prices[match[1].lower()].add(float(match[2].replace(',','')))
 if any(len(values)>1 for values in prices.values()):raise ConflictingTablePrices('Published table prices disagree between form prose and choices.')
 pair={key:next(iter(values)) for key,values in prices.items() if values}
 if any(value<=0 or value>10000 for value in pair.values()):raise ConflictingTablePrices('Table prices need organizer confirmation.')
 if len(pair)==2 and pair['half']>pair['full']:raise ConflictingTablePrices('Half-table and full-table prices are inconsistent.')
 fee_notes=' '.join(f'{key.capitalize()} table: ${value:,.2f}.' for key,value in pair.items())
 if len(pair)==2:fee_notes=f"Table options: half table ${pair['half']:,.2f}; full table ${pair['full']:,.2f}."
 if fee_notes:fee_notes+=' Confirm remaining table options with the organizer.'
 requirements=[]
 for pattern,message in [
  (r'vendors must be present for the full event','Attendance for the full event is required.'),
  (r'table fees are due upon selection','Table fees are due upon selection.'),
  (r'no refunds of table fees','Table fees are nonrefundable.'),
  (r'will not take a commission','The organizer states it takes no commission on sales.'),
  (r'provide marketing, clean table space, chairs','The organizer provides table space and chairs; bring your sales setup materials.'),
  (r'submissions will be juried','Selection is juried.'),
  (r'selections will be made on a rolling basis','Selections are made on a rolling basis.'),
 ]:
  if re.search(pattern,text,re.I):requirements.append(message)
 return {'booth_fee':min(pair.values()) if pair else None,'fee_notes':fee_notes,'requirements':' '.join(requirements)}
