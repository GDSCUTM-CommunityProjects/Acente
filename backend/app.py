from firebase_admin import firestore
from firebase_admin import credentials
import firebase_admin
from google.cloud import speech_v1p1beta1 as speech
import os
import base64
from flask_cors import CORS, cross_origin
import pyrebase
import json
from flask import Flask, request, jsonify, make_response, session
from flask_cors import CORS
import random
from flask_session import Session
from datetime import timedelta
# App configuration
app = Flask(__name__)
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "filesystem"
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=5)
app.config['SESSION_FILE_THRESHOLD'] = 100
app.secret_key = "Acente DSC Group 3"
Session(app)

# # #Enable CORs
cors = CORS(app)

# Connect to firebase
firebase = pyrebase.initialize_app(json.load(open('secrets.json')))
auth = firebase.auth()
# Authenticate Firebase tables
db = firebase.database()

PERFECT = 0
ALMOST_THERE = 1
POOR = 2

cors = CORS(app)
# service key required to access google cloud services
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "service-account-key.json"
speech_client = speech.SpeechClient()

# The confidence of word at index i in gcp_output_words is located at index i in gcp_output_confidence


def parseGCPOutput(sentence, gcp_output_words, gcp_output_confidence):
    sentence_arr = sentence.lower().split(" ")
    confidence_arr = []
    confidence_levels = []
    index = 0
    for word in sentence_arr:
        if word in gcp_output_words[index:]:
            index = gcp_output_words.index(word, index)
            confidence_arr.append(gcp_output_confidence[index])
            if gcp_output_confidence[index] >= 0.97:
                confidence_levels.append(PERFECT)
            elif gcp_output_confidence[index] >= 0.90:
                confidence_levels.append(ALMOST_THERE)
            else:
                confidence_levels.append(POOR)
            index += 1
        else:
            confidence_arr.append(0)
            confidence_levels.append(POOR)

    return confidence_arr, confidence_levels


@app.route("/messages", methods=["POST"])
@cross_origin()
def user():
    byte_data = base64.b64decode(request.json['message'])
    audio_mp3 = speech.RecognitionAudio(content=byte_data)
    config_mp3 = speech.RecognitionConfig(
        encoding='MP3',
        sample_rate_hertz=16000,
        enable_automatic_punctuation=True,
        language_code='en-US',
        enable_word_confidence=True
    )

    # Transcribing the audio into text
    response = speech_client.recognize(
        config=config_mp3,
        audio=audio_mp3
    )
    words = []
    confidence = []
    sentence = request.json['sentence']
    sentence_id = request.json['id']
    user_id = request.json['uid']
    for result in response.results:
        for pair in result.alternatives[0].words:
            words.append(pair.word.lower())
            confidence.append(pair.confidence)
    arr1, arr2 = parseGCPOutput(sentence, words, confidence)
    sentence_arr = sentence.split(" ")
    if not request.json.get('sandbox', None):
        def find_avg(x, y): return (x*5+y*2)/7
        sen_confidence = response.results[0].alternatives[0].confidence
        prev = db.child('voice-data').child(user_id).child(sentence_id).get()
        if prev.val():
            sen_confidence = find_avg(prev.val(), sen_confidence)
        db.child(
            'voice-data').child(user_id).update({sentence_id: sen_confidence})
        data = {}
        for i in range(len(arr1)):
            word_confidence = arr1[i]
            prev = db.child('words').child(user_id).child(sentence_id).get()
            if prev.val():
                word_confidence = find_avg(prev.val(), word_confidence)
            data[sentence_arr[i].strip('.')] = word_confidence
        db.child('words').child(user_id).update(data)
    return make_response(jsonify(confidence=arr2, sentence_arr=sentence_arr))
# Api route to get user data


@app.route('/api/userinfo', methods=["POST"])
def userinfo():
    if (request.form.get('uid', None) and request.form.get('token', None)):
        try:
            auth.current_user = session.get("email", auth.current_user)
            user = db.child("users").child(
                request.form['uid']).get(request.form['token'])
            return jsonify(uid={user.key(): user.val()})
        except:
            pass
    # invalid uid or token
    return make_response(jsonify(message='Error cannot retrieve user information'), 400)

# Api route to sign up a new user


@app.route('/api/signup', methods=["POST"])
def signup():
    data = {
        "email": request.form.get('email'),
        "name": request.form.get('name', ""),
        "language": request.form.get('language', "English")
    }
    password = request.form.get('password')
    if not (data['email'] and password):
        return make_response(jsonify(message='Error missing required user information'), 400)
    try:
        user = auth.create_user_with_email_and_password(
            email=data['email'], password=password)
        db.child('users').child(user['localId']).set(data, user['idToken'])
        session["email"] = user
        # auth.send_email_verification(user['idToken'])
        return jsonify(user)
    except:
        return make_response(jsonify(message='Error creating user'), 401)

# Api to refresh user token (Note token expire every hour)


@app.route('/api/login', methods=["POST"])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    try:
        user = auth.sign_in_with_email_and_password(email, password)
        session["email"] = user
        return jsonify(user)
    except:
        return make_response(jsonify(message='Error authenticating user'), 401)

# take refresh token and get new token


@app.route('/api/token', methods=["POST"])
def token():
    if request.form.get('refreshToken', None):
        try:  # Review sign_in_with_custom_token(self, token) function
            auth.current_user = session.setdefault("email", auth.current_user)
            user = auth.refresh(request.form['refreshToken'])
            session["email"].update(user)
            return jsonify(user)
        except:
            pass
    return make_response(jsonify(message='Error invalid refresh token'), 400)


# Firestore Setup

# Use a service account
cred = credentials.Certificate('fireStoreKey.json')
firebase_admin.initialize_app(cred)
firestore_db = firestore.client()

ls, index = [], 0
sentences_ref = firestore_db.collection(u'sentences').stream()
for sentence in sentences_ref:
    ls.append(sentence)
random.shuffle(ls)

@app.route('/api/randomSentenceGenerator', methods=["GET"])
def random_sentence_generator():
    """ Returns a senctence from shuffled list of sentences
    """
    global index
    try:
        if index >= len(ls):
            index = 0
        sentence = jsonify(ls[index].get(u'sentence'))
        index += 1
        return sentence
    except:
        return make_response(jsonify(message='Cannot fetch a sentence'), 400)
    
if __name__ == '__main__':
    app.run()
