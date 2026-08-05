/* 国缆杯学习系统 · 纯前端 SPA（静态部署版）
 * 消费侧全部前端化：自测/学习/闪卡/术语/出卷/大纲/反馈。
 * 判分复用 engine/grade.js（window.Grade），与后端 generate.py 同源。
 * 进度/反馈存 localStorage；生成卷存 sessionStorage。 */
(function(){
"use strict";
const $ = (s,r)=> (r||document).querySelector(s);
const app = $("#app");

// ---------- 资产清单（已知静态产物） ----------
const ASSETS = {
  banks: {
    "gbt_2951_kb_mvp":  {file:"data/gbt_2951_kb_mvp.json",  name:"GB/T 2951.13/21/31/32 标准条款卷(100分)"},
    "gbt_2951_11_12":   {file:"data/gbt_2951_11_12.json",   name:"GB/T 2951.11/12 卷"}
  },
  study: { "gbt_2951_materials": {file:"data/gbt_2951_materials.json", name:"GB/T 2951 学习材料"} },
  decks: { "gbt_2951_flashcards":{file:"data/gbt_2951_flashcards.json", name:"GB/T 2951 闪卡(18张)"} },
  term:  "data/terminology_v1.json",
  syll:  "data/syllabus_2026.json"
};
const cache = {};
function load(k){ return cache[k] || (cache[k]=fetch(k).then(r=>{if(!r.ok)throw new Error(r.status);return r.json();})); }
function esc(s){ return String(s==null?"":s).replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c])); }
function stdOf(src){ if(!src)return "其他"; const m=String(src).match(/GB\/T\s*\d+(?:\.\d+)?(?:-\d+)?/i); return m?m[0].toUpperCase().replace(/\s/g,""):"其他"; }

// ---------- 路由 ----------
function parseHash(){
  let h=location.hash.replace(/^#\/?/,"");
  let [path,qs]=h.split("?");
  const q={}; (qs||"").split("&").forEach(p=>{if(p){const[i,v]=p.split("=");q[i]=decodeURIComponent(v||"");}});
  return {path:path||"home", q};
}
function nav(){ const {path,q}=parseHash();
  document.querySelectorAll(".bar a").forEach(a=>a.classList.toggle("on", a.dataset.r===path));
  const map={home:home, exam:exam, study:study, flashcards:flashcards, terminology:terminology, builder:builder, syllabus:syllabus, feedback:feedback};
  (map[path]||home)(q);
}

// ---------- 首页 ----------
function home(){
  app.innerHTML=`<h1>国缆检测杯 · 在线学习考试系统</h1>
  <p class="sub">大模型出题 + 脚本判分 · 静态部署版（进度/反馈存本机浏览器）</p>
  <div class="note">提示：本在线版为纯前端分享版，自测/学习/闪卡/术语/出卷/大纲全部可用；闭卷防作弊考试、跨设备成绩同步需本机服务端。数据基于 GB/T 2951 系列已验证题库。</div>
  <div class="grid">
    ${tile("#/exam?bank=gbt_2951_kb_mvp","📝 自测卷","做一套题，交卷即时判分看错题")}
    ${tile("#/study?m=gbt_2951_materials","📖 学习页","标准条款解读、Quiz、记忆要点")}
    ${tile("#/flashcards?deck=gbt_2951_flashcards","🃏 闪卡","浏览模式+学习模式(SM-2间隔重复)")}
    ${tile("#/terminology","🔤 术语库","70条电缆检验术语，搜索+分类")}
    ${tile("#/builder","🎯 出卷器","按标准号设权重，一键抽题组卷")}
    ${tile("#/syllabus","📋 考试大纲","2026竞赛复习大纲125条知识点")}
    ${tile("#/feedback","💬 反馈","报错/建议收集（形成本地日志）")}
  </div>`;
}
function tile(h,t,d){return `<a class="tile" href="${h}"><h3>${t}</h3><p>${d}</p></a>`;}

// ---------- 自测卷 ----------
async function exam(q){
  let bank;
  if(q.inline==="1"){ try{bank=JSON.parse(sessionStorage.getItem("genBank")||"null");}catch(e){} }
  if(!bank && q.bank && ASSETS.banks[q.bank]){ bank=await load(ASSETS.banks[q.bank].file); }
  if(!bank){ return builder(); }
  const title = (q.bank&&ASSETS.banks[q.bank])?ASSETS.banks[q.bank].name:"自定义组卷";
  const A={choice:{},judge:{},fill:{},calc:{}};
  let html=`<h1>自测卷</h1><p class="sub">${esc(title)}　·　纯脚本判分（不调大模型）</p><div id="qs">`;
  (bank.choice||[]).forEach((it,i)=>{
    html+=`<div class="q"><span class="pts">${it.points||2}分</span><div class="stem">${i+1}. ${esc(it.q)}</div>`;
    it.options.forEach((o,oi)=>{html+=`<label class="opt"><input type="radio" name="c_${it.id}" value="${oi}" onchange="W['setC']('${it.id}',${oi})">${esc(o)}</label>`;});
    html+=`</div>`;
  });
  (bank.judge||[]).forEach((it,i)=>{
    html+=`<div class="q"><span class="pts">${it.points||1}分</span><div class="stem">${i+1+(bank.choice||[]).length}. ${esc(it.q)}</div>
      <span class="tf" onclick="W['setJ']('${it.id}',true,this)">✓ 对</span>
      <span class="tf" onclick="W['setJ']('${it.id}',false,this)">✗ 错</span></div>`;
  });
  (bank.fill||[]).forEach((it,i)=>{
    html+=`<div class="q"><span class="pts">${it.points||2}分</span><div class="stem">${i+1+(bank.choice||[]).length+(bank.judge||[]).length}. ${esc(it.q)}</div><div>`;
    for(let k=0;k<(it.answers||[]).length;k++) html+=`<input type="text" placeholder="空${k+1}" onchange="W['setF']('${it.id}',${k},this.value)"> `;
    html+=`</div></div>`;
  });
  (bank.calc||[]).forEach((it,i)=>{
    html+=`<div class="q"><span class="pts">计算</span><div class="stem">${esc(it.title||"计算题")}</div><div class="muted" style="margin:6px 0">${esc(it.stem)}</div>`;
    (it.subs||[]).forEach((s,si)=>{ html+=`<div class="calcsub"><span class="lb">${esc(s[0])}</span><input type="text" placeholder="填结果" onchange="W['setCalc']('${it.id}',${si},this.value)"> <span class="muted">(${s[3]}分)</span></div>`; });
    html+=`</div>`;
  });
  html+=`</div><div class="barfix"><button class="b" onclick="W['grade']()">交卷判分</button><span id="score"></span></div><div id="result"></div>`;
  app.innerHTML=html;
  window.W=window.W||{};
  window.W.setC=(id,v)=>A.choice[id]=v;
  window.W.setJ=(id,v,el)=>{document.querySelectorAll(`[onclick^="W['setJ']('${id}'"]`).forEach(e=>e.classList.remove("sel"));el.classList.add("sel");A.judge[id]=v;};
  window.W.setF=(id,k,v)=>{(A.fill[id]=A.fill[id]||[])[k]=v;};
  window.W.setCalc=(id,k,v)=>{(A.calc[id]=A.calc[id]||[])[k]=v;};
  window.W.grade=()=>{
    const r=Grade.gradeAll(bank,A);
    let out=`<div class="card"><div class="score">总分：<span class="n">${r.got.total}</span> / 100</div>
      <div class="muted">选择 ${r.got.choice} · 判断 ${r.got.judge} · 填空 ${r.got.fill} · 计算 ${r.got.calc}</div></div>`;
    const show=(arr,type,getAns,getCorr)=>{
      arr.forEach(it=>{
        const ok=r.detail[type][it.id]>0;
        out+=`<div class="res ${ok?'ok':'bad'}" style="display:block;margin:8px 0">
          <b>${ok?'✓ 正确':'✗ 错误'}</b> ${esc(it.q||it.title)}<br>
          <span class="src">你的答案：${esc(getAns(it))}　|　正确答案：${esc(getCorr(it))}</span>`;
        if(!ok && it.explain) out+=`<br><span class="src">解析：${esc(it.explain)}</span>`;
        if(it.src) out+=`<br><span class="src">来源：${esc(it.src)}</span>`;
        out+=`</div>`;
      });
    };
    show(bank.choice||[],"choice",it=>{const v=A.choice[it.id];return v==null?"未答":it.options[v];},it=>it.options[it.answer]);
    show(bank.judge||[],"judge",it=>{const v=A.judge[it.id];return v==null?"未答":(v?"对":"错");},it=>it.answer?"对":"错");
    show(bank.fill||[],"fill",it=>(A.fill[it.id]||[]).join(" / ")||"未答",it=>(it.answers||[]).join(" / "));
    show(bank.calc||[],"calc",it=>(A.calc[it.id]||[]).join(" / ")||"未答",it=>(it.subs||[]).map(s=>s[1]).join(" / "));
    $("#result").innerHTML=out;
    $("#score").innerHTML=`本次 ${r.got.total} 分`;
  };
}

// ---------- 学习页 ----------
async function study(q){
  const key=q.m||"gbt_2951_materials";
  const m=await load(ASSETS.study[key].file);
  let html=`<h1>学习页</h1><p class="sub">${esc(ASSETS.study[key].name)}</p>`;
  if(m.summary) html+=`<div class="card">${esc(m.summary)}</div>`;
  if(m.quiz) m.quiz.forEach((x,i)=>{html+=`<div class="card"><b>Q${i+1}. ${esc(x.q)}</b><div class="muted" style="margin-top:6px">${esc(x.a)}</div></div>`;});
  if(m.key_points) html+=`<div class="card"><b>记忆要点</b><ul>${m.key_points.map(p=>`<li>${esc(p)}</li>`).join("")}</ul></div>`;
  if(m.interpretations) m.interpretations.forEach(s=>{html+=`<div class="card">${esc(s)}</div>`;});
  if(!m.summary&&!m.quiz&&!m.key_points&&!m.interpretations) html+=`<div class="empty">该学习材料暂无结构化内容</div>`;
  app.innerHTML=html;
}

// ---------- 闪卡 ----------
async function flashcards(q){
  const key=q.deck||"gbt_2951_flashcards";
  const data=await load(ASSETS.decks[key].file);
  const cards=data.cards||[];
  const stds=[...new Set(cards.map(c=>c.std||"其他"))];
  const methods=[...new Set(cards.map(c=>c.method||"其他"))];
  const prios=["P0","P1","P2"];
  let mode="browse";
  let order=[]; let idx=0;
  const prog={}; // SM-2: {cardId:{ease,interval,reps,due}}
  try{Object.assign(prog,JSON.parse(localStorage.getItem("fc_"+key)||"{}"));}catch(e){}
  function buildOrder(){
    let pool=cards.filter(c=>(!curStd||c.std===curStd)&&(!curMethod||c.method===curMethod)&&(!curPrio||c.priority===curPrio));
    if(mode==="study"){
      const now=Date.now();
      pool.sort((a,b)=>((prog[a.id]&&prog[a.id].due<=now)?0:1)-( (prog[b.id]&&prog[b.id].due<=now)?0:1));
    }else{
      const w={P0:3,P1:2,P2:1}; const exp=[]; pool.forEach(c=>{for(let i=0;i<(w[c.priority]||1);i++)exp.push(c);});
      for(let i=exp.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[exp[i],exp[j]]=[exp[j],exp[i]];}
      pool=exp;
    }
    order=pool; idx=0;
  }
  let curStd="",curMethod="",curPrio="";
  function render(){
    if(!order.length){app.innerHTML=`<h1>闪卡</h1><p class="sub">${esc(ASSETS.decks[key].name)}</p><div class="empty">当前筛选无卡片</div>`+filters();return;}
    const c=order[idx];
    const p=prog[c.id];
    const pbadge=`<span class="tag ${c.priority==='P0'?'p0':c.priority==='P1'?'p1':'p2'}">${c.priority}</span>`;
    let html=`<h1>闪卡</h1><p class="sub">${esc(ASSETS.decks[key].name)}　·　${mode==="study"?"学习模式(SM-2)":"浏览模式"}　·　${idx+1}/${order.length}</p>`;
    html+=filters();
    html+=`<div class="fc" id="fc" onclick="W['flip']()"><div class="f">${esc(c.front)}</div><div class="b2">${esc(c.back)}<br><span class="muted">${pbadge}${esc(c.std)} · ${esc(c.method||"")} · 来源：${esc(c.src||"")}</span></div></div>`;
    if(mode==="study"){
      html+=`<div style="display:flex;gap:10px;margin-top:10px"><button class="s" onclick="W['recall'](false)">😣 不记得</button><button class="b" onclick="W['recall'](true)">😎 记得</button></div>`;
      if(p) html+=`<div class="muted">上次间隔 ${p.interval}d · 熟练度 ${p.ease.toFixed(2)}</div>`;
    }else{
      html+=`<div style="display:flex;gap:10px;margin-top:10px"><button class="s" onclick="W['prev']()">← 上一张</button><button class="s" onclick="W['next']()">下一张 →</button></div>`;
    }
    app.innerHTML=html;
  }
  function filters(){
    return `<div class="card"><b>筛选</b>（${mode==="study"?"学习模式按到期排序":"浏览模式按优先级加权洗牌"}）
      <div style="margin-top:8px">
      模式：<button class="s" id="mB" onclick="W['chMode']('browse')">浏览</button><button class="b" id="mS" onclick="W['chMode']('study')">学习</button>
      <span class="muted">（${mode==="study"?"学习模式按到期排序":"浏览模式按优先级加权洗牌"}）</span>
      </div>
      <div style="margin-top:8px">标准：<select id="fStd"><option value="">全部</option>${stds.map(s=>`<option ${curStd===s?'selected':''}>${esc(s)}</option>`).join("")}</select>
      方法：<select id="fMet"><option value="">全部</option>${methods.map(s=>`<option ${curMethod===s?'selected':''}>${esc(s)}</option>`).join("")}</select>
      优先级：<select id="fPri"><option value="">全部</option>${prios.map(s=>`<option ${curPrio===s?'selected':''}>${s}</option>`).join("")}</select>
      <button class="b" onclick="W['applyF']()">应用</button></div></div>`;
  }
  window.W=window.W||{};
  window.W.flip=()=>{$("#fc").classList.toggle("flip");};
  window.W.next=()=>{idx=(idx+1)%order.length;render();};
  window.W.prev=()=>{idx=(idx-1+order.length)%order.length;render();};
  window.W.chMode=(m)=>{mode=m;buildOrder();render();};
  window.W.applyF=()=>{curStd=$("#fStd").value;curMethod=$("#fMet").value;curPrio=$("#fPri").value;buildOrder();render();};
  window.W.recall=(ok)=>{
    const c=order[idx]; const p=prog[c.id]||{ease:2.5,interval:0,reps:0,due:0};
    const q=ok?5:1;
    if(q<3){p.reps=0;p.interval=0;}else{
      if(p.reps===0)p.interval=1; else if(p.reps===1)p.interval=6; else p.interval=Math.round(p.interval*p.ease);
      p.reps++;
    }
    p.ease=Math.max(1.3,p.ease+(0.1-(5-q)*(0.08+(5-q)*0.02)));
    p.due=Date.now()+p.interval*86400000;
    prog[c.id]=p; localStorage.setItem("fc_"+key,JSON.stringify(prog));
    idx=(idx+1)%order.length; render();
  };
  buildOrder(); render();
}

// ---------- 术语库 ----------
async function terminology(){
  const d=await load(ASSETS.term);
  const terms=d.terms||[];
  const cats=[...new Set(terms.map(t=>t.category||"其他"))];
  let kw="",cat="";
  function render(){
    const list=terms.filter(t=>(!cat||t.category===cat)&&(!kw||(t.term_cn+ (t.definition||"")+(t.abbrev||"")).toLowerCase().includes(kw.toLowerCase())));
    let html=`<h1>术语库</h1><p class="sub">${terms.length} 条电缆检验术语（复用旧系统主档）</p>
      <div class="card"><input type="search" placeholder="搜索术语/定义…" id="kw" value="${esc(kw)}" oninput="W['sk'](this.value)">
      分类：<select id="cat" onchange="W['sc'](this.value)"><option value="">全部</option>${cats.map(c=>`<option ${cat===c?'selected':''}>${esc(c)}</option>`).join("")}</select>
      <span class="muted">${list.length} 条</span></div>`;
    list.slice(0,200).forEach(t=>{
      html+=`<div class="card"><b>${esc(t.term_cn)}</b> ${t.abbrev?`<span class="tag">${esc(t.abbrev)}</span>`:""} ${t.term_en?`<span class="muted">${esc(t.term_en)}</span>`:""}
        <div style="margin:6px 0">${esc(t.definition)}</div>
        ${t.key_values?`<div class="muted">关键值：${esc(t.key_values)}</div>`:""}
        ${t.ref_standards&&t.ref_standards.length?`<div class="muted">标准：${esc(t.ref_standards.join("、"))}</div>`:""}
        ${(t.related_terms||[]).length?`<div class="muted">关联：${esc(t.related_terms.join("、"))}</div>`:""}</div>`;
    });
    app.innerHTML=html;
  }
  window.W=window.W||{};
  window.W.sk=v=>{kw=v;render();}; window.W.sc=v=>{cat=v;render();};
  render();
}

// ---------- 出卷器 ----------
async function builder(){
  const keys=Object.keys(ASSETS.banks);
  let bankName=keys[0];
  let weights={};
  async function loadBank(name){return await load(ASSETS.banks[name].file);}
  async function render(){
    const bank=await loadBank(bankName);
    const groups={};
    ["choice","judge","fill","calc"].forEach(t=>(bank[t]||[]).forEach(it=>{const s=stdOf(it.src);(groups[s]=groups[s]||{choice:0,judge:0,fill:0,calc:0})[t]++;}));
    const stds=Object.keys(groups);
    let html=`<h1>出卷器</h1><p class="sub">按标准号设抽题权重，前端一键组卷（纯静态，不依赖后端）</p>
      <div class="card"><b>选择题库</b>：<select id="bk" onchange="W['chBk'](this.value)">${keys.map(k=>`<option value="${k}" ${k===bankName?'selected':''}>${esc(ASSETS.banks[k].name)}</option>`).join("")}</select></div>
      <div class="card"><b>各标准号抽题数</b><div class="muted">该标准号总题数见括号；留空=不抽</div>`;
    stds.forEach(s=>{const g=groups[s];const total=g.choice+g.judge+g.fill+g.calc;
      html+=`<div style="margin:7px 0">${esc(s)} <span class="muted">(共${total}题：选${g.choice}/判${g.judge}/填${g.fill}/算${g.calc})</span>
        <input type="number" min="0" max="${total}" id="w_${b64(s)}" value="${weights[s]||""}" style="width:64px" placeholder="抽"> 题</div>`;
    });
    html+=`</div><div style="margin-top:10px"><button class="b" onclick="W['gen']()">🎯 生成试卷</button></div><div id="genMsg"></div>`;
    app.innerHTML=html;
  }
  function b64(s){return encodeURIComponent(s);}
  window.W=window.W||{};
  window.W.chBk=async n=>{bankName=n;weights={};await render();};
  window.W.gen=async()=>{
    const bank=await loadBank(bankName);
    const nb={choice:[],judge:[],fill:[],calc:[]};
    let drawn=0;
    const stds=[...new Set(["choice","judge","fill","calc"].flatMap(t=>(bank[t]||[]).map(it=>stdOf(it.src))))];
    stds.forEach(s=>{
      const n=parseInt($("#w_"+b64(s)).value)||0;     if(!n)return;
      const pool=[];["choice","judge","fill","calc"].forEach(t=>(bank[t]||[]).forEach(it=>{if(stdOf(it.src)===s)pool.push({t,it});}));
      for(let i=pool.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[pool[i],pool[j]]=[pool[j],pool[i]];}
      pool.slice(0,n).forEach(({t,it})=>{nb[t].push(it);drawn++;});
    });
    if(!drawn){$("#genMsg").innerHTML=`<div class="note">请至少为一个标准号填写抽题数</div>`;return;}
    sessionStorage.setItem("genBank",JSON.stringify(nb));
    location.hash="#/exam?inline=1";
  };
}

// ---------- 考试大纲 ----------
async function syllabus(){
  const d=await load(ASSETS.syll);
  const items=d.items||[];
  let kw="";
  function render(){
    const list=items.filter(it=>!kw||(it.topic+it.requirement+(it.ref_standards||[]).join("")).toLowerCase().includes(kw.toLowerCase()));
    let html=`<h1>考试大纲</h1><p class="sub">${esc(d.meta&&d.meta.name||"2026竞赛复习大纲")}　·　${items.length} 条知识点</p>
      <div class="card"><input type="search" placeholder="搜索知识点…" value="${esc(kw)}" oninput="W['sk'](this.value)"><span class="muted"> ${list.length} 条</span></div>
      <div class="card"><table><tr><th>模块</th><th>分类</th><th>知识点</th><th>依据标准</th></tr>
      ${list.slice(0,300).map(it=>`<tr><td>${esc(it.part)}</td><td>${esc(it.category)}</td><td>${esc(it.topic)}</td><td class="muted">${(it.ref_standards||[]).join("、")||"—"}</td></tr>`).join("")}</table></div>`;
    app.innerHTML=html;
  }
  window.W=window.W||{}; window.W.sk=v=>{kw=v;render();};
  render();
}

// ---------- 反馈 ----------
function feedback(){
  let selText="";
  function render(){
    let arr=[]; try{arr=JSON.parse(localStorage.getItem("feedback_log")||"[]");}catch(e){}
    let html=`<h1>反馈</h1><p class="sub">报错 / 建议收集（存本机浏览器，可导出日志）</p>
      <div class="note">你也可随时点右下角 📝 浮钮提交；划选文字后点反馈会自动带上选区。</div>
      <div class="card"><b>提交一条反馈</b><div class="muted" id="ctx">${selText?("已带入选区："+esc(selText)):""}</div>
      <textarea id="ft" placeholder="描述问题或建议…"></textarea>
      <div style="margin-top:8px"><button class="b" onclick="W['send']()">提交</button></div></div>
      <div class="card"><b>本地记录（${arr.length} 条）</b>
      ${arr.length?`<button class="s" onclick="W['exp']()">导出 jsonl</button>`:""}
      ${arr.slice().reverse().slice(0,50).map(r=>`<div style="border-top:1px solid var(--bd);padding:6px 0"><span class="muted">${esc(r.time)}</span> ${esc(r.text)}${r.sel?`<div class="muted">选区：${esc(r.sel)}</div>`:""}</div>`).join("")}</div>`;
    app.innerHTML=html;
  }
  window.W=window.W||{};
  window.W.send=()=>{const t=$("#ft").value.trim();if(!t)return;const arr=JSON.parse(localStorage.getItem("feedback_log")||"[]");const rec={time:new Date().toISOString(),text:t,sel:selText};arr.push(rec);localStorage.setItem("feedback_log",JSON.stringify(arr));
    // 追加式日志（文本，便于 grep）
    const log=(localStorage.getItem("feedback_log_txt")||"")+`[${rec.time}] ${t}${rec.sel?" | SEL:"+rec.sel:""}\n`;localStorage.setItem("feedback_log_txt",log);
    selText="";render();};
  window.W.exp=()=>{const arr=JSON.parse(localStorage.getItem("feedback_log")||"[]");const blob=new Blob([arr.map(r=>JSON.stringify(r)).join("\n")],{type:"application/jsonl"});const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download="feedback.jsonl";a.click();};
  render();
}

// ---------- 反馈浮钮 ----------
const fbFab=$("#fbFab"),fbBox=$("#fbBox"),fbCtx=$("#fbCtx"),fbText=$("#fbText");
fbFab.onclick=()=>{const sel=window.getSelection&&window.getSelection().toString();fbCtx.textContent=sel?("选区："+sel):"";fbBox.classList.toggle("hidden");};
$("#fbCancel").onclick=()=>fbBox.classList.add("hidden");
$("#fbSend").onclick=()=>{const t=fbText.value.trim();if(!t)return;const arr=JSON.parse(localStorage.getItem("feedback_log")||"[]");const sel=fbCtx.textContent.replace(/^选区：/,"");const rec={time:new Date().toISOString(),text:t,sel};arr.push(rec);localStorage.setItem("feedback_log",JSON.stringify(arr));const log=(localStorage.getItem("feedback_log_txt")||"")+`[${rec.time}] ${t}${rec.sel?" | SEL:"+rec.sel:""}\n`;localStorage.setItem("feedback_log_txt",log);fbText.value="";fbBox.classList.add("hidden");alert("已记录，感谢反馈！（本机浏览器内）");};

window.addEventListener("hashchange",nav);
nav();
})();
