export interface SseFrame {
  id?: string
  event: string
  data: string
}

/**
 * 小程序没有稳定可用的 TextDecoder。这里按流增量解 UTF-8，并保留被网络 chunk
 * 截断的多字节字符，避免中文恰好跨 chunk 时出现乱码。
 */
export class Utf8ChunkDecoder {
  private pending: number[] = []

  decode(chunk: ArrayBuffer, final = false): string {
    const incoming = new Uint8Array(chunk)
    const bytes = new Uint8Array(this.pending.length + incoming.length)
    bytes.set(this.pending, 0)
    bytes.set(incoming, this.pending.length)

    let out = ''
    let i = 0
    while (i < bytes.length) {
      const first = bytes[i]
      if (first < 0x80) {
        out += String.fromCharCode(first)
        i += 1
        continue
      }

      let width = 0
      let codePoint = 0
      let minimum = 0
      if (first >= 0xc2 && first <= 0xdf) {
        width = 2
        codePoint = first & 0x1f
        minimum = 0x80
      } else if (first >= 0xe0 && first <= 0xef) {
        width = 3
        codePoint = first & 0x0f
        minimum = 0x800
      } else if (first >= 0xf0 && first <= 0xf4) {
        width = 4
        codePoint = first & 0x07
        minimum = 0x10000
      } else {
        out += '\ufffd'
        i += 1
        continue
      }

      if (i + width > bytes.length) break

      let valid = true
      for (let j = 1; j < width; j += 1) {
        const next = bytes[i + j]
        if ((next & 0xc0) !== 0x80) {
          valid = false
          break
        }
        codePoint = (codePoint << 6) | (next & 0x3f)
      }

      if (
        !valid ||
        codePoint < minimum ||
        codePoint > 0x10ffff ||
        (codePoint >= 0xd800 && codePoint <= 0xdfff)
      ) {
        out += '\ufffd'
        i += 1
        continue
      }

      if (codePoint <= 0xffff) {
        out += String.fromCharCode(codePoint)
      } else {
        const cp = codePoint - 0x10000
        out += String.fromCharCode(0xd800 + (cp >> 10), 0xdc00 + (cp & 0x3ff))
      }
      i += width
    }

    this.pending = Array.from(bytes.slice(i))
    if (final && this.pending.length) {
      out += '\ufffd'
      this.pending = []
    }
    return out
  }

  finish(): string {
    return this.decode(new ArrayBuffer(0), true)
  }
}

/** 增量解析 text/event-stream；兼容网络 chunk 在任意字符或任意行中间断开。 */
export class SseParser {
  private buffer = ''
  private eventName = 'message'
  private eventId: string | undefined
  private dataLines: string[] = []

  constructor(private readonly emit: (frame: SseFrame) => void) {}

  push(text: string): void {
    if (!text) return
    this.buffer += text

    let start = 0
    for (let i = 0; i < this.buffer.length; i += 1) {
      const ch = this.buffer[i]
      if (ch !== '\n' && ch !== '\r') continue
      // CRLF 可能刚好跨两个网络 chunk，先保留末尾 CR，等下一块再判断。
      if (ch === '\r' && i + 1 === this.buffer.length) break

      this.consumeLine(this.buffer.slice(start, i))
      if (ch === '\r' && this.buffer[i + 1] === '\n') i += 1
      start = i + 1
    }
    this.buffer = this.buffer.slice(start)
  }

  finish(): void {
    if (this.buffer.endsWith('\r')) {
      this.consumeLine(this.buffer.slice(0, -1))
      this.buffer = ''
    } else if (this.buffer) {
      this.consumeLine(this.buffer)
      this.buffer = ''
    }
    this.dispatch()
  }

  private consumeLine(line: string): void {
    if (!line) {
      this.dispatch()
      return
    }
    if (line.startsWith(':')) return

    const colon = line.indexOf(':')
    const field = colon < 0 ? line : line.slice(0, colon)
    let value = colon < 0 ? '' : line.slice(colon + 1)
    if (value.startsWith(' ')) value = value.slice(1)

    if (field === 'event') this.eventName = value || 'message'
    else if (field === 'data') this.dataLines.push(value)
    else if (field === 'id' && !value.includes('\0')) this.eventId = value
  }

  private dispatch(): void {
    if (!this.dataLines.length) {
      this.eventName = 'message'
      return
    }
    this.emit({
      id: this.eventId,
      event: this.eventName,
      data: this.dataLines.join('\n'),
    })
    this.eventName = 'message'
    this.dataLines = []
  }
}
