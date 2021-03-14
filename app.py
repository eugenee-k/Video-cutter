#!flask/bin/python

import os
import PIL
from PIL import Image
import simplejson
import traceback
import json
from shutil import copyfile
import ffmpeg
import random
import string
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip

from flask import Flask, request, render_template, redirect, url_for, send_from_directory
from flask_bootstrap import Bootstrap
from werkzeug import secure_filename

from lib.upload_file import uploadfile


app = Flask(__name__)
app.config['SECRET_KEY'] = 'hard to guess string'
app.config['UPLOAD_FOLDER'] = 'data/'
app.config['THUMBNAIL_FOLDER'] = 'data/thumbnail/'
app.config['CUTTED_FILES_FOLDER'] = 'data/cutted/'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024 * 1024

ALLOWED_EXTENSIONS = set(['mp4', 'mov', 'avi', 'webm', 'mkv'])
IGNORED_FILES = set(['.gitignore'])

bootstrap = Bootstrap(app)


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def gen_file_name(filename):
    """
    If file was exist already, rename it and return a new name
    """

    i = 1
    while os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
        name, extension = os.path.splitext(filename)
        filename = '%s_%s%s' % (name, str(i), extension)
        i += 1

    return filename


def create_thumbnail(image):
    try:
        base_width = 80
        img = Image.open(os.path.join(app.config['UPLOAD_FOLDER'], image))
        w_percent = (base_width / float(img.size[0]))
        h_size = int((float(img.size[1]) * float(w_percent)))
        img = img.resize((base_width, h_size), PIL.Image.ANTIALIAS)
        img.save(os.path.join(app.config['THUMBNAIL_FOLDER'], image))

        return True

    except:
        print traceback.format_exc()
        return False


@app.route("/upload", methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        files = request.files['file']

        if files:
            filename = secure_filename(files.filename)
            filename = gen_file_name(filename)
            mime_type = files.content_type

            if not allowed_file(files.filename):
                result = uploadfile(
                    name=filename, type=mime_type, size=0, not_allowed_msg="File type not allowed")

            else:
                # save file to disk
                for the_file in os.listdir(app.config['UPLOAD_FOLDER']):
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], the_file)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                        #elif os.path.isdir(file_path): shutil.rmtree(file_path)
                    except Exception as e:
                        print(e)
                uploaded_file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                files.save(uploaded_file_path)

                # create thumbnail after saving
                if mime_type.startswith('image'):
                    create_thumbnail(filename)
                
                # get file size after saving
                size = os.path.getsize(uploaded_file_path)

                # return json for js call back
                result = uploadfile(name=filename, type=mime_type, size=size)
            
            return simplejson.dumps({"files": [result.get_file()]})

    if request.method == 'GET':
        # get all file in ./data directory
        files = [f for f in os.listdir(
            app.config['UPLOAD_FOLDER']) if os.path.isfile(
            os.path.join(app.config['UPLOAD_FOLDER'],f)) and f not in IGNORED_FILES ]
        
        file_display = []

        for f in files:
            size = os.path.getsize(os.path.join(app.config['UPLOAD_FOLDER'], f))
            file_saved = uploadfile(name=f, size=size)
            file_display.append(file_saved.get_file())

        return simplejson.dumps({"files": file_display})

    return redirect(url_for('index'))


@app.route("/delete/<string:filename>", methods=['DELETE'])
def delete(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file_thumb_path = os.path.join(app.config['THUMBNAIL_FOLDER'], filename)

    if os.path.exists(file_path):
        try:
            os.remove(file_path)

            if os.path.exists(file_thumb_path):
                os.remove(file_thumb_path)
            
            return simplejson.dumps({filename: 'True'})
        except:
            return simplejson.dumps({filename: 'False'})


# serve static files
@app.route("/thumbnail/<string:filename>", methods=['GET'])
def get_thumbnail(filename):
    return send_from_directory(app.config['THUMBNAIL_FOLDER'], filename=filename)


@app.route("/data/<string:filename>", methods=['GET'])
def get_file(filename):
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER']), filename=filename)


@app.route("/data/cutted/<string:filename>", methods=['GET'])
def get_cutted_file(filename):
    return send_from_directory(os.path.join(app.config['CUTTED_FILES_FOLDER']), filename=filename)


@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')


@app.route('/<video_id>', methods=['GET'])
def video_page(video_id):
    return render_template('video.html', fileid=video_id)


@app.route('/cutted', methods=['POST'])
def cutted():
    p1 = request.form['p1']
    p2 = request.form['p2']
    filename = request.form['file']
    fileid = request.form['id']

    ffmpeg_extract_subclip(
        'data/' + filename, 
        float(p1), 
        float(p2), 
        targetname="data/subclip__{}".format(filename)
        )
    os.unlink('data/' + filename)

    copyfile("data/subclip__{}".format(filename), "data/cutted/{}".format(fileid))

    return json.dumps({'resp':'ok'})


if __name__ == '__main__':
    app.run(debug=True)


