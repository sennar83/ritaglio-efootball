from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from PIL import Image
from rembg import remove, new_session
from io import BytesIO
import os


# ============================================================
# CONFIGURAZIONE
# ============================================================

X1 = 60
Y1 = 60
X2 = 420
Y2 = 430

# Modello LEGGERO per Render Free
MODEL_NAME = "u2netp"


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="Ritaglio Giocatori eFootball",
    description="Rimuove lo sfondo e ritaglia automaticamente le immagini dei giocatori.",
    version="1.0"
)


# ============================================================
# CARICAMENTO MODELLO
# ============================================================

print("========================================")
print("Avvio servizio ritaglio immagini")
print("========================================")
print(f"Modello utilizzato: {MODEL_NAME}")
print("Caricamento modello...")

try:
    session = new_session(MODEL_NAME)
    print("Modello caricato correttamente.")
except Exception as e:
    print("ERRORE durante il caricamento del modello:")
    print(str(e))
    session = None


# ============================================================
# HOME
# ============================================================

@app.get("/")
def home():
    return {
        "status": "online",
        "service": "Ritaglio giocatori eFootball",
        "model": MODEL_NAME,
        "crop": {
            "x1": X1,
            "y1": Y1,
            "x2": X2,
            "y2": Y2
        }
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": session is not None
    }


# ============================================================
# RITAGLIO
# ============================================================

@app.post("/crop")
async def crop_image(file: UploadFile = File(...)):

    if session is None:
        raise HTTPException(
            status_code=500,
            detail="Modello di rimozione sfondo non caricato."
        )

    # --------------------------------------------------------
    # Controllo formato
    # --------------------------------------------------------

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Il file inviato non è un'immagine."
        )

    try:

        # ----------------------------------------------------
        # Lettura immagine
        # ----------------------------------------------------

        input_data = await file.read()

        if not input_data:
            raise HTTPException(
                status_code=400,
                detail="File vuoto."
            )

        original = Image.open(
            BytesIO(input_data)
        ).convert("RGBA")

        print(
            f"Immagine ricevuta: "
            f"{original.width}x{original.height}"
        )

        # ----------------------------------------------------
        # RIMOZIONE SFONDO
        # ----------------------------------------------------

        print("Rimozione sfondo...")

        output_data = remove(
            input_data,
            session=session
        )

        # ----------------------------------------------------
        # Apertura risultato
        # ----------------------------------------------------

        result = Image.open(
            BytesIO(output_data)
        ).convert("RGBA")

        print(
            f"Risultato rimozione sfondo: "
            f"{result.width}x{result.height}"
        )

        # ----------------------------------------------------
        # CROP
        # ----------------------------------------------------

        width = result.width
        height = result.height

        # Le coordinate sono riferite all'immagine
        # originale 1920x1080.
        #
        # Se l'immagine ha una risoluzione diversa,
        # le coordinate vengono scalate proporzionalmente.

        SCALE_X = width / 1920
        SCALE_Y = height / 1080

        crop_x1 = int(X1 * SCALE_X)
        crop_y1 = int(Y1 * SCALE_Y)
        crop_x2 = int(X2 * SCALE_X)
        crop_y2 = int(Y2 * SCALE_Y)

        # ----------------------------------------------------
        # Controllo coordinate
        # ----------------------------------------------------

        crop_x1 = max(0, min(crop_x1, width))
        crop_y1 = max(0, min(crop_y1, height))
        crop_x2 = max(crop_x1, min(crop_x2, width))
        crop_y2 = max(crop_y1, min(crop_y2, height))

        print(
            f"Crop: "
            f"{crop_x1},{crop_y1} -> "
            f"{crop_x2},{crop_y2}"
        )

        cropped = result.crop(
            (
                crop_x1,
                crop_y1,
                crop_x2,
                crop_y2
            )
        )

        # ----------------------------------------------------
        # PNG trasparente
        # ----------------------------------------------------

        output_buffer = BytesIO()

        cropped.save(
            output_buffer,
            format="PNG"
        )

        output_buffer.seek(0)

        print(
            f"Output finale: "
            f"{cropped.width}x{cropped.height}"
        )

        # ----------------------------------------------------
        # Nome file
        # ----------------------------------------------------

        original_name = file.filename or "immagine"

        base_name = os.path.splitext(
            original_name
        )[0]

        output_name = f"{base_name}_ritagliata.png"

        # ----------------------------------------------------
        # Risposta
        # ----------------------------------------------------

        return StreamingResponse(
            output_buffer,
            media_type="image/png",
            headers={
                "Content-Disposition":
                    f'attachment; filename="{output_name}"'
            }
        )

    except HTTPException:
        raise

    except Exception as e:

        print("========================================")
        print("ERRORE DURANTE IL PROCESSAMENTO")
        print(str(e))
        print("========================================")

        raise HTTPException(
            status_code=500,
            detail=f"Errore durante il processamento: {str(e)}"
        )
