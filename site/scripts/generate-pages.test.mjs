import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderProject } from './generate-pages.mjs';

const project = { name: 'p', claudeMd: null, rules: [],
  skills: [{ name: 's', description: 'a | b\nc "q": x', argumentHint: '[n]', manualOnly: true, origin: 'project', path: 'project/p/skills/s/SKILL.md' },
           { name: 't', description: null, argumentHint: null, manualOnly: false, origin: 'common', path: 'common/skills/t/SKILL.md' }],
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
