import { readdir, readFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const outputRoot = fileURLToPath(new URL('../dist/weapp/', import.meta.url))
const rulePattern = /([^{}]+)\{/g
const universalSelectorPattern = /(^|[\s>+~,])\*(?=$|[\s>+~,.#:[{])/m

async function findWxssFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true })
  const nested = await Promise.all(
    entries.map((entry) => {
      const entryPath = path.join(directory, entry.name)
      return entry.isDirectory()
        ? findWxssFiles(entryPath)
        : Promise.resolve(entry.name.endsWith('.wxss') ? [entryPath] : [])
    }),
  )

  return nested.flat()
}

function findUniversalSelectors(css) {
  const source = css.replace(/\/\*[\s\S]*?\*\//g, '')
  const selectors = []

  for (const match of source.matchAll(rulePattern)) {
    const rule = match[1].trim()
    if (!rule.startsWith('@') && universalSelectorPattern.test(rule)) {
      selectors.push(rule)
    }
  }

  return selectors
}

const files = await findWxssFiles(outputRoot)
const violations = []

for (const file of files) {
  const css = await readFile(file, 'utf8')
  for (const selector of findUniversalSelectors(css)) {
    violations.push(`${path.relative(outputRoot, file)}: ${selector}`)
  }
}

if (violations.length > 0) {
  console.error('WXSS compatibility check failed: universal selectors are unsupported.')
  for (const violation of violations) console.error(`- ${violation}`)
  process.exitCode = 1
} else {
  console.log(`WXSS compatibility check passed (${files.length} files checked).`)
}
