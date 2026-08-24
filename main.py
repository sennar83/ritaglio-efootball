from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import Response
from PIL import Image
from rembg import remove, new_session
from io import BytesIO
import asyncio
import threading


# ============================================================
# CONFIGURAZIONE
# ============================================================

app = FastAPI(
    title="Ritaglio eFootball",
    description="Ritaglio automatico immagini giocatori eFootball",
    version="1.0"
)


# ============================================================
# COORDINATE RITAGLIO
# ============================================================

X1 = 60
Y1 = 70
X2 = 400
Y2 = 430


# ============================================================
# MODELLO
# ============================================================

MODEL_NAME = "birefnet-general"

session = None

model_ready = False
model_error = None

model_lock = threading.Lock()


# ============================================================
# CARICAMENTO MODELLO
# ============================================================

def load_model():
    global session
    global model_ready
    global model_error

    try:
        print("=" * 40)
        print("Caricamento modello BiRefNet...")
        print("=" * 40)

        session = new_session(MODEL_NAME)

        model_ready = True

        print("=" * 40)
        print("MODELLO BIREfNET CARICATO CORRETTAMENTE")
        print("=" * 40)

    except Exception as e:

        model_error = str(e)

        print("=" * 40)
        print("ERRORE CARICAMENTO MODELLO")
        print("=" * 40)
        print(e)


# ============================================================
# AVVIO
# ============================================================

@app.on_event("startup")
async def startup_event():

    print("=" * 50)
    print("SERVER RITAGLIO EFOOTBALL AVVIATO")
    print("=" * 50)

    # Carica il modello in un thread separato.
    # In questo modo FastAPI può aprire immediatamente
    # la porta richiesta da Render.

    loop = asyncio.get_running_loop()

    loop.run_in_executor(
        None,
        load_model
    )


# ============================================================
# HOME
# ============================================================

@app.get("/")
async def home():

    if model_ready:

        return {
            "status": "online",
            "model": "BiRefNet",
            "model_ready": True,
            "message": "Servizio pronto"
        }

    if model_error:

        return {
            "status": "error",
            "model_ready": False,
            "error": model_error
        }

    return {
        "status": "starting",
        "model": "BiRefNet",
        "model_ready": False,
        "message": "Il modello è ancora in caricamento"
    }


# ============================================================
# STATO SERVER
# ============================================================

@app.get("/status")
async def status():

    return {
        "server": "online",
        "model_ready": model_ready,
        "model_error": model_error
    }


# ============================================================
# RITAGLIO
# ============================================================

@app.post("/ritaglia")
async def ritaglia(file: UploadFile = File(...)):

    # --------------------------------------------------------
    # CONTROLLO MODELLO
    # --------------------------------------------------------

    if not model_ready:

        if model_error:

            raise HTTPException(
                status_code=500,
                detail=f"Errore caricamento modello: {model_error}"
            )

        raise HTTPException(
            status_code=503,
            detail="Il modello BiRefNet è ancora in caricamento. Riprova tra qualche secondo."
        )


    # --------------------------------------------------------
    # CONTROLLO FILE
    # --------------------------------------------------------

    if not file.content_type:

        raise HTTPException(
            status_code=400,
            detail="Tipo di file non riconosciuto"
        )


    if not file.content_type.startswith("image/"):

        raise HTTPException(
            status_code=400,
            detail="Il file deve essere un'immagine"
        )


    # --------------------------------------------------------
    # LETTURA IMMAGINE
    # --------------------------------------------------------

    try:

        data = await file.read()

        if not data:

            raise HTTPException(
                status_code=400,
                detail="File vuoto"
            )

        image = Image.open(
            BytesIO(data)
        )

        image.load()

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=f"Impossibile leggere l'immagine: {e}"
        )


    # --------------------------------------------------------
    # CONVERSIONE RGBA
    # --------------------------------------------------------

    image = image.convert("RGBA")


    # --------------------------------------------------------
    # RIMOZIONE SFONDO
    # --------------------------------------------------------

    try:

        print(
            f"Elaborazione immagine: "
            f"{image.width}x{image.height}"
        )

        result = remove(
            image,
            session=session
        )

    except Exception as e:

        print(
            f"Errore rimozione sfondo: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail=f"Errore durante la rimozione dello sfondo: {e}"
        )


    # --------------------------------------------------------
    # RITAGLIO
    # --------------------------------------------------------

    width, height = result.size

    # Controllo coordinate
    crop_x1 = max(0, min(X1, width))
    crop_y1 = max(0, min(Y1, height))
    crop_x2 = max(0, min(X2, width))
    crop_y2 = max(0, min(Y2, height))

    if crop_x2 <= crop_x1 or crop_y2 <= crop_y1:

        raise HTTPException(
            status_code=400,
            detail=(
                f"Coordinate ritaglio non valide per "
                f"immagine {width}x{height}"
            )
        )


    cropped = result.crop(
        (
            crop_x1,
            crop_y1,
            crop_x2,
            crop_y2
        )
    )


    # --------------------------------------------------------
    # OUTPUT PNG
    # --------------------------------------------------------

    output = BytesIO()

    cropped.save(
        output,
        format="PNG",
        optimize=True
    )

    output.seek(0)


    print(
        f"Ritaglio completato: "
        f"{cropped.width}x{cropped.height}"
    )


    # --------------------------------------------------------
    # RISPOSTA
    # --------------------------------------------------------

    return Response(
        content=output.getvalue(),
        media_type="image/png",
        headers={
            "Content-Disposition":
                'attachment; filename="ritaglio.png"'
        }
)
