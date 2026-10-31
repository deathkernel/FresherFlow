import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.160.0/+esm";
import { OrbitControls } from "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/controls/OrbitControls.js/+esm";
import { CSS2DRenderer, CSS2DObject } from "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/renderers/CSS2DRenderer.js/+esm";

(() => {
"use strict";
const $=id=>document.getElementById(id);
const root=$("dbx-three-root"),viewport=$("dbx-canvas-viewport"),loading=$("dbx-loading"),errorBox=$("dbx-error");
const sidebar=$("dbx-sidebar-tables"),search=$("dbx-search");
let tables=[],selected=null,mode="3d",query="",scene,camera,renderer,labelRenderer,controls,observer,raf=0;
const nodes=new Map(),edges=[],raycaster=new THREE.Raycaster(),pointer=new THREE.Vector2(),pickables=[];
const make=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;};
const set=(id,value)=>{$(id).textContent=value;};
const groupDefs=[
 {name:"Identity & access",tables:["users","auth_attempts","user_preferences"]},
 {name:"Profiles",tables:["student_profiles","employer_profiles"]},
 {name:"Hiring workflow",tables:["vacancies","applications","saved_jobs","interviews"]},
 {name:"College & verification",tables:["colleges","college_verifiers","college_student_accounts","student_verification_requests"]},
 {name:"Engagement",tables:["notifications","messages","career_tasks"]},
 {name:"Platform",tables:["audit_log","schema_migrations"]}
];
function groupOf(name){return groupDefs.find(g=>g.tables.includes(name))?.name||"Other";}
function isIndexed(t,c){return t.indexes.some(ix=>ix.columns.includes(c.name));}
function getVisible(){const q=query.trim().toLowerCase();return tables.filter(t=>!q||t.name.toLowerCase().includes(q)||t.columns.some(c=>c.name.toLowerCase().includes(q)||c.type.toLowerCase().includes(q)));}
function relationList(t){
 const outgoing=t.foreignKeys.map(f=>({direction:"OUTGOING",column:f.from,target:f.table,targetColumn:f.to,onDelete:f.onDelete,onUpdate:f.onUpdate}));
 const incoming=tables.flatMap(source=>source.foreignKeys.filter(f=>f.table===t.name).map(f=>({direction:"INCOMING",column:f.to,target:source.name,targetColumn:f.from,onDelete:f.onDelete,onUpdate:f.onUpdate})));
 return [...outgoing,...incoming];
}
function renderMetrics(){
 set("dbx-table-count",tables.length);
 set("dbx-relation-count",tables.reduce((n,t)=>n+t.foreignKeys.length,0));
 set("dbx-total-columns",tables.reduce((n,t)=>n+t.columns.length,0));
 set("dbx-total-indexes",tables.reduce((n,t)=>n+t.indexes.length,0));
 set("dbx-sidebar-count",tables.length+" tables");
}
function renderSidebar(){
 sidebar.replaceChildren();let last="";
 const shown=[...getVisible()].sort((a,b)=>groupDefs.findIndex(g=>g.name===groupOf(a.name))-groupDefs.findIndex(g=>g.name===groupOf(b.name))||a.name.localeCompare(b.name));
 for(const t of shown){
  const group=groupOf(t.name);if(group!==last){sidebar.append(make("div","dbs-group-label",group));last=group;}
  const b=make("button","dbs-table-link"+(selected?.name===t.name?" active":""));b.type="button";b.dataset.table=t.name;
  b.append(make("span","dbs-table-glyph","▦"),make("span","",t.name),make("small","",String(t.columns.length)));
  b.addEventListener("click",()=>selectTable(t,true));sidebar.append(b);
 }
 if(!shown.length)sidebar.append(make("p","dbs-empty","No matching tables."));
}
function cardElement(t){
 const card=make("button","dbs-glass-card");card.type="button";card.dataset.table=t.name;
 const head=make("div","dbs-glass-head");head.append(make("span","dbs-glass-glyph","▦"),make("strong","dbs-glass-title",t.name),make("small","dbs-glass-count",t.columns.length+" COL"));
 const fields=make("div","dbs-glass-fields");
 t.columns.slice(0,4).forEach(c=>{
  const row=make("div","dbs-glass-row"),mark=c.primaryKey?"PK":c.foreignKey?"FK":isIndexed(t,c)?"IX":"";
  row.append(make("span","dbs-glass-name",c.name),make("span","dbs-glass-type",c.type||"ANY"),make("span","dbs-glass-key "+mark.toLowerCase(),mark));
  fields.append(row);
 });
 card.append(head,fields);
 if(t.columns.length>4)card.append(make("div","dbs-glass-more","+"+(t.columns.length-4)+" MORE COLUMNS"));
 card.addEventListener("click",()=>selectTable(t,true));
 return card;
}
function positionsForSchema(){
 const positions=new Map(),center=new THREE.Vector3(0,0,0),byName=new Map(tables.map(t=>[t.name,t]));
 if(byName.has("users"))positions.set("users",center);
 const inner=["student_profiles","employer_profiles","vacancies","applications","colleges","notifications","messages","student_verification_requests"].filter(n=>byName.has(n));
 const outer=tables.map(t=>t.name).filter(n=>n!=="users"&&!inner.includes(n));
 const placeRing=(names,radius,offset,zShift)=>{
  names.forEach((name,i)=>{
   const angle=offset+(i/names.length)*Math.PI*2,lift=(i%3-1)*32;
   positions.set(name,new THREE.Vector3(Math.cos(angle)*radius,Math.sin(angle)*radius+lift,zShift+(i%2?36:-36)));
  });
 };
 placeRing(inner,430,-Math.PI/2,-40);
 placeRing(outer,700,-Math.PI/2+Math.PI/outer.length,30);
 tables.forEach((t,i)=>{if(!positions.has(t.name)){const a=i/tables.length*Math.PI*2;positions.set(t.name,new THREE.Vector3(Math.cos(a)*800,Math.sin(a)*800,0));}});
 return positions;
}
function addBackground(){
 const stars=[],count=620;
 for(let i=0;i<count;i++){const angle=Math.random()*Math.PI*2,r=350+Math.random()*1250;stars.push(Math.cos(angle)*r,(Math.random()-.5)*1500,-150-Math.random()*800);}
 const geometry=new THREE.BufferGeometry();geometry.setAttribute("position",new THREE.Float32BufferAttribute(stars,3));
 scene.add(new THREE.Points(geometry,new THREE.PointsMaterial({color:0x9db5d2,size:2.2,transparent:true,opacity:.46,sizeAttenuation:false})));
 const ring1=new THREE.Mesh(new THREE.TorusGeometry(265,1.2,8,160),new THREE.MeshBasicMaterial({color:0xd6ad5d,transparent:true,opacity:.33}));ring1.position.z=-80;scene.add(ring1);
 const ring2=new THREE.Mesh(new THREE.TorusGeometry(285,.55,6,160),new THREE.MeshBasicMaterial({color:0x6f8ca9,transparent:true,opacity:.2}));ring2.position.z=-92;scene.add(ring2);
 const core=new THREE.Mesh(new THREE.IcosahedronGeometry(12,2),new THREE.MeshStandardMaterial({color:0xe9c46f,emissive:0xb27b28,emissiveIntensity:.7,metalness:.7,roughness:.2}));core.position.set(0,0,-25);scene.add(core);
 const light=new THREE.PointLight(0xe8bd68,170,1150);light.position.set(0,0,120);scene.add(light);
 const fill=new THREE.PointLight(0x4d83b4,100,1200);fill.position.set(-500,300,180);scene.add(fill);
}
function makeNode(t,position){
 const group=new THREE.Group();group.position.copy(position);group.userData.table=t;
 const glass=new THREE.Mesh(new THREE.BoxGeometry(260,174,18),new THREE.MeshPhysicalMaterial({color:0x8aa9c7,transparent:true,opacity:.13,metalness:.65,roughness:.16,clearcoat:.8,clearcoatRoughness:.12,depthWrite:false}));group.add(glass);
 const outline=new THREE.LineSegments(new THREE.EdgesGeometry(glass.geometry),new THREE.LineBasicMaterial({color:0xd9bd7e,transparent:true,opacity:.5}));group.add(outline);
 const halo=new THREE.Mesh(new THREE.TorusGeometry(150,1.15,6,80),new THREE.MeshBasicMaterial({color:0xd9b568,transparent:true,opacity:.35}));halo.position.z=-35;group.add(halo);
 const card=cardElement(t),label=new CSS2DObject(card);label.position.set(0,0,13);group.add(label);
 scene.add(group);nodes.set(t.name,{group,glass,outline,halo,label,card,position:position.clone(),table:t});
 const pick=new THREE.Mesh(new THREE.SphereGeometry(115,12,10),new THREE.MeshBasicMaterial({visible:false,transparent:true,opacity:0}));pick.position.copy(position);pick.userData.table=t;scene.add(pick);pickables.push(pick);
}
function addRelationship(from,to,field,index){
 const a=nodes.get(from)?.position,b=nodes.get(to)?.position;if(!a||!b)return;
 const mid=a.clone().lerp(b,.5);mid.x+=(index%2?1:-1)*85;mid.y+=60+(index%4)*22;mid.z+=100+(index%3)*22;
 const curve=new THREE.CatmullRomCurve3([a.clone(),mid,b.clone()]);
 const glow=new THREE.Mesh(new THREE.TubeGeometry(curve,42,5,7,false),new THREE.MeshBasicMaterial({color:0xd8ac54,transparent:true,opacity:.22,depthWrite:false}));
 const line=new THREE.Mesh(new THREE.TubeGeometry(curve,42,1.55,6,false),new THREE.MeshBasicMaterial({color:0xf0ce7c,transparent:true,opacity:.62,depthWrite:false}));
 const spark=new THREE.Mesh(new THREE.SphereGeometry(4.2,10,8),new THREE.MeshBasicMaterial({color:0xffe6a0,transparent:true,opacity:.9}));
 scene.add(glow,line,spark);edges.push({from,to,field,curve,glow,line,spark,phase:Math.random()*Math.PI*2});
}
function resizeScene(){
 if(!renderer||!labelRenderer)return;
 const width=Math.max(1,viewport.clientWidth),height=Math.max(1,viewport.clientHeight);
 camera.aspect=width/height;camera.updateProjectionMatrix();renderer.setSize(width,height,false);labelRenderer.setSize(width,height);
}
function buildScene(){
 if(renderer){cancelAnimationFrame(raf);controls?.dispose();observer?.disconnect();renderer.dispose();labelRenderer?.domElement.remove();renderer.domElement.remove();}
 nodes.clear();edges.length=0;pickables.length=0;
 scene=new THREE.Scene();scene.fog=new THREE.FogExp2(0x08111e,.00012);
 camera=new THREE.PerspectiveCamera(42,1,1,5000);camera.position.set(0,0,1780);camera.lookAt(0,0,0);
 renderer=new THREE.WebGLRenderer({antialias:true,alpha:true});renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,1.6));renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.16;renderer.domElement.className="dbs-webgl";
 root.replaceChildren(renderer.domElement);
 labelRenderer=new CSS2DRenderer();labelRenderer.domElement.className="dbs-label-layer";root.append(labelRenderer.domElement);
 controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.dampingFactor=.055;controls.enablePan=true;controls.minDistance=850;controls.maxDistance=3000;controls.target.set(0,0,0);
 scene.add(new THREE.AmbientLight(0xaec5df,1.45));
 const key=new THREE.DirectionalLight(0xffffff,2.1);key.position.set(-360,620,900);scene.add(key);
 const gold=new THREE.PointLight(0xe6bd67,120,1400);gold.position.set(0,320,400);scene.add(gold);
 addBackground();
 const positions=positionsForSchema();tables.forEach(t=>makeNode(t,positions.get(t.name)));
 let edgeIndex=0;tables.forEach(t=>t.foreignKeys.forEach(f=>addRelationship(t.name,f.table,f.from,edgeIndex++)));
 resizeScene();observer=new ResizeObserver(resizeScene);observer.observe(viewport);
 renderer.domElement.addEventListener("pointerdown",onCanvasPick);
 animate();applySearch();
}
function onCanvasPick(event){
 const rect=renderer.domElement.getBoundingClientRect();pointer.x=((event.clientX-rect.left)/rect.width)*2-1;pointer.y=-((event.clientY-rect.top)/rect.height)*2+1;
 raycaster.setFromCamera(pointer,camera);const hit=raycaster.intersectObjects(pickables,false)[0];if(hit)selectTable(hit.object.userData.table,true);
}
function fitView(){if(!camera||!controls)return;camera.position.set(0,0,1780);controls.target.set(0,0,0);controls.update();set("dbx-zoom-label","100%");}
function focusNode(name){const n=nodes.get(name);if(!n||!controls)return;const offset=camera.position.clone().sub(controls.target);controls.target.copy(n.position);camera.position.copy(n.position.clone().add(offset));controls.update();}
function updateSelection(){
 for(const [name,n] of nodes){
  const active=selected?.name===name;
  const connected=!!selected&&edges.some(e=>(e.from===selected.name&&e.to===name)||(e.to===selected.name&&e.from===name));
  n.card.classList.toggle("selected",active);n.card.classList.toggle("dimmed",!!selected&&!active&&!connected);
  n.glass.material.emissive.set(active?0x725421:connected?0x334052:0x000000);
  n.glass.material.emissiveIntensity=active?0.45:connected?0.18:0;
  n.outline.material.opacity=active?0.98:connected?0.72:0.34;n.halo.material.opacity=active?0.9:connected?0.5:0.19;
 }
 for(const e of edges){
  const active=!!selected&&(e.from===selected.name||e.to===selected.name);
  e.glow.material.opacity=active?0.42:selected?0.08:0.19;e.line.material.opacity=active?1:selected?0.1:0.58;e.spark.visible=active||!selected;
 }
}
function applySearch(){
 const visible=new Set(getVisible().map(t=>t.name));
 for(const [name,n] of nodes){const show=visible.has(name);n.group.visible=show;n.card.style.visibility=show?"visible":"hidden";}
 for(const e of edges){const show=visible.has(e.from)&&visible.has(e.to);e.glow.visible=show;e.line.visible=show;e.spark.visible=show;}
 set("dbx-visible-count",visible.size+" / "+tables.length+" TABLES");renderSidebar();updateSelection();
}
function renderInspector(t){
 set("dbx-detail-name",t.name);set("dbx-object-badge","TABLE");set("dbx-detail-summary",groupOf(t.name)+" · "+t.columns.length+" columns");
 set("dbx-column-count",t.columns.length);set("dbx-fk-count",t.foreignKeys.length);set("dbx-index-count",t.indexes.length);set("dbx-column-label",t.columns.length+" fields");
 const columnBox=$("dbx-columns");columnBox.replaceChildren();
 t.columns.forEach(c=>{
  const row=make("div","dbs-column"),left=make("div"),marker=c.primaryKey?"PRIMARY KEY":c.foreignKey?"FOREIGN KEY":isIndexed(t,c)?"INDEXED":"";
  left.append(make("strong",c.primaryKey?"dbs-key":c.foreignKey?"dbs-fk":"",c.name),make("small","",[(c.notNull?"NOT NULL":""),c.default!==null?"DEFAULT "+c.default:"",marker].filter(Boolean).join(" · ")||"Nullable"));
  row.append(left,make("code","",c.type||"ANY"));columnBox.append(row);
 });
 const rels=relationList(t);set("dbx-rel-label",rels.length+" links");const relBox=$("dbx-relations");relBox.replaceChildren();
 if(!rels.length)relBox.append(make("p","dbs-empty","No foreign-key relationships."));
 rels.forEach(r=>{const row=make("div","dbs-relation");row.append(make("strong","",r.direction+": "+r.column+" → "+r.target+"."+r.targetColumn),make("span","", "ON DELETE "+r.onDelete));relBox.append(row);});
 const indexBox=$("dbx-indexes");indexBox.replaceChildren();
 if(!t.indexes.length)indexBox.append(make("p","dbs-empty","No indexes defined."));
 t.indexes.forEach(ix=>{const row=make("div","dbs-index");row.append(make("strong","",ix.name),make("span","",(ix.unique?"UNIQUE · ":"")+ix.columns.join(", ")));indexBox.append(row);});
 renderSidebar();updateSelection();
}
function selectTable(t,focus){selected=t;renderInspector(t);if(focus)focusNode(t.name);}
function renderCatalog(){
 const host=$("dbx-catalog-view");host.replaceChildren();const grid=make("div","dbs-catalog-grid");
 getVisible().forEach(t=>{const b=make("button","dbs-catalog-card"+(selected?.name===t.name?" active":""));b.type="button";b.append(make("b","",t.name),make("span","",groupOf(t.name)),make("span","",t.columns.length+" columns · "+t.foreignKeys.length+" relations"));b.addEventListener("click",()=>{selectTable(t,false);setMode("3d");});grid.append(b);});
 if(!getVisible().length)grid.append(make("p","dbs-empty","No matching tables."));host.append(grid);
}
function renderSQL(){const host=$("dbx-sql-view");host.replaceChildren();if(!selected){host.append(make("div","dbs-sql-empty","Select a table first."));return;}host.append(make("pre","",selected.sql||"-- No CREATE TABLE statement available."));}
function setMode(next){
 mode=next;root.hidden=next!=="3d";$("dbx-catalog-view").hidden=next!=="catalog";$("dbx-sql-view").hidden=next!=="sql";
 $("dbx-diagram").classList.toggle("active",next==="3d");$("dbx-catalog").classList.toggle("active",next==="catalog");$("dbx-ddl").classList.toggle("active",next==="sql");
 set("dbx-view-title",next==="3d"?"3D RELATIONSHIP MAP":next==="catalog"?"TABLE CATALOG":"SQL DEFINITION");$("dbx-canvas-hint").hidden=next!=="3d";
 if(next==="catalog")renderCatalog();if(next==="sql")renderSQL();if(next==="3d"){resizeScene();updateSelection();}
}
function animate(){
 raf=requestAnimationFrame(animate);const time=performance.now()*.00035;
 for(const [name,n] of nodes){n.group.rotation.z=.012*Math.sin(time*1.3+name.length);n.halo.rotation.z=time*.22;}
 for(const e of edges){const t=(time*.55+e.phase)%1;e.spark.position.copy(e.curve.getPoint(t));}
 controls.update();renderer.render(scene,camera);labelRenderer.render(scene,camera);
}
function bindButtons(){
 $("dbx-diagram").addEventListener("click",()=>setMode("3d"));$("dbx-catalog").addEventListener("click",()=>setMode("catalog"));$("dbx-ddl").addEventListener("click",()=>setMode("sql"));$("dbx-fit").addEventListener("click",fitView);
 $("dbx-zoom-in").addEventListener("click",()=>{camera.position.z=Math.max(850,camera.position.z*.88);controls.update();set("dbx-zoom-label",Math.round(1780/camera.position.z*100)+"%");});
 $("dbx-zoom-out").addEventListener("click",()=>{camera.position.z=Math.min(3000,camera.position.z*1.12);controls.update();set("dbx-zoom-label",Math.round(1780/camera.position.z*100)+"%");});
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
bindButtons();load();
})();