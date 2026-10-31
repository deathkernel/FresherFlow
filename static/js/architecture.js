import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.160.0/+esm";
import { OrbitControls } from "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/controls/OrbitControls.js/+esm";
import { CSS2DRenderer, CSS2DObject } from "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/renderers/CSS2DRenderer.js/+esm";

const canvas=document.getElementById("ff3d-canvas");
if (!canvas) throw new Error("FresherFlow 3D canvas element was not found.");
const stage=document.getElementById("ff3d-stage");
const loading=document.getElementById("ff3d-loading");
const scene=new THREE.Scene();
scene.fog=new THREE.FogExp2(0x091323,.012);
const camera=new THREE.PerspectiveCamera(48,1,.1,500);
camera.position.set(22,19,31);
const renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,2));
renderer.shadowMap.enabled=true;
renderer.shadowMap.type=THREE.PCFSoftShadowMap;
const labels=new CSS2DRenderer();
labels.domElement.style.position="absolute";labels.domElement.style.inset="0";labels.domElement.style.pointerEvents="none";
stage.appendChild(labels.domElement);
const controls=new OrbitControls(camera,renderer.domElement);
controls.enableDamping=true;controls.dampingFactor=.06;controls.minDistance=10;controls.maxDistance=75;
controls.target.set(0,0,0);
scene.add(new THREE.AmbientLight(0x9bb8dc,1.7));
const key=new THREE.DirectionalLight(0xffffff,2.4);key.position.set(12,24,18);key.castShadow=true;scene.add(key);
const rim=new THREE.PointLight(0x38bdf8,45,70);rim.position.set(-16,4,-10);scene.add(rim);
const colors={role:0x60a5fa,service:0xa78bfa,data:0x34d399,security:0xfb923c,ui:0xf472b6,core:0xe2e8f0};
const nodes=[
{id:"core",name:"FresherFlow Core",type:"SYSTEM",kind:"core",path:"app.py",desc:"Flask application factory, configuration, request lifecycle, registered blueprints and top-level portal redirects.",pos:[0,0,0],size:2.15},
{id:"student",name:"Student Portal",type:"ROLE",kind:"role",path:"routes/student_routes.py",desc:"Student profiles, resume handling, opportunity discovery, saved jobs, applications, career planning and interview views.",pos:[-12,4,8]},
{id:"employer",name:"Employer Portal",type:"ROLE",kind:"role",path:"routes/employer_routes.py",desc:"Employer profiles, vacancy creation and bulk import, vacancy management, candidate applications and interview scheduling.",pos:[12,4,8]},
{id:"college",name:"College Portal",type:"ROLE",kind:"role",path:"routes/college_routes.py · routes/college_admin_routes.py",desc:"College representative workflows: student account creation, enrollment information and college-side verification.",pos:[-12,4,-8]},
{id:"admin",name:"Admin Portal",type:"ROLE",kind:"role",path:"routes/admin_routes.py · routes/admin_setup_routes.py",desc:"Platform administration, vacancy moderation, employer management, student verification, reporting and audit review.",pos:[12,4,-8]},
{id:"auth",name:"Authentication",type:"ROUTE MODULE",kind:"service",path:"routes/auth_routes.py",desc:"Student/employer authentication and session entry points, with role-aware access.",pos:[0,8,12]},
{id:"platform",name:"Platform Routes",type:"ROUTE MODULE",kind:"service",path:"routes/platform_routes.py",desc:"Shared platform-level endpoints and cross-role capabilities.",pos:[0,-5,12]},
{id:"settings",name:"Settings",type:"ROUTE MODULE",kind:"service",path:"routes/settings_routes.py",desc:"User preferences and account settings endpoints.",pos:[-4,-7,2]},
{id:"seo",name:"SEO Routes",type:"ROUTE MODULE",kind:"service",path:"routes/seo_routes.py",desc:"SEO-facing routes such as robots and sitemap support.",pos:[4,-7,2]},
{id:"db",name:"SQLite Database",type:"DATA LAYER",kind:"data",path:"database/database.py · database/schema.sql",desc:"SQLite persistence, schema and migrations. Stores users, profiles, vacancies, applications, colleges, verification requests, interviews and supporting records.",pos:[0,0,-14],size:2},
{id:"security",name:"Security Layer",type:"SECURITY",kind:"security",path:"security.py · app.py · config.py",desc:"CSRF validation, secure sessions, password hashing, login throttling, upload validation, security headers and production configuration checks.",pos:[-9,-5,-12],size:1.55},
{id:"templates",name:"Jinja Templates",type:"UI LAYER",kind:"ui",path:"templates/",desc:"Server-rendered screens grouped into student, employer, college and admin experiences, plus shared and public pages.",pos:[13,-5,-12],size:1.7},
{id:"static",name:"Static Assets",type:"UI LAYER",kind:"ui",path:"static/css/ · static/js/ · static/img/",desc:"Stylesheets, browser-side scripts and image assets used by the rendered interface.",pos:[17,-7,-3],size:1.35},
{id:"tests",name:"Automated Tests",type:"QUALITY",kind:"service",path:"tests/ · .github/workflows/",desc:"Pytest workflow, browser accessibility coverage, security tests and GitHub Actions CI.",pos:[-17,-6,-3],size:1.55},
{id:"storage",name:"Private Uploads",type:"STORAGE",kind:"data",path:"uploads/resumes/ · uploads/college-verification/",desc:"Private filesystem storage for resume and college verification uploads, outside the static executable asset directory.",pos:[-15,0,0],size:1.35}
];
const edges=[
["core","student"],["core","employer"],["core","college"],["core","admin"],["core","auth"],["core","platform"],["core","settings"],["core","seo"],["core","security"],["core","templates"],["templates","static"],["student","db"],["employer","db"],["college","db"],["admin","db"],["auth","db"],["platform","db"],["settings","db"],["admin","security"],["auth","security"],["student","storage"],["college","storage"],["tests","core"],["tests","security"],["tests","db"]
];
const nodeMap=new Map(),pickables=[];
const sphereGeo=new THREE.SphereGeometry(1,36,28);
const glowGeo=new THREE.SphereGeometry(1.18,24,18);
const lineMaterial=(color)=>new THREE.LineBasicMaterial({color,transparent:true,opacity:.32});
function makeLabel(text){
 const el=document.createElement("div");el.className="ff3d-label";el.textContent=text;
 Object.assign(el.style,{color:"#dbeafe",font:"600 11px Inter,system-ui,sans-serif",letterSpacing:".02em",textShadow:"0 2px 8px #020617,0 0 12px #020617",whiteSpace:"nowrap",padding:"3px 6px",background:"rgba(8,15,30,.48)",borderRadius:"5px"});
 return new CSS2DObject(el);
}
for(const n of nodes){
 const color=colors[n.kind],group=new THREE.Group();group.position.set(...n.pos);group.userData.node=n;
 const glow=new THREE.Mesh(glowGeo,new THREE.MeshBasicMaterial({color,transparent:true,opacity:.09,depthWrite:false}));glow.scale.setScalar(n.size||1);group.add(glow);
 const mesh=new THREE.Mesh(sphereGeo,new THREE.MeshStandardMaterial({color,roughness:.24,metalness:.24,emissive:color,emissiveIntensity:.18}));mesh.scale.setScalar(n.size||1);mesh.castShadow=true;mesh.receiveShadow=true;mesh.userData.node=n;group.add(mesh);
 const ring=new THREE.Mesh(new THREE.TorusGeometry((n.size||1)*1.35,.025,8,80),new THREE.MeshBasicMaterial({color,transparent:true,opacity:.5}));ring.rotation.x=Math.PI/2.4;group.add(ring);
 group.add(makeLabel(n.name));scene.add(group);nodeMap.set(n.id,group);pickables.push(mesh);
}
for(const [a,b] of edges){
 const A=new THREE.Vector3(...nodes.find(n=>n.id===a).pos),B=new THREE.Vector3(...nodes.find(n=>n.id===b).pos);
 const curve=new THREE.QuadraticBezierCurve3(A,A.clone().lerp(B,.5).add(new THREE.Vector3(0,1.3,0)),B);
 scene.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(curve.getPoints(32)),lineMaterial(colors[nodes.find(n=>n.id===a).kind])));
}
const grid=new THREE.GridHelper(52,26,0x24415f,0x142942);grid.position.y=-9;grid.material.transparent=true;grid.material.opacity=.27;scene.add(grid);
const starGeo=new THREE.BufferGeometry(),starPositions=[];
for(let i=0;i<700;i++)starPositions.push((Math.random()-.5)*100,(Math.random()-.5)*65,(Math.random()-.5)*100);
starGeo.setAttribute("position",new THREE.Float32BufferAttribute(starPositions,3));
scene.add(new THREE.Points(starGeo,new THREE.PointsMaterial({color:0x8dbbe8,size:.055,transparent:true,opacity:.55})));
const raycaster=new THREE.Raycaster(),pointer=new THREE.Vector2();
function inspect(n){
 document.getElementById("ff3d-node-title").textContent=n.name;
 document.getElementById("ff3d-node-desc").textContent=n.desc;
 document.getElementById("ff3d-node-type").textContent=n.type;
 document.getElementById("ff3d-node-path").textContent=n.path;
 const connected=edges.filter(e=>e.includes(n.id)).map(e=>nodes.find(x=>x.id===(e[0]===n.id?e[1]:e[0])).name);
 document.getElementById("ff3d-node-links").textContent=connected.length;
 document.getElementById("ff3d-node-related").replaceChildren(...connected.map(name=>{const s=document.createElement("span");s.className="ff3d-chip";s.textContent=name;return s;}));
 for(const [id,g] of nodeMap){const m=g.children[1];m.material.emissiveIntensity=id===n.id?.75:.18;m.scale.setScalar((nodes.find(x=>x.id===id).size||1)*(id===n.id?1.13:1));}
}
inspect(nodes[0]);
renderer.domElement.addEventListener("pointerdown",e=>{
 const r=renderer.domElement.getBoundingClientRect();pointer.x=((e.clientX-r.left)/r.width)*2-1;pointer.y=-((e.clientY-r.top)/r.height)*2+1;
 raycaster.setFromCamera(pointer,camera);const hit=raycaster.intersectObjects(pickables,false)[0];if(hit)inspect(hit.object.userData.node);
});
document.getElementById("ff3d-reset").addEventListener("click",()=>{camera.position.set(22,19,31);controls.target.set(0,0,0);controls.update();inspect(nodes[0]);});
let showLabels=true;
document.getElementById("ff3d-labels").addEventListener("click",e=>{showLabels=!showLabels;for(const g of nodeMap.values())g.children[g.children.length-1].visible=showLabels;e.currentTarget.textContent=showLabels?"Hide labels":"Show labels";e.currentTarget.setAttribute("aria-pressed",String(showLabels));});
function resize(){const w=stage.clientWidth,h=stage.clientHeight;camera.aspect=w/h;camera.updateProjectionMatrix();renderer.setSize(w,h,false);labels.setSize(w,h);}
new ResizeObserver(resize).observe(stage);resize();loading.style.display="none";
const clock=new THREE.Clock();
function animate(){requestAnimationFrame(animate);const t=clock.getElapsedTime();for(const [id,g] of nodeMap){g.rotation.y=.12*Math.sin(t*.45+id.length);g.children[0].scale.setScalar((nodes.find(n=>n.id===id).size||1)*(1+.035*Math.sin(t*1.5+id.length)));}controls.update();renderer.render(scene,camera);labels.render(scene,camera);}
animate();