from flask import Flask,jsonify
from flask_cors import CORS
import random

app = Flask(__name__)
CORS(app)

data = []


def read_data():
    sentences = []
    with open('all-data.csv', 'r') as file:
        for line in file:
            label, sentence = line.strip().split(',', 1)
            sentences.append(sentence.strip())

    return sentences


@app.route('/getData', methods=['GET'])
def get_data():
    if data:
        index = random.randint(0, len(data) - 1)
        chosen_sentence = data.pop(index).strip('"')
        response = {
            "sentence": chosen_sentence
        }
        return jsonify(response)
    else:
        return jsonify({"error": "No more sentences available."})


if __name__ == "__main__":
    data = read_data()
    app.run(host='0.0.0.0', port=8086)