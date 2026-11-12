from pathlib import Path
from datetime import datetime
import re, zipfile, subprocess, html
import xml.etree.ElementTree as ET
BASE=Path('/Users/ofirfizitsky/PycharmProjects/research_dbeaver/reports/donor_research_report')
SRC=BASE/'DONOR_RESEARCH_REPORT_DRAFT_v0_2.md'
OUT=BASE/'DONOR_RESEARCH_REPORT_DRAFT_v0_2.docx'
TMP=Path('/tmp/donor_word_pngs');TMP.mkdir(exist_ok=True)
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
WP='http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'
A='http://schemas.openxmlformats.org/drawingml/2006/main'
PIC='http://schemas.openxmlformats.org/drawingml/2006/picture'
PR='http://schemas.openxmlformats.org/package/2006/relationships'
CT='http://schemas.openxmlformats.org/package/2006/content-types'
for n,u in [('w',W),('r',R),('wp',WP),('a',A),('pic',PIC)]: ET.register_namespace(n,u)
Q=lambda n,t:'{%s}%s'%(n,t)
def el(p,n,t,v=None,**kw):
 x=ET.SubElement(p,Q(n,t),{Q(W,k[2:]) if k.startswith('w_') else k:str(vv) for k,vv in kw.items()})
 if v is not None:x.text=str(v)
 return x
doc=ET.Element(Q(W,'document')); body=el(doc,W,'body')
rels=ET.Element('Relationships',xmlns=PR);relno=1
media={}
def rel(target,typ,external=False):
 global relno
 id='rId'+str(relno);relno+=1
 attrs={'Id':id,'Type':'http://schemas.openxmlformats.org/officeDocument/2006/relationships/'+typ,'Target':target}
 if external:attrs['TargetMode']='External'
 ET.SubElement(rels,'Relationship',attrs)
 return id
styles=ET.Element(Q(W,'styles'))
for name,size,color,bold,outline in [
 ('Normal',19,'223348',False,None),('Title',38,'173A58',True,None),
 ('Subtitle',23,'536C81',False,None),('Heading1',29,'183B59',True,0),
 ('Heading2',23,'28577A',True,1),('Heading3',21,'315C7A',True,2),
 ('Quote',19,'526B7F',False,None),('Caption',17,'5D7185',False,None),('Code',17,'40546B',False,None)]:
 st=el(styles,W,'style',w_type='paragraph',w_styleId=name);el(st,W,'name',w_val=name)
 if name!='Normal':el(st,W,'basedOn',w_val='Normal')
 if outline is not None:pp=el(st,W,'pPr');el(pp,W,'outlineLvl',w_val=outline)
 rp=el(st,W,'rPr');el(rp,W,'rFonts',w_ascii='Arial',w_hAnsi='Arial');el(rp,W,'sz',w_val=size);el(rp,W,'color',w_val=color)
 if bold:el(rp,W,'b')
def para_style(p,name='Normal',after=130,before=0,indent=None,align=None,breakbefore=False):
 pp=el(p,W,'pPr');el(pp,W,'pStyle',w_val=name);el(pp,W,'spacing',w_after=after,w_before=before)
 if indent is not None:el(pp,W,'ind',w_left=indent)
 if align:el(pp,W,'jc',w_val=align)
 if breakbefore:el(pp,W,'pageBreakBefore')
 if name.startswith('Heading'):el(pp,W,'keepNext')
 return pp
def run(p,text,bold=False,italic=False,mono=False,size=None,color=None):
 rr=el(p,W,'r')
 if bold or italic or mono or size or color:
  rp=el(rr,W,'rPr')
  if bold:el(rp,W,'b')
  if italic:el(rp,W,'i')
  if mono:el(rp,W,'rFonts',w_ascii='Menlo',w_hAnsi='Menlo')
  if size:el(rp,W,'sz',w_val=size)
  if color:el(rp,W,'color',w_val=color)
 tt=el(rr,W,'t',text);tt.set('{http://www.w3.org/XML/1998/namespace}space','preserve')
BT=chr(96)
TOKEN=re.compile(r'(\*\*.+?\*\*|'+re.escape(BT)+r'[^'+re.escape(BT)+r']+'+re.escape(BT)+r'|\[[^\]]+\]\([^)]+\)|(?<!\*)\*[^*]+\*)')
def inline(p,s,small=False):
 for part in TOKEN.split(str(s)):
  if not part:continue
  opts={'size':16} if small else {}
  if part.startswith('**') and part.endswith('**'):run(p,part[2:-2],bold=True,**opts)
  elif part.startswith(BT) and part.endswith(BT):run(p,part[1:-1],mono=True,**opts)
  elif part.startswith('*') and part.endswith('*'):run(p,part[1:-1],italic=True,**opts)
  elif part.startswith('['):
   m=re.match(r'\[([^\]]+)\]\(([^)]+)\)',part)
   if m:
    label,url=m.groups()
    if not url.startswith('http'):url='https://github.com/shluku/neurotrax_cavia/blob/main/reports/donor_research_report/'+url
    h=el(p,W,'hyperlink');h.set(Q(R,'id'),rel(url,'hyperlink',True))
    rr=el(h,W,'r');rp=el(rr,W,'rPr');el(rp,W,'color',w_val='286F9D');el(rp,W,'u',w_val='single')
    el(rr,W,'t',label)
   else:run(p,part,**opts)
  else:run(p,part,**opts)
heads=[];bookmarkid=1
def paragraph(text='',style='Normal',level=0,bullet=False,align=None):
 global bookmarkid
 p=el(body,W,'p')
 if level:
  st='Heading'+str(min(level,3))
  para_style(p,st,before=250 if level==1 else 165,after=125,breakbefore=level==1)
 else:para_style(p,style,after=72 if bullet else 125,indent=320 if bullet else None,align=align)
 if bullet:run(p,'•  ')
 inline(p,text)
 if level:
  name='H'+str(bookmarkid)
  s=el(p,W,'bookmarkStart',w_id=bookmarkid,w_name=name)
  el(p,W,'bookmarkEnd',w_id=bookmarkid);bookmarkid+=1
  heads.append((level,name,text))
 return p
def table(rows):
 cols=max(len(r) for r in rows)
 t=el(body,W,'tbl');pr=el(t,W,'tblPr');el(pr,W,'tblW',w_w=10000,w_type='dxa')
 borders=el(pr,W,'tblBorders')
 for tag in ('top','bottom','left','right','insideH','insideV'):el(borders,W,tag,w_val='single',w_sz=4,w_color='CFDDE7')
 grid=el(t,W,'tblGrid')
 for x in range(cols):el(grid,W,'gridCol',w_w=10000//cols)
 for idx,arr in enumerate(rows):
  tr=el(t,W,'tr')
  if idx==0:trp=el(tr,W,'trPr');el(trp,W,'tblHeader',w_val=1)
  for j in range(cols):
   cell=el(tr,W,'tc');pr=el(cell,W,'tcPr');el(pr,W,'tcW',w_w=10000//cols,w_type='dxa')
   if idx==0:el(pr,W,'shd',w_fill='DFEDF4')
   p=el(cell,W,'p');para_style(p,after=40)
   txt=arr[j].strip() if j<len(arr) else ''
   inline(p,txt,small=True)
def imagefig(path,alt):
 pth=BASE/path
 if not pth.exists():paragraph('Missing graphic: '+path,'Caption');return
 if pth.suffix=='.svg':
  png=TMP/(pth.stem+'.png')
  subprocess.run(['sips','-s','format','png',str(pth),'--out',str(png)],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,check=True)
  try:
   root=ET.parse(pth).getroot();v=[float(a) for a in root.attrib['viewBox'].split()];ratio=v[2]/v[3]
  except:ratio=1.8
 else:png=pth;ratio=1.8
 n='image'+str(len(media)+1)+'.png';media[n]=png.read_bytes()
 r_id=rel('media/'+n,'image')
 pp=el(body,W,'p');para_style(pp,after=75,align='center')
 r=el(pp,W,'r');dr=el(r,W,'drawing');wi=el(dr,WP,'inline')
 width=6.55*914400;height=min(width/ratio,4.2*914400)
 if width/ratio>height:width=height*ratio
 cx,cy=str(round(width)),str(round(height))
 el(wi,WP,'extent',cx=cx,cy=cy);el(wi,WP,'docPr',id=str(len(media)),name=alt[:90],descr=alt)
 graph=el(wi,A,'graphic');gd=el(graph,A,'graphicData',uri=PIC)
 pic=el(gd,PIC,'pic');nv=el(pic,PIC,'nvPicPr')
 el(nv,PIC,'cNvPr',id=0,name=n);el(nv,PIC,'cNvPicPr')
 bf=el(pic,PIC,'blipFill');blip=el(bf,A,'blip');blip.set(Q(R,'embed'),r_id)
 stretch=el(bf,A,'stretch');el(stretch,A,'fillRect')
 sp=el(pic,PIC,'spPr');xf=el(sp,A,'xfrm');el(xf,A,'off',x=0,y=0);el(xf,A,'ext',cx=cx,cy=cy)
 geometry=el(sp,A,'prstGeom',prst='rect');el(geometry,A,'avLst')
 paragraph(alt,'Caption',align='center')
def linebreak():
 p=el(body,W,'p');pp=para_style(p,after=80)
 bd=el(pp,W,'pBdr');el(bd,W,'bottom',w_val='single',w_sz=6,w_color='D9E4EA')
def parse():
 lines=SRC.read_text().splitlines()
 paragraph('PASSIVE SMARTPHONE DIGITAL PHENOTYPING','Title',align='center')
 paragraph('Comprehensive research program report · Donor review draft 0.2','Subtitle',align='center')
 paragraph('Preserved from the source Markdown document, including historical results, methodological limitations and figures.','Quote')
 # add clickable contents later
 p=el(body,W,'p');para_style(p,'Heading1',before=200);run(p,'CONTENTS',bold=True)
 slot=len(body)
 p=el(body,W,'p');para_style(p)
 i=0
 while i<len(lines):
  text=lines[i].strip()
  if not text:i+=1;continue
  if text in ('---','***'):linebreak();i+=1;continue
  m=re.match(r'^(#{1,6})\s+(.*)',text)
  if m:paragraph(m.group(2),level=len(m.group(1)));i+=1;continue
  m=re.match(r'^!\[([^\]]+)\]\(([^)]+)\)$',text)
  if m:imagefig(m.group(2),m.group(1));i+=1;continue
  if text.startswith(BT*3):
   i+=1
   while i<len(lines) and not lines[i].strip().startswith(BT*3):
    paragraph(lines[i],'Code');i+=1
   i+=1;continue
  if text.startswith('|') and i+1<len(lines) and re.search(r'\|\s*:?-{3,}',lines[i+1]):
   data=[]
   while i<len(lines) and lines[i].strip().startswith('|'):
    row=lines[i].strip()
    if not re.search(r'^\|?\s*:?-{3,}',row):data.append([x.strip() for x in row.strip('|').split('|')])
    i+=1
   if data:table(data)
   continue
  if text.startswith('>'):
   arr=[]
   while i<len(lines) and lines[i].strip().startswith('>'):
    arr.append(lines[i].strip().lstrip('>').strip());i+=1
   paragraph(' '.join(arr),'Quote');continue
  if re.match(r'^[-*]\s+',text):
   while i<len(lines) and re.match(r'^\s*[-*]\s+',lines[i]):
    v=re.sub(r'^\s*[-*]\s+','',lines[i])
    v=re.sub(r'^\[[ xX]\]\s*','',v)
    paragraph(v,bullet=True);i+=1
   continue
  if re.match(r'^\d+\.\s+',text):
   while i<len(lines) and re.match(r'^\s*\d+\.\s+',lines[i]):
    paragraph(lines[i].strip(),bullet=True);i+=1
   continue
  arr=[text];i+=1
  while i<len(lines):
   t=lines[i].strip()
   if not t or t.startswith(('#','|','>','![')) or t in ('---','***') or t.startswith(BT*3) or re.match(r'^[-*]\s+|^\d+\.\s+',t):break
   arr.append(t);i+=1
  paragraph(' '.join(arr))
 # insert internal links to headings
 for level,name,heading in heads:
  if level>2:continue
  p=ET.Element(Q(W,'p'));para_style(p,after=55,indent=150 if level==1 else 420)
  link=el(p,W,'hyperlink');link.set(Q(W,'anchor'),name)
  rr=el(link,W,'r');rp=el(rr,W,'rPr');el(rp,W,'color',w_val='2672A0')
  if level==1:el(rp,W,'b')
  el(rr,W,'t',heading)
  body.insert(slot,p);slot+=1
 sect=el(body,W,'sectPr')
 el(sect,W,'pgSz',w_w=11906,w_h=16838)
 el(sect,W,'pgMar',w_top=1040,w_bottom=1080,w_left=925,w_right=925,w_header=500,w_footer=550)
 # page footer
 foot=ET.Element(Q(W,'ftr'));p=el(foot,W,'p');para_style(p,align='center')
 run(p,'Research report v0.2   •   page ',size=15,color='667B8F')
 f=el(p,W,'fldSimple',w_instr='PAGE');rr=el(f,W,'r');el(rr,W,'t','1')
 footrid=rel('footer1.xml','footer');ff=el(sect,W,'footerReference',w_type='default');ff.set(Q(R,'id'),footrid)
 return foot
foot=parse()
content=ET.Element('Types',xmlns=CT)
for ext,typ in [('rels','application/vnd.openxmlformats-package.relationships+xml'),('xml','application/xml'),('png','image/png')]:
 ET.SubElement(content,'Default',Extension=ext,ContentType=typ)
for path,typ in [('word/document.xml','application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml'),('word/styles.xml','application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml'),('word/footer1.xml','application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml')]:
 ET.SubElement(content,'Override',PartName='/'+path,ContentType=typ)
rootrels=ET.Element('Relationships',xmlns=PR)
ET.SubElement(rootrels,'Relationship',Id='rId1',Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument',Target='word/document.xml')
rel('styles.xml','styles')
xml=lambda x:ET.tostring(x,encoding='utf-8',xml_declaration=True)
with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED) as z:
 for n,data in [('[Content_Types].xml',xml(content)),('_rels/.rels',xml(rootrels)),('word/document.xml',xml(doc)),('word/styles.xml',xml(styles)),('word/footer1.xml',xml(foot)),('word/_rels/document.xml.rels',xml(rels))]:z.writestr(n,data)
 for name,data in media.items():z.writestr('word/media/'+name,data)
print('CREATED',OUT,'bytes',OUT.stat().st_size,'headings',len(heads),'images',len(media),'tables',len(body.findall(Q(W,'tbl'))))
