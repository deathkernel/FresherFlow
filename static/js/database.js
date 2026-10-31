(() => {
"use strict";
const $=id=>document.getElementById(id);
const viewport=$("dbx-canvas-viewport"),scene=$("dbx-canvas-scene"),edges=$("dbx-edges"),nodes=$("dbx-nodes");
const sidebar=$("dbx-sidebar-tables"),loading=$("dbx-loading"),errorBox=$("dbx-error"),search=$("dbx-search");
let tables=[],selected=null,mode="diagram",query="",sceneWidth=1000,sceneHeight=1000,zoom=1;
const make=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;};
const set=(id,value)=>{$(id).textContent=value;};
const groups=[
 {name:"Identity & access",match:n=>["users","auth_attempts","user_preferences"].includes(n)},
 {name:"Profiles",match:n=>["student_profiles","employer_profiles"].includes(n)},
 {name:"Hiring workflow",match:n=>["vacancies","applications","saved_jobs","interviews"].includes(n)},
 {name:"College & verification",match:n=>["colleges","college_verifiers","college_student_accounts","student_verification_requests"].includes(n)},
 {name:"Engagement",match:n=>["notifications","messages","career_tasks"].includes(n)},
 {name:"Platform",match:n=>["audit_log","schema_migrations"].includes(n)}
];
function groupOf(name){return groups.find(g=>g.match(name))?.name||"Other";}
function sortedTables(){return [...tables].sort((a,b)=>groups.findIndex(g=>g.name===groupOf(a.name))-groups.findIndex(g=>g.name===groupOf(b.name))||a.name.localeCompare(b.name));}
function visibleTables(){const q=query.trim().toLowerCase();return sortedTables().filter(t=>!q||t.name.toLowerCase().includes(q)||t.columns.some(c=>c.name.toLowerCase().includes(q)||c.type.toLowerCase().includes(q)));}
function isIndexed(t,c){return t.indexes.some(ix=>ix.columns.includes(c.name));}
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
 set("dbx-sidebar-count",tables.length+" objects");
}
function renderSidebar(){
 sidebar.replaceChildren();const shown=visibleTables();let last="";
 for(const t of shown){
  const group=groupOf(t.name);if(group!==last){sidebar.append(make("div","dbs-group-label",group));last=group;}
  const b=make("button","dbs-table-link"+(selected?.name===t.name?" active":""));b.type="button";b.dataset.table=t.name;
  b.append(make("span","dbs-table-glyph","▦"),make("span","",t.name),make("small","",String(t.columns.length)));
  b.addEventListener("click",()=>inspect(t));sidebar.append(b);
 }
 if(!shown.length)sidebar.append(make("p","dbs-empty","No matching tables."));
}
function renderField(t,c){
 const row=make("div","dbs-field-row");
 row.append(make("span","dbs-field-name",c.name),make("span","dbs-field-type",c.type||"ANY"));
 let mark="";if(c.primaryKey)mark="PK";else if(c.foreignKey)mark="FK";else if(isIndexed(t,c))mark="IX";
 row.append(make("span","dbs-field-key "+(mark.toLowerCase()),mark));return row;
}
function renderCard(t,x,y){
 const card=make("button","dbs-table-card"+(selected?.name===t.name?" active":""));card.type="button";card.dataset.table=t.name;card.style.left=x+"px";card.style.top=y+"px";
 const head=make("div","dbs-card-head");head.append(make("span","dbs-card-icon","▦"),make("strong","dbs-card-title",t.name),make("small","dbs-card-group",groupOf(t.name)));
 const body=make("div","");t.columns.slice(0,7).forEach(c=>body.append(renderField(t,c)));
 card.append(head,body);
 if(t.columns.length>7)card.append(make("div","dbs-card-more","+"+(t.columns.length-7)+" more columns"));
 card.addEventListener("click",()=>inspect(t));return card;
}
function renderDiagram(){
 nodes.replaceChildren();edges.replaceChildren();
 const shown=visibleTables();const columns=window.innerWidth>1350?3:2;
 const cardW=255,gapX=38,gapY=34,marginX=32,marginY=28,rowPitch=275;
 const rows=Math.ceil(shown.length/columns);
 sceneWidth=Math.max(viewport.clientWidth,marginX*2+columns*cardW+(columns-1)*gapX);
 sceneHeight=Math.max(viewport.clientHeight,marginY*2+rows*rowPitch+30);
 scene.style.width=sceneWidth+"px";scene.style.height=sceneHeight+"px";
 nodes.style.width=sceneWidth+"px";nodes.style.height=sceneHeight+"px";
 edges.setAttribute("width",sceneWidth);edges.setAttribute("height",sceneHeight);edges.setAttribute("viewBox",`0 0 ${sceneWidth} ${sceneHeight}`);
 const positions=new Map();
 shown.forEach((t,i)=>{
  const col=i%columns,row=Math.floor(i/columns),x=marginX+col*(cardW+gapX),y=marginY+row*rowPitch;
  positions.set(t.name,{x,y});nodes.append(renderCard(t,x,y));
 });
 drawEdges(shown,positions);applyZoom();
 set("dbx-visible-count",shown.length+" / "+tables.length+" tables");
}
function svgEl(name){return document.createElementNS("http://www.w3.org/2000/svg",name);}
function drawEdges(shown,positions){
 edges.replaceChildren();
 const defs=svgEl("defs");
 for(const [id,color] of [["dbs-arrow","#a5afbf"],["dbs-arrow-active","#766ae2"]]){
  const marker=svgEl("marker");marker.setAttribute("id",id);marker.setAttribute("viewBox","0 0 10 10");marker.setAttribute("refX","8");marker.setAttribute("refY","5");marker.setAttribute("markerWidth","5");marker.setAttribute("markerHeight","5");marker.setAttribute("orient","auto");
  const p=svgEl("path");p.setAttribute("d","M0 1L9 5L0 9Z");p.setAttribute("fill",color);marker.append(p);defs.append(marker);
 }
 edges.append(defs);
 const cards=new Map([...nodes.querySelectorAll(".dbs-table-card")].map(el=>[el.dataset.table,el]));
 for(const t of shown)for(const fk of t.foreignKeys){
  if(!positions.has(fk.table))continue;
  const a=positions.get(t.name),b=positions.get(fk.table),dx=b.x-a.x,dy=b.y-a.y;
  let sx,sy,ex,ey,d;
  if(Math.abs(dx)>=Math.abs(dy)){
   const dir=dx>=0?1:-1;sx=a.x+(dir>0?255:0);sy=a.y+60;ex=b.x+(dir>0?0:255);ey=b.y+60;
   const bend=Math.max(28,Math.min(90,Math.abs(ex-sx)*.42));
   d=`M${sx} ${sy} C${sx+dir*bend} ${sy},${ex-dir*bend} ${ey},${ex} ${ey}`;
  }else{
   const dir=dy>=0?1:-1;sx=a.x+127.5;sy=a.y+(dir>0?cardHeight(cards.get(t.name)):0);ex=b.x+127.5;ey=b.y+(dir>0?0:cardHeight(cards.get(fk.table)));
   const bend=Math.max(28,Math.min(85,Math.abs(ey-sy)*.4));
   d=`M${sx} ${sy} C${sx} ${sy+dir*bend},${ex} ${ey-dir*bend},${ex} ${ey}`;
  }
  const active=!!selected&&(selected.name===t.name||selected.name===fk.table);
  const path=svgEl("path");path.setAttribute("class","dbs-edge "+(active?"active":"dim"));path.setAttribute("d",d);path.setAttribute("marker-end",active?"url(#dbs-arrow-active)":"url(#dbs-arrow)");edges.append(path);
  if(active){
   const label=svgEl("text");label.setAttribute("class","dbs-edge-label");label.setAttribute("x",(sx+ex)/2);label.setAttribute("y",(sy+ey)/2-5);label.setAttribute("text-anchor","middle");label.textContent=(fk.from+" → "+fk.table+"."+fk.to).slice(0,40);edges.append(label);
  }
 }
}
function cardHeight(card){return card?card.getBoundingClientRect().height/zoom:205;}
function applyZoom(){scene.style.transform=`scale(${zoom})`;set("dbx-zoom-label",Math.round(zoom*100)+"%");}
function renderInspector(t){
 set("dbx-detail-name",t.name);set("dbx-object-badge","TABLE");
 set("dbx-detail-summary",groupOf(t.name)+" · "+t.columns.length+" columns");
 set("dbx-column-count",t.columns.length);set("dbx-fk-count",t.foreignKeys.length);set("dbx-index-count",t.indexes.length);
 const columns=$("dbx-columns");columns.replaceChildren();
 t.columns.forEach(c=>{
  const row=make("div","dbs-column"),left=make("div");
  const mark=c.primaryKey?"PRIMARY KEY":c.foreignKey?"FOREIGN KEY":isIndexed(t,c)?"INDEXED":"";
  left.append(make("strong",c.primaryKey?"dbs-key":c.foreignKey?"dbs-fk":"",c.name),make("small","",[(c.notNull?"NOT NULL":""),c.default!==null?"DEFAULT "+c.default:"",mark].filter(Boolean).join(" · ")||"Nullable"));
  row.append(left,make("code","",c.type||"ANY"));columns.append(row);
 });
 const rel=relationList(t);set("dbx-rel-label",rel.length+" links");
 const relBox=$("dbx-relations");relBox.replaceChildren();
 if(!rel.length)relBox.append(make("p","dbs-empty","No foreign-key links."));
 rel.forEach(r=>{const row=make("div","dbs-relation");row.append(make("strong","",r.direction+": "+r.column+" → "+r.target+"."+r.targetColumn),make("span","", "ON DELETE "+r.onDelete));relBox.append(row);});
 const ix=$("dbx-indexes");ix.replaceChildren();
 if(!t.indexes.length)ix.append(make("p","dbs-empty","No indexes defined."));
 t.indexes.forEach(i=>{const row=make("div","dbs-index");row.append(make("strong","",i.name),make("span","",(i.unique?"UNIQUE · ":"")+i.columns.join(", ")));ix.append(row);});
 renderSidebar();
 if(mode==="diagram")renderDiagram();else renderMode();
}
function renderCatalog(){
 const host=$("dbx-catalog-view");host.replaceChildren();const grid=make("div","dbs-catalog-grid");
 visibleTables().forEach(t=>{const b=make("button","dbs-catalog-card"+(selected?.name===t.name?" active":""));b.type="button";b.append(make("b","",t.name),make("span","",groupOf(t.name)),make("span","",t.columns.length+" columns · "+t.foreignKeys.length+" foreign keys · "+t.indexes.length+" indexes"));b.addEventListener("click",()=>inspect(t));grid.append(b);});
 if(!visibleTables().length)grid.append(make("p","dbs-empty","No matching tables."));host.append(grid);
}
function renderSQL(){
 const host=$("dbx-sql-view");host.replaceChildren();
 if(!selected){host.append(make("div","dbs-sql-empty","Select a table first."));return;}
 const pre=make("pre","",selected.sql||"-- No CREATE TABLE statement available.");
 host.append(pre);
}
function renderMode(){
 $("dbx-canvas-scene").hidden=mode!=="diagram";$("dbx-catalog-view").hidden=mode!=="catalog";$("dbx-sql-view").hidden=mode!=="sql";
 $("dbx-diagram").classList.toggle("active",mode==="diagram");$("dbx-catalog").classList.toggle("active",mode==="catalog");$("dbx-ddl").classList.toggle("active",mode==="sql");
 set("dbx-view-title",mode==="diagram"?"RELATIONSHIP DIAGRAM":mode==="catalog"?"TABLE CATALOG":"SQL DEFINITION");
 if(mode==="catalog")renderCatalog();if(mode==="sql")renderSQL();if(mode==="diagram")renderDiagram();
}
function inspect(t){selected=t;renderInspector(t);}
function setMode(next){mode=next;renderMode();}
function fitView(){if(!sceneWidth)return;zoom=Math.max(.45,Math.min(1,(viewport.clientWidth-24)/sceneWidth));applyZoom();viewport.scrollLeft=0;viewport.scrollTop=0;}
function bindPan(){
 let down=false,x=0,y=0,left=0,top=0;
 viewport.addEventListener("pointerdown",e=>{if(e.target.closest(".dbs-table-card"))return;down=true;x=e.clientX;y=e.clientY;left=viewport.scrollLeft;top=viewport.scrollTop;viewport.classList.add("panning");});
 window.addEventListener("pointerup",()=>{down=false;viewport.classList.remove("panning");});
 window.addEventListener("pointermove",e=>{if(!down)return;viewport.scrollLeft=left-(e.clientX-x);viewport.scrollTop=top-(e.clientY-y);});
}
async function load(){
 try{
  const response=await fetch("/api/database/schema",{headers:{Accept:"application/json"},cache:"no-store"});
  if(!response.ok)throw new Error("Schema API returned HTTP "+response.status);
  const payload=await response.json();
  tables=(payload.tables||[]).map(t=>({...t,columns:(t.columns||[]).map(c=>({...c,foreignKey:(t.foreignKeys||[]).some(f=>f.from===c.name)})),foreignKeys:t.foreignKeys||[],indexes:t.indexes||[]}));
  if(!tables.length)throw new Error("No tables found in the configured SQLite database.");
  renderMetrics();loading.hidden=true;renderSidebar();selected=tables.find(t=>t.name==="users")||tables[0];renderInspector(selected);fitView();
 }catch(error){loading.hidden=true;errorBox.hidden=false;errorBox.textContent="Could not load schema: "+error.message;console.error("Database Studio:",error);}
}
search.addEventListener("input",()=>{query=search.value;renderSidebar();if(mode==="diagram")renderDiagram();else renderMode();});
$("dbx-diagram").addEventListener("click",()=>setMode("diagram"));$("dbx-catalog").addEventListener("click",()=>setMode("catalog"));$("dbx-ddl").addEventListener("click",()=>setMode("sql"));
$("dbx-zoom-in").addEventListener("click",()=>{zoom=Math.min(1.5,zoom+.1);applyZoom();});
$("dbx-zoom-out").addEventListener("click",()=>{zoom=Math.max(.4,zoom-.1);applyZoom();});
$("dbx-fit").addEventListener("click",fitView);
bindPan();window.addEventListener("resize",()=>{if(mode==="diagram")fitView();});
load();
})();