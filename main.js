/**
 * main.js – BioBreeder 3D · Multiplayer Edition
 * Trades · Online-Spieler · Benachrichtigungen-Polling · Verhandlung
 */
'use strict';

// ═══ MOBILE ═══════════════════════════════════════════════════
const MOBILE = /Android|iPhone|iPad|iPod|IEMobile|Opera Mini/i.test(navigator.userAgent)
             || 'ontouchstart' in window || navigator.maxTouchPoints > 0;

// ═══ STATE ════════════════════════════════════════════════════
const State = {
  eingeloggt:false, spielerName:'',
  blaetter:0, coins:0, inventar:[],
  meineTiere:[], wildeTiere:[], collectibles:[],
  breedSlots:[null,null],
  activePanel:null, totalBreeds:0,
  pointerLocked:false, notifTimer:null,
  verhandlung:null,
  onlineSpieler:[],
  tradeTarget:null,
  meineTrades:[],
};

// ═══ RANG-SYSTEM ══════════════════════════════════════════════
const STUFEN=[
  // Wild-Ränge (1–100)
  {lo:1,   hi:10,  name:"Gewöhnlich",     farbe:"#aaaaaa"},
  {lo:11,  hi:20,  name:"Ungewöhnlich",   farbe:"#55dd55"},
  {lo:21,  hi:30,  name:"Selten",         farbe:"#4499ff"},
  {lo:31,  hi:40,  name:"Episch",         farbe:"#bb44ff"},
  {lo:41,  hi:50,  name:"Legendär",       farbe:"#ffaa00"},
  {lo:51,  hi:60,  name:"Mythisch",       farbe:"#ff5555"},
  {lo:61,  hi:70,  name:"Antik",          farbe:"#00ddff"},
  {lo:71,  hi:80,  name:"Göttlich",       farbe:"#ffee22"},
  {lo:81,  hi:90,  name:"Transzendent",   farbe:"#ff44ff"},
  {lo:91,  hi:100, name:"Absolut",        farbe:"#ffffff"},
  // Zücht-Ränge (101–1000) – nur durch Züchten erreichbar
  {lo:101, hi:200, name:"Übernatürlich",  farbe:"#ff8833"},
  {lo:201, hi:300, name:"Kosmisch",       farbe:"#00ffcc"},
  {lo:301, hi:400, name:"Dimensional",    farbe:"#cc44ff"},
  {lo:401, hi:500, name:"Celestiell",     farbe:"#4488ff"},
  {lo:501, hi:600, name:"Uralt",          farbe:"#ff3300"},
  {lo:601, hi:700, name:"Ewig",           farbe:"#44ff99"},
  {lo:701, hi:800, name:"Primordial",     farbe:"#ffdd33"},
  {lo:801, hi:900, name:"Götterkind",     farbe:"#ff55ff"},
  {lo:901, hi:999, name:"Schöpfer",       farbe:"#aaddff"},
  {lo:1000,hi:1000,name:"PatTat",         farbe:"#ffd700"},
];
function rangInfo(rang){
  rang=Math.max(1,Math.min(1000,rang||1));
  return {...(STUFEN.find(s=>rang>=s.lo&&rang<=s.hi)||STUFEN[0]),rang};
}
function selCls(stufe){
  return {
    Gewöhnlich:'sel-g', Ungewöhnlich:'sel-u', Selten:'sel-s', Episch:'sel-e',
    Legendär:'sel-l',   Mythisch:'sel-m',     Antik:'sel-a',  Göttlich:'sel-go',
    Transzendent:'sel-tr', Absolut:'sel-ab',
    Übernatürlich:'sel-un', Kosmisch:'sel-ko', Dimensional:'sel-di',
    Celestiell:'sel-ce',    Uralt:'sel-ur',    Ewig:'sel-ew',
    Primordial:'sel-pr',    Götterkind:'sel-gk', Schöpfer:'sel-sc',
    PatTat:'sel-pt',
  }[stufe]||'';
}

// ═══ THREE.JS SETUP ═══════════════════════════════════════════
const container=document.getElementById('game-container');
const renderer=new THREE.WebGLRenderer({antialias:true,powerPreference:'high-performance'});
renderer.setPixelRatio(Math.min(window.devicePixelRatio,2));
renderer.setSize(innerWidth,innerHeight);
renderer.shadowMap.enabled=true; renderer.shadowMap.type=THREE.PCFSoftShadowMap;
container.appendChild(renderer.domElement);
const scene=new THREE.Scene();
scene.background=new THREE.Color(0x6ab8e8); scene.fog=new THREE.Fog(0x8dcfee,40,150);
const camera=new THREE.PerspectiveCamera(75,innerWidth/innerHeight,.1,400);
camera.position.set(0,3,0); camera.rotation.order='YXZ';
window.addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight);});
scene.add(new THREE.AmbientLight(0xfff0dd,.65));
const sun=new THREE.DirectionalLight(0xfffde0,1.3);
sun.position.set(60,90,40);sun.castShadow=true;
sun.shadow.mapSize.set(MOBILE?1024:2048,MOBILE?1024:2048);
Object.assign(sun.shadow.camera,{near:.5,far:220,left:-90,right:90,top:90,bottom:-90});
scene.add(sun); scene.add(new THREE.HemisphereLight(0x6ab8e8,0x4a7a20,.4));

// ═══ TERRAIN ══════════════════════════════════════════════════
function terrainH(x,z){return Math.sin(x*.05)*3.5+Math.sin(z*.07)*2.5+Math.sin(x*.13+z*.11)*1.5+Math.cos(x*.09-z*.08)*1.2+Math.sin(x*.25+z*.22)*.4;}
(function(){
  const geo=new THREE.PlaneGeometry(240,240,110,110),pos=geo.attributes.position;
  const col=new Float32Array(pos.count*3);
  for(let i=0;i<pos.count;i++){const wx=pos.getX(i),wz=-pos.getY(i),h=terrainH(wx,wz);pos.setZ(i,h);const t=(h+5)/12;col[i*3]=.22+t*.22;col[i*3+1]=.45+t*.25;col[i*3+2]=.12+t*.1;}
  geo.computeVertexNormals(); geo.setAttribute('color',new THREE.BufferAttribute(col,3));
  const m=new THREE.Mesh(geo,new THREE.MeshLambertMaterial({vertexColors:true}));m.rotation.x=-Math.PI/2;m.receiveShadow=true;scene.add(m);
})();
for(let i=0;i<50;i++){const x=(Math.random()-.5)*200,z=(Math.random()-.5)*200;if(Math.abs(x)>6||Math.abs(z)>6){const g=new THREE.Group(),h=terrainH(x,z),tH=4+Math.random()*4;const tr=new THREE.Mesh(new THREE.CylinderGeometry(.28,.55,tH,7),new THREE.MeshLambertMaterial({color:0x7a5030}));tr.position.y=tH/2;tr.castShadow=true;g.add(tr);const lm=new THREE.MeshLambertMaterial({color:new THREE.Color().setHSL(.28+Math.random()*.12,.62,.3+Math.random()*.2)});for(let j=0;j<4;j++){const lf=new THREE.Mesh(new THREE.SphereGeometry(1.2+Math.random()*1.5,7,5),lm);lf.position.set((Math.random()-.5)*2.6,tH*.65+j*1.1+Math.random()*.5,(Math.random()-.5)*2.6);lf.castShadow=true;g.add(lf);}g.position.set(x,h,z);scene.add(g);}}

function spawnLeaf(x,z){const g=new THREE.Group();const b=new THREE.Mesh(new THREE.SphereGeometry(.28,8,6),new THREE.MeshLambertMaterial({color:0x44cc44,emissive:0x114411}));b.castShadow=true;g.add(b);const r=new THREE.Mesh(new THREE.TorusGeometry(.45,.04,6,16),new THREE.MeshLambertMaterial({color:0xaaff88,emissive:0x336633}));r.rotation.x=Math.PI/2;g.add(r);g.position.set(x,terrainH(x,z)+1.0,z);scene.add(g);return{mesh:g,x,z,dead:false,phase:Math.random()*Math.PI*2};}
for(let i=0;i<35;i++){const x=(Math.random()-.5)*180,z=(Math.random()-.5)*180;State.collectibles.push(spawnLeaf(x,z));}

// ═══ TIER-RENDERING ═══════════════════════════════════════════
function rgb3(c){return(c[0]<<16)|(c[1]<<8)|c[2];}
function buildTierMesh(tier){
  const g=new THREE.Group(),gn=tier.genetik,s=gn.groesse;
  const cy=(rT,rB,h,seg=6)=>new THREE.CylinderGeometry(rT,rB,h,seg);
  const bm=new THREE.MeshLambertMaterial({color:rgb3(gn.koerper_farbe)});
  const vm=new THREE.MeshLambertMaterial({color:rgb3(gn.bauch_farbe)});
  const em=new THREE.MeshLambertMaterial({color:rgb3(gn.ohr_farbe)});
  const nm=new THREE.MeshLambertMaterial({color:0x110500});
  const ey=new THREE.MeshLambertMaterial({color:0x0a0505});
  const sh=new THREE.MeshLambertMaterial({color:0xffffff});
  const art=tier.art.split('-')[0];
  const scX=art==='Fuchs'?.75:art==='Huhn'?.65:1,scZ=art==='Fuchs'?1.6:art==='Huhn'?1.3:1;
  const body=new THREE.Mesh(new THREE.SphereGeometry(.52*s,12,9),bm);body.scale.set(scX,1,scZ);body.castShadow=true;g.add(body);
  const belly=new THREE.Mesh(new THREE.SphereGeometry(.34*s,10,7),vm);belly.position.set(0,-.05*s,.3*s*scZ);belly.scale.z=.45;g.add(belly);
  const hs=.38*s*gn.rundheit;const head=new THREE.Mesh(new THREE.SphereGeometry(hs,12,9),bm);head.position.y=.78*s;head.castShadow=true;g.add(head);
  const ea=gn.ohr_groesse*.22*s;
  for(const sd of[-1,1]){const ear=new THREE.Mesh(new THREE.SphereGeometry(ea,8,6),bm);ear.position.set(sd*.27*s,1.08*s,-.03*s);ear.scale.y=1.25+gn.flauschig*.2;ear.castShadow=true;g.add(ear);const inn=new THREE.Mesh(new THREE.SphereGeometry(ea*.58,7,5),em);inn.position.set(sd*.27*s,1.08*s,ea*.55);inn.scale.y=1.2;g.add(inn);}
  const nose=new THREE.Mesh(new THREE.SphereGeometry(.1*s,7,5),nm);nose.position.set(0,.74*s,.33*s);nose.scale.set(1.5,.9,.65);g.add(nose);
  for(const sd of[-1,1]){const eye=new THREE.Mesh(new THREE.SphereGeometry(.065*s,6,5),ey);eye.position.set(sd*.16*s,.83*s,.29*s);g.add(eye);const gln=new THREE.Mesh(new THREE.SphereGeometry(.024*s,4,4),sh);gln.position.set(sd*.165*s+sd*.018,.845*s,.34*s);g.add(gln);}
  for(const sd of[-1,1]){const arm=new THREE.Mesh(cy(.09*s,.08*s,.48*s),bm);arm.position.set(sd*.57*s,.1*s,.1*s);arm.rotation.z=sd*.6;arm.castShadow=true;g.add(arm);const leg=new THREE.Mesh(cy(.12*s,.1*s,.44*s),bm);leg.position.set(sd*.22*s,-.56*s,.06*s);leg.rotation.x=.28;leg.castShadow=true;g.add(leg);}
  const tail=new THREE.Mesh(new THREE.SphereGeometry(.1*s,6,5),bm);tail.position.set(0,-.1*s,-.5*s);g.add(tail);
  const rang=gn.rang||1;
  if(rang>=41){const info=rangInfo(rang);const c=new THREE.Color(info.farbe);const glow=new THREE.PointLight(c,.3+(rang-40)/120,5);glow.position.set(0,.5*s,0);g.add(glow);}
  return g;
}
function drawTier2D(cv,tier){
  const ctx=cv.getContext('2d'),w=cv.width,h=cv.height,gn=tier.genetik;
  ctx.clearRect(0,0,w,h);
  const bg=ctx.createRadialGradient(w/2,h/2,2,w/2,h/2,w/2);bg.addColorStop(0,'rgba(80,50,20,.3)');bg.addColorStop(1,'rgba(0,0,0,0)');ctx.fillStyle=bg;ctx.beginPath();ctx.arc(w/2,h/2,w/2,0,Math.PI*2);ctx.fill();
  const c=a=>`rgb(${a[0]},${a[1]},${a[2]})`,cx=w/2,cy=h/2+5,s=gn.groesse*14;
  ctx.fillStyle=c(gn.koerper_farbe);ctx.beginPath();ctx.ellipse(cx,cy+s*.25,s*.92,s,0,0,Math.PI*2);ctx.fill();
  ctx.fillStyle=c(gn.bauch_farbe);ctx.beginPath();ctx.ellipse(cx,cy+s*.35,s*.52,s*.65,0,0,Math.PI*2);ctx.fill();
  const hs=s*.72*gn.rundheit;ctx.fillStyle=c(gn.koerper_farbe);ctx.beginPath();ctx.ellipse(cx,cy-s*.72,hs,hs*.96,0,0,Math.PI*2);ctx.fill();
  const ea=gn.ohr_groesse*s*.4;
  for(const sd of[-1,1]){ctx.fillStyle=c(gn.koerper_farbe);ctx.beginPath();ctx.ellipse(cx+sd*hs*.82,cy-s*1.18,ea,ea*1.15,0,0,Math.PI*2);ctx.fill();ctx.fillStyle=c(gn.ohr_farbe);ctx.beginPath();ctx.ellipse(cx+sd*hs*.82,cy-s*1.18,ea*.55,ea*.72,0,0,Math.PI*2);ctx.fill();}
  ctx.fillStyle='#110600';ctx.beginPath();ctx.ellipse(cx,cy-s*.62,s*.2,s*.13,0,0,Math.PI*2);ctx.fill();
  for(const sd of[-1,1]){ctx.fillStyle='#0a0505';ctx.beginPath();ctx.arc(cx+sd*hs*.4,cy-s*.79,s*.1,0,Math.PI*2);ctx.fill();ctx.fillStyle='#fff';ctx.beginPath();ctx.arc(cx+sd*hs*.4+sd*1.5,cy-s*.81,s*.04,0,Math.PI*2);ctx.fill();}
  const rang=gn.rang||1;
  if(rang>=41){const info=rangInfo(rang);ctx.shadowBlur=16;ctx.shadowColor=info.farbe;ctx.beginPath();ctx.arc(cx,cy,s*.5,0,Math.PI*2);ctx.strokeStyle=info.farbe+'66';ctx.lineWidth=3;ctx.stroke();ctx.shadowBlur=0;}
}

// ═══ WILD-TIERE SPAWNEN ════════════════════════════════════════
async function spawnWild(){
  const res=await API.getTiere();if(!res.ok)return;
  const wildDB=res.tiere.filter(t=>!t.besitzer);const zuNehmen=wildDB.slice(0,7);
  for(let i=zuNehmen.length;i<7;i++){const r=await API.neuesWildtier();if(r.ok)zuNehmen.push(r.tier);}
  for(const k of zuNehmen){const x=(Math.random()-.5)*130,z=(Math.random()-.5)*130;if(Math.abs(x)<6&&Math.abs(z)<6)continue;const mesh=buildTierMesh(k);mesh.position.set(x,terrainH(x,z)+.52*k.genetik.groesse,z);scene.add(mesh);k.mesh=mesh;k.tx=x;k.tz=z;k.wt=Math.random()*4;State.wildeTiere.push(k);}
}

// ═══ HUD ══════════════════════════════════════════════════════
function updateHUD(){
  document.getElementById('hud-blaetter').textContent=State.blaetter;
  document.getElementById('hud-coins').textContent=State.coins;
  document.getElementById('hud-tiere').textContent=State.meineTiere.length;
  document.getElementById('hud-name').textContent=State.spielerName;
}

// ═══ STEUERUNG ════════════════════════════════════════════════
const keys={},joyVec={x:0,y:0};
let camYaw=0,camPitch=0,velY=0,onGround=true,isSprinting=false;
let joyTouch=null,joyOrigin={x:0,y:0};const camTouches={};
const EYE_H=1.72,SPEED=8,GRAVITY=-22;

function initMobileUI(){
  document.getElementById('mobile-controls').style.display=MOBILE?'block':'none';
  document.getElementById('controls-hint').style.display=MOBILE?'none':'block';
}

const joyZone=document.getElementById('joy-zone'),joyRing=document.getElementById('joy-ring'),joyNub=document.getElementById('joy-nub');
joyZone.addEventListener('touchstart',e=>{e.preventDefault();for(const t of e.changedTouches){if(joyTouch!==null)continue;joyTouch=t.identifier;const r=joyZone.getBoundingClientRect();joyOrigin={x:t.clientX-r.left,y:t.clientY-r.top};joyRing.style.cssText=`display:block;left:${joyOrigin.x-50}px;top:${joyOrigin.y-50}px;`;joyNub.style.cssText=`display:block;left:${joyOrigin.x-20}px;top:${joyOrigin.y-20}px;`;}},{passive:false});
joyZone.addEventListener('touchmove',e=>{e.preventDefault();for(const t of e.changedTouches){if(t.identifier!==joyTouch)continue;const r=joyZone.getBoundingClientRect();let dx=(t.clientX-r.left)-joyOrigin.x,dy=(t.clientY-r.top)-joyOrigin.y;const d=Math.sqrt(dx*dx+dy*dy);if(d>50){dx=dx/d*50;dy=dy/d*50;}joyVec.x=dx/50;joyVec.y=dy/50;joyNub.style.left=(joyOrigin.x+dx-20)+'px';joyNub.style.top=(joyOrigin.y+dy-20)+'px';}},{passive:false});
function joyEnd(e){for(const t of e.changedTouches)if(t.identifier===joyTouch){joyTouch=null;joyVec.x=0;joyVec.y=0;joyRing.style.display='none';joyNub.style.display='none';}}
joyZone.addEventListener('touchend',joyEnd,{passive:false});joyZone.addEventListener('touchcancel',joyEnd,{passive:false});
const camZone=document.getElementById('cam-zone');
camZone.addEventListener('touchstart',e=>{e.preventDefault();for(const t of e.changedTouches)camTouches[t.identifier]={x:t.clientX,y:t.clientY};},{passive:false});
camZone.addEventListener('touchmove',e=>{e.preventDefault();for(const t of e.changedTouches){const p=camTouches[t.identifier];if(!p)continue;camYaw-=(t.clientX-p.x)*.004;camPitch-=(t.clientY-p.y)*.004;camPitch=Math.max(-Math.PI/2.1,Math.min(Math.PI/2.1,camPitch));camTouches[t.identifier]={x:t.clientX,y:t.clientY};}},{passive:false});
function camEnd(e){for(const t of e.changedTouches)delete camTouches[t.identifier];}
camZone.addEventListener('touchend',camEnd,{passive:false});camZone.addEventListener('touchcancel',camEnd,{passive:false});
document.getElementById('btn-jump')?.addEventListener('touchstart',e=>{e.preventDefault();if(onGround){velY=9.5;onGround=false;}},{passive:false});
document.getElementById('btn-interact')?.addEventListener('touchstart',e=>{e.preventDefault();interact();},{passive:false});
document.getElementById('btn-sprint')?.addEventListener('touchstart',e=>{e.preventDefault();isSprinting=true;},{passive:false});
document.getElementById('btn-sprint')?.addEventListener('touchend',e=>{e.preventDefault();isSprinting=false;},{passive:false});
renderer.domElement.addEventListener('click',()=>{if(!MOBILE&&!State.activePanel&&State.eingeloggt)renderer.domElement.requestPointerLock?.();});
document.addEventListener('pointerlockchange',()=>{State.pointerLocked=document.pointerLockElement===renderer.domElement;const lp=document.getElementById('lock-prompt');if(lp)lp.classList.toggle('show',!State.pointerLocked&&!State.activePanel&&!MOBILE);});
document.addEventListener('mousemove',e=>{if(!State.pointerLocked)return;camYaw-=e.movementX*.002;camPitch-=e.movementY*.002;camPitch=Math.max(-Math.PI/2.05,Math.min(Math.PI/2.05,camPitch));});
document.addEventListener('keydown',e=>{
  keys[e.code]=true;
  if(e.code==='KeyE')interact();
  if(e.code==='Tab'){e.preventDefault();togglePanel('zucht');}
  if(e.code==='Space'&&onGround){velY=9.5;onGround=false;}
  if(e.code==='Escape')closePanel();
});
document.addEventListener('keyup',e=>keys[e.code]=false);

// ═══ INTERAKTION ══════════════════════════════════════════════
async function interact(){
  if(!State.eingeloggt)return;
  const px=camera.position.x,pz=camera.position.z;
  for(const item of State.collectibles){if(item.dead)continue;if((item.x-px)**2+(item.z-pz)**2<8){item.dead=true;scene.remove(item.mesh);const res=await API.blattSammeln();if(res.ok){State.blaetter=res.blaetter;State.coins=res.coins;updateHUD();}notify('🌿 Blatt! ('+State.blaetter+')');setTimeout(()=>{const nx=(Math.random()-.5)*180,nz=(Math.random()-.5)*180;State.collectibles.push(spawnLeaf(nx,nz));},20000);return;}}
  for(const k of State.wildeTiere){if(!k.mesh)continue;if((k.mesh.position.x-px)**2+(k.mesh.position.z-pz)**2<20){if(State.blaetter<3){notify('❌ 3 🌿 benötigt!');return;}const res=await API.zaehmen(k.id);if(!res.ok){notify('❌ '+res.fehler);return;}scene.remove(k.mesh);State.wildeTiere.splice(State.wildeTiere.indexOf(k),1);State.blaetter=res.user.blaetter;State.coins=res.user.coins;State.meineTiere.push(res.tier);updateHUD();const info=rangInfo(res.tier.genetik.rang||1);notify(`🐾 <strong>${res.tier.name}</strong> gezähmt! <span style="color:${info.farbe}">Rang ${info.rang}</span>`);setTimeout(async()=>{const r=await API.neuesWildtier();if(!r.ok)return;const nx=(Math.random()-.5)*120,nz=(Math.random()-.5)*120;const mesh=buildTierMesh(r.tier);mesh.position.set(nx,terrainH(nx,nz)+.52*r.tier.genetik.groesse,nz);scene.add(mesh);r.tier.mesh=mesh;r.tier.tx=nx;r.tier.tz=nz;r.tier.wt=Math.random()*4;State.wildeTiere.push(r.tier);},25000);return;}}
}

function checkHints(){
  if(!State.eingeloggt)return;const px=camera.position.x,pz=camera.position.z;let msg='';
  for(const item of State.collectibles){if(item.dead)continue;if((item.x-px)**2+(item.z-pz)**2<9){msg=MOBILE?'✋ Blatt 🌿':'<strong>E</strong> · Blatt sammeln 🌿';break;}}
  if(!msg)for(const k of State.wildeTiere){if(!k.mesh)continue;if((k.mesh.position.x-px)**2+(k.mesh.position.z-pz)**2<20){msg=(MOBILE?'✋':'<strong>E</strong>')+` · ${k.emoji||'🐾'} ${k.name} zähmen`;break;}}
  const el=document.getElementById('hint');el.innerHTML=msg;el.classList.toggle('show',!!msg);
}

// ═══ PANELS ═══════════════════════════════════════════════════
function togglePanel(name){
  if(State.activePanel===name){closePanel();return;}
  State.activePanel=name;
  document.querySelectorAll('.side-panel').forEach(p=>p.classList.remove('open'));
  document.getElementById('panel-'+name)?.classList.add('open');
  if(!MOBILE&&State.pointerLocked)document.exitPointerLock();
  if(name==='zucht')     renderZuchtPanel();
  if(name==='markt')     renderMarktPanel();
  if(name==='stammbaum') renderStammbaumPanel();
  if(name==='trades')    renderTradePanel();
  if(name==='chat')      renderChatPanel();
}
function closePanel(){
  State.activePanel=null;
  document.querySelectorAll('.side-panel').forEach(p=>p.classList.remove('open'));
  if(!MOBILE)renderer.domElement.requestPointerLock?.();
}

// ─── ZUCHT ────────────────────────────────────────────────────
function renderZuchtPanel(){
  const maxGen=State.meineTiere.reduce((m,k)=>Math.max(m,k.generation||0),0);
  document.getElementById('zucht-stats').innerHTML=`<span>🐾 ${State.meineTiere.length}</span><span>🧬 Gen.${maxGen}</span><span>🔬 ${State.totalBreeds}</span>`;
  const grid=document.getElementById('zucht-grid');
  if(!State.meineTiere.length){grid.innerHTML='<div class="empty-msg">Zähme Wildtiere!<br>🌿 3 Blätter = 1 Tier</div>';return;}
  grid.innerHTML='';
  const sorted=[...State.meineTiere].sort((a,b)=>(b.genetik.rang||1)-(a.genetik.rang||1));
  for(const k of sorted){
    const info=rangInfo(k.genetik.rang||1);
    const card=document.createElement('div');card.className='tier-card'+(State.breedSlots.some(s=>s?.id===k.id)?' selected':'');
    const gn=k.genetik;
    const traits=gn.staerke?`<div class="tier-traits"><span title="Stärke">⚔️${gn.staerke}</span><span title="Intelligenz">🧠${gn.intelligenz}</span><span title="Ausdauer">🏃${gn.ausdauer}</span><span title="Glück">🍀${gn.glueck}</span></div>`:'';
    card.innerHTML=`<div class="tcv"><canvas width="68" height="68"></canvas></div><div class="tname">${k.name}</div><div class="tgen">${k.generation===0?'🌿 Wild':'🧬 Gen.'+k.generation}</div><div class="rang-badge-small ${selCls(info.name)}" style="border-color:${info.farbe};color:${info.farbe}">Rang ${info.rang} · ${info.name}</div>${traits}<div class="tart">${k.emoji||'🐾'} ${k.art}</div>`;
    drawTier2D(card.querySelector('canvas'),k);
    card.addEventListener('click',()=>waehleFuerZucht(k));
    grid.appendChild(card);
  }
  refreshSlots();
}
function waehleFuerZucht(k){const s=State.breedSlots;if(s[0]?.id===k.id)s[0]=null;else if(s[1]?.id===k.id)s[1]=null;else if(!s[0])s[0]=k;else if(!s[1])s[1]=k;else{s[0]=s[1];s[1]=k;}renderZuchtPanel();}
function refreshSlots(){
  for(const[i,elId]of[[0,'slot1'],[1,'slot2']]){const el=document.getElementById(elId),k=State.breedSlots[i];if(k){const cv=document.createElement('canvas');cv.width=66;cv.height=66;drawTier2D(cv,k);el.innerHTML='';el.appendChild(cv);el.classList.add('filled');}else{el.innerHTML=`<span>Elternteil ${i+1}</span>`;el.classList.remove('filled');}}
  const prev=document.getElementById('breed-preview');const[p1,p2]=State.breedSlots;
  if(p1&&p2&&prev){
    const r1=p1.genetik.rang||1,r2=p2.genetik.rang||1;
    const lo=Math.max(1,Math.min(r1,r2)-5),hi=Math.min(100,Math.max(r1,r2)+8);
    const loI=rangInfo(lo),hiI=rangInfo(hi);
    const kosten=Math.max(1,Math.min(10,Math.ceil((r1+r2)/20)));
    const genug=State.blaetter>=kosten;
    prev.innerHTML=`<div class="breed-hint">Mögl.: <span style="color:${loI.farbe}">Rang ${lo}</span>–<span style="color:${hiI.farbe}">${hi}</span></div><div class="breed-kosten ${genug?'':'breed-kosten-warn'}">🌿 ${kosten} Blatt${kosten>1?'e':''} ${genug?'':'⚠️ zu wenig'}</div>`;
    prev.style.display='block';
    const btn=document.getElementById('zuecht-btn');
    btn.disabled=!genug;
    btn.textContent=genug?`🧬 Züchten (${kosten} 🌿)`:'❌ Nicht genug Blätter';
  }else if(prev){
    prev.style.display='none';
    const btn=document.getElementById('zuecht-btn');
    btn.disabled=true;btn.textContent='🧬 Züchten!';
  }
}
window.clearSlot=i=>{State.breedSlots[i]=null;refreshSlots();renderZuchtPanel();};
window.doBreed=async()=>{
  const[p1,p2]=State.breedSlots;if(!p1||!p2){notify('❌ Zwei Elterntiere auswählen!');return;}
  const btn=document.getElementById('zuecht-btn');btn.disabled=true;btn.textContent='🥚 Züchtet...';
  try{
    const res=await API.zuechten(p1.id,p2.id);
    if(!res.ok){notify('❌ '+(res.fehler||'Fehler beim Züchten'));btn.disabled=false;refreshSlots();return;}
    State.meineTiere.push(res.baby);State.blaetter=res.user.blaetter;State.coins=res.user.coins;
    State.totalBreeds++;State.breedSlots=[null,null];updateHUD();renderZuchtPanel();
    const info=rangInfo(res.baby.genetik.rang||1);
    const mut=res.baby.meta?.mutation?' ⚡ MUTATION!':'';
    notify(`🥚 ${res.baby.name} · <span style="color:${info.farbe}">Rang ${info.rang} ${info.name}</span>${mut}`);
  }catch(e){
    // Server hat kein gültiges JSON geliefert – echten Fehler loggen
    console.error('Breed error:', e);
    notify('❌ Serverfehler – prüfe die Konsole (F12)');
    btn.disabled=false;refreshSlots();
  }
};

// ─── MARKT ────────────────────────────────────────────────────
async function renderMarktPanel(){
  const list=document.getElementById('markt-list');
  list.innerHTML='<div class="loading">Lade Marktplatz…</div>';
  const res=await API.getMarkt();if(!res.ok){list.innerHTML='<div class="empty-msg">Fehler</div>';return;}
  list.innerHTML='';

  const botAng=res.angebote.filter(t=>t.markt_von==='MarktBot');
  const meineAng=res.angebote.filter(t=>t.markt_von===State.spielerName);
  const andereAng=res.angebote.filter(t=>t.markt_von!=='MarktBot'&&t.markt_von!==State.spielerName);

  function addSection(title,items,meinEigenes){
    if(!items.length)return;
    const sec=document.createElement('div');sec.innerHTML=`<div class="markt-section-title">${title}</div>`;list.appendChild(sec);
    for(const t of items)list.appendChild(makeMarktCard(t,t.markt_von==='MarktBot',meinEigenes));
  }
  addSection('🤖 MarktBot',botAng,false);
  addSection('👤 Andere Spieler',andereAng,false);
  addSection('📦 Meine Angebote',meineAng,true);

  if(!res.angebote.length)list.innerHTML+='<div class="empty-msg">Keine Angebote</div>';

  // Eigene Tiere einstellen
  if(State.meineTiere.length){
    const sec=document.createElement('div');sec.className='sell-section';
    sec.innerHTML='<div class="markt-section-title">➕ Tier einstellen</div>';
    for(const t of State.meineTiere){
      const info=rangInfo(t.genetik.rang||1);const basis=t.basis_preis||info.rang*10;
      const row=document.createElement('div');row.className='sell-row';
      row.innerHTML=`<span class="sell-name">${t.emoji||'🐾'} ${t.name}</span><span class="sell-rang" style="color:${info.farbe}">Rang ${info.rang}</span><input type="number" value="${basis}" min="1" max="99999" id="preis-${t.id}" class="sell-input"><button class="sell-btn" onclick="verkaufeTier('${t.id}')">Einstellen</button>`;
      sec.appendChild(row);
    }
    list.appendChild(sec);
  }
}

function makeMarktCard(t,istBot,istMeins){
  const card=document.createElement('div');card.className='markt-card';
  const cv=document.createElement('canvas');cv.width=62;cv.height=62;drawTier2D(cv,t);
  const info=rangInfo(t.genetik.rang||1);
  let buttons='';
  if(istMeins){
    buttons=`<button class="m-back" onclick="zurueckziehen('${t.id}')">↩ Zurück</button>`;
  } else if(istBot){
    buttons=`<button class="m-buy" onclick="kaufeTier('${t.id}')">Kaufen</button><button class="m-neg" onclick="startVerhandlung('${t.id}',${t.markt_preis})">Verhandeln</button>`;
  } else {
    // Anderer Spieler
    buttons=`<button class="m-buy" onclick="kaufeTier('${t.id}')">Kaufen</button><button class="m-neg" onclick="startVerhandlung('${t.id}',${t.markt_preis})">Verhandeln</button><button class="m-trade" onclick="startTradeAngebot('${t.markt_von}','${t.id}')">🔄 Tausch</button>`;
  }
  card.innerHTML=`<div class="m-img"></div><div class="m-info"><div class="m-name">${t.emoji||'🐾'} ${t.name}</div><div class="m-rang" style="color:${info.farbe}">Rang ${info.rang} · ${info.name}</div><div class="m-art">${t.art}</div><div class="m-von">${istBot?'🤖 MarktBot':istMeins?'📦 Dein Angebot':'👤 '+t.markt_von}</div></div><div class="m-right"><div class="m-price">💰 ${t.markt_preis}</div>${buttons}</div>`;
  card.querySelector('.m-img').appendChild(cv);
  return card;
}

window.kaufeTier=async id=>{const res=await API.marktKaufen(id);if(!res.ok){notify('❌ '+res.fehler);return;}State.coins=res.user.coins;State.meineTiere.push(res.tier);updateHUD();renderMarktPanel();notify('🛍️ <strong>'+res.tier.name+'</strong> gekauft!');};
window.verkaufeTier=async id=>{const inp=document.getElementById('preis-'+id);const preis=parseInt(inp?.value||'50');const res=await API.marktEinstellen(id,preis);if(!res.ok){notify('❌ '+res.fehler);return;}State.meineTiere=State.meineTiere.filter(t=>t.id!==id);updateHUD();renderMarktPanel();notify('📦 Eingestellt für 💰 '+preis);};
window.zurueckziehen=async id=>{const res=await API.marktZurueckziehen(id);if(!res.ok){notify('❌ '+res.fehler);return;}const tr=await API.getTiere();if(tr.ok){const tier=tr.tiere.find(t=>t.id===id);if(tier)State.meineTiere.push(tier);}updateHUD();renderMarktPanel();notify('↩ Tier zurückgezogen');};

// ─── VERHANDLUNG ──────────────────────────────────────────────
window.startVerhandlung=async function(tierId,listenpreis){
  const tr=await API.getTiere();if(!tr.ok)return;
  const tier=tr.tiere.find(t=>t.id===tierId);if(!tier)return;
  State.verhandlung={tier,listenpreis};
  // Server-Session initialisieren
  await API.verhandlungStarten(tierId);
  const info=rangInfo(tier.genetik.rang||1);
  document.getElementById('vhd-name').textContent=tier.name;
  document.getElementById('vhd-rang').textContent=`Rang ${info.rang} · ${info.name}`;
  document.getElementById('vhd-rang').style.color=info.farbe;
  document.getElementById('vhd-listenpreis').textContent=listenpreis;
  document.getElementById('vhd-von').textContent=tier.markt_von==='MarktBot'?'🤖 MarktBot':'👤 '+tier.markt_von;
  drawTier2D(document.getElementById('vhd-canvas'),tier);
  document.getElementById('vhd-gebot').value=Math.round(listenpreis*.82);
  document.getElementById('vhd-nachricht').textContent='💬 Mach dein erstes Angebot!';
  document.getElementById('vhd-accept-box').style.display='none';
  document.getElementById('vhd-runden').textContent='Runde 1';
  document.getElementById('verhandlung-modal').classList.add('open');
};
window.closeVerhandlung=()=>{document.getElementById('verhandlung-modal').classList.remove('open');State.verhandlung=null;};
window.sendeAngebot=async()=>{
  if(!State.verhandlung)return;
  const gebot=parseInt(document.getElementById('vhd-gebot').value||'0');
  const btn=document.querySelector('.vhd-send-btn');btn.disabled=true;btn.textContent='…';
  const res=await API.verhandlungAngebot(State.verhandlung.tier.id,gebot);
  btn.disabled=false;btn.textContent='Bieten ▶';
  document.getElementById('vhd-nachricht').textContent=res.nachricht||'Fehler';
  if(res.runde) document.getElementById('vhd-runden').textContent=`Runde ${res.runde}`;
  if(!res.ok)return;

  if(res.ergebnis==='angenommen'){
    const ab=await API.verhandlungAbschluss(State.verhandlung.tier.id,res.endpreis);
    if(ab.ok){State.coins=ab.user.coins;State.meineTiere.push(ab.tier);updateHUD();closeVerhandlung();renderMarktPanel();notify(`🤝 Deal! <strong>${ab.tier.name}</strong> für 💰 ${res.endpreis}!`);}
    else document.getElementById('vhd-nachricht').textContent='❌ '+ab.fehler;
  } else if(res.ergebnis==='abgebrochen'){
    setTimeout(()=>closeVerhandlung(),2800);
  } else if(res.ergebnis==='gegenangebot'||res.ergebnis==='letztes_angebot'){
    const box=document.getElementById('vhd-accept-box');box.style.display='block';
    const istLetzes=res.ergebnis==='letztes_angebot';
    document.getElementById('vhd-accept-price').textContent=res.gegenangebot;
    document.getElementById('vhd-accept-label').textContent=istLetzes?'⚠️ Letztes Angebot:':'Gegenangebot:';
    document.getElementById('vhd-accept-btn').onclick=()=>akzeptiereGegenangebot(res.gegenangebot);
    document.getElementById('vhd-gebot').value=Math.round(res.gegenangebot*.99);
    if(istLetzes){box.style.background='rgba(200,100,30,.2)';box.style.borderColor='rgba(240,150,60,.4)';}
    else{box.style.background='rgba(80,180,60,.15)';box.style.borderColor='rgba(80,200,60,.35)';}
  }
};
async function akzeptiereGegenangebot(preis){
  if(!State.verhandlung)return;
  const res=await API.verhandlungAbschluss(State.verhandlung.tier.id,preis);
  if(res.ok){State.coins=res.user.coins;State.meineTiere.push(res.tier);updateHUD();closeVerhandlung();renderMarktPanel();notify(`🤝 <strong>${res.tier.name}</strong> für 💰 ${preis}!`);}
  else document.getElementById('vhd-nachricht').textContent='❌ '+res.fehler;
}

// ─── TRADE-ANGEBOT (Spieler↔Spieler) ─────────────────────────
window.startTradeAngebot=async function(anSpieler,wuenschtTierId){
  State.tradeTarget={an:anSpieler,wuenscht_id:wuenschtTierId};
  const tr=await API.getTiere();const tier=tr.tiere?.find(t=>t.id===wuenschtTierId);
  document.getElementById('trade-an').textContent='👤 '+anSpieler;
  // Gesuchtes Tier anzeigen
  if(tier){
    const info=rangInfo(tier.genetik.rang||1);
    document.getElementById('trade-wuenscht').textContent=`${tier.emoji||'🐾'} ${tier.name} · Rang ${info.rang}`;
    document.getElementById('trade-wuenscht').style.color=info.farbe;
  }
  // Meine Tiere als Tausch-Optionen
  const grid=document.getElementById('trade-meine-tiere');grid.innerHTML='';
  if(!State.meineTiere.length){grid.innerHTML='<div class="empty-msg">Du hast keine Tiere zum Tauschen</div>';return;}
  for(const k of State.meineTiere){
    const info=rangInfo(k.genetik.rang||1);
    const card=document.createElement('div');card.className='tier-card';
    card.innerHTML=`<div class="tcv"><canvas width="62" height="62"></canvas></div><div class="tname">${k.name}</div><div class="rang-badge-small ${selCls(info.name)}" style="color:${info.farbe};border-color:${info.farbe}">Rang ${info.rang}</div>`;
    drawTier2D(card.querySelector('canvas'),k);
    card.addEventListener('click',()=>{document.querySelectorAll('#trade-meine-tiere .tier-card').forEach(c=>c.classList.remove('selected'));card.classList.add('selected');State.tradeTarget.biete_id=k.id;});
    grid.appendChild(card);
  }
  document.getElementById('trade-coins-gebot').value=0;
  document.getElementById('trade-modal').classList.add('open');
};
window.closeTradeModal=()=>{document.getElementById('trade-modal').classList.remove('open');State.tradeTarget=null;};
window.sendeTrade=async()=>{
  if(!State.tradeTarget)return;
  const {an,wuenscht_id,biete_id}=State.tradeTarget;
  const coins=parseInt(document.getElementById('trade-coins-gebot').value||'0');
  if(!biete_id&&coins<=0){notify('❌ Wähle ein Tier oder gib Coins an');return;}
  const res=await API.tradeAnbieten(an,wuenscht_id,biete_id||null,coins);
  if(!res.ok){notify('❌ '+res.fehler);return;}
  closeTradeModal();notify(`📨 Trade-Angebot gesendet an <strong>${an}</strong>!`);
};

// ─── TRADES PANEL ─────────────────────────────────────────────
async function renderTradePanel(){
  // BUG 1 FIX: nur #trades-list ersetzen, nicht den ganzen trades-content
  const list=document.getElementById('trades-list');
  if(!list)return;
  list.innerHTML='<div class="loading">Lade Trades…</div>';
  const res=await API.tradesHolen();
  if(!res.ok||!res.trades.length){list.innerHTML='<div class="empty-msg">Keine offenen Trades</div>';return;}
  list.innerHTML='';
  const tiere={}; (await API.getTiere()).tiere?.forEach(t=>tiere[t.id]=t);
  for(const tr of res.trades){
    const card=document.createElement('div');card.className='trade-card';
    const istEmpf=tr.an===State.spielerName;
    const bieteTier=tiere[tr.biete_tier_id];
    const wuenschtTier=tiere[tr.wuensche_tier_id];
    let inhalt='';
    if(bieteTier){const i=rangInfo(bieteTier.genetik.rang||1);inhalt+=`🔁 ${bieteTier.emoji||'🐾'} <strong>${bieteTier.name}</strong> <span style="color:${i.farbe}">(Rang ${i.rang})</span>`;}
    if(tr.gebot_coins>0)inhalt+=` + 💰 ${tr.gebot_coins}`;
    if(wuenschtTier){const i=rangInfo(wuenschtTier.genetik.rang||1);inhalt+=` gegen ${wuenschtTier.emoji||'🐾'} <strong>${wuenschtTier.name}</strong> <span style="color:${i.farbe}">(Rang ${i.rang})</span>`;}
    card.innerHTML=`
      <div class="trade-header">${istEmpf?'📥 Von <strong>'+tr.von+'</strong>':'📤 An <strong>'+tr.an+'</strong>'} <span class="trade-id">#${tr.id}</span></div>
      <div class="trade-body">${inhalt||'(Coin-Angebot)'}</div>
      ${istEmpf?`<div class="trade-btns"><button class="t-yes" onclick="tradeAnnehmen('${tr.id}')">✅ Annehmen</button><button class="t-no" onclick="tradeAblehnen('${tr.id}')">❌ Ablehnen</button></div>`:'<div class="trade-pending">⏳ Warte auf Antwort…</div>'}`;
    list.appendChild(card);
  }
}
window.tradeAnnehmen=async id=>{const res=await API.tradeAnnehmen(id);if(!res.ok){notify('❌ '+res.fehler);return;}State.coins=res.user.coins;State.inventar=res.user.inventar;const tr=await API.getTiere();if(tr.ok)State.meineTiere=tr.tiere.filter(t=>State.inventar.includes(t.id));updateHUD();renderTradePanel();notify('✅ Trade angenommen!');};
window.tradeAblehnen=async id=>{await API.tradeAblehnen(id);renderTradePanel();notify('❌ Trade abgelehnt');};

// ─── STAMMBAUM ────────────────────────────────────────────────
async function renderStammbaumPanel(){
  const cont=document.getElementById('stammbaum-content');
  if(!State.meineTiere.length){cont.innerHTML='<div class="empty-msg">Keine Tiere</div>';return;}
  const tier=State.meineTiere[State.meineTiere.length-1];
  cont.innerHTML='<div class="loading">Lade…</div>';
  const res=await API.getStammbaum(tier.id);
  if(!res.ok){cont.innerHTML='<div class="empty-msg">Fehler</div>';return;}
  cont.innerHTML=baumHTML(res.stammbaum,0);
}
function baumHTML(node,d){if(!node)return'';const info=rangInfo(node.rang||1);return`<div class="baum-node" style="border-left:3px solid ${info.farbe};padding-left:${d*14+8}px"><span>${node.emoji||'🐾'}</span><span class="bname">${node.name}</span><span class="bgen">Gen.${node.gen}</span><span style="font-size:10px;color:${info.farbe}">Rang ${info.rang} · ${info.name}</span>${baumHTML(node.vater,d+1)}${baumHTML(node.mutter,d+1)}</div>`;}

// ═══ NOTIFICATIONS + ONLINE-POLLING ══════════════════════════
let _pollTimer=null;
async function pollServer(){
  if(!State.eingeloggt)return;
  try {
    // Heartbeat
    API.heartbeat();
    // Benachrichtigungen – BUG 3 FIX: Queue, nicht überschreiben
    const bn=await API.benachrichtigungen();
    if(bn.ok && bn.benachrichtigungen.length) queueSystemNotifs(bn.benachrichtigungen.map(n=>n.text));
    // Online-Spieler
    const ol=await API.spielerOnline();
    if(ol.ok){State.onlineSpieler=ol.online;updateOnlineAnzeige();}
    // Trades-Badge
    const tr=await API.tradesHolen();
    if(tr.ok){State.meineTrades=tr.trades;const cnt=tr.trades.filter(t=>t.an===State.spielerName).length;const badge=document.getElementById('trades-badge');if(badge){badge.textContent=cnt||'';badge.style.display=cnt>0?'inline':'none';}}
    // Chat-Badge: ungelesene Nachrichten
    const ug=await API.ungeleseneAnzahl();
    if(ug.ok){const cb=document.getElementById('chat-badge');if(cb){cb.textContent=ug.anzahl||'';cb.style.display=ug.anzahl>0?'inline':'none';}}
    // Wenn Verlauf gerade geöffnet: automatisch neu laden
    if(State.activePanel==='chat'&&ChatState.partner){
      await ladeVerlauf(ChatState.partner,false);
    }
  } catch(e){}
}

// BUG 3 FIX: Notification-Queue – zeigt Nachrichten nacheinander
const _notifQ={queue:[],running:false};
function queueSystemNotifs(texts){
  _notifQ.queue.push(...texts);
  if(!_notifQ.running) _runNotifQueue();
}
function _runNotifQueue(){
  if(!_notifQ.queue.length){_notifQ.running=false;return;}
  _notifQ.running=true;
  const text=_notifQ.queue.shift();
  showSystemNotif(text,()=>setTimeout(_runNotifQueue,400));
}
function showSystemNotif(text, onDone){
  const el=document.getElementById('sys-notif');
  el.textContent=text; el.classList.add('show');
  clearTimeout(el._timer);
  el._timer=setTimeout(()=>{el.classList.remove('show');if(onDone)onDone();},5000);
}
function updateOnlineAnzeige(){
  const el=document.getElementById('online-liste');if(!el)return;
  if(!State.onlineSpieler.length){el.innerHTML='<div class="empty-msg" style="font-size:11px">Keine anderen Spieler online</div>';return;}
  el.innerHTML='';
  for(const sp of State.onlineSpieler){
    const row=document.createElement('div');row.className='online-row';
    row.innerHTML=`<span class="online-dot">●</span> <strong>${sp.name}</strong>`;
    el.appendChild(row);
  }
}

// ═══ NOTIFICATIONS HUD ════════════════════════════════════════
function notify(msg){const el=document.getElementById('notif');el.innerHTML=msg;el.classList.add('show');clearTimeout(State.notifTimer);State.notifTimer=setTimeout(()=>el.classList.remove('show'),4000);}

// ═══ CHAT-SYSTEM ══════════════════════════════════════════════

const ChatState = {
  partner:     null,
  sozialdaten: { freunde: [], blockiert: [] },
};

function escH(str){
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

async function renderChatPanel(){
  const sd=await API.sozialdaten();
  if(sd.ok) ChatState.sozialdaten=sd;
  
  document.getElementById('chat-panel-titel').textContent='💬 Chat';
  document.getElementById('panel-chat').classList.add('chat-mode');
  
  await ladeEmpfaengerListe();
  chatOeffnen('__alle__');
}

async function ladeEmpfaengerListe(){
  const empfEl=document.getElementById('chat-empfaenger');
  const aktueller=empfEl.value;
  empfEl.innerHTML='<option value="__alle__">🌍 Globaler Chat</option>';
  
  const alleNamen=new Set([
    ...State.onlineSpieler.map(s=>s.name),
    ...ChatState.sozialdaten.freunde,
  ]);
  alleNamen.delete(State.spielerName);
  
  // Füge existierende Konversationen hinzu (falls wir sie haben/brauchen)
  const res=await API.postfach();
  if(res.ok){
    for(const konv of res.konversationen) alleNamen.add(konv.partner);
  }
  
  for(const name of alleNamen){
    const online=State.onlineSpieler.some(s=>s.name===name);
    const istFreund=ChatState.sozialdaten.freunde.includes(name);
    const opt=document.createElement('option');
    opt.value=name;
    opt.textContent=(online?'🟢 ':'⚫ ')+name+(istFreund?' ⭐':'');
    empfEl.appendChild(opt);
  }
  if(Array.from(empfEl.options).some(o=>o.value===aktueller)) empfEl.value=aktueller;
}

window.chatEmpfaengerWechsel=function(){
  chatOeffnen(document.getElementById('chat-empfaenger').value);
};

async function chatOeffnen(partner){
  ChatState.partner=partner;
  document.getElementById('chat-empfaenger').value=partner;
  document.getElementById('chat-partner-name').textContent=partner;
  
  // Freunde- und Block-Buttons nur zeigen, wenn es nicht der globale Chat ist
  const btns=document.querySelector('.chat-partner-btns');
  if(partner==='__alle__'){
    if(btns) btns.style.display='none';
  }else{
    if(btns) btns.style.display='flex';
    _aktualisiereSozialButtons(partner);
  }
  
  await ladeVerlauf(partner,true);
}

function _aktualisiereSozialButtons(partner){
  if(partner==='__alle__')return;
  const istFreund  =ChatState.sozialdaten.freunde.includes(partner);
  const istBlocked =ChatState.sozialdaten.blockiert.includes(partner);
  const fb=document.getElementById('chat-freund-btn');
  const bb=document.getElementById('chat-block-btn');
  if(fb){fb.textContent=istFreund?'⭐ Freund':'➕ Freund'; fb.classList.toggle('aktiv',istFreund);}
  if(bb){bb.textContent=istBlocked?'✅ Entblockiert':'🚫 Block'; bb.classList.toggle('aktiv',istBlocked);}
}

async function ladeVerlauf(partner,scrollUnten=true){
  const box=document.getElementById('chat-nachrichten');
  if(scrollUnten) box.innerHTML='<div class="loading">Lade…</div>';
  const res=await API.verlauf(partner);
  if(!res.ok){box.innerHTML='<div class="empty-msg">Fehler</div>';return;}
  if(!res.verlauf.length){
    const anzeigeName=partner==='__alle__'?'der Welt':escH(partner);
    box.innerHTML=`<div class="empty-msg">Noch keine Nachrichten mit ${anzeigeName}<br>Schreib als Erster! 👋</div>`;
    return;
  }
  const aktuelleAnzahl=box.querySelectorAll('.chat-msg').length;
  if(!scrollUnten&&aktuelleAnzahl===res.verlauf.length)return;
  box.innerHTML='';
  for(const m of res.verlauf){
    const vonMir=m.von===State.spielerName;
    const div=document.createElement('div');
    div.className='chat-msg '+(vonMir?'chat-msg-ich':'chat-msg-du');
    const d=new Date(m.zeit);
    const zeit=d.toLocaleTimeString('de-DE',{hour:'2-digit',minute:'2-digit'});
    let pfName='';
    if(!vonMir && partner==='__alle__') pfName=`<div style="font-size:10px;color:rgba(255,255,255,0.6);margin-bottom:2px;padding-left:4px">👤 ${escH(m.von)}</div>`;
    div.innerHTML=`${pfName}<div class="chat-bubble">${escH(m.text)}</div><div class="chat-zeit">${zeit}</div>`;
    box.appendChild(div);
  }
  if(scrollUnten||box.scrollHeight-box.scrollTop<box.clientHeight+80){
    box.scrollTop=box.scrollHeight;
  }
}

// chatZurueck() und chatNeuStarten() werden nicht mehr zwingend gebraucht, 
// da wir kein Postfach mehr haben, aber wir leeren sie einfach.
window.chatZurueck=async()=>{
  chatOeffnen('__alle__');
};

window.chatNeuStarten=()=>{
  const name=document.getElementById('chat-empfaenger').value;
  if(name) chatOeffnen(name);
};

window.chatSenden=async()=>{
  const textEl=document.getElementById('chat-text');
  const text=textEl.value.trim();
  if(!text||!ChatState.partner)return;
  const btn=document.querySelector('.chat-senden-btn');
  btn.disabled=true;
  const res=await API.nachrichtSenden(ChatState.partner,text);
  btn.disabled=false;
  if(!res.ok){notify('❌ '+res.fehler);return;}
  textEl.value='';
  await ladeVerlauf(ChatState.partner,true);
};

window.toggleFreund=async()=>{
  if(!ChatState.partner)return;
  const istFreund=ChatState.sozialdaten.freunde.includes(ChatState.partner);
  const res=istFreund
    ?await API.freundEntfernen(ChatState.partner)
    :await API.freundHinzufuegen(ChatState.partner);
  if(!res.ok){notify('❌ '+res.fehler);return;}
  if(istFreund) ChatState.sozialdaten.freunde=ChatState.sozialdaten.freunde.filter(f=>f!==ChatState.partner);
  else          ChatState.sozialdaten.freunde.push(ChatState.partner);
  _aktualisiereSozialButtons(ChatState.partner);
  notify(istFreund?'👋 Freund entfernt':'⭐ '+ChatState.partner+' als Freund hinzugefügt!');
};

window.toggleBlock=async()=>{
  if(!ChatState.partner)return;
  const istBlocked=ChatState.sozialdaten.blockiert.includes(ChatState.partner);
  if(!istBlocked&&!confirm(`${ChatState.partner} wirklich blockieren?\nSie können dir dann nicht mehr schreiben.`))return;
  const res=istBlocked
    ?await API.entblockieren(ChatState.partner)
    :await API.blockieren(ChatState.partner);
  if(!res.ok){notify('❌ '+res.fehler);return;}
  if(istBlocked) ChatState.sozialdaten.blockiert=ChatState.sozialdaten.blockiert.filter(b=>b!==ChatState.partner);
  else           ChatState.sozialdaten.blockiert.push(ChatState.partner);
  _aktualisiereSozialButtons(ChatState.partner);
  notify(istBlocked?'✅ Entblockiert':'🚫 '+ChatState.partner+' blockiert');
};

// Enter=senden, Shift+Enter=neue Zeile
document.addEventListener('DOMContentLoaded',()=>{
  document.getElementById('chat-text')?.addEventListener('keydown',e=>{
    if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();chatSenden();}
  });
});

// ═══ GAME LOOP ════════════════════════════════════════════════
const clock=new THREE.Clock();let lastMs=0;
function loop(ms){
  requestAnimationFrame(loop);const dt=Math.min((ms-lastMs)/1000,.05);lastMs=ms;
  if(!State.eingeloggt||State.activePanel){renderer.render(scene,camera);return;}
  const fb=(keys['KeyW']||keys['ArrowUp']?1:keys['KeyS']||keys['ArrowDown']?-1:0)+(-joyVec.y);
  const sr=(keys['KeyD']||keys['ArrowRight']?1:keys['KeyA']||keys['ArrowLeft']?-1:0)+joyVec.x;
  const spd=SPEED*((isSprinting||keys['ShiftLeft'])?1.85:1.0);
  if(Math.abs(fb)>.05||Math.abs(sr)>.05){camera.position.x+=(fb*(-Math.sin(camYaw))+sr*Math.cos(camYaw))*spd*dt;camera.position.z+=(fb*(-Math.cos(camYaw))+sr*(-Math.sin(camYaw)))*spd*dt;}
  velY+=GRAVITY*dt;camera.position.y+=velY*dt;
  const gy=terrainH(camera.position.x,camera.position.z)+EYE_H;
  if(camera.position.y<=gy){camera.position.y=gy;velY=0;onGround=true;}else onGround=camera.position.y<=gy+.1;
  camera.position.x=Math.max(-105,Math.min(105,camera.position.x));camera.position.z=Math.max(-105,Math.min(105,camera.position.z));
  camera.rotation.y=camYaw;camera.rotation.x=camPitch;
  const t=clock.getElapsedTime();
  for(const item of State.collectibles){if(item.dead||!item.mesh)continue;item.mesh.rotation.y+=dt*1.6;item.mesh.position.y=terrainH(item.x,item.z)+1.0+Math.sin(t*2.2+item.phase)*.12;}
  for(const k of State.wildeTiere){if(!k.mesh)continue;k.wt-=dt;if(k.wt<=0){k.wt=2+Math.random()*5;k.tx=Math.max(-100,Math.min(100,k.mesh.position.x+(Math.random()-.5)*16));k.tz=Math.max(-100,Math.min(100,k.mesh.position.z+(Math.random()-.5)*16));}const dx=k.tx-k.mesh.position.x,dz=k.tz-k.mesh.position.z,d=Math.sqrt(dx*dx+dz*dz);if(d>.3){const sp=k.genetik.speed*1.8*dt;k.mesh.position.x+=dx/d*sp;k.mesh.position.z+=dz/d*sp;k.mesh.rotation.y=Math.atan2(dx,dz);}k.mesh.position.y=terrainH(k.mesh.position.x,k.mesh.position.z)+.52*k.genetik.groesse;k.mesh.rotation.z=Math.sin(t*1.8+k.id.charCodeAt(0)*.1)*.04;}
  checkHints();renderer.render(scene,camera);
}

// ═══ INIT / LOGIN ═════════════════════════════════════════════
window.togglePanel=togglePanel;window.closePanel=closePanel;
// DSGVO
window.zeigeKontoLoeschen=()=>{document.getElementById('dsgvo-modal').style.display='flex';document.getElementById('dsgvo-pw').value='';document.getElementById('dsgvo-err').textContent='';};
window.bestaetigeLoeschen=async()=>{
  const pw=document.getElementById('dsgvo-pw').value;
  if(!pw){document.getElementById('dsgvo-err').textContent='Bitte Passwort eingeben';return;}
  const res=await API.post('/api/account/loeschen',{passwort:pw});
  if(!res.ok){document.getElementById('dsgvo-err').textContent=res.fehler||'Fehler';return;}
  alert('Account gelöscht. Auf Wiedersehen!');location.reload();
};
window.setSetting=async(key,val,btn)=>{
  await API.einstellungenSpeichern({[key]:val});
  document.querySelectorAll(`.setting-btn[data-key="${key}"]`).forEach(b=>b.classList.toggle('active',b.dataset.val===val));
  notify('✅ Einstellung gespeichert');
};
async function startSpiel(user){
  State.eingeloggt=true;State.spielerName=user.name;
  State.blaetter=user.blaetter;State.coins=user.coins;State.inventar=user.inventar;
  document.getElementById('login-screen').style.display='none';
  document.getElementById('start-screen').style.display='flex';
}
async function initGame(){
  document.getElementById('start-screen').style.display='none';
  const u=await API.getUser();
  if(u.ok){State.blaetter=u.user.blaetter;State.coins=u.user.coins;State.inventar=u.user.inventar;const tr=await API.getTiere();if(tr.ok)State.meineTiere=tr.tiere.filter(t=>State.inventar.includes(t.id));}
  // Bot-Einstellungen laden
  const es=await API.einstellungenLesen();
  if(es.ok){const av=es.einstellungen.auto_verhandlung||'selbst';document.querySelectorAll('.setting-btn[data-key="auto_verhandlung"]').forEach(b=>{b.classList.toggle('active',b.dataset.val===av);});}
  initMobileUI();updateHUD();await spawnWild();
  _pollTimer=setInterval(pollServer,5000);pollServer();
  requestAnimationFrame(loop);
}
document.getElementById('login-form')?.addEventListener('submit',async e=>{e.preventDefault();const err=document.getElementById('login-err');err.textContent='';const res=await API.login(document.getElementById('l-name').value.trim(),document.getElementById('l-pw').value);if(res.ok)startSpiel(res.user);else err.textContent=res.fehler||'Fehler';});
document.getElementById('reg-form')?.addEventListener('submit',async e=>{e.preventDefault();const err=document.getElementById('reg-err');err.textContent='';const pw=document.getElementById('r-pw').value,pw2=document.getElementById('r-pw2').value;if(pw!==pw2){err.textContent='Passwörter stimmen nicht';return;}const res=await API.register(document.getElementById('r-name').value.trim(),pw);if(res.ok)startSpiel(res.user);else err.textContent=res.fehler||'Fehler';});
window.showTab=tab=>{document.getElementById('login-tab').classList.toggle('active',tab==='login');document.getElementById('reg-tab').classList.toggle('active',tab==='reg');document.getElementById('login-form').style.display=tab==='login'?'flex':'none';document.getElementById('reg-form').style.display=tab==='reg'?'flex':'none';};
document.getElementById('start-btn')?.addEventListener('click',initGame);
window.doLogout=async()=>{clearInterval(_pollTimer);await API.logout();location.reload();};
(async()=>{const res=await API.ich();if(res.ok&&res.eingeloggt)startSpiel(res.user);})();
