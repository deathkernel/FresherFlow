import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.160.0/+esm";
import { OrbitControls } from "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/controls/OrbitControls.js/+esm";
(() => {
"use strict";
const $=id=>document.getElementById(id),root=$("dbx-three-root"),viewport=$("dbx-canvas-viewport"),loading=$("dbx-loading"),errorBox=$("dbx-error"),sidebar=$("dbx-sidebar-tables"),search=$("dbx-search");
const W=448,H=280,TW=1024,TH=640;
let tables=[],selected=null,mode="3d",query="",scene,camera,renderer,controls,observer,raf=0,positions=new Map(),press=null;
const nodes=new Map(),edges=[],raycaster=new THREE.Raycaster(),pointer=new THREE.Vector2(),pickables=[];
const make=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;},set=(id,value)=>{$(id).textContent=value;};
const groups=[
 ["Identity & access",["users","auth_attempts","user_preferences"]],
 ["Profiles",["student_profiles","employer_profiles"]],
 ["Hiring workflow",["vacancies","applications","saved_jobs","interviews"]],
 ["College & verification",["colleges","college_verifiers","college_student_accounts","student_verification_requests"]],
 ["Engagement",["notifications","messages","career_tasks"]],
 ["Platform",["audit_log","schema_migrations"]]
];
function groupOf(name){return groups.find(g=>g[1].includes(name))?.[0]||"Other";}
function isIndexed(t,c){return t.indexes.some(ix=>ix.columns.includes(c.name));}
function sortedTables(){return [...tables].sort((a,b)=>{const ga=groups.findIndex(g=>g[0]===groupOf(a.name)),gb=groups.findIndex(g=>g[0]===groupOf(b.name));return(ga<0?99:ga)-(gb<0?99:gb)||a.name.localeCompare(b.name);});}
function visibleTables(){const q=query.trim().toLowerCase();return sortedTables().filter(t=>!q||t.name.toLowerCase().includes(q)||t.columns.some(c=>c.name.toLowerCase().includes(q)||c.type.toLowerCase().includes(q)));}
function relationList(t){
 const out=t.foreignKeys.map(f=>({direction:"OUTGOING",column:f.from,target:f.table,targetColumn:f.to,onDelete:f.onDelete}));
 const inc=tables.flatMap(s=>s.foreignKeys.filter(f=>f.table===t.name).map(f=>({direction:"INCOMING",column:f.to,target:s.name,targetColumn:f.from,onDelete:f.onDelete})));
 return [...out,...inc];
}
function renderMetrics(){
 set("dbx-table-count",tables.length);set("dbx-relation-count",tables.reduce((n,t)=>n+t.foreignKeys.length,0));
 set("dbx-total-columns",tables.reduce((n,t)=>n+t.columns.length,0));set("dbx-total-indexes",tables.reduce((n,t)=>n+t.indexes.length,0));set("dbx-sidebar-count",tables.length+" tables");
}
function renderSidebar(){
 sidebar.replaceChildren();let last="";
 for(const t of visibleTables()){
  const g=groupOf(t.name);if(g!==last){sidebar.append(make("div","dbs-group-label",g));last=g;}
  const b=make("button","dbs-table-link"+(selected?.name===t.name?" active":""));b.type="button";
  b.append(make("span","dbs-table-glyph","▦"),make("span","",t.name),make("small","",String(t.columns.length)));
  b.addEventListener("click",()=>selectTable(t,true));sidebar.append(b);
 }
 if(!visibleTables().length)sidebar.append(make("p","dbs-empty","No matching tables."));
}
function rounded(ctx,x,y,w,h,r){
 ctx.beginPath();ctx.moveTo(x+r,y);ctx.arcTo(x+w,y,x+w,y+h,r);ctx.arcTo(x+w,y+h,x,y+h,r);ctx.arcTo(x,y+h,x,y,r);ctx.arcTo(x,y,x+w,y,r);ctx.closePath();
}
function paintCard(n){
 const {ctx,texture,table:t,canvas}=n;ctx.clearRect(0,0,TW,TH);ctx.save();
 rounded(ctx,8,8,TW-16,TH-16,26);
 const bg=ctx.createLinearGradient(0,0,0,TH);bg.addColorStop(0,"rgba(39,57,77,.98)");bg.addColorStop(.48,"rgba(17,31,48,.98)");bg.addColorStop(1,"rgba(8,19,33,.98)");
 ctx.fillStyle=bg;ctx.fill();ctx.lineWidth=n.selected?5:2.5;ctx.strokeStyle=n.selected?"rgba(246,211,132,1)":"rgba(172,194,218,.56)";ctx.stroke();
 rounded(ctx,10,10,TW-20,132,24);ctx.fillStyle=n.selected?"rgba(222,178,91,.25)":"rgba(125,154,186,.15)";ctx.fill();
 ctx.fillStyle="#e8c576";ctx.beginPath();ctx.arc(67,76,30,0,Math.PI*2);ctx.fill();
 ctx.fillStyle="#172438";ctx.font="bold 38px Arial";ctx.textAlign="center";ctx.textBaseline="middle";ctx.fillText("▦",67,77);
 ctx.textAlign="left";ctx.fillStyle="#f1f5fa";ctx.font="bold 39px Arial";ctx.fillText(t.name,120,75);
 ctx.textAlign="right";ctx.fillStyle="#b9c8d9";ctx.font="bold 22px Arial";ctx.fillText(t.columns.length+" COLUMNS",976,77);
 ctx.textAlign="left";ctx.fillStyle="#dabb79";ctx.font="bold 18px Arial";ctx.fillText(groupOf(t.name).toUpperCase(),122,112);
 t.columns.slice(0,5).forEach((c,i)=>{
  const y=194+i*78;ctx.fillStyle=i%2?"rgba(255,255,255,.025)":"rgba(255,255,255,.045)";ctx.fillRect(28,y-33,968,66);
  ctx.textBaseline="middle";ctx.textAlign="left";ctx.fillStyle=c.primaryKey?"#f2d17d":c.foreignKey?"#c6b9ff":"#d5e0ec";ctx.font="bold 29px Arial";ctx.fillText(c.name.length>28?c.name.slice(0,26)+"…":c.name,49,y);
  ctx.textAlign="right";ctx.fillStyle="#90a7bf";ctx.font="23px monospace";ctx.fillText((c.type||"ANY").slice(0,17),902,y);
  const mark=c.primaryKey?"PK":c.foreignKey?"FK":isIndexed(t,c)?"IX":"";if(mark){ctx.fillStyle=c.primaryKey?"#f0ce7b":c.foreignKey?"#c3b5ff":"#74d6aa";ctx.font="bold 22px Arial";ctx.fillText(mark,970,y);}
  ctx.strokeStyle="rgba(190,207,225,.12)";ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(34,y+34);ctx.lineTo(990,y+34);ctx.stroke();
 });
 if(t.columns.length>5){ctx.textAlign="left";ctx.fillStyle="#95a9bf";ctx.font="bold 21px Arial";ctx.fillText("+"+(t.columns.length-5)+" MORE COLUMNS",48,590);}
 ctx.restore();texture.needsUpdate=true;
}
function layoutPositions(){
 const list=sortedTables(),cols=4,rows=Math.ceil(list.length/cols),map=new Map();
 list.forEach((t,i)=>{
  const row=Math.floor(i/cols),count=Math.min(cols,list.length-row*cols),col=i%cols;
  map.set(t.name,new THREE.Vector3((col-(count-1)/2)*520,((rows-1)/2-row)*330,((i%3)-1)*42+(row%2?20:-20)));
 });
 return map;
}
function addStars(){
 const data=[];for(let i=0;i<650;i++){const a=Math.random()*Math.PI*2,r=850+Math.random()*1500;data.push(Math.cos(a)*r,(Math.random()-.5)*1850,-300-Math.random()*600);}
 const geo=new THREE.BufferGeometry();geo.setAttribute("position",new THREE.Float32BufferAttribute(data,3));
 scene.add(new THREE.Points(geo,new THREE.PointsMaterial({color:0xa9bfd8,size:2,transparent:true,opacity:.42,sizeAttenuation:false})));
 const ring=new THREE.Mesh(new THREE.TorusGeometry(245,1,8,150),new THREE.MeshBasicMaterial({color:0xd6ad5d,transparent:true,opacity:.18}));ring.position.z=-190;scene.add(ring);
 const core=new THREE.Mesh(new THREE.IcosahedronGeometry(18,1),new THREE.MeshStandardMaterial({color:0xe3c477,emissive:0x926b32,emissiveIntensity:.55,metalness:.65,roughness:.25}));core.position.z=-180;scene.add(core);
 const light=new THREE.PointLight(0xe6bd67,140,1700);light.position.set(0,180,300);scene.add(light);
 const fill=new THREE.PointLight(0x4d83b4,90,1800);fill.position.set(-600,300,160);scene.add(fill);
}
function makeNode(t,pos){
 const group=new THREE.Group();group.position.copy(pos);group.userData.table=t;
 const backing=new THREE.Mesh(new THREE.BoxGeometry(W+12,H+12,15),new THREE.MeshPhysicalMaterial({color:0x88a5c1,transparent:true,opacity:.17,metalness:.55,roughness:.2,clearcoat:.9,depthWrite:true}));
 backing.position.z=-3;group.add(backing);
 const frame=new THREE.LineSegments(new THREE.EdgesGeometry(backing.geometry),new THREE.LineBasicMaterial({color:0xd9bd7e,transparent:true,opacity:.5}));frame.position.copy(backing.position);group.add(frame);
 const canvas=document.createElement("canvas");canvas.width=TW;canvas.height=TH;const ctx=canvas.getContext("2d");
 const texture=new THREE.CanvasTexture(canvas);texture.colorSpace=THREE.SRGBColorSpace;texture.anisotropy=renderer.capabilities.getMaxAnisotropy();
 const panel=new THREE.Mesh(new THREE.PlaneGeometry(W,H),new THREE.MeshBasicMaterial({map:texture,transparent:true,alphaTest:.04,depthTest:true,depthWrite:true,side:THREE.DoubleSide,toneMapped:false}));
 panel.position.z=8;panel.userData.table=t;group.add(panel);
 const halo=new THREE.Mesh(new THREE.TorusGeometry(245,1.5,7,88),new THREE.MeshBasicMaterial({color:0xdcb96d,transparent:true,opacity:.18,depthWrite:false}));halo.position.z=-13;group.add(halo);
 const node={group,backing,frame,panel,halo,canvas,ctx,texture,table:t,position:pos.clone(),selected:false};
 paintCard(node);scene.add(group);nodes.set(t.name,node);pickables.push(panel);
}
function paintCard(n){paintCardTexture(n);}
function paintCardTexture(n){paintCardCanvas(n);}
function paintCardCanvas(n){
 const {ctx,texture,table:t}=n;ctx.clearRect(0,0,TW,TH);ctx.save();rounded(ctx,8,8,TW-16,TH-16,26);
 const bg=ctx.createLinearGradient(0,0,0,TH);bg.addColorStop(0,"rgba(39,57,77,.98)");bg.addColorStop(.48,"rgba(17,31,48,.98)");bg.addColorStop(1,"rgba(8,19,33,.98)");
 ctx.fillStyle=bg;ctx.fill();ctx.lineWidth=n.selected?5:2.5;ctx.strokeStyle=n.selected?"rgba(246,211,132,1)":"rgba(172,194,218,.56)";ctx.stroke();
 rounded(ctx,10,10,TW-20,132,24);ctx.fillStyle=n.selected?"rgba(222,178,91,.25)":"rgba(125,154,186,.15)";ctx.fill();
 ctx.fillStyle="#e8c576";ctx.beginPath();ctx.arc(67,76,30,0,Math.PI*2);ctx.fill();ctx.fillStyle="#172438";ctx.font="bold 38px Arial";ctx.textAlign="center";ctx.textBaseline="middle";ctx.fillText("▦",67,77);
 ctx.textAlign="left";ctx.fillStyle="#f1f5fa";ctx.font="bold 39px Arial";ctx.fillText(t.name,120,75);ctx.textAlign="right";ctx.fillStyle="#b9c8d9";ctx.font="bold 22px Arial";ctx.fillText(t.columns.length+" COLUMNS",976,77);
 ctx.textAlign="left";ctx.fillStyle="#dabb79";ctx.font="bold 18px Arial";ctx.fillText(groupOf(t.name).toUpperCase(),122,112);
 t.columns.slice(0,5).forEach((c,i)=>{const y=194+i*78;ctx.fillStyle=i%2?"rgba(255,255,255,.025)":"rgba(255,255,255,.045)";ctx.fillRect(28,y-33,968,66);ctx.textBaseline="middle";ctx.textAlign="left";ctx.fillStyle=c.primaryKey?"#f2d17d":c.foreignKey?"#c6b9ff":"#d5e0ec";ctx.font="bold 29px Arial";ctx.fillText(c.name.length>28?c.name.slice(0,26)+"…":c.name,49,y);ctx.textAlign="right";ctx.fillStyle="#90a7bf";ctx.font="23px monospace";ctx.fillText((c.type||"ANY").slice(0,17),902,y);const mark=c.primaryKey?"PK":c.foreignKey?"FK":isIndexed(t,c)?"IX":"";if(mark){ctx.fillStyle=c.primaryKey?"#f0ce7b":c.foreignKey?"#c3b5ff":"#74d6aa";ctx.font="bold 22px Arial";ctx.fillText(mark,970,y);}ctx.strokeStyle="rgba(190,207,225,.12)";ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(34,y+34);ctx.lineTo(990,y+34);ctx.stroke();});
 if(t.columns.length>5){ctx.textAlign="left";ctx.fillStyle="#95a9bf";ctx.font="bold 21px Arial";ctx.fillText("+"+(t.columns.length-5)+" MORE COLUMNS",48,590);}ctx.restore();texture.needsUpdate=true;
}
function edgePoint(a,b){const dx=b.x-a.x,dy=b.y-a.y,s=1/Math.max(Math.abs(dx)/(W/2),Math.abs(dy)/(H/2),.0001);return new THREE.Vector3(a.x+dx*s,a.y+dy*s,a.z-34);}
function addLink(from,to,field,index){
 const a=nodes.get(from)?.position,b=nodes.get(to)?.position;if(!a||!b)return;
 const start=edgePoint(a,b),end=edgePoint(b,a),dx=end.x-start.x,dy=end.y-start.y,len=Math.hypot(dx,dy)||1,side=(index%2?1:-1)*(55+(index%3)*18);
 const mid=new THREE.Vector3((start.x+end.x)/2-dy/len*side,(start.y+end.y)/2+dx/len*side,-115-(index%4)*12);
 const curve=new THREE.QuadraticBezierCurve3(start,mid,end);
 const glow=new THREE.Mesh(new THREE.TubeGeometry(curve,42,7,7,false),new THREE.MeshBasicMaterial({color:0xd7a94f,transparent:true,opacity:.18,depthWrite:false}));
 const line=new THREE.Mesh(new THREE.TubeGeometry(curve,42,2,7,false),new THREE.MeshBasicMaterial({color:0xf0cf7e,transparent:true,opacity:.52,depthWrite:false}));
 const spark=new THREE.Mesh(new THREE.SphereGeometry(5,10,8),new THREE.MeshBasicMaterial({color:0xffe6a3}));
 scene.add(glow,line,spark);edges.push({from,to,field,curve,glow,line,spark,phase:Math.random()});
}
function resizeScene(){if(!renderer)return;const w=Math.max(1,viewport.clientWidth),h=Math.max(1,viewport.clientHeight);camera.aspect=w/h;camera.updateProjectionMatrix();renderer.setSize(w,h,false);}
function fitView(){
 if(!camera||!controls||!positions.size)return;
 const x=Math.max(...[...positions.values()].map(p=>Math.abs(p.x)))+W/2+28,y=Math.max(...[...positions.values()].map(p=>Math.abs(p.y)))+H/2+28;
 const tan=Math.tan(THREE.MathUtils.degToRad(camera.fov/2)),aspect=viewport.clientWidth/Math.max(1,viewport.clientHeight);
 const dist=Math.max(y/tan,x/(tan*Math.max(.5,aspect)))*1.14;
 camera.position.set(0,0,Math.max(1450,dist));controls.target.set(0,0,0);controls.update();set("dbx-zoom-label","FIT");
}
function focusNode(name){const n=nodes.get(name);if(!n||!controls)return;const d=camera.position.distanceTo(controls.target),dir=camera.position.clone().sub(controls.target).normalize();controls.target.copy(n.position);camera.position.copy(n.position.clone().add(dir.multiplyScalar(d)));controls.update();}
function updateSelection(){
 for(const [name,n] of nodes){
  const active=selected?.name===name,linked=!!selected&&edges.some(e=>(e.from===selected.name&&e.to===name)||(e.to===selected.name&&e.from===name));
  n.selected=active;paintCard(n);n.frame.material.opacity=active?.98:linked?.75:.28;n.halo.material.opacity=active?.82:linked?.4:.13;
  n.backing.material.emissive.set(active?0x6a4b1d:linked?0x1e3042:0);n.backing.material.emissiveIntensity=active?.35:linked?.12:0;
 }
 for(const e of edges){const active=!!selected&&(e.from===selected.name||e.to===selected.name);e.glow.material.opacity=active?.4:selected?.035:.13;e.line.material.opacity=active?.98:selected?.08:.43;e.spark.visible=active||!selected;}
}
function renderSidebar(){
 sidebar.replaceChildren();let last="";
 for(const t of visibleTables()){const g=groupOf(t.name);if(g!==last){sidebar.append(make("div","dbs-group-label",g));last=g;}const b=make("button","dbs-table-link"+(selected?.name===t.name?" active":""));b.type="button";b.append(make("span","dbs-table-glyph","▦"),make("span","",t.name),make("small","",String(t.columns.length)));b.addEventListener("click",()=>selectTable(t,true));sidebar.append(b);}
 if(!visibleTables().length)sidebar.append(make("p","dbs-empty","No matching tables."));
}
function applySearch(){const names=new Set(visibleTables().map(t=>t.name));for(const [name,n] of nodes)n.group.visible=names.has(name);for(const e of edges){const show=names.has(e.from)&&names.has(e.to);e.glow.visible=show;e.line.visible=show;e.spark.visible=show;}set("dbx-visible-count",names.size+" / "+tables.length+" TABLES");renderSidebar();updateSelection();}
function renderInspector(t){
 set("dbx-detail-name",t.name);set("dbx-object-badge","TABLE");set("dbx-detail-summary",groupOf(t.name)+" · "+t.columns.length+" columns");
 set("dbx-column-count",t.columns.length);set("dbx-fk-count",t.foreignKeys.length);set("dbx-index-count",t.indexes.length);set("dbx-column-label",t.columns.length+" fields");
 const box=$("dbx-columns");box.replaceChildren();
 t.columns.forEach(c=>{const row=make("div","dbs-column"),left=make("div"),mark=c.primaryKey?"PRIMARY KEY":c.foreignKey?"FOREIGN KEY":isIndexed(t,c)?"INDEXED":"";left.append(make("strong",c.primaryKey?"dbs-key":c.foreignKey?"dbs-fk":"",c.name),make("small","",[(c.notNull?"NOT NULL":""),c.default!==null?"DEFAULT "+c.default:"",mark].filter(Boolean).join(" · ")||"Nullable"));row.append(left,make("code","",c.type||"ANY"));box.append(row);});
 const rels=relationList(t);set("dbx-rel-label",rels.length+" links");const rb=$("dbx-relations");rb.replaceChildren();if(!rels.length)rb.append(make("p","dbs-empty","No foreign-key relationships."));
 rels.forEach(r=>{const row=make("div","dbs-relation");row.append(make("strong","",r.direction+": "+r.column+" → "+r.target+"."+r.targetColumn),make("span","","ON DELETE "+r.onDelete));rb.append(row);});
 const ib=$("dbx-indexes");ib.replaceChildren();if(!t.indexes.length)ib.append(make("p","dbs-empty","No indexes defined."));t.indexes.forEach(ix=>{const row=make("div","dbs-index");row.append(make("strong","",ix.name),make("span","",(ix.unique?"UNIQUE · ":"")+ix.columns.join(", ")));ib.append(row);});
 renderSidebar();updateSelection();
}
function selectTable(t,focus){selected=t;renderInspector(t);if(focus)focusNode(t.name);}
function onCanvasPointerDown(e){press={x:e.clientX,y:e.clientY};}
function onCanvasPointerUp(e){
 if(!press)return;const moved=Math.hypot(e.clientX-press.x,e.clientY-press.y);press=null;if(moved>6||!renderer)return;
 const r=renderer.domElement.getBoundingClientRect();pointer.x=((e.clientX-r.left)/r.width)*2-1;pointer.y=-((e.clientY-r.top)/r.height)*2+1;
 raycaster.setFromCamera(pointer,camera);const hit=raycaster.intersectObjects(pickables,false)[0];if(hit?.object?.userData?.table)selectTable(hit.object.userData.table,true);
}
function renderCatalog(){
 const host=$("dbx-catalog-view");host.replaceChildren();const grid=make("div","dbs-catalog-grid");
 visibleTables().forEach(t=>{const b=make("button","dbs-catalog-card"+(selected?.name===t.name?" active":""));b.type="button";b.append(make("b","",t.name),make("span","",groupOf(t.name)),make("span","",t.columns.length+" columns · "+t.foreignKeys.length+" relations"));b.addEventListener("click",()=>{selectTable(t,false);setMode("3d");});grid.append(b);});
 if(!visibleTables().length)grid.append(make("p","dbs-empty","No matching tables."));host.append(grid);
}
function renderSQL(){const host=$("dbx-sql-view");host.replaceChildren();if(!selected){host.append(make("div","dbs-sql-empty","Select a table first."));return;}host.append(make("pre","",selected.sql||"-- No CREATE TABLE statement available."));}
function setMode(next){
 mode=next;root.hidden=next!=="3d";$("dbx-catalog-view").hidden=next!=="catalog";$("dbx-sql-view").hidden=next!=="sql";
 $("dbx-diagram").classList.toggle("active",next==="3d");$("dbx-catalog").classList.toggle("active",next==="catalog");$("dbx-ddl").classList.toggle("active",next==="sql");
 set("dbx-view-title",next==="3d"?"3D RELATIONSHIP MAP":next==="catalog"?"TABLE CATALOG":"SQL DEFINITION");$("dbx-canvas-hint").hidden=next!=="3d";
 if(next==="catalog")renderCatalog();if(next==="sql")renderSQL();if(next==="3d"){resizeScene();updateSelection();}
}
function animate(){raf=requestAnimationFrame(animate);const time=performance.now()*.0003;for(const e of edges){const p=(time*.34+e.phase)%1;e.spark.position.copy(e.curve.getPoint(p));}controls.update();renderer.render(scene,camera);}
function buildScene(){
 if(renderer){cancelAnimationFrame(raf);controls?.dispose();observer?.disconnect();renderer.dispose();renderer.domElement.remove();}
 nodes.clear();edges.length=0;pickables.length=0;scene=new THREE.Scene();scene.fog=new THREE.FogExp2(0x08111e,.00008);
 camera=new THREE.PerspectiveCamera(42,1,1,9000);camera.position.set(0,0,2500);
 renderer=new THREE.WebGLRenderer({antialias:true,alpha:true,powerPreference:"high-performance"});renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,1.5));renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.12;renderer.domElement.className="dbs-webgl";root.replaceChildren(renderer.domElement);
 controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.dampingFactor=.065;controls.enablePan=true;controls.minDistance=1000;controls.maxDistance=7000;controls.target.set(0,0,0);
 scene.add(new THREE.AmbientLight(0xb5c8dc,1.6));const key=new THREE.DirectionalLight(0xffffff,2);key.position.set(-450,650,1000);scene.add(key);
 const gold=new THREE.PointLight(0xe6bd67,125,1800);gold.position.set(0,250,360);scene.add(gold);addStars();
 positions=layoutPositions();tables.forEach(t=>makeNode(t,positions.get(t.name)));
 let index=0;tables.forEach(t=>t.foreignKeys.forEach(f=>addLink(t.name,f.table,f.from,index++)));
 resizeScene();fitView();observer=new ResizeObserver(resizeScene);observer.observe(viewport);
 renderer.domElement.addEventListener("pointerdown",onCanvasPointerDown);renderer.domElement.addEventListener("pointerup",onCanvasPointerUp);
 animate();applySearch();
}
function bind(){
 $("dbx-diagram").addEventListener("click",()=>setMode("3d"));$("dbx-catalog").addEventListener("click",()=>setMode("catalog"));$("dbx-ddl").addEventListener("click",()=>setMode("sql"));$("dbx-fit").addEventListener("click",fitView);
 $("dbx-zoom-in").addEventListener("click",()=>{const d=camera.position.distanceTo(controls.target),v=camera.position.clone().sub(controls.target).normalize();camera.position.copy(controls.target.clone().add(v.multiplyScalar(Math.max(1000,d*.88))));set("dbx-zoom-label","ZOOM");});
 $("dbx-zoom-out").addEventListener("click",()=>{const d=camera.position.distanceTo(controls.target),v=camera.position.clone().sub(controls.target).normalize();camera.position.copy(controls.target.clone().add(v.multiplyScalar(Math.min(7000,d*1.12))));set("dbx-zoom-label","ZOOM");});
 search.addEventListener("input",()=>{query=search.value;if(mode==="3d")applySearch();else if(mode==="catalog")renderCatalog();else renderSQL();});
}
async function load(){
 try{
  const response=await fetch("/api/database/schema",{headers:{Accept:"application/json"},cache:"no-store"});if(!response.ok)throw new Error("Schema API returned HTTP "+response.status);
  const payload=await response.json();tables=(payload.tables||[]).map(t=>({...t,columns:(t.columns||[]).map(c=>({...c,foreignKey:(t.foreignKeys||[]).some(f=>f.from===c.name)})),foreignKeys:t.foreignKeys||[],indexes:t.indexes||[]}));
  if(!tables.length)throw new Error("No tables found in the configured SQLite database.");
  renderMetrics();renderSidebar();buildScene();loading.hidden=true;selected=tables.find(t=>t.name==="users")||tables[0];renderInspector(selected);setMode("3d");fitView();
 }catch(error){loading.hidden=true;errorBox.hidden=false;errorBox.textContent="Unable to build schema visualization: "+error.message;console.error("Database Universe:",error);}
}
bind();load();
})();