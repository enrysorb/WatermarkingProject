/**
 * API functions for watermarking images
 */

// Types for watermark methods
export interface WatermarkMethod {
  name: string
  description: string
  strength: string
  speed: string
  recommended_for: string
  requires?: string
}

export interface WatermarkMethods {
  invisible_methods: Record<string, WatermarkMethod>
}

export interface ExtractionResult {
  success: boolean
  extracted_text?: string
  method_used: string
  error?: string
}

// Apply text watermark to an image
export async function applyTextWatermark(
  imageFile: File,
  text: string,
  position: string,
  opacity: number,
  size: number,
): Promise<Blob> {
  const formData = new FormData()
  formData.append("file", imageFile)
  formData.append("text", text)
  formData.append("position", position)
  formData.append("opacity", (opacity / 100).toString()) // Convert percentage to decimal
  formData.append("size", size.toString())

  const response = await fetch("http://localhost:8000/apply-visible-watermark", {
    method: "POST",
    body: formData,
  })

  if (!response.ok) {
    throw new Error(`Failed to apply text watermark: ${response.statusText}`)
  }

  return await response.blob()
}

// Apply invisible watermark to an image (using advanced method)
export async function applyInvisibleWatermark(imageFile: File, hiddenText: string, method = "lsb"): Promise<Blob> {
  const formData = new FormData()
  formData.append("file", imageFile)
  formData.append("hidden_text", hiddenText) // Note: parameter name is "hidden_text"
  formData.append("method", method)

  const response = await fetch("http://localhost:8000/apply-invisible-watermark", {
    method: "POST",
    body: formData,
  })

  if (!response.ok) {
    throw new Error(`Failed to apply invisible watermark: ${response.statusText}`)
  }

  return await response.blob()
}

// Extract invisible watermark from an image
export async function extractInvisibleWatermark(imageFile: File, method = "lsb"): Promise<ExtractionResult> {
  const formData = new FormData()
  formData.append("file", imageFile)
  formData.append("method", method)

  const response = await fetch("http://localhost:8000/extract-invisible-watermark", {
    method: "POST",
    body: formData,
  })

  if (!response.ok) {
    throw new Error(`Failed to extract invisible watermark: ${response.statusText}`)
  }

  return await response.json()
}

// Apply logo watermark to an image
export async function applyLogoWatermark(
  imageFile: File,
  logoFile: File,
  position: string,
  opacity: number,
  size: number,
): Promise<Blob> {
  const formData = new FormData()
  formData.append("file", imageFile)
  formData.append("logo", logoFile)
  formData.append("position", position)
  formData.append("opacity", (opacity / 100).toString()) // Convert percentage to decimal
  formData.append("size", (size / 100).toString()) // Convert percentage to decimal

  const response = await fetch("http://localhost:8000/apply-logo-watermark", {
    method: "POST",
    body: formData,
  })

  if (!response.ok) {
    throw new Error(`Failed to apply logo watermark: ${response.statusText}`)
  }

  return await response.blob()
}

// Get available watermark methods
export async function getWatermarkMethods(): Promise<WatermarkMethods> {
  const response = await fetch("http://localhost:8000/watermark-methods")

  if (!response.ok) {
    throw new Error(`Failed to get watermark methods: ${response.statusText}`)
  }

  return await response.json()
}

// Check server health
export async function checkServerHealth(): Promise<any> {
  const response = await fetch("http://localhost:8000/health")

  if (!response.ok) {
    throw new Error(`Failed to check server health: ${response.statusText}`)
  }

  return await response.json()
}

// Helper function to download a blob as a file
export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement("a")
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

// Helper function to get file extension
export function getFileExtension(filename: string): string {
  return filename.split(".").pop() || "png"
}

// Helper function to generate watermarked filename
export function generateWatermarkedFilename(originalFilename: string, watermarkType: string, method?: string): string {
  const nameWithoutExt = originalFilename.replace(/\.[^/.]+$/, "")
  const ext = getFileExtension(originalFilename)
  const methodSuffix = method ? `_${method}` : ""
  return `${nameWithoutExt}_watermarked_${watermarkType}${methodSuffix}.${ext}`
}
