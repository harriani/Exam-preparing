/* learning-system-v2 · 判分内核（JS 版）
 * ==========================================
 * 本文件是 engine/generate.py 判分逻辑的【逐条镜像】。
 * 用途：① 内联进离线试卷 HTML，实现浏览器端即时判分；② 被 node 加载做一致性测试。
 * 规则：只判客观题（选择/判断/填空/计算），全部死规则，不调用任何大模型。
 * 任何一侧改动，必须同步另一侧，并跑 engine/test_parity.py 验证两边判分完全一致。
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.Grade = factory();
})(typeof self !== "undefined" ? self : this, function () {

  // ---- 归一化（镜像 generate.py normalize）----
  function normalize(s) {
    if (s === null || s === undefined) return "";
    s = String(s);
    ["\u0020", "\u00a0", "\u3000", "\t"].forEach(function (ch) {
      s = s.split(ch).join("");
    });
    var map = {
      "％": "%", "×": "x", "÷": "/", "²": "2", "³": "3",
      "（": "(", "）": ")", "：": ":", "，": ",",
      "。": ".", "、": ",", "～": "~", "—": "-"
    };
    Object.keys(map).forEach(function (k) { s = s.split(k).join(map[k]); });
    return s.toLowerCase().trim();
  }

  // ---- 严格数值解析（镜像 generate.py to_num）----
  var NUM_RE = /^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$/;
  function toNum(x) {
    var s = String(x === null || x === undefined ? "" : x).trim();
    ["\u0020", "\u00a0", "\u3000"].forEach(function (ch) { s = s.split(ch).join(""); });
    return NUM_RE.test(s) ? parseFloat(s) : null;
  }

  function closeEnough(a, b, tol) {
    var na = toNum(a), nb = toNum(b);
    if (na === null || nb === null) return normalize(a) === normalize(b);
    var t = toNum(tol);
    if (t === null) t = 0;
    return Math.abs(na - nb) <= t + 1e-9;
  }

  // ---- 单题判分 ----
  function gradeChoice(it, sub) {
    var pts = it.points === undefined ? 2 : it.points;
    if (sub === null || sub === undefined || sub === "") return 0;
    return parseInt(sub, 10) === parseInt(it.answer, 10) ? pts : 0;
  }

  var TRUE_SET = ["true", "t", "对", "正确", "√", "v", "y", "yes", "1"];
  var FALSE_SET = ["false", "f", "错", "错误", "x", "×", "n", "no", "0"];
  function gradeJudge(it, sub) {
    var pts = it.points === undefined ? 1 : it.points;
    var user;
    if (typeof sub === "boolean") {
      user = sub;
    } else {
      var s = normalize(sub);
      if (TRUE_SET.indexOf(s) >= 0) user = true;
      else if (FALSE_SET.indexOf(s) >= 0) user = false;
      else return 0;
    }
    return user === Boolean(it.answer) ? pts : 0;
  }

  function gradeFill(it, subs) {
    var pts = it.points === undefined ? 2 : it.points;
    var ans = it.answers || [], syn = it.syn || [];
    if (!subs || subs.length !== ans.length) return 0;
    for (var i = 0; i < subs.length; i++) {
      var ok = normalize(subs[i]) === normalize(ans[i]);
      if (!ok && i < syn.length && syn[i]) {
        ok = syn[i].map(normalize).indexOf(normalize(subs[i])) >= 0;
      }
      if (!ok) return 0;
    }
    return pts;
  }

  function gradeCalc(it, subs) {
    var total = 0;
    for (var i = 0; i < it.subs.length; i++) {
      var label = it.subs[i][0], target = it.subs[i][1],
          tol = it.subs[i][2], pts = it.subs[i][3];
      var sub = subs && subs[i] !== undefined ? subs[i] : "";
      if (label === "合格性判定") {
        total += normalize(sub) === normalize(target) ? pts : 0;
      } else {
        total += closeEnough(sub, target, tol) ? pts : 0;
      }
    }
    return total;
  }

  // ---- 整卷判分 ----
  // answers 结构: {choice:{id:idx}, judge:{id:bool|str}, fill:{id:[..]}, calc:{id:[..]}}
  function gradeAll(bank, answers) {
    var detail = { choice: {}, judge: {}, fill: {}, calc: {} };
    var got = { choice: 0, judge: 0, fill: 0, calc: 0 };
    (bank.choice || []).forEach(function (it) {
      var s = gradeChoice(it, (answers.choice || {})[it.id]);
      detail.choice[it.id] = s; got.choice += s;
    });
    (bank.judge || []).forEach(function (it) {
      var s = gradeJudge(it, (answers.judge || {})[it.id]);
      detail.judge[it.id] = s; got.judge += s;
    });
    (bank.fill || []).forEach(function (it) {
      var s = gradeFill(it, (answers.fill || {})[it.id]);
      detail.fill[it.id] = s; got.fill += s;
    });
    (bank.calc || []).forEach(function (it) {
      var s = gradeCalc(it, (answers.calc || {})[it.id]);
      detail.calc[it.id] = s; got.calc += s;
    });
    got.total = got.choice + got.judge + got.fill + got.calc;
    return { got: got, detail: detail };
  }

  return {
    normalize: normalize, toNum: toNum, closeEnough: closeEnough,
    gradeChoice: gradeChoice, gradeJudge: gradeJudge,
    gradeFill: gradeFill, gradeCalc: gradeCalc, gradeAll: gradeAll
  };
});
