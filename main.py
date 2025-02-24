import os
import json
from flask import Flask, redirect, request, send_file
from google.cloud import storage
import google.generativeai as genai
from io import BytesIO
from PIL import Image
import io
import re


app = Flask(__name__)
os.makedirs('files', exist_ok=True)

# Google Cloud Storage bucket name
bucket_name = 'cnd-bucket-z23746775'

# Configure Gemini AI
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))  # Ensure this is set in the environment



# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))



def generate_caption_description(image_path):
    """
    Uses Google Gemini AI API to generate a caption and description for an image.
    """
    with open(image_path, "rb") as image_file:
        image_bytes = image_file.read()

    model = genai.GenerativeModel("gemini-1.5-flash")

    image_blob = {"mime_type": "image/jpeg", "data": image_bytes}

    prompt = (
        "Analyze the provided image and generate a clear and concise title and description.\n\n"
        "### **Response Format (strict JSON)**:\n"
        "{\n"
        '  "title": "A short, engaging title describing the image",\n'
        '  "description": "A well-structured description of the image, highlighting key elements and context."\n'
        "}\n\n"
        "- The **title** should be **5-10 words long**, engaging, and relevant to the image.\n"
        "- The **description** should be **2-3 sentences**, providing details about the scene, emotions, and key elements.\n"
        "- **Do not add any extra text outside the JSON format.**\n"
        "- **Do not include any introductory phrases like 'Here's a title and description'**.\n"
    )

    try:
        response = model.generate_content([image_blob, prompt])
        print("Raw Response:", response)  # Debugging print

        if response and hasattr(response, 'text'):
            response_text = response.text.strip()

            # Remove Markdown formatting (```json ... ```)
            response_text = re.sub(r"^```json\s*", "", response_text)
            response_text = re.sub(r"\s*```$", "", response_text)

            try:
                response_data = json.loads(response_text)

                title = response_data.get("title", "No title generated")
                description = response_data.get("description", "No description generated")

                return {"title": title, "description": description}

            except json.JSONDecodeError:
                print("Error: API response is not valid JSON. Response received:", response_text)
                return {"title": "No title generated", "description": "No description generated"}

    except Exception as e:
        print("Error while generating caption:", e)
        return {"title": "No title generated", "description": "No description generated"}




def upload_blob(bucket_name, file, destination_blob_name):
    """
    Upload a file to Google Cloud Storage.
    """
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_file(file)

@app.route('/')
def index():
    """
    Render the file upload interface and list uploaded images.
    """
    index_html = """  
    <html>
    <head>
        <title>File Upload</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background-color: #f4f4f4;
                text-align: center;
                padding: 20px;
            }
            .container {
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0px 0px 10px gray;
                display: inline-block;
            }
            ul {
                list-style-type: none;
                padding: 0;
            }
            li {
                margin: 10px 0;
            }
            img {
                max-width: 300px;
                height: auto;
                display: block;
                margin: 10px auto;
                border-radius: 5px;
                box-shadow: 0px 0px 5px gray;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Upload an Image</h2>
            <form method="post" enctype="multipart/form-data" action="/upload"> 
                <div> 
                    <label for="file">Choose file to upload</label> 
                    <input type="file" id="file" name="form_file" accept="image/jpeg, image/png"/> 
                </div> 
                <div> 
                    <button>Submit</button> 
                </div> 
            </form>
            <h3>Uploaded Images</h3>
            <ul>"""
    for file in list_files():
        index_html += f"<li><a href='/files/{file}'><img src='/files/{file}' alt='{file}'/></a></li>"
    index_html += """</ul>
        </div>
    </body>
    </html>"""
    return index_html

@app.route('/upload', methods=["POST"])
def upload():
    """
    Handle file upload, generate image captions using Gemini AI, 
    and store the metadata as a JSON file in the cloud storage bucket.
    """
    file = request.files['form_file']
    filename = file.filename
    local_image_path = os.path.join("./files", filename)
    
    # Save locally before processing
    file.save(local_image_path)

    # Generate AI-based caption and description
    caption_data = generate_caption_description(local_image_path)

    # Upload image to cloud storage
    file.seek(0)  # Reset file pointer for upload
    upload_blob(bucket_name, file, filename)

    # Save caption data as JSON and upload to cloud storage
    json_filename = f"{os.path.splitext(filename)[0]}.json"
    json_data = json.dumps(caption_data, indent=4)

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(json_filename)
    blob.upload_from_string(json_data, content_type='application/json')

    return redirect("/")

def list_files():
    """
    List JPEG and PNG images from the Google Cloud Storage bucket.
    """
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs()

    return [blob.name for blob in blobs if blob.name.lower().endswith(('.jpeg', '.jpg', '.png'))]

@app.route('/files/<filename>')
def get_file(filename):
    """
    Retrieve the requested file from Google Cloud Storage.
    """
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(filename)

    file_stream = BytesIO()
    blob.download_to_file(file_stream)
    file_stream.seek(0)

    return send_file(file_stream, mimetype='image/jpeg', as_attachment=False)

if __name__ == '__main__':
    app.run(debug=True)
