from flask import Flask, jsonify, send_from_directory, render_template
import os

app = Flask(__name__)

# Parent directory containing all subdirectories
PARENT_FOLDER = os.path.join('public')

# Serve the index.html template from the templates folder
@app.route('/')
def index():
    return render_template('index.html')

# Route to list available images from all subdirectories in JSON format
@app.route('/images')
def list_images():
    valid_extensions = ('.png', '.jpg', '.jpeg', '.gif')
    images_by_folder = {}
    for subdir in ['HL', 'RS', 'mslet', 'temp', 'GUST']:
        folder_path = os.path.join(PARENT_FOLDER, subdir)
        try:
            images = [img for img in os.listdir(folder_path) if img.lower().endswith(valid_extensions)]
            if images:
                images_by_folder[subdir] = images
        except FileNotFoundError:
            continue
    return jsonify(images_by_folder)

# Route to serve a specific image
@app.route('/public/<path:filename>')
def get_image(filename):
    directory, file = os.path.split(filename)
    return send_from_directory(os.path.join(PARENT_FOLDER, directory), file)

if __name__ == '__main__':
    app.run(debug=True)
