from flask import Flask, request, jsonify
from flask_cors import CORS
from transformers import pipeline

app = Flask(__name__)
CORS(app)

company_name_recognition = pipeline("token-classification", model="dslim/bert-large-NER")
sentiment_analysis = pipeline("sentiment-analysis", model="mrm8488/distilroberta-finetuned-financial-news-sentiment"
                                                          "-analysis")


@app.route('/getSentimentScore', methods=['POST'])
def get_sentiment_score():
    content = request.json
    text = content.get("text")
    if not text:
        return jsonify({"error": "No text provided"}), 400
    result = sentiment_analysis(text)[0]
    if result['label'] == 'positive':
        score = 1
    elif result['label'] == 'neutral':
        score = 0
    else:
        score = -1

    return jsonify({"score": score})


@app.route('/getCompanyName', methods=['POST'])
def get_company_name():
    content = request.json
    text = content.get("text")
    if not text:
        return jsonify({"error": "No text provided"}), 400
    results = company_name_recognition(text)
    company = ""
    for result in results:
        if 'ORG' in result['entity']:
            if result['word'].startswith("##"):
                company = company + result['word'].replace("##", "")
            else:
                if company != "":
                    break
                else:
                    company = result['word']

    return jsonify(company)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8090)
