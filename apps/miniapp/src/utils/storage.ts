import Taro from '@tarojs/taro'

/** localStorage 的小程序等价物。Taro 的同步存储 API 在小程序/H5 下行为一致。 */
export const storage = {
  get<T>(key: string): T | null {
    try {
      const v = Taro.getStorageSync(key)
      return v === '' || v === undefined || v === null ? null : (v as T)
    } catch {
      return null
    }
  },
  set(key: string, value: unknown) {
    try {
      Taro.setStorageSync(key, value)
    } catch {
      // 存储满/被禁用时忽略，调用方不应因缓存失败而中断主流程
    }
  },
  remove(key: string) {
    try {
      Taro.removeStorageSync(key)
    } catch {
      // 同上
    }
  },
}
