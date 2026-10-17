// @ts-check
import fs from 'node:fs';
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// `npm run export` が書き出すデータ。無ければ（初回 dev など）共通・プロジェクト無しで起動する
const dataPath = new URL('./src/generated/docs-data.json', import.meta.url);
const data = fs.existsSync(dataPath) ? JSON.parse(fs.readFileSync(dataPath, 'utf8')) : null;

// 共通・各プロジェクトのサイドバーグループ。スキルのページは
// generate-pages.mjs と同じ規則で置かれる（共通スキルは共通側にだけある）
const section = (dir, label, ownSkills) => ({
	label,
	items: [
		{ slug: dir },
		...(ownSkills.length ? [{ label: 'スキル', items: [{ autogenerate: { directory: `${dir}/skills` } }] }] : []),
		{ slug: `${dir}/hooks` },
		{ slug: `${dir}/permissions` },
	],
});
const sections = data
	? [
			section('common', '共通', data.common.skills),
			...data.projects.map((p) => section(p.name, p.name, p.skills.filter((s) => s.origin === 'project'))),
		]
	: [];

// https://astro.build/config
export default defineConfig({
	site: 'https://j0811s.github.io',
	base: '/share-claude',
	integrations: [
		starlight({
			title: 'share-claude',
			defaultLocale: 'root',
			locales: { root: { label: '日本語', lang: 'ja' } },
			social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/j0811s/share-claude' }],
			sidebar: [
				{ label: 'はじめに', link: '/' },
				...sections,
			],
		}),
	],
});
