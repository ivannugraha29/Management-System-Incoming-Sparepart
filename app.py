from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from io import BytesIO
from reportlab.pdfgen import canvas
from datetime import datetime
import mysql.connector
from mysql.connector import Error
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph

app = Flask(__name__)
app.config['SECRET_KEY'] = 'iniSecretKeyKu2019'

# Database configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_DATABASE'] = 'spareparts_db'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'cicurug123tea'

# Initialize MySQL connection
def get_db_connection():
    conn = mysql.connector.connect(
        host=app.config['MYSQL_HOST'],
        database=app.config['MYSQL_DATABASE'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD']
    )
    return conn

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'email' in session:
        return redirect(url_for('penerima_sparepart'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if email == 'admin@gmail.com' and password == 'pass':
            session['email'] = email
            session['role'] = 'admin'
            flash('Admin login successful!', 'success')
            return redirect(url_for('penerima_sparepart'))
        elif email == 'vendor@gmail.com' and password == 'pass':
            session['email'] = email
            session['role'] = 'vendor'
            flash('Vendor login successful!', 'success')
            return redirect(url_for('vendor_dashboard'))
        else:
            flash('Invalid email or password', 'danger')

    return render_template('index.html')

# Admin routes
@app.route('/penerima-sparepart')
def penerima_sparepart():
    if 'email' not in session:
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM spareparts')
    spareparts = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('penerima_sparepart.html', spareparts=spareparts)

@app.route('/edit-sparepart/<int:part_id>', methods=['GET', 'POST'])
def edit_sparepart(part_id):
    print(f"Attempting to edit sparepart with ID: {part_id}")

    if 'email' not in session:
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        name = request.form['name']
        quantity = request.form['quantity']
        vendor = request.form['vendor']
        entry_date = request.form['entry_date']

        cursor.execute('UPDATE spareparts SET name=%s, quantity=%s, vendor=%s, entry_date=%s WHERE id=%s',
                       (name, quantity, vendor, entry_date, part_id))
        conn.commit()
        flash('Spare part updated successfully', 'success')
        return redirect(url_for('penerima_sparepart'))

    cursor.execute('SELECT * FROM spareparts WHERE id=%s', (part_id,))
    sparepart = cursor.fetchone()
    cursor.close()
    conn.close()

    if sparepart is None:
        flash('Invalid part ID', 'danger')
        return redirect(url_for('penerima_sparepart'))

    return render_template('edit_sparepart.html', sparepart=sparepart, part_id=part_id)

@app.route('/delete-sparepart/<int:part_id>', methods=['GET', 'POST'])
def delete_sparepart(part_id):
    if 'email' not in session:
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute('SELECT * FROM spareparts WHERE id=%s', (part_id,))
    deleted_part = cursor.fetchone()

    if deleted_part:
        cursor.execute('DELETE FROM spareparts WHERE id=%s', (part_id,))
        conn.commit()

        cursor.execute('INSERT INTO delete_history (name, quantity, vendor, entry_date) VALUES (%s, %s, %s, %s)',
                       (deleted_part['name'], deleted_part['quantity'], deleted_part['vendor'], deleted_part['entry_date']))
        conn.commit()

        flash('Spare part deleted successfully', 'success')
    else:
        flash('Invalid part ID', 'danger')

    cursor.close()
    conn.close()

    return redirect(url_for('penerima_sparepart'))

@app.route('/send-sparepart/<int:part_id>')
def send_sparepart(part_id):
    if 'email' not in session or session.get('role') != 'admin':
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute('UPDATE spareparts SET status=%s WHERE id=%s', ('sent', part_id))
    conn.commit()
    flash('Spare part sent successfully', 'success')

    cursor.close()
    conn.close()

    return redirect(url_for('gudang'))

@app.route('/gudang')
def gudang():
    if 'email' not in session or session.get('role') != 'admin':
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM spareparts WHERE status=%s', ('sent',))
    gudang_spareparts = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('gudang.html', spareparts=gudang_spareparts)

# Vendor routes
@app.route('/vendor-dashboard')
def vendor_dashboard():
    if 'email' not in session or session.get('role') != 'vendor':
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM spareparts WHERE vendor=%s', (session['email'],))
    vendor_spareparts = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('vendor_dashboard.html', spareparts=vendor_spareparts)

@app.route('/vendor-send-sparepart', methods=['GET', 'POST'])
def vendor_send_sparepart():
    if 'email' not in session or session.get('role') != 'vendor':
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form['name']
        quantity = request.form['quantity']
        vendor = session.get('email')
        entry_date = datetime.now().strftime('%Y-%m-%d')

        if not name or not quantity:
            flash('Name and quantity are required', 'danger')
            return redirect(url_for('vendor_send_sparepart'))

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO spareparts (name, quantity, vendor, entry_date) VALUES (%s, %s, %s, %s)',
                       (name, quantity, vendor, entry_date))
        conn.commit()
        cursor.close()
        conn.close()

        flash('Spare part sent successfully', 'success')
        return redirect(url_for('vendor_spareparts_sent'))

    return render_template('vendor_send_sparepart.html')

@app.route('/vendor-spareparts-sent')
def vendor_spareparts_sent():
    if 'email' not in session or session.get('role') != 'vendor':
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM spareparts WHERE vendor=%s', (session['email'],))
    vendor_spareparts = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('vendor_spareparts_sent.html', spareparts=vendor_spareparts)


@app.route('/generate-report')
def generate_report():
    if 'email' not in session or session.get('role') != 'admin':
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT name, quantity, vendor, entry_date FROM spareparts WHERE status=%s', ('sent',))
    gudang_spareparts = cursor.fetchall()
    cursor.close()
    conn.close()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    elements = []

    # Title
    styles = getSampleStyleSheet()
    title = Paragraph("Spare Parts Report - Gudang", styles['Title'])
    elements.append(title)
    
    # Table Data
    data = [["Name", "Quantity", "Vendor", "Entry Date"]]
    for part in gudang_spareparts:
        data.append([part['name'], part['quantity'], part['vendor'], part['entry_date']])

    # Create the Table
    table = Table(data, colWidths=[2.5 * inch, 1.5 * inch, 2 * inch, 2 * inch])

    # Add style to the table with white background
    table.setStyle(TableStyle([
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    elements.append(table)

    doc.build(elements)

    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name='spareparts_gudang_report.pdf', mimetype='application/pdf')

@app.route('/logout')
def logout():
    session.pop('email', None)
    session.pop('role', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5001)
