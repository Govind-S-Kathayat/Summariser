from flask import Flask, render_template, request, jsonify
import os

from readers import read_document
from utils import clean_text, deep_clean_text, split_into_chunks
from summarizer import DocumentSummarizer

app = Flask(__name__)

UPLOAD_FOLDER="uploads"

os.makedirs(UPLOAD_FOLDER,exist_ok=True)


@app.route("/")
def home():

    return render_template("index.html")


@app.route("/summarize",methods=["POST"])
def summarize():

    try:

        model=request.form.get("model")

        input_type=request.form.get("type")

        if input_type=="youtube":

            url=request.form.get("youtube")

            raw_text=read_document(url)

        elif input_type=="file":

            file=request.files["file"]

            path=os.path.join(UPLOAD_FOLDER,file.filename)

            file.save(path)

            raw_text=read_document(path)

        else:

            raw_text=request.form.get("text")


        text=clean_text(raw_text)

        text=deep_clean_text(text)

        chunks=split_into_chunks(text)

        summarizer=DocumentSummarizer(

            model_name=model

        )

        summary=summarizer.summarize_chunks(chunks)

        return jsonify({

            "summary":summary,

            "words":len(summary.split())

        })


    except Exception as e:

        return jsonify({

            "error":str(e)

        })


if __name__=="__main__":

    app.run(debug=True)