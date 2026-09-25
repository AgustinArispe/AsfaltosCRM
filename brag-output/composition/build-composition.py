"""Build the approved seven-scene composition from audited real UI crops."""
from pathlib import Path
import json
base=Path(__file__).resolve().parent

def img(id: str, asset: str, x: float, y: float, w: float, h: float, cls: str = 'panel') -> str:
    return f'<div id="{id}" class="{cls}" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px"><img src="assets/{asset}.png" alt="" width="{w}" height="{h}"></div>'
def scene(id: str, start: float, duration: float, body: str, track: int = 0) -> str:
    return f'<section id="{id}" class="clip scene" data-start="{start}" data-duration="{duration}" data-track-index="{track}"><div id="{id}-visual" class="scene-visual">{body}</div></section>'
def brand(prefix: str) -> str:
    return img(prefix+'-logo','pulse-brand-touch',810,292,300,300,'logo')
scenes=[]
scenes.append(scene('opening',0,2.7,brand('opening')))
scenes.append(scene('arrival',2.5,3.5,
    img('arrival-notice','notification',202,367,1515,126)+img('arrival-badge','notification-badge',203,248,335,63)+
    '<div id="badge-ring" class="ring" style="left:417px;top:259px;width:39px;height:39px"></div>'))
# Pipeline begins inside the lead-arrival scene and continues into its dedicated interval.
board=img('pipeline-title','pipeline-title',240,134,576,62,'plain')+img('board','pipeline',240,300,1440,474)+img('nexo','nexo-card',736.2,381.5,446.4,118)+img('board-badge','notification-badge',240,216,287,54,'plain')
board+=''.join(f'<div id="stage-{i}" class="focus" style="left:{x}px;top:307px;width:450px;height:58px"></div>' for i,x in enumerate([248,732,1216]))
board+='<div id="delta-focus" class="focus" style="left:249px;top:505px;width:450px;height:119px"></div>'
board+='<div id="nexo-focus" class="focus" style="left:734px;top:379px;width:450px;height:121px"></div>'
scenes.append(scene('pipeline',4.2,6.8,board,1))
detail=img('detail-header','detail-header',144,135,702,104,'plain')+img('relation','relation',144,290,530,308)+img('query','query',704,290,1064,185)+img('product','product',704,510,590,86)+img('activity','activity',1335,510,428,399)+img('notes','notes',1335,510,428,304)+img('whatsapp-action','whatsapp-action',704,690,302,81)
detail+='<div id="query-focus" class="focus" style="left:720px;top:375px;width:1030px;height:79px"></div>'
scenes.append(scene('detail',10.7,5.3,detail,2))
chat=img('whatsapp-nav','whatsapp-nav',144,135,335,66,'plain')
chat+=img('paula-header','paula-header',144,241,1332,117,'plain')+img('paula-in','paula-in',144,394,979,117)+img('paula-out','paula-out',797,585,979,114)
chat+=img('delta-header','delta-header',144,241,1332,117,'plain')+img('delta-image','delta-image',420,380,976,402)
chat+=img('urbania-header','urbania-header',144,241,1332,117,'plain')+img('urbania-audio','urbania-audio',420,410,976,298)
chat+='<div id="read-focus" class="focus" style="left:1680px;top:643px;width:85px;height:46px"></div>'
scenes.append(scene('whatsapp',15.7,6.3,chat,1))
dash=img('dashboard-title','dashboard-title',144,120,750,64,'plain')+img('period','period',144,214,1630,44,'plain')+img('won','won',200,322,672,133)+img('conversion','conversion',1045,308,605,222)+img('active','active',240,550,1440,338)+img('evolution','evolution',160,288,1601,550)+img('origins','origins',1112,288,629,626)
dash+='<div id="conversion-focus" class="focus" style="left:1034px;top:297px;width:627px;height:244px"></div>'
scenes.append(scene('dashboard',21.8,5.2,dash,2))
scenes.append(scene('closing',26.7,3.3,brand('closing'),1))
overlays=[('opening-copy','Seguí el ritmo de tus ventas',.1,.4,2.3,2.5,668),('arrival-copy','Tus oportunidades llegan a un solo lugar.',2.6,2.9,5.7,5.9,933),('pipeline-copy','Cada oportunidad, bajo control.',6.1,6.4,10.6,10.8,933),('detail-copy','Todo el contexto. En un solo lugar.',11.1,11.4,15.6,15.8,933),('whatsapp-copy','Conversaciones conectadas con tus oportunidades.',16.1,16.4,21.6,21.8,904),('dashboard-copy','Decidí con datos reales.',22.1,22.4,26.6,26.8,933),('closing-copy','Seguí el ritmo de tus ventas',27.2,27.5,30,30,668)]
texts=''.join(f'<div id="{id}-clip" class="clip caption" data-start="{a}" data-duration="{d-a:.3f}" data-track-index="3" style="top:{y}px"><p id="{id}">{text}</p></div>' for id,text,a,b,c,d,y in overlays)
css='''@font-face{font-family:Manrope;src:url('assets/manrope.woff2') format('woff2');font-weight:400 700;font-display:block}*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%;background:#e8eef7;font-family:Manrope,sans-serif;color:#173b6d}#root{position:relative;width:100%;height:100%;overflow:hidden;background:#e8eef7}.scene,.scene-visual{position:absolute;inset:0}.scene-visual{background:transparent}#pipeline-visual,#detail-visual,#whatsapp-visual,#dashboard-visual{opacity:0}.panel,.plain,.logo{position:absolute;transform-origin:center}.panel{border-radius:14px;overflow:hidden;box-shadow:0 12px 28px #173b6d12}.panel img,.plain img,.logo img{display:block;width:100%;height:100%}.focus{position:absolute;border:3px solid #cba100;border-radius:16px;pointer-events:none;opacity:0}.ring{position:absolute;border:3px solid #cba100;border-radius:50%;opacity:0}.caption{position:absolute;left:96px;width:1728px;height:130px;z-index:20;display:flex;justify-content:center;align-items:flex-start}.caption p{margin:0;font-weight:600;font-size:56px;line-height:1.15;text-align:center;max-width:1610px;color:#173b6d}#whatsapp-copy{max-width:1440px}.cursor-layer{position:absolute;inset:0;z-index:15;pointer-events:none}#cursor{position:absolute;width:38px;height:46px;left:0;top:0;opacity:0}#click-ring{position:absolute;left:-18px;top:-18px;width:52px;height:52px;border:3px solid #cba100;border-radius:50%;opacity:0}'''
js='''const tl=gsap.timeline({paused:true,defaults:{ease:'power2.inOut'}});
// All positions are authored capture coordinates; no runtime DOM measurements.
function show(s,t,d=.3){tl.fromTo(s,{opacity:0,y:16},{opacity:1,y:0,duration:d,immediateRender:false},t)}
function hide(s,t,d=.2){tl.to(s,{opacity:0,duration:d},t)}
function flash(s,t,d=.3){tl.fromTo(s,{opacity:0},{opacity:1,duration:d/2,immediateRender:false},t).to(s,{opacity:0,duration:d/2},t+d/2)}
tl.fromTo('#opening-logo',{scale:.97,y:16},{scale:1,y:0,duration:.3},0);
hide('#opening-visual',2.4,.3);
show('#arrival-notice',2.5); show('#arrival-badge',2.5);
flash('#badge-ring',3.3);flash('#delta-focus',4.5,.3);
hide('#arrival-visual',4.2,.3);show('#pipeline-visual',4.2,.3);
tl.fromTo('#board',{scale:1.02,x:24},{scale:1,x:0,duration:.3,immediateRender:false},4.5);
tl.to('#board,#nexo',{x:-24,duration:1},6).to('#board,#nexo',{x:0,duration:1},7);
// Nexo is an exact crop of its card, raised 4px over the captured resting pose.
tl.to('#nexo',{y:-4,scale:1.02,duration:.25},7.3);
flash('#nexo-focus',8.2,.3);
flash('#stage-0',9,.3);flash('#stage-1',9.3,.3);flash('#stage-2',9.6,.3);
hide('#pipeline-visual',10.7,.3);
show('#detail-visual',10.7,.3);flash('#query-focus',12.2,.3);
tl.to('#query',{y:-24,duration:.4},12.4).to('#query',{y:0,duration:.4},12.8);
tl.set('#product,#activity',{opacity:0},0);show('#product',13,.3);show('#activity',13,.3);
tl.set('#notes',{opacity:0},0);show('#notes',14.1,.3);hide('#activity',14.1,.3);
tl.to('#whatsapp-action',{scale:1.06,duration:.3},15.2);
hide('#detail-visual',15.7,.3);
tl.set('#paula-in,#paula-out,#delta-header,#delta-image,#urbania-header,#urbania-audio',{opacity:0},0);
show('#whatsapp-visual',15.7,.3);show('#paula-in',16.2,.3);show('#paula-out',17,.3);flash('#read-focus',17.4,.3);
hide('#paula-header,#paula-in,#paula-out',17.9,.2);show('#delta-header',17.9,.2);show('#delta-image',18.1,.3);
tl.to('#delta-image',{scale:1.06,y:-24,duration:1.2},18.5);
hide('#delta-header,#delta-image',19.9,.2);show('#urbania-header',19.9,.2);show('#urbania-audio',20.1,.3);
hide('#whatsapp-visual',21.8,.2);
tl.set('#won,#conversion,#active,#evolution,#origins',{opacity:0},0);
show('#dashboard-visual',21.8,.3);show('#won',22.2,.3);show('#conversion',23,.3);
flash('#conversion-focus',23.3,.3);show('#active',24,.3);
hide('#won,#conversion,#active',24.8,.2);show('#evolution',25,.3);
tl.to('#evolution',{x:-24,duration:.7},25.2);
hide('#evolution',25.8,.2);show('#origins',26,.3);
// Origin has its native four rows, values unchanged. No custom charts.
tl.to('#origins',{x:-360,duration:.3},26.35);
hide('#dashboard-visual',26.7,.3);
tl.fromTo('#closing-logo',{opacity:0,scale:.97,y:16},{opacity:1,scale:1,y:0,duration:.3,immediateRender:false},26.7);
'''
for id,text,a,b,c,d,y in overlays:
    js+=f"show('#{id}',{a},{b-a:.3f});\n"
    if c<d: js+=f"hide('#{id}',{c},{d-c:.3f});\n"
js+='''// One cursor follows authored screen coordinates. No live click or data mutation.
tl.set('#cursor',{x:470,y:610,opacity:0},0);
tl.to('#cursor',{opacity:1,duration:.2},6.7).to('#cursor',{x:992,y:420,duration:.6},6.8);
tl.to('#cursor',{x:1010,y:425,duration:.3},10.2);
flash('#click-ring',10.6,.2);hide('#cursor',10.8,.2);
tl.set('#cursor',{x:1540,y:630},13.7);tl.to('#cursor',{opacity:1,duration:.2},13.9);flash('#click-ring',14.1,.2);
tl.to('#cursor',{x:865,y:722,duration:.4},15.1);flash('#click-ring',15.6,.2);hide('#cursor',15.8,.2);
tl.set('#cursor',{x:482,y:505},20.2);tl.to('#cursor',{opacity:1,duration:.2},20.5);hide('#cursor',21.5,.2);
tl.set('#cursor',{x:1300,y:635},24);tl.to('#cursor',{opacity:1,duration:.2},24.3);hide('#cursor',24.8,.2);
window.__timelines=window.__timelines||{};window.__timelines['pulse-crm']=tl;
'''
cursor='<div class="cursor-layer"><div id="cursor"><svg width="38" height="46" viewBox="0 0 38 46"><path d="M4 3 L5 36 L14 28 L22 43 L28 40 L20 25 L33 24 Z" fill="#173b6d" stroke="#ffffff" stroke-width="2.5"/></svg><div id="click-ring"></div></div></div>'
html=f'<!doctype html><html lang="es"><head><meta charset="utf-8"><title>PULSE CRM — 30 segundos · Light mode</title><script src="assets/gsap.min.js"></script><style>{css}</style></head><body><div id="root" data-composition-id="pulse-crm" data-start="0" data-duration="30" data-width="1920" data-height="1080" data-fps="30">'+''.join(scenes)+texts+cursor+f'</div><script>{js}</script></body></html>'
(base/'index.html').write_text(html)
(base/'index.motion.json').write_text(json.dumps({'duration':30,'assertions':[{'kind':'appearsBy','selector':'#opening-logo','bySec':0.5},*[{'kind':'staysInFrame','selector':'#'+i} for i,t,a,b,c,d,y in overlays],{'kind':'staysInFrame','selector':'#closing-logo'}]},indent=2)+'\n')
(base/'timing.json').write_text(json.dumps({'duration':30,'fps':30,'frames':900,'width':1920,'height':1080,'theme':'light','audio':'none','sceneBoundaries':[0,2.5,6,11,16,22,27,30],'overlays':[{'id':i,'copy':t,'in':[a,b],'hold':[b,c],'out':[c,d]} for i,t,a,b,c,d,y in overlays]},indent=2)+'\n')
print('Built 30s composition with local GSAP, Manrope and real UI crops.')
