import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderProject } from './generate-pages.mjs';

const project = { name: 'p', claudeMd: null, rules: [],
  skills: [{ name: 's', dir: 's', description: 'a | b\nc "q": x', argumentHint: '[n]', manualOnly: true, origin: 'project', path: 'project/p/skills/s/SKILL.md' },
           { name: 't', dir: 't', description: null, argumentHint: null, manualOnly: false, origin: 'common', path: 'common/skills/t/SKILL.md' }],
  hooks: [], permissions: { deny: [], ask: [], allow: [] } };
const files = Object.fromEntries(renderProject(project).map(f => [f.path, f.content]));

test('生成されるファイル', () => assert.deepEqual(Object.keys(files).sort(),
  ['p/hooks.md', 'p/index.md', 'p/permissions.md', 'p/skills/s.md', 'p/skills/t.md']));
test('表セルの | と改行をエスケープ', () => assert.match(files['p/index.md'], /a \\\| b c "q": x/));
test('呼び方と区分', () => { assert.match(files['p/index.md'], /`\/s \[n\]`/); assert.match(files['p/index.md'], /専用・手動のみ/); });
test('説明なし', () => assert.match(files['p/index.md'], /（説明なし）/));
test('frontmatter が壊れない', () => assert.match(files['p/skills/s.md'], /^---\ntitle: "s"\n/));
test('hooks/permissions 0件は「なし」', () => { assert.match(files['p/hooks.md'], /なし/); assert.match(files['p/permissions.md'], /なし/); });
test('GitHub リンク', () => assert.match(files['p/skills/s.md'],
  /https:\/\/github\.com\/j0811s\/share-claude\/blob\/main\/project\/p\/skills\/s\/SKILL\.md/));

const full = { name: 'q', claudeMd: 'project/q/CLAUDE.md', rules: ['project/q/rules/r.md'],
  skills: [{ name: 'x', dir: 'x-dir', description: '<b> を & で使う', argumentHint: null, manualOnly: false, origin: 'project', path: 'project/q/skills/x-dir/SKILL.md' }],
  hooks: [
    { event: 'PreToolUse', matcher: 'Edit|Write', command: '$CLAUDE_PROJECT_DIR/.claude/hooks/a.sh', origin: 'common',
      script: { path: 'common/hooks/a.sh', description: '説明A' } },
    { event: 'Stop', matcher: null, command: 'echo `date` | tee log', origin: 'project', script: null },
  ],
  permissions: { deny: [{ rule: 'Bash(rm -rf:*)', origin: 'common' }], ask: [], allow: [{ rule: 'Bash(npm run:*)', origin: 'project' }] } };
const q = Object.fromEntries(renderProject(full).map(f => [f.path, f.content]));

test('スキルのページはディレクトリ名で作り、リンクも合わせる', () => {
  assert.ok(q['q/skills/x-dir.md']);
  assert.match(q['q/index.md'], /\(\/share-claude\/q\/skills\/x-dir\/\)/);
});
test('説明文の HTML 記号をエスケープ', () => {
  assert.match(q['q/index.md'], /&lt;b&gt; を &amp; で使う/);
  assert.match(q['q/skills/x-dir.md'], /&lt;b&gt; を &amp; で使う/);
});
test('hooks: matcher とイベント名の表示、スクリプトの説明とリンク', () => {
  assert.match(q['q/hooks.md'], /`Edit\\\|Write` のツール実行前/);
  assert.match(q['q/hooks.md'], /説明A （\[スクリプト\]\(https:\/\/github\.com\/j0811s\/share-claude\/blob\/main\/common\/hooks\/a\.sh\)）/);
  assert.match(q['q/hooks.md'], /\| Stop \|/);
});
test('hooks: バッククォートを含むコマンドは長いフェンスのコード表示', () =>
  assert.match(q['q/hooks.md'], /`` echo `date` \\\| tee log ``/));
test('permissions の行と区分', () => {
  assert.match(q['q/permissions.md'], /\| `Bash\(rm -rf:\*\)` \| 共通 \|/);
  assert.match(q['q/permissions.md'], /## 実行前に確認\n\nなし/);
  assert.match(q['q/permissions.md'], /\| `Bash\(npm run:\*\)` \| 専用 \|/);
});
test('CLAUDE.md と rules へのリンク', () => {
  assert.match(q['q/index.md'], /\[CLAUDE\.md\]\(https:\/\/github\.com\/j0811s\/share-claude\/blob\/main\/project\/q\/CLAUDE\.md\)/);
  assert.match(q['q/index.md'], /\[r\.md\]\(https:\/\/github\.com\/j0811s\/share-claude\/blob\/main\/project\/q\/rules\/r\.md\)/);
});
test('スキル0件は「なし」', () => {
  const empty = Object.fromEntries(renderProject({ ...full, skills: [] }).map(f => [f.path, f.content]));
  assert.match(empty['q/index.md'], /## スキル一覧\n\nなし/);
});
