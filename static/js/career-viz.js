(() => {
  const svg = document.querySelector('#career-map-svg');
  if (!svg) return;

  const skills = [
    {name:'Python', score:88, x:18, y:28},
    {name:'SQL', score:76, x:31, y:72},
    {name:'Cloud', score:68, x:69, y:72},
    {name:'Security', score:84, x:82, y:28},
    {name:'Git', score:91, x:52, y:12},
    {name:'Projects', score:73, x:52, y:88}
  ];
  const links = [[0,1],[0,4],[1,5],[2,5],[2,4],[3,4],[3,2],[4,5]];
  const ns = 'http://www.w3.org/2000/svg';
  const nodeLayer = svg.querySelector('#skill-nodes');
  const linkLayer = svg.querySelector('#skill-links');

  links.forEach(([a,b]) => {
    const line = document.createElementNS(ns,'line');
    line.classList.add('viz-link');
    line.dataset.a=a; line.dataset.b=b;
    linkLayer.appendChild(line);
  });

  skills.forEach((s, i) => {
    const g = document.createElementNS(ns,'g');
    g.classList.add('skill-node');
    g.dataset.skill = i;
    g.setAttribute('tabindex','0');
    g.setAttribute('role','button');
    g.setAttribute('aria-label', `${s.name}, ${s.score}% readiness`);
    const circle = document.createElementNS(ns,'circle');
    circle.setAttribute('r', i === 4 ? 28 : 25);
    const text = document.createElementNS(ns,'text');
    text.setAttribute('y','-2'); text.textContent=s.name;
    const score = document.createElementNS(ns,'text');
    score.classList.add('score'); score.setAttribute('y','12'); score.textContent=`${s.score}%`;
    g.append(circle,text,score); nodeLayer.appendChild(g);
  });

  function position() {
    const box = svg.viewBox.baseVal;
    const w = box.width || 700, h = box.height || 480;
    const px = p => (p / 100) * w;
    const py = p => (p / 100) * h;
    svg.querySelectorAll('.skill-node').forEach((g,i)=>g.setAttribute('transform',`translate(${px(skills[i].x)} ${py(skills[i].y)})`));
    linkLayer.querySelectorAll('line').forEach(line=>{
      const a=Number(line.dataset.a), b=Number(line.dataset.b);
      line.setAttribute('x1',px(skills[a].x)); line.setAttribute('y1',py(skills[a].y));
      line.setAttribute('x2',px(skills[b].x)); line.setAttribute('y2',py(skills[b].y));
    });
  }

  function select(index) {
    svg.querySelectorAll('.skill-node').forEach(g=>g.classList.toggle('selected', Number(g.dataset.skill)===index));
    svg.querySelectorAll('.viz-link').forEach(l=>l.classList.toggle('hot', Number(l.dataset.a)===index || Number(l.dataset.b)===index));
    const label=document.querySelector('#viz-focus');
    if(label) label.textContent=`Focus: ${skills[index].name} · ${skills[index].score}% readiness`;
  }

  svg.querySelectorAll('.skill-node').forEach(g=>{
    g.addEventListener('click',()=>select(Number(g.dataset.skill)));
    g.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();select(Number(g.dataset.skill));}});
  });

  document.querySelectorAll('.viz-filter').forEach(btn=>btn.addEventListener('click',()=>{
    document.querySelectorAll('.viz-filter').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');
    const mode=btn.dataset.mode;
    skills.forEach((s,i)=>{
      const g=svg.querySelector(`[data-skill="${i}"]`);
      const match=mode==='all'||(mode==='strength'&&s.score>=80)||(mode==='gap'&&s.score<80);
      g.style.opacity=match?'1':'.18';
    });
  }));

  const reveal=document.querySelectorAll('.career-viz-section .reveal');
  const observer='IntersectionObserver' in window ? new IntersectionObserver(entries=>entries.forEach(entry=>{if(entry.isIntersecting){entry.target.classList.add('is-visible');observer.unobserve(entry.target)}}),{threshold:.12}) : null;
  reveal.forEach(el=>observer?observer.observe(el):el.classList.add('is-visible'));
  position(); select(0);
  window.addEventListener('resize',position,{passive:true});
})();