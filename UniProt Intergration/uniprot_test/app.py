from flask import Flask, render_template, request, redirect, url_for, flash
import requests

app = Flask(__name__)
app.secret_key = "dev" # In production, use a secure random key

def fetch_uniprot(accession: str) -> dict: #input is string and output is dictionary
    url = f"https://rest.uniprot.org/uniprotkb/{accession}.json" #f-string to create the URL for the UniProt API request
    response = requests.get(url, timeout=15) # Send a GET request to the UniProt API with a timeout of 15 seconds

    if response.status_code != 200: # Check if the response status code is not 200 (OK)
        raise ValueError(f"UniProt request failed ({response.status_code})") # If the request failed, raise a ValueError with the status code 

    
    data = response.json()

    protein_name = (
        data["proteinDescription"]
        ["recommendedName"]
        ["fullName"]
        ["value"]
    )

    sequence = data["sequence"]["value"]

    return {
        "accession": accession,
        "protein_name": protein_name,
        "sequence": sequence,
        "sequence_length": len(sequence),
    }

@app.get("/")
def home():
    return redirect(url_for("stage_get"))

@app.get("/stage")
def stage_get():
    return render_template("stage.html")

@app.post("/stage")
def stage_post():
    accession = request.form.get("accession", "").strip()

    if not accession:
        flash("Please enter a UniProt accession.")
        return redirect(url_for("stage_get"))

    try:
        wt = fetch_uniprot(accession)
        return render_template("stage_result.html", wt=wt)
    except ValueError as err:
        flash(str(err))
        return redirect(url_for("stage_get"))

if __name__ == "__main__":
    app.run(debug=True)
