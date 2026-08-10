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
    "gbt_2951_11_12":   {file:"data/gbt_2951_11_12.json",   name:"GB/T 2951.11/12 卷(98分)", std:"GB/T 2951", _count:43},
    "gbt_3048_8":       {file:"data/gbt_3048_8.json",        name:"GB/T 3048.8-2025 卷(60分)", std:"GB/T 3048.8", _count:26},
    "gbt_3956":         {file:"data/gbt_3956.json",           name:"GB/T 3956-2008 卷(23分)", std:"GB/T 3956", _count:11},
    "gbt_2951_full":    {file:"data/gbt_2951_full.json",      name:"GB/T 2951 全系卷(214分)", std:"GB/T 2951", _count:88},
    "gbt_3048_full":    {file:"data/gbt_3048_full.json",      name:"GB/T 3048 全系卷(376分)", std:"GB/T 3048", _count:152},
    "gbt_others_full":   {file:"data/gbt_others_full.json",      name:"产品标准合集卷(67分)", std:"其他标准", _count:32},
    "gbt_5023_full":    {file:"data/gbt_5023_full.json",      name:"GB/T 5023 聚氯乙烯绝缘电缆卷(67分)", std:"GB/T 5023", _count:27},
    "gbt_8734_full":    {file:"data/gbt_8734_full.json",      name:"JB/T 8734 聚氯乙烯绝缘电线卷(71分)", std:"JB/T 8734", _count:29},
    "gbt_10491_full":   {file:"data/gbt_10491_full.json",     name:"JB/T 10491 交联聚烯烃绝缘电缆卷(64分)", std:"JB/T 10491", _count:27},
    "gbt_19666_full":   {file:"data/gbt_19666_full.json",      name:"GB/T 19666 阻燃耐火卷(79分)", std:"GB/T 19666", _count:41},
    "gbt_9330_full":    {file:"data/gbt_9330_full.json",       name:"GB/T 9330 控制电缆卷(79分)", std:"GB/T 9330", _count:41},
    "gbt_12706_full":   {file:"data/gbt_12706_full.json",      name:"GB/T 12706.3 电力电缆卷(79分)", std:"GB/T 12706", _count:41},
    "gbt_5013_full":    {file:"data/gbt_5013_full.json",       name:"GB/T 5013.3 橡皮绝缘卷(79分)", std:"GB/T 5013", _count:41},
    "gbt_8735_full":    {file:"data/gbt_8735_full.json",       name:"JB/T 8735.2 橡皮软电缆卷(79分)", std:"JB/T 8735", _count:41},
    "gbt_11017_full":   {file:"data/gbt_11017_full.json",      name:"GB/T 11017 超高压电缆卷(79分)", std:"GB/T 11017", _count:41},
    "gbt_18890_full":   {file:"data/gbt_18890_full.json",      name:"GB/T 18890 超高压附件卷(79分)", std:"GB/T 18890", _count:41}
  },
  study: {
    "gbt_2951_materials":     {file:"data/gbt_2951_materials.json",      name:"GB/T 2951 学习材料(54节)"},
    "gbt_3048_8_materials":   {file:"data/gbt_3048_8_materials.json",    name:"GB/T 3048.8 学习材料(35节)"},
    "gbt_3956_materials":     {file:"data/gbt_3956_materials.json",      name:"GB/T 3956 学习材料(15节)"},
    "gbt_2951_full_materials":{file:"data/gbt_2951_full_materials.json",name:"GB/T 2951 全系 学习材料(119节)"},
    "gbt_3048_full_materials":{file:"data/gbt_3048_full_materials.json",name:"GB/T 3048 全系 学习材料(181节)"},
    "gbt_others_full_materials":{file:"data/gbt_others_full_materials.json",name:"产品标准合集 学习材料(44节)"},
    "gbt_5023_full_materials":{file:"data/gbt_5023_full_materials.json",name:"GB/T 5023 学习材料(31节)"},
    "gbt_8734_full_materials":{file:"data/gbt_8734_full_materials.json",name:"JB/T 8734 学习材料(43节)"},
    "gbt_10491_full_materials":{file:"data/gbt_10491_full_materials.json",name:"JB/T 10491 学习材料(38节)"},
    "gbt_19666_materials":    {file:"data/gbt_19666_full_materials.json", name:"GB/T 19666 阻燃耐火材料(23节)"},
    "gbt_9330_materials":     {file:"data/gbt_9330_full_materials.json",  name:"GB/T 9330 控制电缆材料(18节)"},
    "gbt_12706_materials":    {file:"data/gbt_12706_full_materials.json", name:"GB/T 12706.3 电力电缆材料(21节)"},
    "gbt_5013_materials":     {file:"data/gbt_5013_full_materials.json",  name:"GB/T 5013.3 橡皮绝缘材料(19节)"},
    "gbt_8735_materials":     {file:"data/gbt_8735_full_materials.json",  name:"JB/T 8735.2 橡皮软电缆材料(20节)"},
    "gbt_11017_materials":    {file:"data/gbt_11017_full_materials.json", name:"GB/T 11017 超高压电缆材料(20节)"},
    "gbt_18890_materials":    {file:"data/gbt_18890_full_materials.json", name:"GB/T 18890 超高压附件材料(22节)"}
  },
  decks: {
    "gbt_2951_flashcards":    {file:"data/gbt_2951_flashcards.json",    name:"GB/T 2951 闪卡(43张)", _count:43},
    "gbt_3048_8_flashcards":  {file:"data/gbt_3048_8_flashcards.json",  name:"GB/T 3048.8 闪卡(26张)", _count:26},
    "gbt_3956_flashcards":    {file:"data/gbt_3956_flashcards.json",    name:"GB/T 3956 闪卡(11张)", _count:11},
    "gbt_2951_full_flashcards":{file:"data/gbt_2951_full_flashcards.json",name:"GB/T 2951 全系 闪卡(88张)", _count:88},
    "gbt_3048_full_flashcards":{file:"data/gbt_3048_full_flashcards.json",name:"GB/T 3048 全系 闪卡(152张)", _count:152},
    "gbt_others_full_flashcards":{file:"data/gbt_others_full_flashcards.json",name:"产品标准合集 闪卡(32张)", _count:32},
    "gbt_5023_full_flashcards":{file:"data/gbt_5023_full_flashcards.json",name:"GB/T 5023 闪卡(27张)", _count:27},
    "gbt_8734_full_flashcards":{file:"data/gbt_8734_full_flashcards.json",name:"JB/T 8734 闪卡(29张)", _count:29},
    "gbt_10491_full_flashcards":{file:"data/gbt_10491_full_flashcards.json",name:"JB/T 10491 闪卡(27张)", _count:27},
    "gbt_19666_flashcards":   {file:"data/gbt_19666_full_flashcards.json", name:"GB/T 19666 阻燃耐火闪卡(30张)", _count:30},
    "gbt_9330_flashcards":    {file:"data/gbt_9330_full_flashcards.json",  name:"GB/T 9330 控制电缆闪卡(30张)", _count:30},
    "gbt_12706_flashcards":   {file:"data/gbt_12706_full_flashcards.json", name:"GB/T 12706.3 电力电缆闪卡(30张)", _count:30},
    "gbt_5013_flashcards":    {file:"data/gbt_5013_full_flashcards.json",  name:"GB/T 5013.3 橡皮绝缘闪卡(30张)", _count:30},
    "gbt_8735_flashcards":    {file:"data/gbt_8735_full_flashcards.json",  name:"JB/T 8735.2 橡皮软电缆闪卡(30张)", _count:30},
    "gbt_11017_flashcards":   {file:"data/gbt_11017_full_flashcards.json", name:"GB/T 11017 超高压闪卡(30张)", _count:30},
    "gbt_18890_flashcards":   {file:"data/gbt_18890_full_flashcards.json", name:"GB/T 18890 超高压附件闪卡(38张)", _count:38}
  },
  term:  "data/terminology_v1.json",
  syll:  "data/syllabus_2026.json"
};
const cache = {};
function load(k){ return cache[k] || (cache[k]=fetch(k).then(r=>{if(!r.ok)throw new Error(r.status);return r.json();})); }
function esc(s){ return String(s==null?"":s).replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c])); }
function stdOf(src){
  if(!src) return "其他";
  let s;
  if(typeof src==="object") s=(src.standard_no||"")+" "+(src.clause||"");
  else s=String(src);
  const m=s.match(/GB\/T\s*\d+(?:\.\d+)?(?:-\d+)?/i);
  return m?m[0].toUpperCase().replace(/\s/g,""):"其他";
}

// ---------- 路由 ----------
function parseHash(){
  let h=location.hash.replace(/^#\/?/,"");
  let [path,qs]=h.split("?");
  const q={}; (qs||"").split("&").forEach(p=>{if(p){const[i,v]=p.split("=");q[i]=decodeURIComponent(v||"");}});
  return {path:path||"home", q};
}
function nav(){ const {path,q}=parseHash();
  document.querySelectorAll(".bar a").forEach(a=>a.classList.toggle("on", a.dataset.r===path));
  const map={home:home, exam:exam, study:study, flashcards:flashcards, terminology:terminology, builder:builder, syllabus:syllabus, "syllabus-weight":syllabusWeight, feedback:feedback};
  (map[path]||home)(q);
}

// ---------- 首页 ----------
function home(){
  const bankKeys=Object.keys(ASSETS.banks);
  const studyKeys=Object.keys(ASSETS.study);
  const deckKeys=Object.keys(ASSETS.decks);
  const totalQ=bankKeys.reduce((s,k)=>{const b=ASSETS.banks[k];return s+(b._count||0);},0);
  const totalC=deckKeys.reduce((s,k)=>{const d=ASSETS.decks[k];return s+(d._count||0);},0);

  let bankTiles=bankKeys.map(k=>{const b=ASSETS.banks[k];
    return tile(`#/exam?bank=${k}`,`📝 ${b.name}`,`共${b._count||"?"}题 · 纯脚本即时判分`);}).join("");
  let studyTiles=`<div style="grid-column:1/-1"><h3 style="margin:10px 0 6px">📖 学习材料</h3></div>`+
    studyKeys.map(k=>tile(`#/study?m=${k}`,ASSETS.study[k].name,"标准解读 / Quiz / 易错点")).join("");
  let deckTiles=`<div style="grid-column:1/-1"><h3 style="margin:10px 0 6px">🃏 闪卡库</h3></div>`+
    deckKeys.map(k=>tile(`#/${k==="gbt_2951_flashcards"?"flashcards":"flashcards"}?deck=${k}`,ASSETS.decks[k].name,"浏览+SM-2学习模式")).join("");

  app.innerHTML=`<h1>国缆检测杯 · 在线学习考试系统</h1>
  <p class="sub">大模型出题 + 脚本判分 · 静态部署版（进度/反馈存本机浏览器）</p>
  <div class="note">已收录 ${bankKeys} 套题库(${totalQ}题) / ${deckKeys} 套闪卡(${totalC}张) / ${studyKeys} 套学习材料。纯前端分享版，闭卷防作弊/跨设备同步需本机服务端。</div>
  <div class="grid">
    <div style="grid-column:1/-1"><h3 style="margin:0 0 6px">📝 自测题库</h3></div>${bankTiles}
    ${studyTiles}
    ${deckTiles}
    ${tile("#/terminology","🔤 术语库","70条电缆检验术语，搜索+分类")}
    ${tile("#/builder","🎯 出卷器","跨标准按权重抽题组卷")}
    ${tile("#/syllabus","📋 考试大纲","2026竞赛复习大纲125条知识点")}
    ${tile("#/syllabus-weight","📊 大纲权重","认知层次占比·熟练掌握→教材映射")}
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
  const title = (bank.meta&&bank.meta.name)?bank.meta.name:"自定义组卷";
  const A={choice:{},judge:{},fill:{},calc:{}};
  const dlBar=(q.inline==="1")?`<div class="card" style="margin-bottom:10px"><b>导出 Word：</b> <button class="b" onclick="W['dlPaper']()">⬇ 试卷</button> <button class="b" onclick="W['dlAnswer']()">⬇ 答案解析</button> <span class="muted">（试卷与答案分开两个文件，答案解析带依据）</span></div>`:"";
  let html=`${dlBar}<h1>自测卷</h1><p class="sub">${esc(title)}　·　纯脚本判分（不调大模型）</p><div id="qs">`;
  (bank.choice||[]).forEach((it,i)=>{
    const no=i+1, src=stdNo(it.src||(bank.meta&&bank.meta.name)||"");
    html+=`<div class="q" data-qno="${no}" data-qtype="选择题" data-qsrc="${esc(src)}"><span class="pts">${it.points||2}分</span><div class="stem">${i+1}. ${esc(it.q)}</div>`;
    it.options.forEach((o,oi)=>{html+=`<label class="opt"><input type="radio" name="c_${it.id}" value="${oi}" onchange="W['setC']('${it.id}',${oi})">${esc(o)}</label>`;});
    html+=`</div>`;
  });
  (bank.judge||[]).forEach((it,i)=>{
    const no=i+1+(bank.choice||[]).length, src=stdNo(it.src||(bank.meta&&bank.meta.name)||"");
    html+=`<div class="q" data-qno="${no}" data-qtype="判断题" data-qsrc="${esc(src)}"><span class="pts">${it.points||1}分</span><div class="stem">${i+1+(bank.choice||[]).length}. ${esc(it.q)}</div>
      <span class="tf" onclick="W['setJ']('${it.id}',true,this)">✓ 对</span>
      <span class="tf" onclick="W['setJ']('${it.id}',false,this)">✗ 错</span></div>`;
  });
  (bank.fill||[]).forEach((it,i)=>{
    const no=i+1+(bank.choice||[]).length+(bank.judge||[]).length, src=stdNo(it.src||(bank.meta&&bank.meta.name)||"");
    html+=`<div class="q" data-qno="${no}" data-qtype="填空题" data-qsrc="${esc(src)}"><span class="pts">${it.points||2}分</span><div class="stem">${i+1+(bank.choice||[]).length+(bank.judge||[]).length}. ${esc(it.q)}</div><div>`;
    for(let k=0;k<(it.answers||[]).length;k++) html+=`<input type="text" placeholder="空${k+1}" onchange="W['setF']('${it.id}',${k},this.value)"> `;
    html+=`</div></div>`;
  });
  (bank.calc||[]).forEach((it,i)=>{
    const no=i+1+(bank.choice||[]).length+(bank.judge||[]).length+(bank.fill||[]).length, src=stdNo(it.src||(bank.meta&&bank.meta.name)||"");
    html+=`<div class="q" data-qno="${no}" data-qtype="计算题" data-qsrc="${esc(src)}"><span class="pts">计算</span><div class="stem">${esc(it.title||"计算题")}</div><div class="muted" style="margin:6px 0">${esc(it.stem)}</div>`;
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
  window.W.dlPaper=()=>downloadPaper();
  window.W.dlAnswer=()=>downloadAnswer();
  window.W.grade=()=>{
    const r=Grade.gradeAll(bank,A);
    const maxTotal=(bank.meta&&bank.meta.total)||(function(){let t=0;["choice","judge","fill"].forEach(s=>(bank[s]||[]).forEach(it=>{t+=(it.points||0);}));(bank.calc||[]).forEach(it=>{(it.subs||[]).forEach(su=>{if(su[3])t+=su[3];});});return t||100;})();
    let out=`<div class="card"><div class="score">总分：<span class="n">${r.got.total}</span> / ${maxTotal}</div>
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

// ---------- Word 导出（真正的 .docx，OOXML 格式）----------
const WSECTIONS=[["choice","一、单项选择题"],["judge","二、判断题"],["fill","三、填空题"],["calc","四、计算题"]];

async function buildDocx(bank, mode){
  const {Document,Packer,Paragraph,TextRun,HeadingLevel,AlignmentType,BorderStyle,UnderlineType}=docx;
  const title=(bank.meta&&bank.meta.name)?bank.meta.name:"自定义组卷";
  const total=(bank.meta&&bank.meta.total)||100;
  const showAns=(mode==="answer");
  const children=[];

  // 标题
  children.push(new Paragraph({text:title,heading:HeadingLevel.HEADING_1,alignment:AlignmentType.CENTER,spacing:{after:120}}));
  children.push(new Paragraph({
    alignment:AlignmentType.CENTER,spacing:{after:240},
    children:[new TextRun({text:"满分 "+total+" 分　·　"+(showAns?"附答案解析与依据（客观题判分 100% 脚本死规则）":"答题卷（答案见单独下发的《答案解析》）"),size:22,color:"666666"})]
  }));

  let no=0;
  WSECTIONS.forEach(([t,label])=>{
    const arr=bank[t]||[];
    if(!arr.length) return;
    const secPts=t==="calc"?arr.reduce((a,c)=>a+(c.points||(c.subs||[]).reduce((x,s)=>x+(s[3]||0),0)),0):arr.reduce((a,c)=>a+(c.points||0),0);
    // 大标题
    children.push(new Paragraph({text:label+"（共 "+arr.length+" 题，计 "+secPts+" 分）",heading:HeadingLevel.HEADING_2,spacing:{before:360,after:160}}));

    arr.forEach(it=>{
      no++;
      if(t==="choice"){
        children.push(new Paragraph({spacing:{before:200},children:[new TextRun({text:no+". ",bold:true,size:24}),new TextRun({text:it.q,size:24})]}));
        it.options.forEach((o,oi)=>{
          children.push(new Paragraph({indent:{left:480},spacing:{after:40},children:[new TextRun({text:String.fromCharCode(65+oi)+". "+o,size:22})]}));
        });
        if(showAns){
          children.push(new Paragraph({indent:{left:480},spacing:{after:60},children:[
            new TextRun({text:"答案：",bold:true,color:"1A5276",size:22}),
            new TextRun({text:String.fromCharCode(65+it.answer)+". "+it.options[it.answer],color:"1A5276",size:22})
          ]}));
          if(it.explain) children.push(new Paragraph({indent:{left:480},spacing:{after:40},children:[
            new TextRun({text:"解析：",bold:true,color:"555555",size:21}),
            new TextRun({text:it.explain,color:"555555",size:21})
          ]}));
          if(it.src) children.push(new Paragraph({indent:{left:480},spacing:{after:120},children:[
            new TextRun({text:"依据：",bold:true,color:"7D3C98",size:21}),
            new TextRun({text:it.src,color:"7D3C98",size:21})
          ]}));
        }
      }else if(t==="judge"){
        children.push(new Paragraph({spacing:{before:200},children:[
          new TextRun({text:no+". ",bold:true,size:24}),new TextRun({text:it.q+"　（　　　）",size:24})
        ]}));
        if(showAns){
          children.push(new Paragraph({indent:{left:480},spacing:{after:60},children:[
            new TextRun({text:"答案：",bold:true,color:"1A5276",size:22}),
            new TextRun({text:it.answer?"正确":"错误",color:"1A5276",size:22})
          ]}));
          if(it.explain) children.push(new Paragraph({indent:{left:480},spacing:{after:40},children:[
            new TextRun({text:"解析：",bold:true,color:"555555",size:21}),new TextRun({text:it.explain,color:"555555",size:21})
          ]}));
          if(it.src) children.push(new Paragraph({indent:{left:480},spacing:{after:120},children:[
            new TextRun({text:"依据：",bold:true,color:"7D3C98",size:21}),new TextRun({text:it.src,color:"7D3C98",size:21})
          ]}));
        }
      }else if(t==="fill"){
        children.push(new Paragraph({spacing:{before:200},children:[
          new TextRun({text:no+". ",bold:true,size:24}),new TextRun({text:it.q,size:24})
        ]}));
        if(showAns){
          children.push(new Paragraph({indent:{left:480},spacing:{after:60},children:[
            new TextRun({text:"答案：",bold:true,color:"1A5276",size:22}),
            new TextRun({text:(it.answers||[]).join(" / "),color:"1A5276",size:22})
          ]}));
          if(it.explain) children.push(new Paragraph({indent:{left:480},spacing:{after:40},children:[
            new TextRun({text:"解析：",bold:true,color:"555555",size:21}),new TextRun({text:it.explain,color:"555555",size:21})
          ]}));
          if(it.src) children.push(new Paragraph({indent:{left:480},spacing:{after:120},children:[
            new TextRun({text:"依据：",bold:true,color:"7D3C98",size:21}),new TextRun({text:it.src,color:"7D3C98",size:21})
          ]}));
        }
      }else if(t==="calc"){
        children.push(new Paragraph({spacing:{before:200},children:[
          new TextRun({text:no+". ",bold:true,size:24}),new TextRun({text:it.title||"计算题",size:24,bold:true})
        ]}));
        if(it.stem) children.push(new Paragraph({indent:{left:480},spacing:{after:60},children:[
          new TextRun({text:it.stem,size:22,color:"555555"})
        ]}));
        (it.subs||[]).forEach((s,si)=>{
          children.push(new Paragraph({indent:{left:480},spacing:{after:40},children:[
            new TextRun({text:"（"+(si+1)+"）"+s[0]+"：______________　（"+s[3]+"分）",size:22})
          ]}));
          if(showAns) children.push(new Paragraph({indent:{left:960},spacing:{after:40},children:[
            new TextRun({text:"答案：",bold:true,color:"1A5276",size:22}),
            new TextRun({text:String(s[1])+(s[2]?"（允许误差 ±"+s[2]+"）":""),color:"1A5276",size:22})
          ]}));
        });
        if(showAns){
          if(it.explain) children.push(new Paragraph({indent:{left:480},spacing:{after:40},children:[
            new TextRun({text:"解析：",bold:true,color:"555555",size:21}),new TextRun({text:it.explain,color:"555555",size:21})
          ]}));
          if(it.src) children.push(new Paragraph({indent:{left:480},spacing:{after:120},children:[
            new TextRun({text:"依据：",bold:true,color:"7D3C98",size:21}),new TextRun({text:it.src,color:"7D3C98",size:21})
          ]}));
        }
      }
      // 分隔
      children.push(new Paragraph({border:{bottom:{style:BorderStyle.SINGLE,size:1,color:"EEEEEE"}},spacing:{after:120}}));
    });
  });

  return new Document({sections:[{properties:{page:{margin:{top:1134,right:1134,bottom:1134,left:1134}}},children}]});
}

async function downloadPaper(){
  const bank=JSON.parse(sessionStorage.getItem("genBank"));
  if(!bank){alert("请先在出卷器生成试卷");return;}
  const doc=await buildDocx(bank,"paper");
  const blob=await docx.Packer.toBlob(doc);
  const name=((bank.meta&&bank.meta.name)||"试卷")+"_试卷.docx";
  saveAs(blob,name);
}
async function downloadAnswer(){
  const bank=JSON.parse(sessionStorage.getItem("genBank"));
  if(!bank){alert("请先在出卷器生成试卷");return;}
  const doc=await buildDocx(bank,"answer");
  const blob=await docx.Packer.toBlob(doc);
  const name=((bank.meta&&bank.meta.name)||"试卷")+"_答案解析.docx";
  saveAs(blob,name);
}

// ---------- 学习页 ----------
async function study(q){
  const keys=Object.keys(ASSETS.study);
  const key=q.m||(keys[0]||"");
  if(!key || !ASSETS.study[key]){ app.innerHTML=`<h1>学习页</h1><div class="empty">暂无学习材料</div>`; return; }
  const m=await load(ASSETS.study[key].file);
  let selHtml=`<div class="card" style="margin-bottom:12px"><b>选择材料：</b> <select onchange="location.hash='#/study?m='+this.value">${keys.map(k=>`<option value="${k}" ${k===key?'selected':''}>${esc(ASSETS.study[k].name)}</option>`).join("")}</select></div>`;
  let html=`<h1>学习页</h1>${selHtml}<p class="sub">${esc(ASSETS.study[key].name)}</p>`;
  if(m.summary) html+=`<div class="card">${esc(m.summary)}</div>`;
  if(m.quiz) m.quiz.forEach((x,i)=>{html+=`<div class="card"><b>Q${i+1}. ${esc(x.q)}</b><div class="muted" style="margin-top:6px">${esc(x.a)}</div></div>`;});
  if(m.key_points) html+=`<div class="card"><b>记忆要点</b><ul>${m.key_points.map(p=>`<li>${esc(p)}</li>`).join("")}</ul></div>`;
  if(m.interpretations) m.interpretations.forEach(s=>{html+=`<div class="card">${esc(s)}</div>`;});
  // 渲染 sections[]（当前数据格式：summary/quiz/pitfall/key_table/flashcard）
  (m.sections||[]).forEach(s=>{
    if(s.type==="summary"){ html+=`<div class="card"><h3 style="margin:0 0 6px">${esc(s.title||"概述")}</h3><div>${esc(s.body||"")}</div></div>`; }
    else if(s.type==="flashcard"){ /* 闪卡类型归属闪卡页，学习页跳过 */ }
    else if(s.type==="key_table"){
      const cols=(s.columns||[]).map(c=>`<th>${esc(c)}</th>`).join("");
      const rows=(s.rows||[]).map(r=>`<tr>${r.map(v=>`<td>${esc(v)}</td>`).join("")}</tr>`).join("");
      html+=`<div class="card"><b>${esc(s.title||"参数表")}</b><table class="ktab"><tr>${cols}</tr>${rows}</table><div class="muted">来源：${esc(s.src||"")}</div></div>`;
    }
    else if(s.type==="quiz"){ html+=`<div class="card"><b>Q. ${esc(s.q||"")}</b><div class="muted" style="margin-top:6px">答：${esc(s.a||"")}</div>${s.explain?`<div class="muted">解析：${esc(s.explain)}</div>`:""}<div class="muted">来源：${esc(s.src||"")}</div></div>`; }
    else if(s.type==="pitfall"){ html+=`<div class="card note"><b>⚠ 易错点</b><div>${esc(s.desc||"")}</div><div class="muted" style="margin-top:6px">正确：${esc(s.correct||"")}</div><div class="muted">来源：${esc(s.src||"")}</div></div>`; }
    else { html+=`<div class="card">${esc(s.title||"")} ${esc(s.body||"")}</div>`; }
  });
  if(!m.summary&&!m.quiz&&!m.key_points&&!m.interpretations&&!(m.sections&&m.sections.length)) html+=`<div class="empty">该学习材料暂无结构化内容</div>`;
  app.innerHTML=html;
}

// ---------- 闪卡 ----------
async function flashcards(q){
  const deckKeys=Object.keys(ASSETS.decks);
  const key=q.deck||(deckKeys[0]||"");
  if(!key || !ASSETS.decks[key]){ app.innerHTML=`<h1>闪卡</h1><div class="empty">暂无闪卡</div>`; return; }
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
    let pool=cards.filter(c=>(!curStd||c.std===curStd)&&(!curMethod||c.method===curMethod)&&(!curPrio||c.priority===curPrio)&&!c._skip);
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
      html+=`<div class="fc-act"><button class="s" onclick="W['recall'](false)">😣 不记得</button><button class="b" onclick="W['recall'](true)">😎 记得</button></div>`;
      if(p) html+=`<div class="muted">上次间隔 ${p.interval}d · 熟练度 ${p.ease.toFixed(2)}</div>`;
    }else{
      html+=`<div class="fc-act"><button class="s" onclick="W['prev']()">← 上一张</button><button class="s" onclick="W['next']()">下一张 →</button></div>`;
    }
    app.innerHTML=html;
  }
  function filters(){
    const deckSel=deckKeys.length>1?`<div style="margin-bottom:8px"><b>卡组：</b><select onchange="location.hash='#/flashcards?deck='+this.value">${deckKeys.map(k=>`<option value="${k}" ${k===key?'selected':''}>${esc(ASSETS.decks[k].name)}</option>`).join("")}</select></div>`:"";
    return `<div class="card">${deckSel}<b>筛选</b>（${mode==="study"?"学习模式按到期排序":"浏览模式按优先级加权洗牌"}）
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
  let scope="__all__";
  let mode="preset";
  let counts={choice:15, judge:0, fill:12, calc:2};
  let weighted=true;
  const PRESETS={
    practice:{choice:15, judge:0, fill:12, calc:2, label:"练习卷"},
    mock:   {choice:30, judge:10, fill:20, calc:2, label:"模拟考"}
  };
  function b64(s){return encodeURIComponent(s);}
  function shuffle(a){for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));const t=a[i];a[i]=a[j];a[j]=t;}return a;}
  async function loadScope(){
    if(scope==="__all__"){
      const banks=await Promise.all(keys.map(k=>load(ASSETS.banks[k].file)));
      const merged={choice:[],judge:[],fill:[],calc:[]};
      const seen=new Set();
      banks.forEach((b,bi)=>{
        ["choice","judge","fill","calc"].forEach(t=>{
          (b[t]||[]).forEach(it=>{
            let id=it.id;
            while(seen.has(id)) id=id+"__"+(bi+1);
            seen.add(id);
            const c=Object.assign({},it); c.id=id; merged[t].push(c);
          });
        });
      });
      return merged;
    }
    return await load(ASSETS.banks[scope].file);
  }
  function planScores(n,W){
    const types=Object.keys(n).filter(t=>n[t]>0);
    let wsum=0; types.forEach(t=>wsum+=n[t]*W[t]);
    if(wsum===0) return {};
    const ideal={}; types.forEach(t=>ideal[t]=100*W[t]/wsum);
    let best=null;
    function rec(i,pe){
      if(i===types.length){
        let tot=0; types.forEach((t,j)=>tot+=n[t]*pe[j]);
        let cost=Math.abs(tot-100)*10000;
        types.forEach((t,j)=>cost+=(pe[j]-ideal[t])*(pe[j]-ideal[t]));
        if(!best||cost<best.cost) best={cost:cost,pe:pe.slice()};
        return;
      }
      for(let v=1;v<=12;v++){pe.push(v);rec(i+1,pe);pe.pop();}
    }
    rec(0,[]);
    const pe={}; types.forEach((t,j)=>pe[t]=best.pe[j]);
    return pe;
  }
  async function render(){
    let bank=null;
    if(mode==="std") bank=await loadScope();
    let html=`<h1>出卷器</h1><p class="sub">参照旧系统比例：卷型预设 + 总分100分（计算题每道约10分，选择/判断/填空每题约2分）</p>
      <div class="card"><b>题库范围</b>：<select id="sc" onchange="W['chScope'](this.value)">
        <option value="__all__" ${scope==="__all__"?"selected":""}>全部标准合并</option>
        ${keys.map(k=>`<option value="${k}" ${scope===k?"selected":""}>${esc(ASSETS.banks[k].name)}</option>`).join("")}
      </select></div>
      <div class="card"><b>出卷方式</b>：
        <button class="${mode==='preset'?'b':'s'}" onclick="W['chMode']('preset')">卷型预设</button>
        <button class="${mode==='std'?'b':'s'}" onclick="W['chMode']('std')">按标准号(高级)</button></div>`;
    if(mode==="preset"){
      html+=`<div class="card"><b>卷型预设</b>：
        <button class="s" onclick="W['applyPreset']('practice')">练习卷(选择15/填空12/计算2)</button>
        <button class="s" onclick="W['applyPreset']('mock')">模拟考(选择30/判断10/填空20/计算2)</button>
        <span class="muted">点一下自动填入下方题数</span></div>
        <div class="card"><b>各题型题数</b>
        选择<input type="number" min="0" id="c_choice" value="${counts.choice}" oninput="W['setCount']('choice',this.value)" style="width:50px">
        判断<input type="number" min="0" id="c_judge" value="${counts.judge}" oninput="W['setCount']('judge',this.value)" style="width:50px">
        填空<input type="number" min="0" id="c_fill" value="${counts.fill}" oninput="W['setCount']('fill',this.value)" style="width:50px">
        计算<input type="number" min="0" id="c_calc" value="${counts.calc}" oninput="W['setCount']('calc',this.value)" style="width:50px">
        </div>
        <div class="card"><label><input type="checkbox" id="wg" ${weighted?"checked":""} onchange="W['setW'](this.checked)"> 均衡覆盖各标准（避免某标准扎堆）</label></div>`;
    } else {
      const groups={};
      ["choice","judge","fill","calc"].forEach(t=>(bank[t]||[]).forEach(it=>{const s=stdOf(it.src);(groups[s]=groups[s]||{choice:0,judge:0,fill:0,calc:0})[t]++;}));
      const stds=Object.keys(groups);
      let g=`<div class="card"><b>各标准号抽题数</b><div class="muted">该标准号总题数见括号；留空=不抽</div>`;
      stds.forEach(s=>{const gr=groups[s];const total=gr.choice+gr.judge+gr.fill+gr.calc;
        g+=`<div style="margin:7px 0">${esc(s)} <span class="muted">(共${total}题：选${gr.choice}/判${gr.judge}/填${gr.fill}/算${gr.calc})</span>
          <input type="number" min="0" max="${total}" id="w_${b64(s)}" value="" style="width:64px" placeholder="抽"> 题</div>`;
      });
      g+=`</div>`;
      html+=g;
    }
    html+=`<div style="margin-top:10px"><button class="b" onclick="W['gen']()">🎯 生成试卷</button></div><div id="genMsg"></div>`;
    app.innerHTML=html;
  }
  window.W=window.W||{};
  window.W.chScope=async n=>{scope=n; await render();};
  window.W.chMode=async m=>{mode=m; await render();};
  window.W.applyPreset=async p=>{const pr=PRESETS[p]; counts={choice:pr.choice,judge:pr.judge,fill:pr.fill,calc:pr.calc}; await render();};
  window.W.setCount=(t,v)=>{counts[t]=parseInt(v)||0;};
  window.W.setW=v=>{weighted=v;};
  window.W.gen=async()=>{
    const bank=await loadScope();
    const nb={choice:[],judge:[],fill:[],calc:[]};
    if(mode==="std"){
      const stds=[...new Set(["choice","judge","fill","calc"].flatMap(t=>(bank[t]||[]).map(it=>stdOf(it.src))))];
      stds.forEach(s=>{
        const el=document.getElementById("w_"+b64(s)); const n=el?parseInt(el.value)||0:0; if(!n)return;
        const pool=[];["choice","judge","fill","calc"].forEach(t=>(bank[t]||[]).forEach(it=>{if(stdOf(it.src)===s&&!it._skip)pool.push({t,it});}));
        shuffle(pool);
        pool.slice(0,n).forEach(({t,it})=>nb[t].push(it));
      });
      if(!nb.choice.length&&!nb.judge.length&&!nb.fill.length&&!nb.calc.length){ $("#genMsg").innerHTML=`<div class="note">请至少为一个标准号填写抽题数</div>`; return; }
    } else {
      ["choice","judge","fill","calc"].forEach(t=>{
        let need=counts[t]||0;
        const el=document.getElementById("c_"+t); if(el) need=parseInt(el.value)||0;
        if(!need) return;
        let pool=(bank[t]||[]).filter(it=>!it._skip).slice();
        if(weighted){
          const buckets={};
          pool.forEach(it=>{const s=stdOf(it.src);(buckets[s]=buckets[s]||[]).push(it);});
          const order=Object.keys(buckets).sort((a,b)=>buckets[b].length-buckets[a].length);
          order.forEach(k=>shuffle(buckets[k]));
          const cap=Math.max(2, Math.ceil(need/order.length)+2);
          const taken={};
          let progress=true;
          while(nb[t].length<need && progress){
            progress=false;
            for(const s of order){
              if(nb[t].length>=need) break;
              if((taken[s]||0)>=cap) continue;
              const it=buckets[s].shift();
              if(it){ nb[t].push(it); taken[s]=(taken[s]||0)+1; progress=true; }
            }
          }
          while(nb[t].length<need && pool.length){ nb[t].push(pool.splice(Math.floor(Math.random()*pool.length),1)[0]); }
        } else {
          shuffle(pool);
          nb[t].push(...pool.slice(0,need));
        }
      });
      if(!nb.choice.length&&!nb.judge.length&&!nb.fill.length&&!nb.calc.length){ $("#genMsg").innerHTML=`<div class="note">请设置题型题数或选择卷型预设</div>`; return; }
    }
    const n={choice:nb.choice.length,judge:nb.judge.length,fill:nb.fill.length,calc:nb.calc.length};
    const pe=planScores(n,{choice:2,judge:2,fill:2,calc:10});
    ["choice","judge","fill"].forEach(t=>nb[t].forEach(it=>{it.points=pe[t]||2;}));
    nb.calc.forEach(it=>{
      const big=pe.calc||10;
      const orig=it.subs.reduce((s,x)=>s+(x[3]||0),0)||1;
      const raw=it.subs.map(x=>big*x[3]/orig);
      const fl=raw.map(Math.floor);
      let rem=big-fl.reduce((a,b)=>a+b,0);
      const order=raw.map((v,i)=>[i,v-fl[i]]).sort((a,b)=>b[1]-a[1]);
      for(let k=0;k<rem;k++) fl[order[k][0]]++;
      it.subs.forEach((s,i)=>{ s[3]=fl[i]; });
    });
    const scopeName = scope==="__all__" ? "全部标准合并" : ASSETS.banks[scope].name;
    nb.meta={name: scopeName+" · 自定义组卷(满分100)", total:100};
    sessionStorage.setItem("genBank",JSON.stringify(nb));
    location.hash="#/exam?inline=1";
  };
  await render();
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

// ---------- 大纲认知层次权重 ----------
async function syllabusWeight(){
  const d=await load(ASSETS.syll);
  const items=d.items||[];
  const ORDER=["了解","熟悉","掌握","熟练掌握"];
  const COLORS={"了解":"#9aa7b5","熟悉":"#3b82f6","掌握":"#f59e0b","熟练掌握":"#ef4444"};
  function lvlOf(it){
    const cl=it.cognitive_level;
    if(ORDER.indexOf(cl)>=0) return cl;
    const req=it.requirement||"";
    for(const L of ORDER){ if(req.indexOf(L)>=0) return L; }
    return "了解";
  }
  const cnt={}; ORDER.forEach(L=>cnt[L]=0);
  items.forEach(it=>{ cnt[lvlOf(it)]++; });
  const total=items.length;
  const pct=n=>(100*n/total).toFixed(1)+"%";
  function textbooksFor(std){
    const s=std||"";
    if(s.indexOf("2951")>=0) return "《电缆产品检验-非电性能检验》第三/四/五章（绝缘护套通用/弹性体/聚氯乙烯）";
    if(s.indexOf("3048")>=0) return "《电缆产品检验-电性能检验》第二/四章（通用电性能/原始记录）";
    if(s.indexOf("19666")>=0) return "《电缆产品检验-非电性能检验》第七章（燃烧性能）";
    if(s.indexOf("3956")>=0) return "《电缆产品检验-电性能检验》第一章（导体）";
    return "对应教材相关章节";
  }
  function productsFor(std){
    const s=std||"";
    if(s.indexOf("2951")>=0||s.indexOf("3048")>=0||s.indexOf("19666")>=0)
      return "GB/T 11017 / 18890 / 12706 / 5023 / 8734 / 5013 / 9330 等（按产品类型取用）";
    if(s.indexOf("3956")>=0) return "GB/T 5023 / 8734 / 5013 / 9330 / 12706 等";
    return "—";
  }
  const byLvl={}; ORDER.forEach(L=>byLvl[L]=[]);
  items.forEach(it=>byLvl[lvlOf(it)].push(it));
  let html=`  <div style="margin-bottom:10px"><a class="back" href="#/syllabus">← 返回考试大纲</a></div>
  <h1>大纲认知层次权重</h1>
  <p class="sub">2026竞赛复习大纲 · 认知层次：了解 &lt; 熟悉 &lt; 掌握 &lt; 熟练掌握（决定命题深度与权重）</p>
  <div class="card"><h3>① 四层权重总览（共 ${total} 条）</h3>
    ${ORDER.map(L=>`<div style="margin:10px 0">
      <div style="display:flex;justify-content:space-between"><b style="color:${COLORS[L]}">${L}</b><span class="muted">${cnt[L]} 条 · ${pct(cnt[L])}</span></div>
      <div style="height:14px;background:var(--bd);border-radius:7px;overflow:hidden"><div style="height:100%;width:${pct(cnt[L])};background:${COLORS[L]}"></div></div>
    </div>`).join("")}
    <div class="note">命题深度权重：熟练掌握(${cnt["熟练掌握"]}) &gt; 掌握(${cnt["掌握"]}) &gt; 熟悉(${cnt["熟悉"]}) &gt; 了解(${cnt["了解"]})。复习策略：先死磕 ${cnt["熟练掌握"]} 条熟练掌握 + ${cnt["掌握"]} 条掌握（占深度大头），了解点到为止。</div>
  </div>
  <div class="card"><h3>② 熟练掌握 → 教材 / 依据标准 / 关联产品标准</h3>
    <p class="muted">竞赛对动手操作要求极高，以下 ${byLvl["熟练掌握"].length} 条「熟练掌握」最该优先（实操为主 + 少量理论）。</p>
    <table><tr><th>知识点</th><th>依据标准</th><th>教材对应</th><th>关联产品标准</th></tr>
    ${byLvl["熟练掌握"].map(it=>`<tr><td>${esc(it.topic)}</td><td class="muted">${(it.ref_standards||[]).join("、")||"—"}</td><td>${textbooksFor((it.ref_standards||[]).join(" "))}</td><td class="muted">${productsFor((it.ref_standards||[]).join(" "))}</td></tr>`).join("")}
    </table>
  </div>
  <div class="card"><h3>③ 125 条按层次分组（点击展开）</h3>
    ${ORDER.slice().reverse().map(L=>`<details><summary><b style="color:${COLORS[L]}">${L}</b> · ${byLvl[L].length} 条</summary>
      <table><tr><th>模块</th><th>分类</th><th>知识点</th><th>依据标准</th></tr>
      ${byLvl[L].map(it=>`<tr><td>${esc(it.part)}</td><td>${esc(it.category)}</td><td>${esc(it.topic)}</td><td class="muted">${(it.ref_standards||[]).join("、")||"—"}</td></tr>`).join("")}
      </table></details>`).join("")}
  </div>
  <div class="card"><h3>④ 出题 / 闪卡占比建议</h3>
    <ul>
      <li><b>熟练掌握</b>：必出且可多题/高权重（操作类优先出实操步骤题）。</li>
      <li><b>掌握</b>：高权出题，覆盖计算/判定。</li>
      <li><b>熟悉</b>：中等权重，概念/辨析为主。</li>
      <li><b>了解</b>：少出，点到为止（占分低）。</li>
    </ul>
    <div class="note">本地 Flask 版出题已按此权重加权（guideline.py 认知层次权重）；线上版出卷器/闪卡如需同权重，需在 public/app.js 接入本层次。</div>
  </div>`;
  app.innerHTML=html;
}

// ---------- 反馈（三类 + 划词题干识别 + 双写 localStorage/后端） ----------
function stdNo(s){ if(!s) return ""; const m=String(s).match(/GB\/T\s*\d+(?:\.\d+)?|GB\s*\d+|JB\/T\s*\d+|YD\/T\s*\d+|IEC\s*\d+/i); return m?m[0].replace(/\s+/g,""):String(s).slice(0,30); }

function feedback(){
  window.W=window.W||{};
  window.W.syncServer=async()=>{
    const arr=JSON.parse(localStorage.getItem("feedback_log")||"[]"); let n=0, pulled=0;
    for(const r of arr){ if(r._synced) continue;
      try{ const res=await fetch("/api/feedback",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({page:r.page||"",category:r.category||"其他问题",location:r.location||"",detail:r.detail||r.text||""})}); const j=await res.json(); if(j.ok){r._synced=true; if(j.id) r.id=j.id; r.status=r.status||"待整改"; n++;} }catch(e){}
    }
    // 拉取服务器整改状态，按 id 合并到本地记录（让你在静态站也能看到「有没有整改」）
    try{ const res=await fetch("/api/feedback"); const srv=await res.json(); const byId={}; (srv||[]).forEach(s=>byId[s.id]=s);
      for(const r of arr){ if(r.id && byId[r.id]){ r.status=byId[r.id].status; r.resolution=byId[r.id].resolution; r.resolved_at=byId[r.id].resolved_at; r._synced=true; pulled++; } }
    }catch(e){}
    localStorage.setItem("feedback_log",JSON.stringify(arr));
    renderFeedback((n||pulled)?`已同步 ${n} 条到服务器；刷新整改状态 ${pulled} 条（data/feedback.jsonl，每日自动整改会读取）`:"没有需要同步的新反馈");
  };
  window.W.exp=()=>{const arr=JSON.parse(localStorage.getItem("feedback_log")||"[]");const blob=new Blob([arr.map(r=>JSON.stringify({time:r.time,category:r.category,location:r.location,detail:r.detail||r.text,sel:r.sel})).join("\n")],{type:"application/jsonl"});const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download="feedback.jsonl";a.click();};
  renderFeedback();
}
function renderFeedback(msg){
  let arr=[]; try{arr=JSON.parse(localStorage.getItem("feedback_log")||"[]");}catch(e){}
  const catCount={}; arr.forEach(r=>{const c=r.category||"其他问题";catCount[c]=(catCount[c]||0)+1;});
  const stat=Object.keys(catCount).map(c=>`<span class="chip">${esc(c)} ${catCount[c]}</span>`).join("")||"—";
  const app=document.getElementById("app"); if(!app) return;
  app.innerHTML=`<h1>反馈日志</h1><p class="sub">随时随地划选题干或点右下角 📝 提交；所有反馈形成日志。</p>
    <div class="card" style="display:flex;gap:10px;flex-wrap:wrap;align-items:center">
      <span class="muted">分类统计：</span>${stat}
      <span style="flex:1"></span>
      <button class="b" onclick="W['syncServer']()">🔄 同步到服务器</button>
      ${arr.length?`<button class="s" onclick="W['exp']()">导出 jsonl</button>`:""}
    </div>
    ${msg?`<div class="note">${msg}</div>`:""}
    <div class="card"><b>本地记录（${arr.length} 条）</b>
    ${arr.slice().reverse().slice(0,80).map(r=>{ const st=r.status||(r._synced?"待整改":""); const stCls=st==="已整改"?"ok":st==="整改中"?"warn":""; return `<div style="border-top:1px solid var(--bd);padding:8px 0">
      <span class="chip ${r.category==='题干问题'?'c1':r.category==='提取质量问题'?'c2':'c3'}">${esc(r.category||'其他问题')}</span>
      <span class="muted">${esc(r.time)}</span>
      ${st?`<span class="chip ${stCls}">${esc(st)}</span>`:""}
      ${r._synced&&!r.id?'<span class="chip">已同步</span>':""}
      ${r.location?`<div class="muted">对象：${esc(r.location)}</div>`:""}
      <div>${esc(r.detail||r.text||'')}</div>
      ${r.resolution?`<div class="fbx"><b>整改：</b>${esc(r.resolution)}${r.resolved_at?` <span class="muted">(${esc(r.resolved_at)})</span>`:""}</div>`:""}
      ${r.sel?`<div class="muted">选区：${esc(r.sel)}</div>`:""}</div>`; }).join("")||'<div class="muted" style="padding:12px">暂无反馈</div>'}</div>`;
}

// ---------- 反馈浮钮 ----------
const fbFab=$("#fbFab"),fbBox=$("#fbBox"),fbCtx=$("#fbCtx"),fbText=$("#fbText"),fbCat=$("#fbCat"),fbLoc=$("#fbLoc"),fbSync=$("#fbSync");
function detectQContext(sel){
  let el=sel&&sel.anchorNode?sel.anchorNode.parentElement:null;
  while(el){ if(el.classList&&el.classList.contains("q")){
    const no=el.getAttribute("data-qno")||"", src=el.getAttribute("data-qsrc")||"", type=el.getAttribute("data-qtype")||"";
    const txt=(sel.toString()||"").trim();
    return {isQ:true, cat:"题干问题", loc:`题号${no}${src?" · "+src:""}${type?" · "+type:""}`, q:txt};
  } el=el.parentElement; }
  return {isQ:false};
}
function openFb(){
  const sel=window.getSelection?window.getSelection():null; const seltxt=sel?sel.toString().trim():"";
  const ctx=detectQContext(sel);
  if(ctx.isQ){
    fbCat.value="题干问题"; fbLoc.value=ctx.loc; fbCtx.textContent="检测到题干选区，已归类为「题干问题」";
    fbText.value=seltxt?("题干内容："+seltxt):"";
  }else{
    if(!fbCat.value) fbCat.value="其他问题";
    fbLoc.value=location.hash||""; fbCtx.textContent=seltxt?("选区："+seltxt):"整页 / 其他问题反馈";
  }
  fbSync.textContent=""; fbBox.classList.remove("hidden");
}
fbFab.onclick=openFb;
$("#fbCancel").onclick=()=>fbBox.classList.add("hidden");
$("#fbSend").onclick=submitFb;
async function submitFb(){
  const cat=fbCat.value, loc=(fbLoc.value||"").trim(), detail=fbText.value.trim();
  if(!detail){alert("请填写反馈内容");return;}
  const selRaw=(fbCtx.textContent||"").replace(/^选区：/,"").replace(/^检测到题干选区，已归类为「题干问题」/,"");
  const rec={time:new Date().toISOString(),category:cat,location:loc,detail,page:location.hash||"",sel:selRaw};
  const arr=JSON.parse(localStorage.getItem("feedback_log")||"[]"); arr.push(rec); localStorage.setItem("feedback_log",JSON.stringify(arr));
  localStorage.setItem("feedback_log_txt",(localStorage.getItem("feedback_log_txt")||"")+`[${rec.time}] cat=${cat} loc=${loc} :: ${detail}\n`);
  let synced=false;
  try{ const r=await fetch("/api/feedback",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({page:rec.page,category:cat,location:loc,detail})}); const j=await r.json(); synced=!!j.ok; if(j.ok&&j.id){rec.id=j.id; rec.status="待整改";} }catch(e){ synced=false; }
  fbText.value=""; fbBox.classList.add("hidden");
  fbSync.textContent=synced?"✅ 已记录并同步到服务器日志":"✅ 已记录（本机浏览器；回本机打开站点点「同步到服务器」即可入库）";
  if(location.hash==="#/feedback") renderFeedback();
}

// ---------- 阅读字号调节（A−/A/A+，记忆本机） ----------
(function(){
  const KEY="rd_fs";
  const apply=v=>document.documentElement.style.setProperty("--fs",v);
  let v=parseFloat(localStorage.getItem(KEY)); if(!(v>=0.8&&v<=1.4)) v=1;
  apply(v);
  const btns=document.querySelectorAll("[data-fs]");
  btns.forEach(b=>{ b.classList.toggle("on", parseFloat(b.dataset.fs)===v);
    b.onclick=()=>{ const nv=parseFloat(b.dataset.fs); apply(nv); localStorage.setItem(KEY,nv);
      btns.forEach(x=>x.classList.toggle("on", parseFloat(x.dataset.fs)===nv)); }; });
})();

window.addEventListener("hashchange",nav);
nav();
})();
