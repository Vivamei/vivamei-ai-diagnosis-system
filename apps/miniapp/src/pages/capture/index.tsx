import { useState } from 'react'
import { Button, Checkbox, Image, Text, View } from '@tarojs/components'
import Taro, { useLoad } from '@tarojs/taro'

import { createAnalyze, LastTaskStore } from '@/api/analyze'
import { getUploadToken, registerPhoto, StsResp, uploadLocal } from '@/api/upload'
import { config } from '@/config'
import { requireLogin } from '@/utils/nav'
import { storage } from '@/utils/storage'
import './index.css'

const CONSENT_KEY = 'venus.consent'

interface Picked {
  path: string
  width: number
  height: number
  bytes: number
}

async function putImage(token: StsResp, p: Picked) {
  // 未配 OSS（MOCK 凭证）时改传后端本地存储，让原图能到后端供分析上送 LLM。
  if (token.accessKeyId.startsWith('STS.MOCK')) {
    await uploadLocal(token.objectKey, p.path)
    return
  }
  // 真 OSS 直传需要 V4 签名的 PostObject 表单（小程序只能发 multipart），
  // 这部分随 M10 部署阶段接入，当前先明确报错而不是静默传失败。
  throw new Error('OSS 直传尚未在小程序端接入，请联系管理员')
}

export default function Capture() {
  const [showConsent, setShowConsent] = useState(false)
  const [consentChecked, setConsentChecked] = useState(false)
  const [picked, setPicked] = useState<Picked | null>(null)
  const [uploading, setUploading] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  useLoad(() => {
    if (!requireLogin()) return
    if (storage.get<string>(CONSENT_KEY) !== config.consentVer) setShowConsent(true)
  })

  const agree = () => {
    storage.set(CONSENT_KEY, config.consentVer)
    setShowConsent(false)
  }

  // 只开相机、不给相册入口，保证采集来源可控（与 H5 端一致）。
  const shoot = async () => {
    setErr(null)
    try {
      const res = await Taro.chooseMedia({
        count: 1,
        mediaType: ['image'],
        sourceType: ['camera'],
        camera: 'front',
        sizeType: ['compressed'],
      })
      const f = res.tempFiles[0]
      if (!f) return
      const info = await Taro.getImageInfo({ src: f.tempFilePath })
      setPicked({
        path: f.tempFilePath,
        width: info.width,
        height: info.height,
        bytes: f.size,
      })
    } catch (e) {
      const msg = String((e as { errMsg?: string })?.errMsg || '')
      if (msg.includes('cancel')) return
      setErr('相机不可用，请检查小程序的相机权限后重试')
    }
  }

  const submit = async () => {
    if (!picked || uploading) return
    setUploading(true)
    setErr(null)
    try {
      const token = await getUploadToken()
      await putImage(token, picked)
      const photo = await registerPhoto({
        ossKey: token.objectKey,
        mime: 'image/jpeg',
        width: picked.width,
        height: picked.height,
        bytes: picked.bytes,
      })
      // 等待后端机审（mock 模式即时通过）
      await new Promise((r) => setTimeout(r, 700))
      const task = await createAnalyze(photo.photoId)
      // 记住这次任务，供中途离开后在首页找回（见 home 页的续看入口）
      LastTaskStore.save(task.taskId)
      Taro.redirectTo({ url: `/pages/analyzing/index?taskId=${task.taskId}` })
    } catch (e) {
      setErr(e instanceof Error ? e.message : '上传失败')
      setUploading(false)
    }
  }

  return (
    <View className='cap-page'>
      <View className='cap-title'>开始薇分美学4S测评</View>

      {uploading ? (
        <View className='cap-loading'>
          <View className='cap-spinner' />
          <View className='cap-loading__text'>正在上传并校验图像…</View>
        </View>
      ) : (
        <View>
          <View className='cap-tip'>
            建议自然光下正脸拍摄，去除眼镜与浓妆，分析效果更准。
          </View>

          <View className='cap-frame'>
            {picked ? (
              <Image className='cap-preview' src={picked.path} mode='aspectFill' />
            ) : (
              <View className='cap-frame__hint'>
                点击下方按钮开启相机{'\n'}保持正脸、光线均匀
              </View>
            )}
          </View>

          {picked ? (
            <View>
              <Button className='cap-btn' onClick={submit}>
                开始分析
              </Button>
              <Button className='cap-btn cap-btn--ghost' onClick={shoot}>
                重新拍摄
              </Button>
            </View>
          ) : (
            <Button className='cap-btn' onClick={shoot}>
              拍摄
            </Button>
          )}
        </View>
      )}

      {err && <View className='cap-err'>{err}</View>}

      {showConsent && (
        <View>
          <View className='cap-mask' />
          <View className='cap-sheet'>
            <View className='cap-sheet__title'>隐私协议与人脸采集授权</View>
            <View className='cap-sheet__body'>
              <View>本服务需收集您的：</View>
              <View className='cap-sheet__li'>
                · 面部照片（用于 AI 薇分美学4S诊断分析，分析后 10 天内自动删除）
              </View>
              <View className='cap-sheet__li'>· 手机号（用于身份验证与到店预约联系）</View>
              <View>详见《隐私政策》与《用户协议》。</View>
              <View className='cap-sheet__warn'>
                本报告为美学形象参考，不构成医疗诊断、治疗或术式建议。
              </View>
            </View>
            <View className='cap-sheet__check' onClick={() => setConsentChecked((v) => !v)}>
              <Checkbox value='consent' checked={consentChecked} color='#c8a376' />
              <Text>我已阅读并同意以上协议</Text>
            </View>
            <View className='cap-sheet__actions'>
              <Button
                className='cap-btn cap-btn--ghost cap-sheet__cancel'
                onClick={() => Taro.navigateBack()}
              >
                取消
              </Button>
              <Button
                className='cap-btn cap-sheet__ok'
                disabled={!consentChecked}
                onClick={agree}
              >
                同意并继续
              </Button>
            </View>
          </View>
        </View>
      )}
    </View>
  )
}
