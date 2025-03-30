import os
import json
from flask import Flask, redirect, request, send_file
from google.cloud import storage
import google.generativeai as genai
from io import BytesIO
from PIL import Image
import io
import re
import google.cloud.secretmanager as secretmanager


app = Flask(__name__)
os.makedirs('files', exist_ok=True)

# Google Cloud Storage bucket name
bucket_name = 'cnd-bucket-z23746775'

def get_gemini_api_key():
    client = secretmanager.SecretManagerServiceClient()
    secret_name = f"projects/858704599700/secrets/GEMINI_API_KEY/versions/latest"
    
    response = client.access_secret_version(name=secret_name)
    return response.payload.data.decode("UTF-8")

# Configure Gemini AI with the retrieved API key
genai.configure(api_key=get_gemini_api_key())


def generate_caption_description(image_path):
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
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_file(file)

@app.route('/')
def index():
    index_html = """  
    <html>
    <head>
        <title>File Upload</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background-color: #6ac5fe;
                text-align: center;
                padding: 20px;
            }
            .container {
                background: #6ac5fe;
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
                margin: 20px 0;
                border: 1px solid #ccc;
                padding: 10px;
                border-radius: 10px;
                background-color: #f9f9f9;
                box-shadow: 0px 0px 5px gray;
            }
            img {
                max-width: 300px;
                height: auto;
                display: block;
                margin: 10px auto;
                border-radius: 5px;
                box-shadow: 0px 0px 5px gray;
            }
            button {
                padding: 10px;
                background: green;
                border-radius: 30px;
                margin-top:20px;
            }
            .caption-title {
                font-weight: bold;
                font-size: 18px;
                color: #333;
            }
            .caption-desc {
                font-size: 14px;
                color: #555;
                margin-top: 5px;
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

    # Display image + description
    for file in list_files():
        title = "N/A"
        description = "N/A"

        # Look for corresponding .json caption file
        base_name = os.path.splitext(file)[0]
        caption_file = f"{base_name}.json"

        try:
            storage_client = storage.Client()
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(caption_file)
            caption_json = json.loads(blob.download_as_string())
            title = caption_json.get("title", "N/A")
            description = caption_json.get("description", "N/A")
        except Exception as e:
            print(f"Could not fetch caption for {file}: {e}")

        index_html += f"""
            <li>
                <a href='/files/{file}'><img src='/files/{file}' alt='{file}'/></a>
                <div class='caption-title'>{title}</div>
                <div class='caption-desc'>{description}</div>
            </li>
        """

    index_html += """</ul>
        </div>
    </body>
    </html>"""
    return index_html


@app.route('/upload', methods=["POST"])
def upload():
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
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs()

    # Filter only image files and store their creation time
    image_files = [(blob.name, blob.time_created) for blob in blobs if blob.name.lower().endswith(('.jpeg', '.jpg', '.png'))]

    # Sort by creation date (oldest first)
    sorted_files = sorted(image_files, key=lambda x: x[1], reverse=True)

    # Return only file names in sorted order
    return [file[0] for file in sorted_files]

@app.route('/files/<filename>')
def get_file(filename):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(filename)

    file_stream = BytesIO()
    blob.download_to_file(file_stream)
    file_stream.seek(0)

    return send_file(file_stream, mimetype='image/jpeg', as_attachment=False)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

