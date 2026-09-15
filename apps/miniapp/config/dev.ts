import type { UserConfigExport } from '@tarojs/cli'

export default {
  logger: {
    quiet: false,
    stats: true,
  },
  mini: {},
  h5: {
    devServer: {
      port: 10086,
      // H5 开发期同源代理：普通 API 与 SSE 都由 devServer 转给后端，浏览器看到的是同源，
      // 不必为了本地联调去放开后端 CORS。
      proxy: {
        '/api': {
          target: 'http://localhost:8080',
          changeOrigin: true,
        },
      },
    },
  },
} satisfies UserConfigExport<'webpack5'>
