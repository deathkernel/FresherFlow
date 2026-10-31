(() => {
"use strict";
const $=id=>document.getElementById(id);
const graph=$("dbx-graph"),stage=$("dbx-stage"),loading=$("dbx-loading"),errorBox=$("dbx-error"),search=$("dbx-search");
let tables=[],selected=null,mode="er",query="",resizeObserver;
const esc=v=>String(v??"");
const make=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;};
const set=(id,value)=>{$(id).textContent=value;};
const relCount=()=>tables.reduce((n,t)=>n+t.foreignKeys.length,0);
function filtered(){const q=query.trim().toLowerCase();return tables.filter(t=>!q||t.name.toLowerCase().includes(q)||t.columns.some(c=>c.name.toLowerCase().includes(q)||c.type.toLowerCase().includes(q)));}
function isIndexed(t,c){return t.indexes.some(i=>i.columns.includes(c.name));}
function renderMetrics(){
 set("dbx-table-count",tables.length);set("dbx-relation-count",relCount());
 set("dbx-total-columns",tables.reduce((n,t)=>n+t.columns.length,0));
 set("dbx-total-indexes",tables.reduce((n,t)=>n+t.indexes.length,0));
}
function fieldRow(t,c){
 const row=make("div","dbx-er-field"),name=make("span","dbx-er-field-name",c.name),type=make("span","dbx-er-field-type",c.type||"ANY"),badge=make("span","dbx-field-badge");
 if(c.primaryKey){badge.className+=" pk";badge.textContent="PK";}
 else if(c.foreignKey){badge.className+=" fk";badge.textContent="FK";}
 else if(isIndexed(t,c)){badge.className+=" ix";badge.textContent="IX";}
 row.append(name,type,badge);return row;
}
function card(t){
 const article=make("article","dbx-er-card"+(selected?.name===t.name?" selected":""));
 article.dataset.table=t.name;article.tabIndex=0;article.setAttribute("role","button");article.setAttribute("aria-label","Inspect table "+t.name);
 const head=make("div","dbx-er-card-head");head.append(make("span","dbx-er-table-icon","▦"),make("strong","",t.name),make("small","",t.columns.length+" COL"));
 const fields=make("div","dbx-er-fields"),shown=t.columns.slice(0,8);
 shown.forEach(c=>fields.append(fieldRow(t,c)));
 article.append(head,fields);
 if(t.columns.length>shown.length)article.append(make("div","dbx-er-more","+"+(t.columns.length-shown.length)+" more columns"));
 article.addEventListener("click",()=>inspect(t));article.addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();inspect(t);}});
 return article;
}
function drawEdges(grid,visible){
 grid.querySelector(".dbx-er-svg")?.remove();
 const width=grid.scrollWidth,height=grid.scrollHeight;
 const svg=document.createElementNS("http://www.w3.org/2000/svg","svg");
 svg.setAttribute("class","dbx-er-svg");svg.setAttribute("width",width);svg.setAttribute("height",height);svg.setAttribute("viewBox",`0 0 ${width} ${height}`);
 const defs=document.createElementNS(svg.namespaceURI,"defs"),marker=document.createElementNS(svg.namespaceURI,"marker");
 marker.setAttribute("id","dbx-arrow");marker.setAttribute("viewBox","0 0 10 10");marker.setAttribute("refX","9");marker.setAttribute("refY","5");marker.setAttribute("markerWidth","5");marker.setAttribute("markerHeight","5");marker.setAttribute("orient","auto-start-reverse");
 const arrow=document.createElementNS(svg.namespaceURI,"path");arrow.setAttribute("d","M 0 0 L 10 5 L 0 10 z");arrow.setAttribute("fill","#9ba8bc");marker.append(arrow);defs.append(marker);svg.append(defs);
 const rect=grid.getBoundingClientRect(),byName=new Map([...grid.querySelectorAll(".dbx-er-card")].map(el=>[el.dataset.table,el]));
 for(const t of visible){const from=byName.get(t.name);if(!from)continue;
  for(const fk of t.foreignKeys){const to=byName.get(fk.table);if(!to)continue;
   const a=from.getBoundingClientRect(),b=to.getBoundingClientRect();
   const x1=a.left-rect.left+a.width/2,y1=a.top-rect.top+a.height/2;
   const x2=b.left-rect.left+b.width/2,y2=b.top-rect.top+b.height/2;
   const dx=x2-x1,dy=y2-y1;const bend=Math.max(26,Math.min(90,Math.abs(dx)*.18));
   const path=document.createElementNS(svg.namespaceURI,"path");
   path.setAttribute("class","dbx-er-edge");
   path.setAttribute("d",`M ${x1} ${y1} C ${x1+Math.sign(dx||1)*bend} ${y1}, ${x2-Math.sign(dx||1)*bend} ${y2}, ${x2} ${y2}`);
   path.setAttribute("marker-end","url(#dbx-arrow)");
   if(selected&&(selected.name===t.name||selected.name===fk.table))path.setAttribute("style","stroke:#7669e8;stroke-width:2.5");
   svg.append(path);
  }
 }
 grid.prepend(svg);
}
function renderER(){
 graph.replaceChildren();const visible=filtered();set("dbx-visible-count",visible.length+" of "+tables.length+" tables");
 if(!visible.length){graph.append(make("div","dbx-empty","No tables or columns match your search."));return;}
 const grid=make("div","dbx-er-grid");visible.forEach(t=>grid.append(card(t)));graph.append(grid);
 requestAnimationFrame(()=>drawEdges(grid,visible));
}
function renderList(){
 graph.replaceChildren();const visible=filtered();set("dbx-visible-count",visible.length+" of "+tables.length+" tables");
 if(!visible.length){graph.append(make("div","dbx-empty","No tables or columns match your search."));return;}
 const list=make("div","dbx-list-view");
 visible.forEach(t=>{const b=make("button","dbx-list-card"+(selected?.name===t.name?" active":""));b.type="button";b.append(make("strong","",t.name),make("span","",t.columns.length+" columns · "+t.foreignKeys.length+" foreign keys · "+t.indexes.length+" indexes"));b.addEventListener("click",()=>inspect(t));list.append(b);});
 graph.append(list);
}
function render(){if(mode==="er")renderER();else renderList();}
function inspect(t){
 selected=t;set("dbx-detail-name",t.name);set("dbx-detail-summary",t.columns.length+" columns · "+t.foreignKeys.length+" outgoing relationships · "+t.indexes.length+" indexes");
 set("dbx-column-count",t.columns.length);set("dbx-fk-count",t.foreignKeys.length);set("dbx-index-count",t.indexes.length);set("dbx-column-label",t.columns.length+" fields");
 const columns=$("dbx-columns");columns.replaceChildren();
 t.columns.forEach(c=>{const row=make("div","dbx-column"),left=make("div"),title=make("strong",c.primaryKey?"dbx-key":c.foreignKey?"dbx-fk":"",c.name),meta=make("small","",[(c.notNull?"NOT NULL":""),c.default!==null?"DEFAULT "+c.default:"",isIndexed(t,c)?"INDEXED":""].filter(Boolean).join(" · ")||"Nullable");left.append(title,meta);row.append(left,make("code","",c.type||"ANY"));columns.append(row);});
 const rel=$("dbx-relations");rel.replaceChildren();set("dbx-rel-label",t.foreignKeys.length+" links");
 if(!t.foreignKeys.length)rel.append(make("p","dbx-muted","No outgoing foreign keys."));
 t.foreignKeys.forEach(f=>{const row=make("div","dbx-relation");const strong=make("strong","",f.from+"  →  "+f.table+"."+f.to);const detail=make("span","", "ON DELETE "+f.onDelete+" · ON UPDATE "+f.onUpdate);row.append(strong,detail);rel.append(row);});
 const indexes=$("dbx-indexes");indexes.replaceChildren();
 if(!t.indexes.length)indexes.append(make("p","dbx-muted","No indexes defined."));
 t.indexes.forEach(ix=>{const row=make("div","dbx-index");row.append(make("strong","",ix.name),make("span","",(ix.unique?"UNIQUE · ":"")+ix.columns.join(", ")));indexes.append(row);});
 render();
}
function setMode(next){mode=next;$("dbx-3d").classList.toggle("active",next==="er");$("dbx-list").classList.toggle("active",next==="list");set("dbx-view-title",next==="er"?"ENTITY RELATIONSHIP DIAGRAM":"DATABASE TABLE CATALOG");render();}
async function load(){
 try{
  const response=await fetch("/api/database/schema",{headers:{Accept:"application/json"}});
  if(!response.ok)throw new Error("Schema API returned HTTP "+response.status);
  const payload=await response.json();tables=(payload.tables||[]).map(t=>({...t,columns:(t.columns||[]).map(c=>({...c,foreignKey:(t.foreignKeys||[]).some(f=>f.from===c.name)}))}));
  renderMetrics();loading.hidden=true;
  if(!tables.length)throw new Error("No tables found in the configured SQLite database.");
  setMode("er");inspect(tables[0]);
 }catch(error){loading.hidden=true;errorBox.hidden=false;errorBox.textContent="Unable to read database schema: "+error.message;console.error("Database Studio:",error);}
}
search.addEventListener("input",()=>{query=search.value;render();});
$("dbx-3d").addEventListener("click",()=>setMode("er"));$("dbx-list").addEventListener("click",()=>setMode("list"));
if(window.ResizeObserver){resizeObserver=new ResizeObserver(()=>{if(mode==="er")renderER();});resizeObserver.observe(stage);}
load();
})();