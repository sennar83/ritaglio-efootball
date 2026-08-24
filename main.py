from io import BytesIO

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse, Response
from PIL import Image

from rembg import remove, new_session


app = FastAPI()


# ============================================================
# SESSIONE MODELLO
# ============================================================

# Il modello NON viene caricato all'avvio.
# Verrà caricato solamente quando arriva la prima immagine.

session = None


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

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1.0"
        >

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

                box-shadow:
                    0 3px 15px
                    rgba(0,0,0,0.15);
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


            <h1>
                Ritaglio eFootball
            </h1>


            <p>
                Seleziona un'immagine del giocatore.
            </p>


            <input
                type="file"
                id="file"
                accept="image/png,image/jpeg,image/webp"
            >


            <button
                id="button"
                onclick="ritaglia()"
            >
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


                // ------------------------------------------------
                // CONTROLLO FILE
                // ------------------------------------------------

                if (!fileInput.files.length) {

                    status.innerHTML =
                        "Seleziona prima un'immagine.";

                    return;
                }


                const file =
                    fileInput.files[0];


                // ------------------------------------------------
                // PREPARAZIONE UPLOAD
                // ------------------------------------------------

                const formData =
                    new FormData();


                formData.append(
                    "file",
                    file
                );


                // ------------------------------------------------
                // BLOCCA PULSANTE
                // ------------------------------------------------

                button.disabled = true;


                status.innerHTML =
                    "Rimozione dello sfondo in corso...";


                result.innerHTML = "";


                try {


                    // --------------------------------------------
                    // INVIO AL SERVER
                    // --------------------------------------------

                    const response =
                        await fetch(
                            "/ritaglia",
                            {
                                method: "POST",
                                body: formData
                            }
                        );


                    // --------------------------------------------
                    // CONTROLLO RISPOSTA
                    // --------------------------------------------

                    if (!response.ok) {

                        const text =
                            await response.text();

                        throw new Error(text);
                    }


                    // --------------------------------------------
                    // RICEVE PNG
                    // --------------------------------------------

                    const blob =
                        await response.blob();


                    const url =
                        URL.createObjectURL(
                            blob
                        );


                    // --------------------------------------------
                    // MOSTRA RISULTATO
                    // --------------------------------------------

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


                }


                catch (error) {


                    console.error(error);


                    status.innerHTML =
                        "Errore durante l'elaborazione.";


                    result.innerHTML = `
                        <p>
                            ${error.message}
                        </p>
                    `;


                }


                finally {


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
async def ritaglia(
    file: UploadFile = File(...)
):


    # ========================================================
    # LETTURA IMMAGINE
    # ========================================================

    contenuto = await file.read()


    immagine = Image.open(
        BytesIO(contenuto)
    ).convert("RGBA")


    print(
        f"Immagine ricevuta: "
        f"{immagine.width}x{immagine.height}",
        flush=True
    )


    # ========================================================
    # CARICAMENTO MODELLO AL PRIMO UTILIZZO
    # ========================================================

    global session


    if session is None:


        print(
            "========================================",
            flush=True
        )


        print(
            "Caricamento modello BiRefNet...",
            flush=True
        )


        print(
            "========================================",
            flush=True
        )


        session = new_session(
            "birefnet-general"
        )


        print(
            "Modello BiRefNet caricato correttamente.",
            flush=True
        )


    # ========================================================
    # RIMOZIONE SFONDO
    # ========================================================

    print(
        "Rimozione dello sfondo...",
        flush=True
    )


    risultato = remove(
        immagine,
        session=session
    )


    print(
        "Rimozione sfondo completata.",
        flush=True
    )


    # ========================================================
    # CROP
    # ========================================================

    X1 = 60
    Y1 = 60
    X2 = 420
    Y2 = 430


    crop = risultato.crop(
        (
            X1,
            Y1,
            X2,
            Y2
        )
    )


    print(
        f"Crop eseguito: "
        f"{X1},{Y1} -> {X2},{Y2}",
        flush=True
    )


    # ========================================================
    # OUTPUT PNG
    # ========================================================

    output = BytesIO()


    crop.save(
        output,
        format="PNG"
    )


    print(
        "PNG creato.",
        flush=True
    )


    # ========================================================
    # RISPOSTA
    # ========================================================

    return Response(

        content=output.getvalue(),

        media_type="image/png",

        headers={
            "Content-Disposition":
                "attachment; filename=ritaglio.png"
        }

    )
