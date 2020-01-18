import os

from flask import Flask
from flask import request
import json
from flask import Response
from datetime import datetime
import requests

from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from msrest.authentication import CognitiveServicesCredentials
from azure.servicebus import ServiceBusService, Message, Topic, Rule, DEFAULT_RULE_NAME

bus_service = ServiceBusService(
    service_namespace='licenseplatepublisher',
    shared_access_key_name='INSERTKEY',
    shared_access_key_value='INSERTKEY')


FLASK_DEBUG = os.environ.get('FLASK_DEBUG', True)
SUPPORTED_EXTENSIONS = ('.png', '.jpg', '.jpeg')

app = Flask(__name__)

COMPUTER_VISION_SUBSCRIPTION_KEY = "INSERTKEY"
COMPUTER_VISION_ENDPOINT = "INSERTKEY"

computervision_client = ComputerVisionClient(COMPUTER_VISION_ENDPOINT, CognitiveServicesCredentials(COMPUTER_VISION_SUBSCRIPTION_KEY))


@app.route("/ping")
def ping():
    return "ping"


@app.route("/time")
def time():
    return str(datetime.utcnow())


@app.route("/sendPlateLocation", methods = ['GET'])
def send_plate_location():

    msg = bus_service.receive_subscription_message( 'licenseplateread', 'eG4y7VYFse8NvW53', peek_lock=True )

    request_url = "https://licenseplatevalidator.azurewebsites.net/api/lpr/platelocation"
    username = "equipe13"
    password = "RTFragcan38P5h8j"
    req_json = msg.body
    resp = requests.post(request_url, data=req_json, auth=(username, password))
    return Response(
        resp.text,
        status=resp.status_code,
        content_type=resp.headers['content-type']
    )


@app.route( "/initGetMoney", methods=['GET'] )
def init_get_money():
    with open( 'daily_wanted.txt' ) as json_file:
        data = json.load(json_file)
        plates = data['plates']

    while True:
        msg = bus_service.receive_subscription_message('licenseplateread', 'eG4y7VYFse8NvW53', peek_lock=True)

        msg_json = json.loads(msg.body)

        plate_num = msg_json['LicensePlate']

        if plate_num in plates:
            request_url = "https://licenseplatevalidator.azurewebsites.net/api/lpr/platelocation"
            username = "equipe13"
            password = "RTFragcan38P5h8j"
            req_json = msg.body
            resp = requests.post( request_url, data=req_json, auth=(username, password))


@app.route("/analyzePlate", methods = ['GET'])
def analyze_plate():
    remote_image_url = "https://raw.githubusercontent.com/Azure-Samples/cognitive-services-sample-data-files/master/ComputerVision/Images/landmark.jpg"

    description_results = computervision_client.describe_image(remote_image_url)

    # Get the captions (descriptions) from the response, with confidence level
    print("Description of remote image: ")
    if len(description_results.captions) == 0:
        print("No description detected.")
    else:
        for caption in description_results.captions:
            print("'{}' with confidence {:.2f}%".format( caption.text, caption.confidence * 100 ))
            return "success"


if __name__ == "__main__":
    app.run(debug=FLASK_DEBUG, host='0.0.0.0', port=5005)