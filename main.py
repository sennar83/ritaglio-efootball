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
Y1 = 70
X2 = 400
Y2 = 430

OUTPUT_WIDTH = 420
OUTPUT_HEIGHT = 490


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="Ritaglio eFootball",
    description="Ritaglio automatico e rimozione dello sfondo",
    version="1.0"
)


# ============================================================
# MODELLO AI
# ============================================================

print("========================================")
print("Caricamento modello BiRefNet...")
print("========================================")

session = new_session("birefnet-general")

print("========================================")
print("Modello BiRefNet caricato.")
print("========================================")


# ============================================================
# TEST SERVER
# ============================================================

@app.get("/")
def home():
    return {
        "status": "online",
        "port": os.environ.get("PORT", "10000"),
        "message": "Render funziona correttamente"
    }


# ============================================================
# RITAGLIO
# ============================================================

@app.post("/ritaglia")
async def ritaglia(file: UploadFile = File(...)):

    # Controllo formato
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Il file deve essere un'immagine."
        )

    try:

        # ----------------------------------------------------
        # LETTURA IMMAGINE
        # ----------------------------------------------------

        contenuto = await file.read()

        immagine = Image.open(
            BytesIO(contenuto)
        ).convert("RGBA")

        print(
            f"Immagine ricevuta: "
            f"{immagine.width}x{immagine.height}"
        )

        # ----------------------------------------------------
        # CROP
        # ----------------------------------------------------

        larghezza = immagine.width
        altezza = immagine.height

        # Coordinate proporzionali rispetto a 1920x1080
        scala_x = larghezza / 1920
        scala_y = altezza / 1080

        x1 = int(X1 * scala_x)
        y1 = int(Y1 * scala_y)
        x2 = int(X2 * scala_x)
        y2 = int(Y2 * scala_y)

        print(
            f"Crop: "
            f"{x1},{y1} -> {x2},{y2}"
        )

        # Evita coordinate fuori immagine
        x1 = max(0, min(x1, larghezza))
        x2 = max(0, min(x2, larghezza))

        y1 = max(0, min(y1, altezza))
        y2 = max(0, min(y2, altezza))

        if x2 <= x1 or y2 <= y1:
            raise HTTPException(
                status_code=400,
                detail="Coordinate di ritaglio non valide."
            )

        ritaglio = immagine.crop(
            (x1, y1, x2, y2)
        )

        # ----------------------------------------------------
        # RIMOZIONE SFONDO
        # ----------------------------------------------------

        print("Rimozione dello sfondo...")

        risultato = remove(
            ritaglio,
            session=session
        )

        # rembg può restituire bytes
        if isinstance(risultato, bytes):
            risultato = Image.open(
                BytesIO(risultato)
            ).convert("RGBA")
        else:
            risultato = risultato.convert("RGBA")

        # ----------------------------------------------------
        # RIDIMENSIONAMENTO
        # ----------------------------------------------------

        risultato = risultato.resize(
            (OUTPUT_WIDTH, OUTPUT_HEIGHT),
            Image.Resampling.LANCZOS
        )

        # ----------------------------------------------------
        # OUTPUT PNG
        # ----------------------------------------------------

        output = BytesIO()

        risultato.save(
            output,
            format="PNG",
            optimize=True
        )

        output.seek(0)

        # Nome file
        nome_originale = file.filename or "immagine"

        nome_base = os.path.splitext(
            nome_originale
        )[0]

        nome_output = f"{nome_base}_ritagliata.png"

        print(
            f"Elaborazione completata: {nome_output}"
        )

        # ----------------------------------------------------
        # RISPOSTA
        # ----------------------------------------------------

        return StreamingResponse(
            output,
            media_type="image/png",
            headers={
                "Content-Disposition":
                    f'attachment; filename="{nome_output}"'
            }
        )

    except HTTPException:
        raise

    except Exception as e:

        print(
            f"ERRORE durante l'elaborazione: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail=f"Errore durante l'elaborazione: {str(e)}"
        )
