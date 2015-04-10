# -*- coding: utf-8 -*-

import os
import zipfile
from flask import Flask, request, redirect, render_template, flash, url_for, \
    send_from_directory, make_response
from werkzeug import secure_filename

from pyPdf import PdfFileWriter, PdfFileReader, utils


app = Flask(__name__)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ALLOWED_EXTENSIONS = ['pdf']

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = ALLOWED_EXTENSIONS
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'Secret'


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']


def save_file(file_obj, filename):
    file_obj.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))


def remove_file(filename):
    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))


def validate_files(file_list):
    """
    If file passes validation it is saved on upload dir
    """
    for uploaded_file in file_list:
        if not uploaded_file.filename:
            flash(u"Nie wskazano pliku", "danger")
            return False
        elif not allowed_file(uploaded_file.filename):
            flash(u"Plik %s jest niepoprawny (musi być z rozszerzeniem .pdf)"
                  % uploaded_file.filename,
                  "danger")
            return False
        save_file(uploaded_file, uploaded_file.filename)
        try:
            PdfFileReader(open(os.path.join(app.config['UPLOAD_FOLDER'],
                                            uploaded_file.filename)))
        except utils.PdfReadError:
            flash("Plik %s wcale nie jest plikiem .pdf"
                  % uploaded_file.filename,
                  "danger")
            remove_file(uploaded_file.filename)
            return False
    return True


def clean_meta_data(input_filename):
    output = PdfFileWriter()
    input_ = PdfFileReader(open(os.path.join(app.config['UPLOAD_FOLDER'],
                                             input_filename)))
    for page in range(input_.getNumPages()):
        output.addPage(input_.getPage(page))

    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], input_filename))

    output_stream = file(
        os.path.join(app.config['UPLOAD_FOLDER'], input_filename), 'wb'
    )
    output.write(output_stream)
    output_stream.close()


def make_secure_filename(filename, extension=".pdf"):
    filename = secure_filename(filename)
    filename = filename.replace('.', '_')
    if not filename.endswith(extension):
        filename += extension
    return filename


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        uploaded_files = request.files.getlist('files')
        if not validate_files(uploaded_files):
            flash(u"Spróbuj jeszcze raz", "info")
            return redirect(url_for('upload_file'))
        for uploaded_file in uploaded_files:
            clean_meta_data(uploaded_file.filename)
        print "uploaded files to %d" % len(uploaded_files)
        extension = ".pdf" if len(uploaded_files) == 1 else ".zip"
        if request.form.get('filename'):
            output_name = make_secure_filename(request.form['filename'],
                                               extension=extension)
        else:
            output_name = "pdf_files.zip" if extension == '.zip' \
                else uploaded_files[0].filename
        print output_name
        if extension == ".zip":
            zip_arch = zipfile.ZipFile(
                os.path.join(app.config['UPLOAD_FOLDER'], output_name), "w"
            )
            for uploaded_file in uploaded_files:
                zip_arch.write(os.path.join(app.config['UPLOAD_FOLDER'],
                                            uploaded_file.filename),
                               arcname=uploaded_file.filename)
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'],
                                       uploaded_file.filename))
            zip_arch.close()
        else:
            os.rename(
                os.path.join(app.config['UPLOAD_FOLDER'],
                             uploaded_files[0].filename),
                os.path.join(app.config['UPLOAD_FOLDER'],
                             output_name)
            )
        return redirect(url_for('download_file_from_uploads',
                                filename=output_name))
    return render_template("upload.html")


@app.route('/uploads/<path:filename>')
def download_file_from_uploads(filename):
    uploads = app.config['UPLOAD_FOLDER']
    response = send_from_directory(directory=uploads, filename=filename,
                                   as_attachment=True)
    os.remove(os.path.join(uploads, filename))
    return response


@app.route('/download/<filename>')
def download_file_making_raw_response(filename):
    u"""
    View not used for now
    """
    file_ = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    raw_bytes = ''
    with open(file_, 'rb') as pdf:
        for line in pdf:
            raw_bytes += line
    response = make_response(raw_bytes)
    response.headers['Content-Type'] = "application/octet-stream"
    response.headers['Content-Disposition'] = "as_attachment; filename=" \
                                              + filename
    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    return response


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500


if __name__ == '__main__':
    app.run(debug=True)
