// Copyright (c) 2025 CC-Island Contributors
// SPDX-License-Identifier: MIT
import { useState } from 'react'
import { BarcodeScanner, BarcodeFormat } from '@capacitor-mlkit/barcode-scanning'
import 'barcode-detector/polyfill'

interface AddDeviceModalProps {
  onClose: () => void
  onAdd: (token: string) => void
  onUpdateServer?: (url: string) => void
}

export function AddDeviceModal({ onClose, onAdd, onUpdateServer }: AddDeviceModalProps) {
  const [token, setToken] = useState('')
  const [scanning, setScanning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = () => {
    if (token.trim()) {
      onAdd(token.trim())
      onClose()
    }
  }

  const handleScan = async () => {
    setError(null)
    setScanning(true)

    try {
      // Request permissions first
      const { camera } = await BarcodeScanner.requestPermissions()
      if (!camera) {
        setError('需要相机权限才能扫描二维码')
        setScanning(false)
        return
      }

      // Scan for QR codes
      const { barcodes } = await BarcodeScanner.scan({
        formats: [BarcodeFormat.QrCode],
      })

      if (barcodes.length > 0 && barcodes[0].rawValue) {
        const rawValue = barcodes[0].rawValue

        // Try to parse as JSON (new format with device_token and server_url)
        try {
          const payload = JSON.parse(rawValue)
          if (payload.device_token) {
            setToken(payload.device_token)
            // Also update server URL if provided
            if (payload.server_url && onUpdateServer) {
              onUpdateServer(payload.server_url)
            }
            setError(null)
          } else {
            // Fallback: treat as plain token
            setToken(rawValue)
            setError(null)
          }
        } catch {
          // Not JSON, treat as plain token (backward compatibility)
          setToken(rawValue)
          setError(null)
        }
      } else {
        setError('未检测到二维码')
      }
    } catch (err) {
      console.error('Scan error:', err)
      setError('扫描失败，请手动输入')
    }

    setScanning(false)
  }

  return (
    <div className="fixed inset-0 bg-[#0f0f0f]/80 flex items-center justify-center z-50">
      <div className="bg-white rounded-[12px] w-[90%] max-w-sm shadow-lg">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#e5e5e5]">
          <span className="text-[#1a1a1a] text-lg font-medium">添加设备</span>
          <button onClick={onClose} className="text-[#737373] text-lg">×</button>
        </div>

        {/* Content */}
        <div className="p-4">
          <div className="text-[#737373] text-xs mb-1">设备 Token</div>
          <input
            type="text"
            placeholder="粘贴从桌面端复制的 Token"
            value={token}
            onChange={e => setToken(e.target.value)}
            className="w-full px-3 py-2 bg-[#f5f5f5] border border-[#e5e5e5] rounded-[8px] text-[#1a1a1a] text-sm outline-none focus:border-[#22c55e]"
          />

          {error && (
            <div className="text-[#ef4444] text-xs mt-2">{error}</div>
          )}

          <div className="text-[#737373] text-xs mt-3 mb-4">
            在桌面端设置中查看设备 Token，或扫描二维码自动填入
          </div>

          {/* Buttons */}
          <div className="flex gap-3 mb-3">
            <button
              onClick={handleScan}
              disabled={scanning}
              className="flex-1 py-2 bg-[#1a1a1a] rounded-[8px] text-white text-sm font-medium disabled:bg-[#e5e5e5] disabled:text-[#737373]"
            >
              {scanning ? '扫描中...' : '扫描二维码'}
            </button>
          </div>

          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="flex-1 py-2 bg-[#f5f5f5] rounded-[8px] text-[#737373] text-sm"
            >
              取消
            </button>
            <button
              onClick={handleSubmit}
              disabled={!token.trim()}
              className="flex-1 py-2 bg-[#22c55e] rounded-[8px] text-white text-sm font-medium disabled:bg-[#e5e5e5] disabled:text-[#737373]"
            >
              添加
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}