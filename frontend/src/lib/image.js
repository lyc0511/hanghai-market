/**
 * 图片预处理：在浏览器里把图片重新画一遍再导出。校园墙的图片上传前都会经过这里，有三个作用：
 *   1. 去掉照片里的隐藏信息（EXIF：拍摄地点、设备型号、拍摄时间）——匿名投稿不能靠照片被定位到人
 *   2. 把长边缩小到 1600 像素以内并压缩，上传更快、看墙更省流量
 *   3. 统一成 JPEG，后面的打码工具直接在这张图上涂抹
 * 整个过程在用户自己的设备上完成，原图不会离开浏览器。
 */
const MAX_SIDE = 1600
const QUALITY = 0.86

/** 把文件 / Blob 解码成 <img>；浏览器会按 EXIF 里的方向自动把图片摆正 */
export function loadImage(blob) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(blob)
    const img = new Image()
    img.onload = () => {
      URL.revokeObjectURL(url)
      resolve(img)
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('图片无法读取'))
    }
    img.src = url
  })
}

export function canvasToJpeg(canvas) {
  return new Promise((resolve, reject) => {
    canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('图片导出失败'))), 'image/jpeg', QUALITY)
  })
}

/** 缩小、去掉隐藏信息、转成 JPEG，返回 Blob */
export async function prepareImage(file) {
  const img = await loadImage(file)
  const scale = Math.min(1, MAX_SIDE / Math.max(img.naturalWidth, img.naturalHeight))
  const canvas = document.createElement('canvas')
  canvas.width = Math.max(1, Math.round(img.naturalWidth * scale))
  canvas.height = Math.max(1, Math.round(img.naturalHeight * scale))
  const ctx = canvas.getContext('2d')
  // JPEG 没有透明：先铺白底，透明的 PNG 才不会变成黑色
  ctx.fillStyle = '#fff'
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
  return canvasToJpeg(canvas)
}
