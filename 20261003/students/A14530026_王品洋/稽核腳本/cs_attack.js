// 攻擊 course-submit。全部在暫存資料夾：假的上游(origin)與假的 fork 都是本機 bare repo，不碰網路、不碰真的 GitHub。
const fs = require('fs'), path = require('path');
const { execFileSync, spawnSync } = require('child_process');
const [,, srcDir, root] = process.argv;           // srcDir = 對方的 course-submit 資料夾（只讀）
const ME = 'A14530068_黃建升', OTHER = 'A15530027_黃麟珍';
const sh = (cwd, args, o = {}) => spawnSync('git', args, Object.assign({ cwd, encoding: 'utf8' }, o));
const must = (cwd, args) => { const r = sh(cwd, args); if (r.status !== 0) throw new Error('git ' + args.join(' ') + ': ' + r.stderr); return r.stdout.trim(); };
const W = (p, c) => { fs.mkdirSync(path.dirname(p), { recursive: true }); fs.writeFileSync(p, c); };

function fresh(name, { dates = ['20260919', '20261003', '20261017', '20261121', '20261219', '20270116'], forkSame = false, forkUrlDotGit = false } = {}) {
  const base = path.join(root, name); fs.rmSync(base, { recursive: true, force: true }); fs.mkdirSync(base, { recursive: true });
  const up = path.join(base, 'up.git'), fk = path.join(base, 'fork.git'), wk = path.join(base, 'work');
  must(base, ['init', '--bare', '-b', 'main', up]); must(base, ['init', '--bare', '-b', 'main', fk]);
  must(base, ['clone', up, wk]);
  must(wk, ['config', 'user.email', 't@t']); must(wk, ['config', 'user.name', 't']); must(wk, ['config', 'core.autocrlf', 'false']);
  W(path.join(wk, 'README.md'), 'x');
  for (const d of dates) { W(path.join(wk, d, 'students', ME, 'README.md'), 'me'); W(path.join(wk, d, 'students', OTHER, 'README.md'), 'other ' + d); }
  W(path.join(wk, '20260919', 'README.md'), 'course');
  must(wk, ['add', '-A']); must(wk, ['commit', '-m', 'init']); must(wk, ['push', 'origin', 'HEAD:main']);
  const forkUrl = forkSame ? (forkUrlDotGit ? up.replace(/\\/g, '/') + '/' : up) : fk;
  must(wk, ['remote', 'add', 'fork', forkUrl]);
  must(wk, ['checkout', '-b', 'student/A14530068-test']);
  // 複製對方的腳本與設定（設定只改 repo 路徑與網址，指向假 repo）
  const cs = path.join(base, 'cs'); fs.cpSync(srcDir, cs, { recursive: true });
  const cfg = JSON.parse(fs.readFileSync(path.join(cs, '設定.json'), 'utf8'));
  cfg.repo = wk.replace(/\\/g, '/'); cfg.上課日期資料夾 = dates.length ? cfg.上課日期資料夾 : cfg.上課日期資料夾;
  fs.writeFileSync(path.join(cs, '設定.json'), JSON.stringify(cfg));
  return { base, up, fk, wk, cs };
}
const run = (E, msg, extra = []) => spawnSync('node', [path.join(E.cs, 'scripts', '交件.js'), msg, ...extra], { cwd: E.cs, encoding: 'utf8' });
const check = E => spawnSync('node', [path.join(E.cs, 'scripts', '檢查.js')], { cwd: E.cs, encoding: 'utf8' });
const forkLog = E => { const r = sh(E.fk, ['log', '--all', '--name-status', '--format=%s']); return r.stdout.trim(); };
const results = [];
const rec = (id, title, verdict, evidence) => { results.push({ id, title, verdict, evidence }); console.log((verdict === 'BUG' ? '✘ ' : verdict === 'OK' ? '✔ ' : '· ') + id + ' ' + title + '\n    ' + evidence.split('\n').slice(0, 6).join('\n    ')); };

// ---- S1：把別人的檔案「改名」進自己資料夾，原路徑（在別人資料夾）被刪除，檢查器看不到
{ const E = fresh('s1');
  W(path.join(E.wk, '20260919', 'students', ME, 'x.md'), 'tmp'); fs.rmSync(path.join(E.wk, '20260919', 'students', ME, 'x.md'));
  must(E.wk, ['mv', `20260919/students/${OTHER}/README.md`, `20260919/students/${ME}/stolen.md`]);
  const c = check(E); const r = run(E, 's1');
  const fl = forkLog(E);
  const deleted = /D\s+20260919\/students\/A15530027/.test(fl);
  rec('S1', '把別人的檔案 git mv 進自己資料夾', (c.status === 0 && deleted) ? 'BUG' : 'OK',
    '檢查結果 exit=' + c.status + '；fork 上的提交是否刪掉了別人的檔案：' + deleted + '\n' + fl.split('\n').slice(0, 4).join('\n')); }

// ---- S2：已經手動 commit 過動到別人的檔案，工作區是乾淨的 → 檢查器只看工作區
{ const E = fresh('s2');
  W(path.join(E.wk, '20260919', 'students', OTHER, 'README.md'), 'HACKED');
  must(E.wk, ['commit', '-am', 'oops 動到別人的']);
  const c = check(E); const r = run(E, 's2');
  const fl = forkLog(E); const pushed = /oops/.test(fl);
  rec('S2', '先手動 commit 別人的檔案、再跑交件', (c.status === 0 && pushed) ? 'BUG' : 'OK',
    '檢查 exit=' + c.status + '；push 到 fork 的內容含別人資料夾的修改：' + pushed + '\n' + (c.stdout.split('\n').filter(l => /提醒|阻擋/.test(l)).join(' | '))); }

// ---- S3：detached HEAD
{ const E = fresh('s3'); must(E.wk, ['checkout', '--detach']); W(path.join(E.wk, '20260919', 'students', ME, 'a.md'), 'a');
  const c = check(E); const r = run(E, 's3');
  rec('S3', 'detached HEAD 上交件', /Traceback|fatal|Error/i.test(r.stderr + r.stdout) || r.status !== 0 ? 'BUG' : 'OK',
    '檢查 exit=' + c.status + '；交件 exit=' + r.status + '\n' + (r.stdout + r.stderr).split('\n').filter(l => /分支|fatal|錯|push/.test(l)).slice(0, 4).join('\n')); }

// ---- S4：fork 與 origin 指向同一個倉庫，只差結尾斜線／.git／大小寫
for (const [tag, mut] of [['結尾斜線', u => u + '/'], ['加 .git', u => u + '.git'], ['大小寫', u => u.toUpperCase()]]) {
  const E = fresh('s4' + tag);
  // origin 是 up.git；fork 指向「同一個」倉庫但寫法不同
  const up = E.up; must(E.wk, ['remote', 'set-url', 'origin', up]);
  must(E.wk, ['remote', 'set-url', 'fork', tag === '加 .git' ? up : (tag === '大小寫' ? up : up + '/')]);
  W(path.join(E.wk, '20260919', 'students', ME, 'a.md'), 'a');
  const c = check(E);
  const same = sh(E.wk, ['remote', 'get-url', 'origin']).stdout.trim() === sh(E.wk, ['remote', 'get-url', 'fork']).stdout.trim();
  const blocked = /同一個網址/.test(c.stdout);
  rec('S4-' + tag, 'fork 與上游其實是同一個倉庫但網址寫法不同', (!same && !blocked && c.status === 0) ? 'BUG' : (same ? 'N/A' : 'OK'),
    'fork=' + sh(E.wk, ['remote', 'get-url', 'fork']).stdout.trim() + '\norigin=' + sh(E.wk, ['remote', 'get-url', 'origin']).stdout.trim() + '\n檢查 exit=' + c.status + '，是否擋下：' + blocked); }

// ---- S5：機密檔 漏抓／誤抓
{ const E = fresh('s5'); const dir = path.join(E.wk, '20260919', 'students', ME);
  const names = ['id_rsa', 'deploy.pfx', 'cert.p12', 'token.txt', '.npmrc', 'api_key.json', 'a.keynote', 'my.environment.md', 'monkey.md', 'secret.txt', 'private.pem', 'x.ENV', '.env.local', 'password.txt'];
  names.forEach(n => W(path.join(dir, n), 'z'));
  const c = check(E); const blocked = names.filter(n => c.stdout.includes('疑似機密檔：20260919/students/' + ME + '/' + n));
  const shouldBlock = ['id_rsa', 'deploy.pfx', 'cert.p12', 'token.txt', '.npmrc', 'api_key.json', 'secret.txt', 'private.pem', 'x.ENV', '.env.local', 'password.txt'];
  const shouldPass = ['a.keynote', 'my.environment.md', 'monkey.md'];
  const missed = shouldBlock.filter(n => !blocked.includes(n)); const falsePos = shouldPass.filter(n => blocked.includes(n));
  rec('S5', '機密檔辨識', (missed.length || falsePos.length) ? 'BUG' : 'OK', '漏抓（該擋沒擋）：' + missed.join('、') + '\n誤抓（不該擋卻擋）：' + falsePos.join('、')); }

// ---- S6：大檔案副檔名繞過
{ const E = fresh('s6'); const dir = path.join(E.wk, '20260919', 'students', ME);
  const names = ['model.rvt', 'model.RVT', 'model.rvt.bak', 'model.rvt.zip', 'scene.skp.txt', 'a.zip', 'a.7z', 'a.rar', 'a.pdf', 'plan.dwg', 'plan.DWG', '渲染.png'];
  names.forEach(n => W(path.join(dir, n), 'z'));
  const c = check(E); const blocked = names.filter(n => c.stdout.includes('大檔案不進 repo：20260919/students/' + ME + '/' + n));
  const ok = ['model.rvt', 'model.RVT', 'plan.dwg', 'plan.DWG'];
  const wrong = ok.filter(n => !blocked.includes(n));
  const bypass = ['model.rvt.bak', 'model.rvt.zip', 'scene.skp.txt'].filter(n => !blocked.includes(n));
  rec('S6', '大檔案副檔名', wrong.length ? 'BUG' : 'INFO', '該擋沒擋：' + wrong.join('、') + '\n改副檔名即可繞過（.rvt.zip／.rvt.bak／.skp.txt）：' + bypass.join('、') + '（實際內容仍是 Revit/SketchUp 原檔，只靠 5MB 上限擋）'); }

// ---- S7：5MB 上限、總量無上限
{ const E = fresh('s7'); const dir = path.join(E.wk, '20260919', 'students', ME);
  fs.writeFileSync(path.join(dir, 'exact.bin'), Buffer.alloc(5 * 1024 * 1024)); fs.writeFileSync(path.join(dir, 'plus1.bin'), Buffer.alloc(5 * 1024 * 1024 + 1));
  for (let i = 0; i < 30; i++) fs.writeFileSync(path.join(dir, 'p' + i + '.bin'), Buffer.alloc(4.9 * 1024 * 1024));
  const c = check(E);
  const exact = c.stdout.includes('exact.bin'), plus1 = c.stdout.includes('plus1.bin'); const total = c.status === 0;
  rec('S7', '大小上限', (!plus1) ? 'BUG' : 'INFO', '恰好 5MB 被擋：' + exact + '；5MB+1 被擋：' + plus1 + '\n30 個 4.9MB 檔案（共約 147MB）合計是否被擋：' + (!total ? '是（有阻擋項）' : '否——只管單檔，總量沒有上限')); }

// ---- S8：commit 訊息只有空白 → add 之後才失敗？
{ const E = fresh('s8'); W(path.join(E.wk, '20260919', 'students', ME, 'a.md'), 'a');
  const r = run(E, '   ');
  const staged = sh(E.wk, ['diff', '--cached', '--name-only']).stdout.trim();
  rec('S8', 'commit 訊息只有空白', (r.status !== 0 && /Error|at /.test(r.stderr)) ? 'BUG' : 'OK',
    '交件 exit=' + r.status + '；失敗後檔案已被 git add（殘留暫存）：' + (staged || '無') + '\n' + r.stderr.split('\n').filter(l => /Error|fatal|empty/i.test(l)).slice(0, 2).join('\n')); }

// ---- S9：自己的日期資料夾只有部分存在 → git add 整批失敗
{ const E = fresh('s9', { dates: ['20260919'] });
  // 第 1 次上課之外的日期資料夾在這個 repo 裡根本沒有「我的」子資料夾（新同學、或還沒上到的課）
  W(path.join(E.wk, '20260919', 'students', ME, 'a.md'), 'a');
  const c = check(E); const r = run(E, 's9');
  rec('S9', '只有部分日期資料夾存在我的子資料夾（新同學／還沒上的課）', (c.status === 0 && r.status !== 0) ? 'BUG' : 'OK',
    '檢查 exit=' + c.status + '（通過）；交件 exit=' + r.status + '\n' + (r.stderr + r.stdout).split('\n').filter(l => /fatal|pathspec|Error|失敗/.test(l)).slice(0, 3).join('\n')); }

// ---- S10：路徑含空白／引號／中文／特殊字元
{ const E = fresh('s10'); const dir = path.join(E.wk, '20260919', 'students', ME);
  ['空 白 檔.md', "it's.md", '中文＆符號#1.md', 'a"b.md'].forEach(n => { try { W(path.join(dir, n), 'z'); } catch (e) {} });
  const r = run(E, 's10 特殊檔名'); const fl = forkLog(E);
  rec('S10', '特殊檔名（空白、引號、中文）', (r.status !== 0) ? 'BUG' : 'OK', '交件 exit=' + r.status + '；fork 上的檔案數：' + (fl.match(/^A\s/gm) || []).length); }

// ---- S11：未追蹤的整個「別人資料夾」被刪 → 是否擋
{ const E = fresh('s11'); fs.rmSync(path.join(E.wk, '20260919', 'students', OTHER), { recursive: true });
  W(path.join(E.wk, '20260919', 'students', ME, 'a.md'), 'a');
  const c = check(E);
  rec('S11', '刪掉別人的資料夾', c.status === 0 ? 'BUG' : 'OK', '檢查 exit=' + c.status); }

// ---- S12：在 main 以外但不是學生分支（master、別人的分支名）
{ const E = fresh('s12'); must(E.wk, ['checkout', '-b', 'master']); W(path.join(E.wk, '20260919', 'students', ME, 'a.md'), 'a');
  const c = check(E);
  rec('S12', '分支名不檢查前綴（master／別人的前綴）', c.status === 0 ? 'INFO' : 'OK', '在 master 上檢查 exit=' + c.status + '（設定只擋「main」，分支前綴 student/A14530068 沒有被強制）'); }

fs.writeFileSync(path.join(root, 'cs_results.json'), JSON.stringify(results, null, 1), 'utf8');
console.log('\n總結：BUG ' + results.filter(r => r.verdict === 'BUG').length + ' ｜ INFO ' + results.filter(r => r.verdict === 'INFO').length + ' ｜ OK ' + results.filter(r => r.verdict === 'OK').length);
