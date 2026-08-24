from io import BytesIO

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse, Response
from PIL import Image

from rembg import remove, new_session


app = FastAPI()


# ============================================================
# CARICAMENTO MODELLO
# ============================================================

print("========================================")
print("Caricamento modello BiRefNet...")
print("========================================")

session = new_session("birefnet-general")


print("Modello BiRefNet caricato correttamente.")


# ============================================================
# PAGINA WEB
# ============================================================

@app.get("/", response_class=HTMLResponse)
def home():

    return """
    <!DOCTYPE html>
    <html lang="it">

    <head>
        <meta charset="UTF-8">
        <meta name="viewport"
              content="width=device-width, initial-scale=1.0">

        <title>Ritaglio eFootball</title>

        <style>

            * {
                box-sizing: border-box;
            }

            body {
                margin: 0;
                padding: 20px;
                background: #f2f2f2;
                font-family: Arial, sans-serif;
                text-align: center;
            }

            .container {
                max-width: 500px;
                margin: 0 auto;
                background: white;
                padding: 25px;
                border-radius: 15px;
                box-shadow: 0 3px 15px rgba(0,0,0,0.15);
            }

            h1 {
                margin-top: 0;
            }

            input[type="file"] {
                width: 100%;
                margin: 20px 0;
                padding: 12px;
            }

            button {
                width: 100%;
                padding: 15px;
                border: none;
                border-radius: 10px;
                background: #222;
                color: white;
                font-size: 18px;
                cursor: pointer;
            }

            button:disabled {
                background: #999;
            }

            #status {
                margin-top: 20px;
                font-size: 16px;
            }

            #result {
                margin-top: 20px;
            }

            #preview {
                max-width: 100%;
                margin-top: 15px;
                border-radius: 10px;
            }

            .download {
                display: inline-block;
                margin-top: 15px;
                padding: 12px 20px;
                background: #198754;
                color: white;
                text-decoration: none;
                border-radius: 8px;
            }

        </style>

    </head>

    <body>

        <div class="container">

            <h1>Ritaglio eFootball</h1>

            <p>Seleziona un'immagine del giocatore.</p>

            <input
                type="file"
                id="file"
                accept="image/png,image/jpeg,image/webp"
            >

            <button id="button" onclick="ritaglia()">
                RITAGLIA
            </button>

            <div id="status"></div>

            <div id="result"></div>

        </div>


        <script>

            async function ritaglia() {

                const fileInput =
                    document.getElementById("file");

                const button =
                    document.getElementById("button");

                const status =
                    document.getElementById("status");

                const result =
                    document.getElementById("result");


                if (!fileInput.files.length) {

                    status.innerHTML =
                        "Seleziona prima un'immagine.";

                    return;
                }


                const file = fileInput.files[0];

                const formData = new FormData();

                formData.append("file", file);


                button.disabled = true;

                status.innerHTML =
                    "Rimozione dello sfondo in corso...";

                result.innerHTML = "";


                try {

                    const response = await fetch(
                        "/ritaglia",
                        {
                            method: "POST",
                            body: formData
                        }
                    );


                    if (!response.ok) {

                        const text =
                            await response.text();

                        throw new Error(text);
                    }


                    const blob =
                        await response.blob();


                    const url =
                        URL.createObjectURL(blob);


                    result.innerHTML = `

                        <p>
                            Elaborazione completata!
                        </p>

                        <img
                            id="preview"
                            src="${url}"
                        >

                        <br>

                        <a
                            class="download"
                            href="${url}"
                            download="ritaglio.png"
                        >
                            SCARICA PNG
                        </a>

                    `;


                    status.innerHTML = "";


                } catch (error) {

                    status.innerHTML =
                        "Errore durante l'elaborazione.";

                    console.error(error);

                } finally {

                    button.disabled = false;

                }

            }

        </script>

    </body>

    </html>
    """


# ============================================================
# RITAGLIO + RIMOZIONE SFONDO
# ============================================================

@app.post("/ritaglia")
async def ritaglia(file: UploadFile = File(...)):

    # --------------------------------------------------------
    # LETTURA IMMAGINE
    # --------------------------------------------------------

    contenuto = await file.read()

    immagine = Image.open(
        BytesIO(contenuto)
    ).convert("RGBA")


    # --------------------------------------------------------
    # RIMOZIONE SFONDO
    # --------------------------------------------------------

    print(
        f"Elaborazione immagine: "
        f"{immagine.width}x{immagine.height}"
    )

    risultato = remove(
        immagine,
        session=session
    )


    # --------------------------------------------------------
    # CROP
    # --------------------------------------------------------

    crop = risultato.crop(
        (60, 60, 420, 430)
    )


    # --------------------------------------------------------
    # OUTPUT PNG
    # --------------------------------------------------------

    output = BytesIO()

    crop.save(
        output,
        format="PNG"
    )


    return Response(
        content=output.getvalue(),
        media_type="image/png",
        headers={
            "Content-Disposition":
                "attachment; filename=ritaglio.png"
        }
    )
