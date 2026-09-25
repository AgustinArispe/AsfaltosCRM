"""Lossless rectangular crops of real 1920x1080 demo screenshots."""
from pathlib import Path
import json, subprocess
base=Path(__file__).resolve().parent
crops={
'pipeline':('pipeline',297,182,1184,390),
'pipeline-title':('pipeline',288,28,480,52),
'nexo-card':('pipeline',705,249,367,97),
'delta-card':('pipeline',306,352,367,95),
'notification':('notifications',289,184,1010,84),
'notification-badge':('notifications',8,204,239,45),
'detail-header':('detail',424,110,351,52),
'relation':('detail',420,227,353,205),
'query':('detail',420,658,760,132),
'product':('detail',435,851,590,86),
'activity':('detail',1194,658,306,285),
'notes':('detail-notes',1194,614,306,217),
'whatsapp-action':('detail',820,457,168,45),
'paula-header':('paula',608,17,740,65),
'paula-in':('paula',626,256,612,73),
'paula-out':('paula',1258,337,612,71),
'whatsapp-nav':('paula',8,265,239,47),
'delta-header':('delta',608,17,740,65),
'delta-image':('delta',627,100,610,251),
'urbania-header':('urbania',608,17,740,65),
'urbania-audio':('urbania',627,99,610,186),
'dashboard-title':('dashboard',287,27,625,53),
'period':('dashboard',311,180,1552,42),
'won':('dashboard',314,239,373,74),
'conversion':('dashboard',1094,231,378,139),
'active':('dashboard',287,410,1601,376),
'evolution':('dashboard-evolution',287,47,1601,550),
'origins':('dashboard-origins',287,430,524,522),
}
manifest={}
for name,(source,x,y,w,h) in crops.items():
    src=base.parent/'captures'/f'{source}.png'
    dst=base/'assets'/f'{name}.png'
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(src),'-vf',f'crop={w}:{h}:{x}:{y}','-frames:v','1',str(dst)],check=True)
    manifest[name]={'source':f'../captures/{source}.png','crop':[x,y,w,h],'asset':f'assets/{name}.png'}
(base/'capture-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(f'{len(crops)} lossless crops prepared.')
