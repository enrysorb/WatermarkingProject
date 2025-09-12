import { type NextRequest, NextResponse } from "next/server"

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData()
    const file = formData.get("file") as File

    if (!file) {
      return NextResponse.json({ error: "No file provided" }, { status: 400 })
    }

    const watermarkType = formData.get("type") as string
    const position = (formData.get("position") as string) || "bottom-right"

    // Convert file to array buffer
    const bytes = await file.arrayBuffer()
    const buffer = Buffer.from(bytes)

    // Prepare the form data to send to FastAPI
    const apiFormData = new FormData()
    apiFormData.append("file", new Blob([buffer]), file.name)

    if (watermarkType === "text") {
      const text = (formData.get("text") as string) || "Watermark"
      apiFormData.append("text", text)
      apiFormData.append("position", position)

      // Call FastAPI endpoint
      const response = await fetch("http://localhost:8000/apply-visible-watermark", {
        method: "POST",
        body: apiFormData,
      })

      if (!response.ok) {
        throw new Error("Failed to apply visible watermark")
      }

      const result = await response.blob()
      return new NextResponse(result, {
        headers: {
          "Content-Type": "image/png",
        },
      })
    } else if (watermarkType === "invisible") {
      const text = (formData.get("text") as string) || "Copyright"
      apiFormData.append("text", text)

      // Call FastAPI endpoint
      const response = await fetch("http://localhost:8000/apply-invisible-watermark", {
        method: "POST",
        body: apiFormData,
      })

      if (!response.ok) {
        throw new Error("Failed to apply invisible watermark")
      }

      const result = await response.blob()
      return new NextResponse(result, {
        headers: {
          "Content-Type": "image/png",
        },
      })
    } else if (watermarkType === "logo") {
      const logo = formData.get("logo") as File
      if (!logo) {
        return NextResponse.json({ error: "No logo provided" }, { status: 400 })
      }

      const logoBytes = await logo.arrayBuffer()
      const logoBuffer = Buffer.from(logoBytes)

      apiFormData.append("logo", new Blob([logoBuffer]), logo.name)
      apiFormData.append("position", position)

      // Call FastAPI endpoint
      const response = await fetch("http://localhost:8000/apply-logo-watermark", {
        method: "POST",
        body: apiFormData,
      })

      if (!response.ok) {
        throw new Error("Failed to apply logo watermark")
      }

      const result = await response.blob()
      return new NextResponse(result, {
        headers: {
          "Content-Type": "image/png",
        },
      })
    }

    return NextResponse.json({ error: "Invalid watermark type" }, { status: 400 })
  } catch (error) {
    console.error("Error processing watermark:", error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to process watermark" },
      { status: 500 },
    )
  }
}
