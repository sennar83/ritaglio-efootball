from io import BytesIO

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import Response
from PIL import Image


app = FastAPI()


@app.get("/")
def home():
    return {
        "status": "ok",
        "message": "Ritaglio eFootball server attivo!"
    }


@app.post("/ritaglia")
async def ritaglia(file: UploadFile = File(...)):

    # Legge l'immagine ricevuta
    contenuto = await file.read()

    # Apre l'immagine
    immagine = Image.open(BytesIO(contenuto))

    # Convertiamo in RGBA
    immagine = immagine.convert("RGBA")

    # Crop di prova
    crop = immagine.crop((60, 60, 420, 430))

    # Salviamo il risultato in memoria
    output = BytesIO()
    crop.save(output, format="PNG")

    return Response(
        content=output.getvalue(),
        media_type="image/png",
        headers={
            "Content-Disposition": "attachment; filename=ritaglio.png"
        }
    )
