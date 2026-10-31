import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.160.0/+esm";
import { OrbitControls } from "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/controls/OrbitControls.js/+esm";
import { CSS2DRenderer, CSS2DObject } from "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/renderers/CSS2DRenderer.js/+esm";

const stage=document.getElementById("dbx-stage");
const graph=document.getElementById("dbx-graph");
const loading=document.getElementById("dbx-loading");
const errorBox=document.getElementById("dbx-error");
const search=document.getElementById("dbx-search");
const tableCount=document.getElementById("dbx-table-count");
const relationCount=document.getElementById("dbx-relation-count");
const pills=document.getElementById("dbx-table-pills");
const nodesByName=new Map();
let tables=[],selected=null,view="3d",query="";
let renderer,labels,scene,camera,controls,raf=0;
const raycaster=new THREE.Raycaster(),pointer=new THREE.Vector2(),pickables=[];
const palette={table:0x38bdf8,selected:0xfbbf24,linked:0xa78bfa};
const esc=s=>String(s??"");
function setText(id,value){document.getElementById(id).textContent=value;}
function el(tag,className,text){const node=document.createElement(tag);if(className)node.className=className;if(text!==undefined)node.textContent=text;return node;}
function matching(t){const q=query.trim().toLowerCase();return !q||t.name.toLowerCase().includes(q)||t.columns.some(c=>c.name.toLowerCase().includes(q)||c.type.toLowerCase().includes(q));}
function relationships(t){return t.foreignKeys.map(f=>({from:t.name,column:f.from,to:f.table,targetColumn:f.to,onDelete:f.onDelete}));}
function inspect(t){
 selected=t;setText("dbx-detail-name",t.name);setText("dbx-detail-summary",t.columns.length+" columns · "+t.foreignKeys.length+" foreign keys · "+t.indexes.length+" indexes");
 setText("dbx-column-count",t.columns.length);setText("dbx-fk-count",t.foreignKeys.length);setText("dbx-index-count",t.indexes.length);setText("dbx-column-label",t.columns.length+" fields");
 const colBox=document.getElementById("dbx-columns");colBox.replaceChildren();
 for(const c of t.columns){const row=el("div","dbx-column");const left=el("div");const name=el("strong",c.primaryKey?"dbx-key":c.foreignKey?"dbx-fk":"",c.name+(c.primaryKey?"  ◆":"")+(c.foreignKey?"  ↗":""));const meta=el("small","",[(c.notNull?"NOT NULL":""),c.default!==null?"DEFAULT "+c.default:""].filter(Boolean).join(" · ")||"nullable");left.append(name,meta);row.append(left,el("code","",c.type));colBox.append(row);}
 const relBox=document.getElementById("dbx-relations");relBox.replaceChildren();
 const rels=relationships(t);if(!rels.length)relBox.append(el("p","dbx-muted","No foreign-key relationships declared."));
 for(const f of rels){const row=el("div","dbx-relation");row.append(el("strong","",f.column+" → "+f.to+"."+f.targetColumn),el("div","", "ON DELETE "+f.onDelete));relBox.append(row);}
 const indexBox=document.getElementById("dbx-indexes");indexBox.replaceChildren();
 if(!t.indexes.length)indexBox.append(el("p","dbx-muted","No indexes found."));
 for(const ix of t.indexes){const row=el("div","dbx-index");row.append(el("strong","",ix.name),el("div","",(ix.unique?"UNIQUE · ":"")+ix.columns.join(", ")));indexBox.append(row);}
 pills.querySelectorAll(".dbx-pill").forEach(p=>p.classList.toggle("active",p.dataset.table===t.name));
 refreshNodeStyles();
}
function makeLabel(name){const d=el("div","dbx-node-label",name);return new CSS2DObject(d);}
function buildScene(){
 if(renderer){cancelAnimationFrame(raf);controls?.dispose();renderer.dispose();labels?.domElement.remove();renderer.domElement.remove();}
 graph.replaceChildren();scene=new THREE.Scene();scene.fog=new THREE.FogExp2(0x081525,.009);
 camera=new THREE.PerspectiveCamera(48,1,.1,500);camera.position.set(0,22,37);
 renderer=new THREE.WebGLRenderer({antialias:true,alpha:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.shadowMap.enabled=true;graph.append(renderer.domElement);
 labels=new CSS2DRenderer();labels.domElement.className="dbx-label-layer";graph.append(labels.domElement);
 controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.dampingFactor=.07;controls.minDistance=9;controls.maxDistance=90;
 scene.add(new THREE.AmbientLight(0xa8c9ed,1.7));const light=new THREE.DirectionalLight(0xffffff,2.1);light.position.set(12,22,15);scene.add(light);
 const rim=new THREE.PointLight(0x38bdf8,38,90);rim.position.set(-18,6,-15);scene.add(rim);
 const count=tables.length, radius=Math.max(11,Math.min(25,count*1.05));nodesByName.clear();pickables.length=0;
 const positions=new Map();
 tables.forEach((t,i)=>{const angle=(i/count)*Math.PI*2-Math.PI/2;const ring= i%3;const r=radius+(ring-1)*3;positions.set(t.name,new THREE.Vector3(Math.cos(angle)*r,((i%4)-1.5)*1.6,Math.sin(angle)*r));});
 const sphere=new THREE.SphereGeometry(1,28,22);
 tables.forEach(t=>{const pos=positions.get(t.name),group=new THREE.Group();group.position.copy(pos);group.userData.table=t;
  const hasPk=t.columns.some(c=>c.primaryKey),color=hasPk?palette.table:0x818cf8;
  const glow=new THREE.Mesh(new THREE.SphereGeometry(1.45,20,16),new THREE.MeshBasicMaterial({color,transparent:true,opacity:.10,depthWrite:false}));group.add(glow);
  const mesh=new THREE.Mesh(sphere,new THREE.MeshStandardMaterial({color,roughness:.27,metalness:.18,emissive:color,emissiveIntensity:.23}));mesh.scale.setScalar(Math.min(1.5,.82+t.columns.length*.035));mesh.userData.table=t;mesh.castShadow=true;group.add(mesh);pickables.push(mesh);
  const ringMesh=new THREE.Mesh(new THREE.TorusGeometry(1.22,.025,8,48),new THREE.MeshBasicMaterial({color,transparent:true,opacity:.55}));ringMesh.rotation.x=Math.PI/2.2;group.add(ringMesh);group.add(makeLabel(t.name));scene.add(group);nodesByName.set(t.name,group);
 });
 const edgeMat=new THREE.LineBasicMaterial({color:0x7893b4,transparent:true,opacity:.55});
 tables.forEach(t=>t.foreignKeys.forEach(f=>{const a=positions.get(t.name),b=positions.get(f.table);if(!b)return;const mid=a.clone().lerp(b,.5);mid.y+=2.5;const curve=new THREE.QuadraticBezierCurve3(a,mid,b);scene.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(curve.getPoints(24)),edgeMat));}));
 const grid=new THREE.GridHelper(radius*3,Math.max(12,count),0x27415e,0x142a42);grid.position.y=-8;grid.material.transparent=true;grid.material.opacity=.3;scene.add(grid);
 renderer.domElement.addEventListener("pointerdown",onPick);resize();animate();refreshNodeStyles();
}
function onPick(e){const r=renderer.domElement.getBoundingClientRect();pointer.set(((e.clientX-r.left)/r.width)*2-1,-((e.clientY-r.top)/r.height)*2+1);raycaster.setFromCamera(pointer,camera);const hit=raycaster.intersectObjects(pickables,false)[0];if(hit)inspect(hit.object.userData.table);}
function refreshNodeStyles(){for(const [name,g] of nodesByName){const mesh=g.children[1],active=selected?.name===name,linked=selected&&selected.foreignKeys.some(f=>f.table===name)||selected?.name===name&&selected.foreignKeys.length>0;mesh.material.emissiveIntensity=active?.8:linked?.45:.18;mesh.scale.setScalar(active?1.18:1);g.visible=matching(g.userData.table);g.children[g.children.length-1].visible=g.visible;}}
function resize(){if(!renderer||!stage.clientWidth)return;const w=Math.max(1,stage.clientWidth),h=Math.max(1,stage.clientHeight);camera.aspect=w/h;camera.updateProjectionMatrix();renderer.setSize(w,h,false);labels.setSize(w,h);}
function animate(){raf=requestAnimationFrame(animate);const t=performance.now()*.00035;for(const [name,g] of nodesByName)g.rotation.y=.1*Math.sin(t+name.length);controls.update();renderer.render(scene,camera);labels.render(scene,camera);}
function renderPills(){pills.replaceChildren();for(const t of tables.filter(matching)){const b=el("button","dbx-pill",t.name);b.type="button";b.dataset.table=t.name;b.addEventListener("click",()=>{inspect(t);const g=nodesByName.get(t.name);if(g){controls.target.copy(g.position);}});pills.append(b);}}
function renderList(){graph.replaceChildren();const list=el("div","dbx-list-view");for(const t of tables.filter(matching)){const b=el("button","dbx-list-card");b.type="button";b.append(el("strong","",t.name),el("span","",t.columns.length+" columns · "+t.foreignKeys.length+" relations"));b.addEventListener("click",()=>inspect(t));list.append(b);}graph.append(list);}
function applySearch(){renderPills();if(view==="list")renderList();else refreshNodeStyles();}
function setView(next){view=next;document.getElementById("dbx-3d").classList.toggle("active",next==="3d");document.getElementById("dbx-list").classList.toggle("active",next==="list");document.getElementById("dbx-hint").hidden=next==="list";if(next==="3d"){graph.replaceChildren();buildScene();}else{if(renderer){cancelAnimationFrame(raf);controls?.dispose();renderer.dispose();renderer=null;}graph.replaceChildren();renderList();}}
async function load(){try{const response=await fetch("/api/database/schema",{headers:{Accept:"application/json"}});if(!response.ok)throw new Error("Schema endpoint returned HTTP "+response.status);const payload=await response.json();tables=payload.tables.map(t=>({...t,columns:t.columns.map(c=>({...c,foreignKey:t.foreignKeys.some(f=>f.from===c.name)}))}));tableCount.textContent=payload.tableCount;relationCount.textContent=tables.reduce((sum,t)=>sum+t.foreignKeys.length,0);loading.hidden=true;if(!tables.length)throw new Error("No SQLite tables were found in the configured database.");renderPills();buildScene();inspect(tables[0]);}catch(err){loading.hidden=true;errorBox.hidden=false;errorBox.textContent="Could not load database schema: "+err.message;console.error("Database Explorer:",err);}}
search.addEventListener("input",()=>{query=search.value;applySearch();});
document.getElementById("dbx-3d").addEventListener("click",()=>setView("3d"));
document.getElementById("dbx-list").addEventListener("click",()=>setView("list"));
document.getElementById("dbx-reset").addEventListener("click",()=>{if(view!=="3d"){setView("3d");return;}camera.position.set(0,22,37);controls.target.set(0,0,0);controls.update();});
new ResizeObserver(resize).observe(stage);
load();
