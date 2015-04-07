import os
from flask import Flask, request, redirect, render_template, flash, url_for, \
    send_from_directory, current_app, make_response
from werkzeug import secure_filename

from pyPdf import PdfFileWriter, PdfFileReader
from pyPdf.generic import NameObject, createStringObject


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


def clean_meta_data(input_filename):
    output = PdfFileWriter()
    info_dict = output._info.getObject()
    info_dict.update({
        NameObject('/Title'): createStringObject(u''),
        NameObject('/Author'): createStringObject(u''),
        NameObject('/Subject'): createStringObject(u''),
        NameObject('/Creator'): createStringObject(u'')
    })
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


def assure_that_filename_is_pdf(filename):
    if not filename.endswith('.pdf'):
        return filename + '.pdf'
    return filename


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file_ = request.files['file_1']
        if file_ and allowed_file(file_.filename):
            filename = request.form.get('filename_1') or \
                secure_filename(file_.filename)
            filename = assure_that_filename_is_pdf(filename)
            file_.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            clean_meta_data(filename)

            return redirect(
                url_for(
                    'download_file',
                    filename=filename
                )
            )
        else:
            flash('Niepoprawny plik', 'danger')
            return redirect(url_for('upload_file'))
    return render_template('upload.html')


@app.route('/uploads/<path:filename>')
def show_file(filename):
    u"""
    View for showing uploaded file. Not in use for now.
    """
    uploads = app.config['UPLOAD_FOLDER']
    return send_from_directory(directory=uploads, filename=filename)


@app.route('/download/<filename>')
def download_file(filename):
    file_ = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    raw_bytes = ''
    with open(file_, 'rb') as pdf:
        for line in pdf:
            raw_bytes += line
    response = make_response(raw_bytes)
    response.headers['Content-Type'] = "application/octet-stream"
    response.headers['Content-Disposition'] = "inline; filename=" + filename
    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    return response


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500


if __name__ == '__main__':
    app.run()
