from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from watermark.visible import apply_visible_watermark
from watermark.invisible import apply_invisible_watermark_advanced, extract_invisible_watermark_advanced
from watermark.logo import apply_logo_watermark
from io import BytesIO
import uvicorn

app = FastAPI(title="Watermark API", description="API per applicare watermark visibili e invisibili alle immagini")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Watermark API - Server attivo"}

@app.post("/apply-visible-watermark")
async def visible_watermark(
    file: UploadFile = File(...),
    text: str = Form(...),
    position: str = Form("bottom-right"), 
    opacity: float = Form(0.5), 
    size: int = Form(20)  
):
    image = await file.read()
    output_image = apply_visible_watermark(image, text, position, opacity, size)
    return StreamingResponse(BytesIO(output_image), media_type="image/png")

@app.post("/apply-invisible-watermark")
async def invisible_watermark(
    file: UploadFile = File(...),
    hidden_text: str = Form(...),
    method: str = Form("lsb") 
):
    """
    Applica watermark invisibile con diversi metodi:
    - lsb: Least Significant Bit (metodo originale, veloce ma debole)
    - dct: Discrete Cosine Transform (robusto contro compressione JPEG)
    - dft: Discrete Fourier Transform (robusto contro rotazioni)
    - dwt: Discrete Wavelet Transform (molto robusto, richiede PyWavelets)
    - robust: Combinazione di tutti i metodi (massima sicurezza)
    """
    image = await file.read()
    
    
    output_image = apply_invisible_watermark_advanced(image, hidden_text, method)
    
    return StreamingResponse(BytesIO(output_image), media_type="image/png")

@app.post("/extract-invisible-watermark")
async def extract_invisible_watermark(
    file: UploadFile = File(...),
    method: str = Form("lsb")  
):
    """
    Estrae watermark invisibile dall'immagine
    """
    image = await file.read()
    
    try:
        extracted_text = extract_invisible_watermark_advanced(image, method)
        return {
            "success": True,
            "extracted_text": extracted_text,
            "method_used": method
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "method_used": method
        }

@app.post("/apply-logo-watermark")
async def logo_watermark(
    file: UploadFile = File(...),
    logo: UploadFile = File(...),
    position: str = Form("bottom-right"),
    opacity: float = Form(0.7),
    size: float = Form(0.1) 
):
    image = await file.read()
    logo_image = await logo.read()
    output_image = apply_logo_watermark(image, logo_image, position, opacity, size)
    return StreamingResponse(BytesIO(output_image), media_type="image/png")

@app.get("/watermark-methods")
async def get_watermark_methods():
    """
    Restituisce informazioni sui metodi di watermarking disponibili
    """
    return {
        "invisible_methods": {
            "lsb": {
                "name": "Least Significant Bit",
                "description": "Metodo veloce ma debole, modificabile con editing base",
                "strength": "Bassa",
                "speed": "Molto veloce",
                "recommended_for": "Test rapidi, immagini non critiche"
            },
            "dct": {
                "name": "Discrete Cosine Transform",
                "description": "Robusto contro compressione JPEG",
                "strength": "Alta",
                "speed": "Veloce",
                "recommended_for": "Immagini che potrebbero essere compresse"
            },
            "dft": {
                "name": "Discrete Fourier Transform", 
                "description": "Robusto contro rotazioni e trasformazioni geometriche",
                "strength": "Alta",
                "speed": "Media",
                "recommended_for": "Immagini che potrebbero essere ruotate/trasformate"
            },
            "dwt": {
                "name": "Discrete Wavelet Transform",
                "description": "Molto robusto contro vari tipi di attacchi",
                "strength": "Molto alta",
                "speed": "Media",
                "recommended_for": "Massima sicurezza (richiede PyWavelets)",
                "requires": "pip install PyWavelets"
            },
            "robust": {
                "name": "Metodo Combinato",
                "description": "Usa DCT + DFT + DWT insieme per massima robustezza",
                "strength": "Massima",
                "speed": "Lenta",
                "recommended_for": "Contenuti altamente sensibili"
            }
        }
    }

@app.get("/health")
async def health_check():
    """
    Verifica lo stato del server e delle dipendenze
    """
    status = {
        "server": "OK",
        "dependencies": {}
    }
    
    
    try:
        import numpy
        status["dependencies"]["numpy"] = "OK"
    except ImportError:
        status["dependencies"]["numpy"] = "MISSING"
    
    try:
        import cv2
        status["dependencies"]["opencv"] = "OK"
    except ImportError:
        status["dependencies"]["opencv"] = "MISSING"
    
    try:
        import scipy
        status["dependencies"]["scipy"] = "OK"
    except ImportError:
        status["dependencies"]["scipy"] = "MISSING"
    
    try:
        import pywt
        status["dependencies"]["PyWavelets"] = "OK"
    except ImportError:
        status["dependencies"]["PyWavelets"] = "MISSING - DWT method not available"
    
    try:
        from stegano import lsb
        status["dependencies"]["stegano"] = "OK"
    except ImportError:
        status["dependencies"]["stegano"] = "MISSING - LSB method not available"
    
    return status

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)