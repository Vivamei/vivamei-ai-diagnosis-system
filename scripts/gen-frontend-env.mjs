/**
 * 由 config/frontend.env（前端配置唯一真源）生成两端各自的 .env 文件。
 *
 * 为什么需要这一层：Vite 只注入 VITE_ 前缀的变量，Taro 只注入 TARO_APP_ 前缀的，
 * 前缀是构建工具的硬规则、互不相认，两端没法直接共读一个文件。于是真源里写不带前缀
 * 的键，这里按目标平台补前缀分发。人只维护一份，避免「H5 文案改了小程序没改」。
 *
 * 用法（都已串进构建流程，一般不用手跑）：
 *   node scripts/gen-frontend-env.mjs          → 生成全部三个文件
 *   node scripts/gen-frontend-env.mjs web      → 只生成 apps/web/.env.production
 *   node scripts/gen-frontend-env.mjs miniapp  → 只生成 apps/miniapp 的两个 .env
 * 目标走命令行参数而不是环境变量前缀式写法，因为本项目日常在 Windows cmd 下开发。
 */
import { readFileSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const srcPath = resolve(root, 'config/frontend.env')

const SECTIONS = {
  共用: 'shared',
  'H5 专用': 'h5',
  小程序专用: 'weapp',
  小程序开发专用: 'weappDev',
}

/**
 * 解析真源：以 `# ===== [段名] =====` 分段，段内是普通 KEY=VALUE。
 * 值不做引号剥离——文案里带中文标点很常见，原样写出去即可。
 */
function parse(text) {
  const out = { shared: [], h5: [], weapp: [], weappDev: [] }
  let cur = null
  for (const line of text.split(/\r?\n/)) {
    const header = line.match(/^#\s*=+\s*\[(.+?)\]\s*=+\s*$/)
    if (header) {
      cur = SECTIONS[header[1].trim()]
      if (!cur) throw new Error(`config/frontend.env 出现未知段名 [${header[1]}]`)
      continue
    }
    const trimmed = line.trim()
    if (!cur || !trimmed || trimmed.startsWith('#')) continue
    const eq = trimmed.indexOf('=')
    if (eq === -1) continue
    out[cur].push([trimmed.slice(0, eq).trim(), trimmed.slice(eq + 1).trim()])
  }
  return out
}

/** 后面的段覆盖前面的同名键（小程序开发段覆盖生产段）。 */
function merge(...groups) {
  const map = new Map()
  for (const g of groups) for (const [k, v] of g) map.set(k, v)
  return [...map]
}

function render(prefix, pairs, note) {
  const head = [
    '# 本文件由 scripts/gen-frontend-env.mjs 从 config/frontend.env 生成，请勿手改。',
    '# 要改值请改 config/frontend.env，然后重新构建（构建脚本会自动重新生成本文件）。',
    `# ${note}`,
    '',
  ]
  return `${head.concat(pairs.map(([k, v]) => `${prefix}${k}=${v}`)).join('\n')}\n`
}

const src = parse(readFileSync(srcPath, 'utf8'))
const target = process.argv[2] || 'all'

const jobs = []
if (target === 'all' || target === 'web') {
  jobs.push([
    'apps/web/.env.production',
    render('VITE_', merge(src.shared, src.h5), 'H5 生产配置（Vite 构建期注入）'),
  ])
}
if (target === 'all' || target === 'miniapp') {
  jobs.push([
    'apps/miniapp/.env.production',
    render('TARO_APP_', merge(src.shared, src.weapp), '小程序生产配置（build:weapp / build:h5 读取）'),
  ])
  jobs.push([
    'apps/miniapp/.env.development',
    render(
      'TARO_APP_',
      merge(src.shared, src.weapp, src.weappDev),
      '小程序开发配置（dev:weapp / dev:h5 读取）',
    ),
  ])
}
if (!jobs.length) {
  console.error(`[gen-frontend-env] 未知目标 "${target}"（可用：all / web / miniapp）`)
  process.exit(2)
}

for (const [rel, content] of jobs) {
  writeFileSync(resolve(root, rel), content, 'utf8')
  console.log(`[gen-frontend-env] ${rel}`)
}
