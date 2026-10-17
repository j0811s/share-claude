// @ts-check
import fs from 'node:fs';
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// `npm run export` が書き出すデータ。無ければ（初回 dev など）プロジェクト無しで起動する
const dataPath = new URL('./src/generated/docs-data.json', import.meta.url);
const projects = fs.existsSync(dataPath) ? JSON.parse(fs.readFileSync(dataPath, 'utf8')).projects : [];

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
				...projects.map((p) => ({ label: p.name, items: [{ autogenerate: { directory: p.name } }] })),
			],
		}),
	],
});
