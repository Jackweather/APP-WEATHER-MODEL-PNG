from flask import Flask, jsonify, send_from_directory, render_template
import os

app = Flask(__name__)

# Cross-platform way to set image folder path
IMAGE_FOLDER = os.path.join('public', 'HL',)  # ✅ updated path to public/RS/USA

# Serve the index.html template from the templates folder
@app.route('/')
def index():
    return render_template('index.html')

# Route to list available images in JSON format
@app.route('/images')
def list_images():
    # Only include valid image file extensions
    valid_extensions = ('.png', '.jpg', '.jpeg', '.gif')
    try:
        images = [img for img in os.listdir(IMAGE_FOLDER) if img.lower().endswith(valid_extensions)]
    except FileNotFoundError:
        images = []
    return jsonify(images)

# Route to serve a specific image
@app.route('/public/HL/<path:filename>')  # ✅ updated path to public/RS/USA
def get_image(filename):
    return send_from_directory(IMAGE_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=True)
