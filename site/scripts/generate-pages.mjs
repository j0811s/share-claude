import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const BASE = '/share-claude';
const GITHUB = 'https://github.com/j0811s/share-claude/blob/main/';
const NO_DESC = '（説明なし）';
const NONE = 'なし';
// 共通設定のページを置くディレクトリ。エクスポータがプロジェクト名としての使用を禁止している
const COMMON = 'common';
const EVENT_LABELS = { PreToolUse: 'ツール実行前', PostToolUse: 'ツール実行後' };

const originLabel = (o) => (o === 'common' ? '共通' : '専用');
const ghLink = (text, repoPath) => `[${text}](${GITHUB}${repoPath})`;
const oneLine = (s) => String(s).replace(/\s*\n\s*/g, ' ');
const escapeTable = (s) => s.replace(/\|/g, '\\|');
// 説明文中の <tag> が HTML として解釈され消えるのを防ぐ
const escapeHtml = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const text = (s) => escapeHtml(oneLine(s));
const cell = (s) => escapeTable(text(s));
// 中身のバッククォートより長いフェンスで囲む（コードスパン内は HTML エスケープ不要）
const code = (s) => {
  const body = oneLine(s);
  const longest = Math.max(0, ...(body.match(/`+/g) ?? []).map((run) => run.length));
  const fence = '`'.repeat(longest + 1);
  const pad = longest ? ' ' : '';
  return `${fence}${pad}${body}${pad}${fence}`;
};
const codeCell = (s) => escapeTable(code(s));
const frontmatter = (title, order, label) => {
  const lines = [`title: ${JSON.stringify(title)}`];
  if (order !== undefined) {
    lines.push('sidebar:', `  order: ${order}`);
    if (label) lines.push(`  label: ${JSON.stringify(label)}`);
  }
  return `---\n${lines.join('\n')}\n---\n\n`;
};
const table = (headers, rows) =>
  [`| ${headers.join(' | ')} |`, `| ${headers.map(() => '---').join(' | ')} |`, ...rows.map((r) => `| ${r.join(' | ')} |`)].join('\n') + '\n';

const invocation = (s) => `/${s.name}${s.argumentHint ? ` ${s.argumentHint}` : ''}`;
// 共通スキルのページは共通側にだけ作り、プロジェクトからはそこへリンクする
const skillSection = (section, s) => (s.origin === 'common' ? COMMON : section.name);
const skillUrl = (section, s) => `${BASE}/${skillSection(section, s)}/skills/${s.dir}/`;

function renderIndex(project) {
  const rows = project.skills.map((s) => [
    `[${codeCell(invocation(s))}](${skillUrl(project, s)})`,
    s.description ? cell(s.description) : NO_DESC,
    originLabel(s.origin) + (s.manualOnly ? '・手動のみ' : ''),
  ]);
  const links = [
    `- [自動で動くもの（hooks）](${BASE}/${project.name}/hooks/)`,
    `- [禁止・許可](${BASE}/${project.name}/permissions/)`,
  ];
  if (project.claudeMd) links.push(`- ${ghLink('CLAUDE.md', project.claudeMd)}`);
  for (const r of project.rules) links.push(`- ${ghLink(path.posix.basename(r), r)}`);
  return (
    frontmatter(project.title ?? project.name, 0, '概要') +
    (project.intro ? `${project.intro}\n\n` : '') +
    '## スキル一覧\n\n' +
    (rows.length ? table(['呼び方', 'できること', '区分'], rows) : `${NONE}\n`) +
    '\n## 関連\n\n' + links.join('\n') + '\n'
  );
}

function renderSkill(s) {
  return (
    frontmatter(s.name) +
    ':::note\n' +
    `- 呼び方: ${code(invocation(s))}\n` +
    `- できること: ${s.description ? text(s.description) : NO_DESC}\n` +
    `- 区分: ${originLabel(s.origin)}\n` +
    `- Claude が自動で使うか: ${s.manualOnly ? 'いいえ（手動で呼んだときだけ）' : 'はい'}\n` +
    `- ソース: ${ghLink(s.path, s.path)}\n` +
    ':::\n'
  );
}

function renderHooks(project) {
  const rows = project.hooks.map((h) => {
    const timing = (h.matcher ? `${codeCell(h.matcher)} の` : '') + cell(EVENT_LABELS[h.event] ?? h.event);
    const content = h.script
      ? `${h.script.description ? cell(h.script.description) : NO_DESC} （${ghLink('スクリプト', h.script.path)}）`
      : codeCell(h.command);
    return [timing, content, originLabel(h.origin)];
  });
  return frontmatter('自動で動くもの', 90) + (rows.length ? table(['タイミング', '内容', '区分'], rows) : `${NONE}\n`);
}

function renderPermissions(project) {
  const sections = [['deny', '禁止'], ['ask', '実行前に確認'], ['allow', '確認なしで実行']];
  const body = sections.map(([key, title]) => {
    const items = project.permissions[key] ?? [];
    const rows = items.map((p) => [codeCell(p.rule), originLabel(p.origin)]);
    return `## ${title}\n\n` + (rows.length ? table(['ルール', '区分'], rows) : `${NONE}\n`);
  });
  return frontmatter('禁止・許可', 91) + body.join('\n');
}

function renderSection(section) {
  const n = section.name;
  return [
    { path: `${n}/index.md`, content: renderIndex(section) },
    ...section.skills
      .filter((s) => skillSection(section, s) === n)
      .map((s) => ({ path: `${n}/skills/${s.dir}.md`, content: renderSkill(s) })),
    { path: `${n}/hooks.md`, content: renderHooks(section) },
    { path: `${n}/permissions.md`, content: renderPermissions(section) },
  ];
}

export const renderProject = (project) => renderSection(project);

export const renderCommon = (common) =>
  renderSection({
    ...common,
    name: COMMON,
    title: '共通',
    intro: 'すべてのプロジェクトに配られる設定です。各プロジェクトのページにも、この内容が含まれています。',
    claudeMd: null,
    rules: [],
  });

function main() {
  const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
  const data = JSON.parse(fs.readFileSync(path.join(root, 'src/generated/docs-data.json'), 'utf8'));
  const docs = path.join(root, 'src/content/docs');
  // 生成物だけを消す: 手書きの index.mdx 等は残し、サブディレクトリのみ対象
  for (const entry of fs.readdirSync(docs, { withFileTypes: true })) {
    if (entry.isDirectory()) fs.rmSync(path.join(docs, entry.name), { recursive: true });
  }
  for (const files of [renderCommon(data.common), ...data.projects.map(renderProject)]) {
    for (const f of files) {
      const dest = path.join(docs, f.path);
      fs.mkdirSync(path.dirname(dest), { recursive: true });
      fs.writeFileSync(dest, f.content);
    }
  }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) main();
