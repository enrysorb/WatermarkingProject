"use client"

import type React from "react"

import { useState, useRef, useEffect } from "react"
import {
  Upload,
  ImageIcon,
  Type,
  EyeOff,
  ArrowRight,
  ImageIcon as ImageIcon2,
  Sliders,
  Download,
  CheckCircle,
  Search,
  Info,
  AlertCircle,
  FileSearch,
} from "lucide-react"
import { useDropzone } from "react-dropzone"
import {
  applyTextWatermark,
  applyInvisibleWatermark,
  applyLogoWatermark,
  extractInvisibleWatermark,
  getWatermarkMethods,
  checkServerHealth,
  downloadBlob,
  generateWatermarkedFilename,
  type WatermarkMethods,
  type ExtractionResult,
} from "@/lib/api"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Slider } from "@/components/ui/slider"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import { toast } from "@/components/ui/use-toast"
import { Progress } from "@/components/ui/progress"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Textarea } from "@/components/ui/textarea"

export default function WatermarkApp() {
  // State for uploaded images
  const [files, setFiles] = useState<File[]>([])
  const [previews, setPreviews] = useState<string[]>([])

  // State for watermark settings
  const [watermarkType, setWatermarkType] = useState("text")
  const [watermarkText, setWatermarkText] = useState("Watermark")
  const [watermarkPosition, setWatermarkPosition] = useState("bottom-right")
  const [watermarkOpacity, setWatermarkOpacity] = useState([70])
  const [watermarkSize, setWatermarkSize] = useState([30])

  // State for invisible watermark method
  const [invisibleMethod, setInvisibleMethod] = useState("lsb")
  const [watermarkMethods, setWatermarkMethods] = useState<WatermarkMethods | null>(null)

  // State for logo watermark
  const [logoFile, setLogoFile] = useState<File | null>(null)
  const [logoPreview, setLogoPreview] = useState<string>("")

  // State for extraction
  const [extractionFile, setExtractionFile] = useState<File | null>(null)
  const [extractionPreview, setExtractionPreview] = useState<string>("")
  const [extractionResult, setExtractionResult] = useState<ExtractionResult | null>(null)
  const [isExtracting, setIsExtracting] = useState(false)

  // Processing state
  const [isLoading, setIsLoading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [processedCount, setProcessedCount] = useState(0)

  // Server health state
  const [serverHealth, setServerHealth] = useState<any>(null)

  // Refs for file inputs
  const logoInputRef = useRef<HTMLInputElement>(null)
  const extractionInputRef = useRef<HTMLInputElement>(null)

  // Load watermark methods and server health on component mount
  useEffect(() => {
    const loadData = async () => {
      try {
        const [methods, health] = await Promise.all([getWatermarkMethods(), checkServerHealth()])
        setWatermarkMethods(methods)
        setServerHealth(health)
      } catch (error) {
        console.error("Failed to load server data:", error)
        toast({
          variant: "destructive",
          title: "Server connection failed",
          description: "Could not connect to the watermarking server. Please check if it's running.",
        })
      }
    }
    loadData()
  }, [])

  // Dropzone for main images
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      "image/*": [".jpeg", ".jpg", ".png", ".gif", ".webp"],
    },
    onDrop: (acceptedFiles) => {
      setFiles([...files, ...acceptedFiles])

      // Generate previews
      const newPreviews = acceptedFiles.map((file) => URL.createObjectURL(file))
      setPreviews([...previews, ...newPreviews])

      toast({
        title: "Images uploaded",
        description: `${acceptedFiles.length} image${acceptedFiles.length > 1 ? "s" : ""} successfully uploaded.`,
      })
    },
  })

  // Handle logo upload
  const handleLogoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0]
      setLogoFile(file)

      // Revoke previous object URL to avoid memory leaks
      if (logoPreview) {
        URL.revokeObjectURL(logoPreview)
      }

      // Create new preview
      const preview = URL.createObjectURL(file)
      setLogoPreview(preview)

      toast({
        title: "Logo uploaded",
        description: "Your logo has been uploaded and is ready to use as a watermark.",
      })
    }
  }

  // Handle extraction file upload
  const handleExtractionUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0]
      setExtractionFile(file)

      // Revoke previous object URL to avoid memory leaks
      if (extractionPreview) {
        URL.revokeObjectURL(extractionPreview)
      }

      // Create new preview
      const preview = URL.createObjectURL(file)
      setExtractionPreview(preview)

      // Reset previous extraction result
      setExtractionResult(null)

      toast({
        title: "Image uploaded for extraction",
        description: "Image ready for watermark extraction.",
      })
    }
  }

  // Remove an image from the preview
  const removeImage = (index: number) => {
    const newFiles = [...files]
    const newPreviews = [...previews]

    // Revoke object URL to avoid memory leaks
    URL.revokeObjectURL(previews[index])

    newFiles.splice(index, 1)
    newPreviews.splice(index, 1)

    setFiles(newFiles)
    setPreviews(newPreviews)

    toast({
      title: "Image removed",
      description: "The selected image has been removed from the queue.",
    })
  }

  // Remove logo
  const removeLogo = () => {
    if (logoPreview) {
      URL.revokeObjectURL(logoPreview)
    }
    setLogoFile(null)
    setLogoPreview("")

    toast({
      title: "Logo removed",
      description: "Your logo has been removed.",
    })
  }

  // Handle watermark extraction
  const handleExtractWatermark = async () => {
    if (!extractionFile) {
      toast({
        variant: "destructive",
        title: "No image selected",
        description: "Please upload an image to extract watermark from.",
      })
      return
    }

    setIsExtracting(true)

    try {
      const result = await extractInvisibleWatermark(extractionFile, invisibleMethod)
      setExtractionResult(result)

      if (result.success) {
        toast({
          title: "Watermark extracted successfully!",
          description: `Found hidden text using ${result.method_used} method.`,
        })
      } else {
        toast({
          variant: "destructive",
          title: "Extraction failed",
          description: result.error || "Could not extract watermark from this image.",
        })
      }
    } catch (error) {
      console.error("Error extracting watermark:", error)
      toast({
        variant: "destructive",
        title: "Extraction failed",
        description: error instanceof Error ? error.message : "Failed to extract watermark.",
      })
    } finally {
      setIsExtracting(false)
    }
  }

  // Handle apply watermark with automatic download
  const handleApplyWatermark = async () => {
    if (files.length === 0) {
      toast({
        variant: "destructive",
        title: "No images selected",
        description: "Please upload at least one image to apply watermark.",
      })
      return
    }

    if (watermarkType === "logo" && !logoFile) {
      toast({
        variant: "destructive",
        title: "No logo selected",
        description: "Please upload a logo image for the watermark.",
      })
      return
    }

    setIsLoading(true)
    setProgress(0)
    setProcessedCount(0)

    try {
      let successCount = 0
      let errorCount = 0

      // Process each image sequentially to avoid overwhelming the server
      for (let i = 0; i < files.length; i++) {
        const file = files[i]

        try {
          let processedBlob: Blob
          let watermarkTypeLabel: string
          let method: string | undefined

          if (watermarkType === "text") {
            processedBlob = await applyTextWatermark(
              file,
              watermarkText,
              watermarkPosition,
              watermarkOpacity[0],
              watermarkSize[0],
            )
            watermarkTypeLabel = "text"
          } else if (watermarkType === "invisible") {
            processedBlob = await applyInvisibleWatermark(file, watermarkText || "Copyright", invisibleMethod)
            watermarkTypeLabel = "invisible"
            method = invisibleMethod
          } else if (watermarkType === "logo" && logoFile) {
            processedBlob = await applyLogoWatermark(
              file,
              logoFile,
              watermarkPosition,
              watermarkOpacity[0],
              watermarkSize[0],
            )
            watermarkTypeLabel = "logo"
          } else {
            throw new Error("Invalid watermark configuration")
          }

          // Generate filename and download immediately
          const watermarkedFilename = generateWatermarkedFilename(file.name, watermarkTypeLabel, method)
          downloadBlob(processedBlob, watermarkedFilename)

          successCount++
          setProcessedCount(successCount)

          // Update progress
          const progressPercentage = ((i + 1) / files.length) * 100
          setProgress(progressPercentage)

          // Small delay between downloads to avoid browser blocking
          if (i < files.length - 1) {
            await new Promise((resolve) => setTimeout(resolve, 500))
          }
        } catch (error) {
          console.error(`Error processing ${file.name}:`, error)
          errorCount++

          toast({
            variant: "destructive",
            title: `Failed to process ${file.name}`,
            description: error instanceof Error ? error.message : "Unknown error occurred",
          })
        }
      }

      // Show final result
      if (successCount > 0) {
        toast({
          title: "Processing completed!",
          description: `Successfully processed and downloaded ${successCount} image${successCount > 1 ? "s" : ""}${errorCount > 0 ? `. ${errorCount} failed.` : "."}`,
          duration: 5000,
        })
      }
    } catch (error) {
      console.error("Error applying watermark:", error)
      toast({
        variant: "destructive",
        title: "Processing failed",
        description: error instanceof Error ? error.message : "Failed to apply watermark to images.",
      })
    } finally {
      setIsLoading(false)
      setProgress(0)
      setProcessedCount(0)
    }
  }

  return (
    <div className="container mx-auto py-10 px-4 max-w-6xl">
      <h1 className="text-3xl font-bold mb-2 text-center">Advanced Image Watermarking App</h1>
      <p className="text-center text-muted-foreground mb-8">
        Professional watermarking with multiple invisible methods and extraction capabilities
      </p>

      {/* Server Health Status */}
      {serverHealth && (
        <Card className="mb-6">
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-green-500" />
                <span className="font-medium">Server Status: Active</span>
              </div>
              <div className="flex gap-2">
                {Object.entries(serverHealth.dependencies).map(([dep, status]) => (
                  <Badge key={dep} variant={status === "OK" ? "default" : "destructive"}>
                    {dep}: {status as string}
                  </Badge>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-8">
        {/* Main Tabs */}
        <Tabs defaultValue="apply" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="apply">Apply Watermark</TabsTrigger>
            <TabsTrigger value="extract">Extract Watermark</TabsTrigger>
          </TabsList>

          {/* Apply Watermark Tab */}
          <TabsContent value="apply" className="space-y-8">
            {/* Upload Section */}
            <Card>
              <CardContent className="pt-6">
                <div
                  {...getRootProps()}
                  className={cn(
                    "border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors",
                    isDragActive ? "border-primary bg-primary/5" : "border-muted-foreground/25 hover:border-primary/50",
                  )}
                >
                  <input {...getInputProps()} />
                  <div className="flex flex-col items-center gap-2">
                    <Upload className="h-12 w-12 text-muted-foreground" />
                    <h3 className="text-lg font-medium mt-2">
                      {isDragActive ? "Drop images here" : "Drag & drop images here"}
                    </h3>
                    <p className="text-sm text-muted-foreground">or click to select files</p>
                    <p className="text-xs text-muted-foreground mt-1">Supports JPG, PNG, GIF up to 10MB</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Processing Progress */}
            {isLoading && (
              <Card>
                <CardContent className="pt-6">
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <h3 className="text-lg font-medium">Processing Images...</h3>
                      <Badge variant="outline">
                        {processedCount} / {files.length}
                      </Badge>
                    </div>
                    <Progress value={progress} className="w-full" />
                    <p className="text-sm text-muted-foreground text-center">
                      Processed images will be downloaded automatically
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Preview Section */}
            {previews.length > 0 && (
              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-xl font-semibold flex items-center gap-2">
                      <ImageIcon className="h-5 w-5" />
                      Image Preview
                    </h2>
                    <Badge variant="outline">
                      {files.length} image{files.length !== 1 ? "s" : ""}
                    </Badge>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                    {previews.map((preview, index) => (
                      <div key={index} className="relative group aspect-square">
                        <img
                          src={preview || "/placeholder.svg"}
                          alt={`Preview ${index + 1}`}
                          className="w-full h-full object-cover rounded-md"
                        />
                        <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity rounded-md flex items-center justify-center">
                          <Button variant="destructive" size="sm" onClick={() => removeImage(index)}>
                            Remove
                          </Button>
                        </div>

                        {/* Text Watermark Preview */}
                        {watermarkType === "text" && (
                          <div
                            className={cn(
                              "absolute text-white text-sm font-medium p-2 pointer-events-none shadow-lg",
                              watermarkPosition === "top-left" && "top-2 left-2",
                              watermarkPosition === "top-right" && "top-2 right-2",
                              watermarkPosition === "bottom-left" && "bottom-2 left-2",
                              watermarkPosition === "bottom-right" && "bottom-2 right-2",
                              watermarkPosition === "center" && "top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2",
                            )}
                            style={{
                              opacity: watermarkOpacity[0] / 100,
                              fontSize: `${watermarkSize[0] / 10}rem`,
                              textShadow: "1px 1px 2px rgba(0,0,0,0.8)",
                            }}
                          >
                            {watermarkText}
                          </div>
                        )}

                        {/* Logo Watermark Preview */}
                        {watermarkType === "logo" && logoPreview && (
                          <div
                            className={cn(
                              "absolute pointer-events-none",
                              watermarkPosition === "top-left" && "top-2 left-2",
                              watermarkPosition === "top-right" && "top-2 right-2",
                              watermarkPosition === "bottom-left" && "bottom-2 left-2",
                              watermarkPosition === "bottom-right" && "bottom-2 right-2",
                              watermarkPosition === "center" && "top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2",
                            )}
                            style={{
                              opacity: watermarkOpacity[0] / 100,
                              width: `${watermarkSize[0]}%`,
                              height: "auto",
                            }}
                          >
                            <img
                              src={logoPreview || "/placeholder.svg"}
                              alt="Logo Watermark"
                              className="max-w-full max-h-full object-contain"
                            />
                          </div>
                        )}

                        {/* Invisible Watermark Indicator */}
                        {watermarkType === "invisible" && (
                          <div className="absolute bottom-2 right-2 bg-black/70 text-white text-xs px-2 py-1 rounded-full">
                            <EyeOff className="h-3 w-3 inline mr-1" />
                            {invisibleMethod.toUpperCase()}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Watermark Settings */}
            <Card>
              <CardContent className="pt-6">
                <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                  <Sliders className="h-5 w-5" />
                  Watermark Settings
                </h2>

                <Tabs defaultValue="text" onValueChange={setWatermarkType} className="mt-4">
                  <TabsList className="grid grid-cols-3 mb-4">
                    <TabsTrigger value="text" className="flex items-center gap-2">
                      <Type className="h-4 w-4" />
                      Text
                    </TabsTrigger>
                    <TabsTrigger value="logo" className="flex items-center gap-2">
                      <ImageIcon2 className="h-4 w-4" />
                      Logo
                    </TabsTrigger>
                    <TabsTrigger value="invisible" className="flex items-center gap-2">
                      <EyeOff className="h-4 w-4" />
                      Invisible
                    </TabsTrigger>
                  </TabsList>

                  {/* Text Watermark Settings */}
                  <TabsContent value="text" className="space-y-4">
                    <div className="grid gap-2">
                      <Label htmlFor="watermark-text" className="flex items-center gap-2">
                        <Type className="h-4 w-4" />
                        Watermark Text
                      </Label>
                      <Input
                        id="watermark-text"
                        value={watermarkText}
                        onChange={(e) => setWatermarkText(e.target.value)}
                        placeholder="Enter watermark text"
                      />
                    </div>

                    <div className="grid gap-2">
                      <Label htmlFor="watermark-position">Position</Label>
                      <Select value={watermarkPosition} onValueChange={setWatermarkPosition}>
                        <SelectTrigger id="watermark-position">
                          <SelectValue placeholder="Select position" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="top-left">Top Left</SelectItem>
                          <SelectItem value="top-right">Top Right</SelectItem>
                          <SelectItem value="center">Center</SelectItem>
                          <SelectItem value="bottom-left">Bottom Left</SelectItem>
                          <SelectItem value="bottom-right">Bottom Right</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="grid gap-2">
                      <Label htmlFor="watermark-opacity">Opacity: {watermarkOpacity}%</Label>
                      <Slider
                        id="watermark-opacity"
                        min={10}
                        max={100}
                        step={1}
                        value={watermarkOpacity}
                        onValueChange={setWatermarkOpacity}
                      />
                    </div>

                    <div className="grid gap-2">
                      <Label htmlFor="watermark-size">Font Size: {watermarkSize}</Label>
                      <Slider
                        id="watermark-size"
                        min={10}
                        max={60}
                        step={1}
                        value={watermarkSize}
                        onValueChange={setWatermarkSize}
                      />
                    </div>
                  </TabsContent>

                  {/* Logo Watermark Settings */}
                  <TabsContent value="logo" className="space-y-4">
                    <div className="grid gap-2">
                      <Label htmlFor="logo-upload">Logo Image</Label>
                      <div className="flex items-center gap-2">
                        <Button variant="outline" onClick={() => logoInputRef.current?.click()} className="flex-1">
                          <Upload className="h-4 w-4 mr-2" />
                          {logoFile ? "Change Logo" : "Upload Logo"}
                        </Button>
                        {logoFile && (
                          <Button variant="outline" size="icon" onClick={removeLogo}>
                            <svg
                              xmlns="http://www.w3.org/2000/svg"
                              width="24"
                              height="24"
                              viewBox="0 0 24 24"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="2"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              className="h-4 w-4"
                            >
                              <path d="M3 6h18"></path>
                              <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path>
                              <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path>
                            </svg>
                          </Button>
                        )}
                        <input
                          ref={logoInputRef}
                          id="logo-upload"
                          type="file"
                          accept="image/*"
                          className="hidden"
                          onChange={handleLogoUpload}
                        />
                      </div>
                    </div>

                    {logoPreview && (
                      <div className="mt-2 p-4 border rounded-md">
                        <p className="text-sm font-medium mb-2">Logo Preview</p>
                        <div className="flex justify-center bg-gray-100 dark:bg-gray-800 rounded-md p-4">
                          <img
                            src={logoPreview || "/placeholder.svg"}
                            alt="Logo Preview"
                            className="max-h-24 object-contain"
                          />
                        </div>
                      </div>
                    )}

                    <Separator className="my-4" />

                    <div className="grid gap-2">
                      <Label htmlFor="logo-position">Position</Label>
                      <Select value={watermarkPosition} onValueChange={setWatermarkPosition}>
                        <SelectTrigger id="logo-position">
                          <SelectValue placeholder="Select position" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="top-left">Top Left</SelectItem>
                          <SelectItem value="top-right">Top Right</SelectItem>
                          <SelectItem value="center">Center</SelectItem>
                          <SelectItem value="bottom-left">Bottom Left</SelectItem>
                          <SelectItem value="bottom-right">Bottom Right</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="grid gap-2">
                      <Label htmlFor="logo-opacity">Opacity: {watermarkOpacity}%</Label>
                      <Slider
                        id="logo-opacity"
                        min={10}
                        max={100}
                        step={1}
                        value={watermarkOpacity}
                        onValueChange={setWatermarkOpacity}
                      />
                    </div>

                    <div className="grid gap-2">
                      <Label htmlFor="logo-size">Size: {watermarkSize}% of image width</Label>
                      <Slider
                        id="logo-size"
                        min={5}
                        max={50}
                        step={1}
                        value={watermarkSize}
                        onValueChange={setWatermarkSize}
                      />
                    </div>
                  </TabsContent>

                  {/* Invisible Watermark Settings */}
                  <TabsContent value="invisible" className="space-y-4">
                    <div className="grid gap-2">
                      <Label htmlFor="hidden-text" className="flex items-center gap-2">
                        <EyeOff className="h-4 w-4" />
                        Hidden Text
                      </Label>
                      <Input
                        id="hidden-text"
                        value={watermarkText}
                        onChange={(e) => setWatermarkText(e.target.value)}
                        placeholder="Enter text to hide in image"
                      />
                    </div>

                    <div className="grid gap-2">
                      <Label htmlFor="invisible-method">Watermarking Method</Label>
                      <Select value={invisibleMethod} onValueChange={setInvisibleMethod}>
                        <SelectTrigger id="invisible-method">
                          <SelectValue placeholder="Select method" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="lsb">LSB - Least Significant Bit (Fast)</SelectItem>
                          <SelectItem value="dct">DCT - Discrete Cosine Transform (JPEG Robust)</SelectItem>
                          {
                          //<SelectItem value="dft">DFT - Discrete Fourier Transform (Rotation Robust)</SelectItem>
                          }

                          <SelectItem value="dwt">DWT - Discrete Wavelet Transform (Very Robust)</SelectItem>
                          <SelectItem value="robust">Robust - Combined Methods (Maximum Security)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    {/* Dependency Warning */}
                    {serverHealth &&
                      ((invisibleMethod === "dwt" && serverHealth.dependencies?.PyWavelets?.includes("MISSING")) ||
                        (invisibleMethod === "lsb" && serverHealth.dependencies?.stegano?.includes("MISSING"))) && (
                        <Alert variant="destructive">
                          <AlertCircle className="h-4 w-4" />
                          <AlertDescription>
                            {invisibleMethod === "dwt"
                              ? "PyWavelets library is required for DWT method. Install with: pip install PyWavelets"
                              : "Stegano library is required for LSB method. Install with: pip install stegano"}
                          </AlertDescription>
                        </Alert>
                      )}

                    {/* Method Information */}
                    {watermarkMethods && watermarkMethods.invisible_methods[invisibleMethod] && (
                      <Alert>
                        <Info className="h-4 w-4" />
                        <AlertDescription>
                          <strong>{watermarkMethods.invisible_methods[invisibleMethod].name}</strong>
                          <br />
                          {watermarkMethods.invisible_methods[invisibleMethod].description}
                          <br />
                          <span className="text-sm text-muted-foreground">
                            Strength: {watermarkMethods.invisible_methods[invisibleMethod].strength} | Speed:{" "}
                            {watermarkMethods.invisible_methods[invisibleMethod].speed}
                          </span>
                        </AlertDescription>
                      </Alert>
                    )}
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>

            {/* Apply Button */}
            <Button
              size="lg"
              className="w-full mt-2"
              onClick={handleApplyWatermark}
              disabled={isLoading || files.length === 0 || (watermarkType === "logo" && !logoFile)}
            >
              {isLoading ? (
                <span className="flex items-center gap-2">
                  <div className="h-4 w-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                  Processing & Downloading...
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <Download className="h-4 w-4" />
                  Apply Watermark & Download
                  <ArrowRight className="h-4 w-4" />
                </span>
              )}
            </Button>

            {files.length > 0 && !isLoading && (
              <div className="text-center text-sm text-muted-foreground">
                <p className="flex items-center justify-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  Ready to process {files.length} image{files.length > 1 ? "s" : ""}. Downloads will start
                  automatically.
                </p>
              </div>
            )}
          </TabsContent>

          {/* Extract Watermark Tab */}
          <TabsContent value="extract" className="space-y-8">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileSearch className="h-5 w-5" />
                  Extract Hidden Watermark
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Upload Section for Extraction */}
                <div className="grid gap-2">
                  <Label htmlFor="extraction-upload">Upload Image with Hidden Watermark</Label>
                  <div className="flex items-center gap-2">
                    <Button variant="outline" onClick={() => extractionInputRef.current?.click()} className="flex-1">
                      <Upload className="h-4 w-4 mr-2" />
                      {extractionFile ? "Change Image" : "Upload Image"}
                    </Button>
                    <input
                      ref={extractionInputRef}
                      id="extraction-upload"
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={handleExtractionUpload}
                    />
                  </div>
                </div>

                {/* Extraction Preview */}
                {extractionPreview && (
                  <div className="p-4 border rounded-md">
                    <p className="text-sm font-medium mb-2">Image for Extraction</p>
                    <div className="flex justify-center bg-gray-100 dark:bg-gray-800 rounded-md p-4">
                      <img
                        src={extractionPreview || "/placeholder.svg"}
                        alt="Extraction Preview"
                        className="max-h-48 object-contain"
                      />
                    </div>
                  </div>
                )}

                {/* Method Selection for Extraction */}
                <div className="grid gap-2">
                  <Label htmlFor="extraction-method">Extraction Method</Label>
                  <Select value={invisibleMethod} onValueChange={setInvisibleMethod}>
                    <SelectTrigger id="extraction-method">
                      <SelectValue placeholder="Select extraction method" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="lsb">LSB - Least Significant Bit</SelectItem>
                      <SelectItem value="dct">DCT - Discrete Cosine Transform</SelectItem>
                      <SelectItem value="dft">DFT - Discrete Fourier Transform</SelectItem>
                      <SelectItem value="dwt">DWT - Discrete Wavelet Transform</SelectItem>
                      <SelectItem value="robust">Robust - Combined Methods</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Extract Button */}
                <Button
                  size="lg"
                  className="w-full"
                  onClick={handleExtractWatermark}
                  disabled={isExtracting || !extractionFile}
                >
                  {isExtracting ? (
                    <span className="flex items-center gap-2">
                      <div className="h-4 w-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                      Extracting...
                    </span>
                  ) : (
                    <span className="flex items-center gap-2">
                      <Search className="h-4 w-4" />
                      Extract Hidden Watermark
                    </span>
                  )}
                </Button>

                {/* Extraction Results */}
                {extractionResult && (
                  <Card>
                    <CardContent className="pt-4">
                      {extractionResult.success ? (
                        <div className="space-y-3">
                          <div className="flex items-center gap-2 text-green-600">
                            <CheckCircle className="h-5 w-5" />
                            <span className="font-medium">Watermark Found!</span>
                          </div>
                          <div className="grid gap-2">
                            <Label htmlFor="extracted-text">Extracted Text:</Label>
                            <Textarea
                              id="extracted-text"
                              value={extractionResult.extracted_text || ""}
                              readOnly
                              className="min-h-[100px]"
                            />
                          </div>
                          <p className="text-sm text-muted-foreground">
                            Method used: {extractionResult.method_used.toUpperCase()}
                          </p>
                        </div>
                      ) : (
                        <div className="space-y-3">
                          <div className="flex items-center gap-2 text-red-600">
                            <AlertCircle className="h-5 w-5" />
                            <span className="font-medium">Extraction Failed</span>
                          </div>
                          <p className="text-sm text-muted-foreground">
                            {extractionResult.error || "No watermark found with the selected method."}
                          </p>
                          <p className="text-sm text-muted-foreground">
                            Try a different extraction method or ensure the image contains a watermark.
                          </p>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
