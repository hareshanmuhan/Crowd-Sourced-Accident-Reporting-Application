from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
import os
from werkzeug.utils import secure_filename
import requests
import json
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration
from twilio.rest import Client


app = Flask(__name__)

UPLOAD_FOLDER = os.path.join(os.getcwd(), "static", "uploads")  # Corrected path
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Ensure directory exists
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER  # Update Flask config

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app.secret_key = 'c83c524a6eafb3efea896ff3b353576c'

VALID_USER_ID = "user123"
VALID_PASSWORD = "password123"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def image_to_text(image_path):
    processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
    raw_image = Image.open(image_path).convert("RGB")
    inputs = processor(raw_image, return_tensors="pt")
    out = model.generate(**inputs)
    caption = processor.decode(out[0], skip_special_tokens=True)

    disaster_keywords = {
        "Accident": {"collision", "crash", "overturned", "wreck", "pileup", "vehicle", "flipped", "collided"},
        "Flood": {"flood", "water", "submerged", "drowning", "heavy rain", "overflow", "washed away"},
        "Fire": {"fire", "burning", "flames", "smoke", "wildfire", "inferno", "blaze", "scorched", "charred"},
        "Earthquake": {"collapsed", "rubble", "cracks", "shaking", "quake", "destroyed", "damaged building"},
        "Storm": {"storm", "hurricane", "tornado", "cyclone", "typhoon", "wind", "fallen trees", "damaged roofs"},
        "Landslide": {"landslide", "mudslide", "rocks", "falling debris", "mountain", "hill collapse"},
        "Explosion": {"explosion", "blast", "bomb", "fireball", "shockwave", "debris"},
        "Snowstorm": {"snowstorm", "blizzard", "whiteout", "heavy snow", "freezing", "icy roads", "frost"},
    }

    caption_lower = caption.lower()
    for disaster, keywords in disaster_keywords.items():
        if any(word in caption_lower for word in keywords):
            caption = caption.capitalize()
            return caption, disaster
    return caption, "No disaster detected."

def detect_image_type(image_path):
    params = {
        'models': 'genai',
        'api_user': '1154867899',
        'api_secret': '9rD4FbDB4kFtWdaMpw8NvwDjrApP2fpy'
    }
    files = {'media': open(image_path, 'rb')}
    r = requests.post('https://api.sightengine.com/1.0/check.json', files=files, data=params)
    output = json.loads(r.text)
    score = output['type']['ai_generated']
    return score

def send_sms(message_body):
    account_sid = 'ACda4793581b76db0be57ead8ee8ef3097'
    auth_token = '3ff84879a391c339f7cf39f1449be47e'

    client = Client(account_sid, auth_token)

    message = client.messages.create(
        body= message_body,  
        from_="+1 9706506960",       
        to="+91 9176383760"           
    )
    print(f"SMS sent! Message SID: {message.sid}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        password = request.form.get('password')

        if user_id == VALID_USER_ID and password == VALID_PASSWORD:
            session['logged_in'] = True  
            return redirect(url_for('upload_image')) 
        else:
            error = "Invalid User ID or Password"
            return render_template('login.html', error=error)

    return render_template('login.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload_image():
    if not session.get('logged_in'):
        return redirect(url_for('login')) 

    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            print(f"File saved to: {filepath}")


            ai_score = detect_image_type(filepath)
            threshold = 0.95

            if ai_score > threshold:
                result = "AI IMAGE"
            else:
                result = "REAL IMAGE"

            return render_template('detect_image_type.html', result=result, filename=filename)

    return render_template('upload.html')

@app.route('/result/<filename>')
def result(filename):
    if not session.get('logged_in'):
        return redirect(url_for('login')) 

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    caption, action = image_to_text(filepath)
    return render_template('result.html', caption=caption, action=action, filename=filename)

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)  # Serve from correct folder

@app.route('/info_retriv')
def info_retriv():
    if not session.get('logged_in'):
        return redirect(url_for('login')) 

    action = request.args.get('action') 
    return render_template('info_retriv.html', action=action)

@app.route('/submit_info', methods=['POST'])
def submit_info():
    if not session.get('logged_in'):
        return redirect(url_for('login')) 

    action = request.form.get('action')
    injured = request.form.get('injured')
    trapped = request.form.get('trapped')
    trapped_count = request.form.get('trappedCount')
    landmark = request.form.get('landmark')
    emergency_services = request.form.get('emergencyServices')
    damage_level = request.form.get('damageLevel')
    image_time = request.form.get('imageTime')
    missing_persons = request.form.get('missingPersons')
    missing_count = request.form.get('missingCount')

    disaster_data = [
        f"Emergency Alert, a Disaster has been identified!!",
        f"Disaster Type: {action}",
        f"Injured: {injured}",
        f"Trapped: {trapped}",
        f"Trapped Count: {trapped_count}",
        f"Landmark: {landmark}",
        f"Emergency Services: {emergency_services}",
        f"Damage Level: {damage_level}",
        f"Image Time: {image_time}",
        f"Missing Persons: {missing_persons}",
        f"Missing Count: {missing_count}"
    ]

    message_body = "\n".join(disaster_data) 
    send_sms(message_body)

    if action == "Accident":
        return render_template('Accident.html')
    elif action == "Flood":
        return render_template('Flood.html')
    elif action == "Fire":
        return render_template('Fire.html')
    elif action == "Earthquake":
        return render_template('Earthquake.html')
    elif action == "Storm":
        return render_template('Storm.html')
    elif action == "Landslide":
        return render_template('Landslide.html')
    elif action == "Explosion":
        return render_template('Explosion.html')
    else:
        return render_template('no_disaster.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None) 
    return redirect(url_for('index')) 

if __name__ == '__main__':
    app.run(debug=True)