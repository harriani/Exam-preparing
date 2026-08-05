// 被 test_parity.py 调用：用 grade.js 对同一批作答判分，输出 JSON 供 Python 比对。
const fs = require("fs");
const path = require("path");
const Grade = require(path.join(__dirname, "grade.js"));

const cases = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const out = cases.cases.map(c => Grade.gradeAll(cases.bank, c.answers));
fs.writeFileSync(process.argv[3], JSON.stringify(out, null, 2), "utf8");
console.log("js graded " + out.length + " cases");
