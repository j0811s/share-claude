import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const BASE = '/share-claude';
const GITHUB = 'https://github.com/j0811s/share-claude/blob/main/';
const NO_DESC = '（説明なし）';
const NONE = 'なし';
const EVENT_LABELS = { PreToolUse: 'ツール実行前', PostToolUse: 'ツール実行後' };

const originLabel = (o) => (o === 'common' ? '共通' : '専用');
const ghLink = (text, repoPath) => `[${text}](${GITHUB}${repoPath})`;
const oneLine = (s) => String(s).replace(/\s*\n\s*/g, ' ');
const cell = (s) => oneLine(s).replace(/\|/g, '\\|');
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
const skillUrl = (project, s) => `${BASE}/${project.name}/skills/${s.name}/`;

function renderIndex(project) {
  const rows = project.skills.map((s) => [
    `[\`${cell(invocation(s))}\`](${skillUrl(project, s)})`,
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
    frontmatter(project.name, 0, '概要') +
    '## スキル一覧\n\n' +
    (rows.length ? table(['呼び方', 'できること', '区分'], rows) : `${NONE}\n`) +
    '\n## 関連\n\n' + links.join('\n') + '\n'
  );
}

function renderSkill(s) {
  return (
    frontmatter(s.name) +
    ':::note\n' +
    `- 呼び方: \`${invocation(s)}\`\n` +
    `- できること: ${s.description ? oneLine(s.description) : NO_DESC}\n` +
    `- 区分: ${originLabel(s.origin)}\n` +
    `- Claude が自動で使うか: ${s.manualOnly ? 'いいえ（手動で呼んだときだけ）' : 'はい'}\n` +
    `- ソース: ${ghLink(s.path, s.path)}\n` +
    ':::\n'
  );
}

function renderHooks(project) {
  const rows = project.hooks.map((h) => {
    const timing = (h.matcher ? `\`${cell(h.matcher)}\` の` : '') + (EVENT_LABELS[h.event] ?? h.event);
    const content = h.script
      ? `${h.script.description ? cell(h.script.description) : NO_DESC} （${ghLink('スクリプト', h.script.path)}）`
      : `\`${cell(h.command)}\``;
    return [timing, content, originLabel(h.origin)];
  });
  return frontmatter('自動で動くもの', 90) + (rows.length ? table(['タイミング', '内容', '区分'], rows) : `${NONE}\n`);
}

function renderPermissions(project) {
  const sections = [['deny', '禁止'], ['ask', '実行前に確認'], ['allow', '確認なしで実行']];
  const body = sections.map(([key, title]) => {
    const items = project.permissions[key] ?? [];
    const rows = items.map((p) => [`\`${cell(p.rule)}\``, originLabel(p.origin)]);
    return `## ${title}\n\n` + (rows.length ? table(['ルール', '区分'], rows) : `${NONE}\n`);
  });
  return frontmatter('禁止・許可', 91) + body.join('\n');
}

export function renderProject(project) {
  const n = project.name;
  return [
    { path: `${n}/index.md`, content: renderIndex(project) },
    ...project.skills.map((s) => ({ path: `${n}/skills/${s.name}.md`, content: renderSkill(s) })),
    { path: `${n}/hooks.md`, content: renderHooks(project) },
    { path: `${n}/permissions.md`, content: renderPermissions(project) },
  ];
}

function main() {
  const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
  const data = JSON.parse(fs.readFileSync(path.join(root, 'src/generated/docs-data.json'), 'utf8'));
  const docs = path.join(root, 'src/content/docs');
  // 生成物だけを消す: 手書きの index.mdx 等は残し、サブディレクトリのみ対象
  for (const entry of fs.readdirSync(docs, { withFileTypes: true })) {
    if (entry.isDirectory()) fs.rmSync(path.join(docs, entry.name), { recursive: true });
  }
  for (const project of data.projects) {
    for (const f of renderProject(project)) {
      const dest = path.join(docs, f.path);
      fs.mkdirSync(path.dirname(dest), { recursive: true });
      fs.writeFileSync(dest, f.content);
    }
  }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) main();
