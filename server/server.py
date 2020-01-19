import os

from flask import Flask
from flask import request
import json
from flask import Response
from datetime import datetime
import requests
import base64
from itertools import product
import re

from azure.storage.blob import BlockBlobService
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from msrest.authentication import CognitiveServicesCredentials
from azure.servicebus import ServiceBusService, Message, Topic, Rule, DEFAULT_RULE_NAME

bus_service = ServiceBusService(
    service_namespace='licenseplatepublisher',
    shared_access_key_name='ConsumeReads',
    shared_access_key_value='VNcJZVQAVMazTAfrssP6Irzlg/pKwbwfnOqMXqROtCQ=')


account_name = 'meganoni'
account_key = 'dqODmqRYtyXC1skyDa8VmsY9Hupc+pQQp/OyKZFEcFU4yO1qZXPoW8BiOuZLJwldVo7G724NhIL3jyRpeAUgjA=='
context_container_name = 'test'
plate_container_name = 'plaque'

block_blob_service = BlockBlobService(
    account_name=account_name,
    account_key=account_key
)

blob_url_template = "https://meganoni.blob.core.windows.net/test/%s"
plate_blob_url_template = "https://meganoni.blob.core.windows.net/plaque/%s"

FLASK_DEBUG = os.environ.get('FLASK_DEBUG', True)
SUPPORTED_EXTENSIONS = ('.png', '.jpg', '.jpeg')

app = Flask(__name__)

COMPUTER_VISION_SUBSCRIPTION_KEY = "40d4b184080c436aaab896d811353948"
COMPUTER_VISION_ENDPOINT = "https://meganoni.cognitiveservices.azure.com/"

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
        msg = bus_service.receive_subscription_message('licenseplateread', 'eG4y7VYFse8NvW53', peek_lock=False)

        msg_json = json.loads(msg.body)

        plate_num = msg_json['LicensePlate']

        if plate_num in plates:
            request_url = "https://licenseplatevalidator.azurewebsites.net/api/lpr/platelocation"
            username = "equipe13"
            password = "RTFragcan38P5h8j"
            req_json = msg.body
            resp = requests.post( request_url, data=req_json, auth=(username, password))
            json_file.close()
            return Response(
                resp.text,
                status=resp.status_code
            )

fuzzy_dict = {
    'B' : ['B','8'],
    'C' : ['C','G'],
    'E' : ['E','F'],
    'K' : ['K','X','Y'],
    'I' : ['I','1','T','J'],
    'S' : ['S','5'],
    'O' : ['O','D','Q','0'],
    'P' : ['P','R'],
    'Z' : ['Z','2']
}


def generate_fuzzy_list(plate_num):
    fuzzy_list = set()
    is_fuzzy = False

    for letter in plate_num:
        if letter in fuzzy_dict:
            is_fuzzy = True
            break

    if not is_fuzzy:
        return [plate_num]

    indexes, replacements = zip(*[(i, fuzzy_dict[c]) for i, c in enumerate(plate_num) if c in fuzzy_dict])
    seq_plate_num = list(plate_num)

    for p in product(*replacements):
        for index, replacement in zip(indexes, p):
            seq_plate_num[index] = replacement
            fuzzy_list.add(''.join(seq_plate_num))

    return list(sorted(fuzzy_list))


@app.route( "/initGetMoney3", methods=['GET'] )
def init_get_money_3():
    with open( 'daily_wanted.txt' ) as json_file:
        data = json.load( json_file )
        wanted_plates = data['plates']

    while True:
        msg = bus_service.receive_subscription_message( 'licenseplateread', 'eG4y7VYFse8NvW53', peek_lock=False )

        msg_json = json.loads( msg.body )

        plate_num = msg_json['LicensePlate']
        print("PLATE NUMBER :" + plate_num)

        fuzzy_plate_nums = generate_fuzzy_list(plate_num)

        for fuzzy_plate_num in fuzzy_plate_nums:
            print("FUZZY PLATE: " + fuzzy_plate_num)
            if fuzzy_plate_num in wanted_plates:
                msg_json['LicensePlate'] = fuzzy_plate_num
                request_url = "https://licenseplatevalidator.azurewebsites.net/api/lpr/platelocation"
                username = "equipe13"
                password = "RTFragcan38P5h8j"
                msg_json.pop("LicensePlateImageJpg")
                img_context = msg_json.pop("ContextImageJpg")
                blob_name = plate_num + ".jpg"
                block_blob_service.create_blob_from_bytes(context_container_name, blob_name, base64.decodestring(img_context))

                blob_url = blob_url_template % blob_name

                msg_json['ContextImageReference'] = blob_url
                req_json = json.dumps(msg_json)
                resp = requests.post( request_url, data=req_json, auth=(username, password) )
                json_file.close()
                return Response(
                    msg_json['LicensePlate'],
                    status=resp.status_code
                )


@app.route( "/initGetMoney2", methods=['GET'] )
def init_get_money_2():
    with open( 'daily_wanted.txt' ) as json_file:
        data = json.load( json_file )
        plates = data['plates']

    while True:
        msg = bus_service.receive_subscription_message( 'licenseplateread', 'eG4y7VYFse8NvW53', peek_lock=False )

        msg_json = json.loads( msg.body )

        plate_num = msg_json['LicensePlate']
        print("PLATE NUMBER :" + plate_num)

        if plate_num in plates:
            request_url = "https://licenseplatevalidator.azurewebsites.net/api/lpr/platelocation"
            username = "equipe13"
            password = "RTFragcan38P5h8j"
            msg_json.pop("LicensePlateImageJpg")
            img_context = msg_json.pop("ContextImageJpg")
            blob_name = plate_num + ".jpg"
            block_blob_service.create_blob_from_bytes(context_container_name, blob_name, base64.decodestring(img_context))

            blob_url = blob_url_template % blob_name

            msg_json['ContextImageReference'] = blob_url
            req_json = json.dumps(msg_json)
            resp = requests.post( request_url, data=req_json, auth=(username, password) )
            json_file.close()
            return Response(
                str(plate_num),
                status=resp.status_code
            )


@app.route( "/initGetMoney4", methods=['GET'] )
def init_get_money_4():
    with open( 'daily_wanted.txt' ) as json_file:
        data = json.load( json_file )
        wanted_plates = data['plates']

    while True:
        msg = bus_service.receive_subscription_message( 'licenseplateread', 'eG4y7VYFse8NvW53', peek_lock=False )

        msg_json = json.loads( msg.body )

        plate_num = msg_json['LicensePlate']
        print("PLATE NUMBER :" + plate_num)

        img_plate = msg_json.pop("LicensePlateImageJpg")
        blob_name = plate_num + ".jpg"
        block_blob_service.create_blob_from_bytes(plate_container_name, blob_name, base64.decodestring( img_plate ) )

        plate_blob_url = plate_blob_url_template % blob_name

        fuzzy_plate_nums = generate_fuzzy_list(plate_num)

        for fuzzy_plate_num in fuzzy_plate_nums:
            print("FUZZY PLATE: " + fuzzy_plate_num)
            if fuzzy_plate_num in wanted_plates:
                msg_json['LicensePlate'] = fuzzy_plate_num
                request_url = "https://licenseplatevalidator.azurewebsites.net/api/lpr/platelocation"
                username = "equipe13"
                password = "RTFragcan38P5h8j"

                img_context = msg_json.pop("ContextImageJpg")
                blob_name = plate_num + ".jpg"
                block_blob_service.create_blob_from_bytes(context_container_name, blob_name, base64.decodestring(img_context))

                blob_url = blob_url_template % blob_name

                msg_json['ContextImageReference'] = blob_url
                req_json = json.dumps(msg_json)
                resp = requests.post( request_url, data=req_json, auth=(username, password) )
                json_file.close()
                return Response(
                    req_json,
                    status=resp.status_code
                )

        extract_plate_num = extract_text(plate_blob_url)
        print("EXTRACT: " + extract_plate_num)

        if extract_plate_num in wanted_plates:
            msg_json['LicensePlate'] = extract_plate_num
            request_url = "https://licenseplatevalidator.azurewebsites.net/api/lpr/platelocation"
            username = "equipe13"
            password = "RTFragcan38P5h8j"

            img_context = msg_json.pop( "ContextImageJpg" )
            blob_name = plate_num + ".jpg"
            block_blob_service.create_blob_from_bytes(context_container_name, blob_name, base64.decodestring( img_context ) )

            blob_url = blob_url_template % blob_name

            msg_json['ContextImageReference'] = blob_url
            req_json = json.dumps( msg_json )
            resp = requests.post( request_url, data=req_json, auth=(username, password) )
            json_file.close()
            return Response(
                req_json,
                status=resp.status_code
            )


ocr_url = COMPUTER_VISION_ENDPOINT + "vision/v2.1/ocr"


def extract_text(remote_image_url):
    img = requests.get(remote_image_url)
    length = img.headers.get("content-length")
    print("CONTENT LENTGH: " + length + " TOO SMALL? " + str(int(length) < 5000))
    if int(length) < 5000:
        return ""

    headers = {'Ocp-Apim-Subscription-Key': COMPUTER_VISION_SUBSCRIPTION_KEY}
    params = {'language': 'unk', 'detectOrientation': 'true'}
    data = {'url': remote_image_url}

    print(remote_image_url)
    response = requests.post( ocr_url, headers=headers, params=params, json=data )

    response.raise_for_status()

    analysis = response.json()
    # Extract the word bounding boxes and text.
    line_infos = [region["lines"] for region in analysis["regions"]]
    words = list()
    for line in line_infos:
        for word_metadata in line:
            word_to_add = ""
            for word_info in word_metadata["words"]:
                word_to_add = word_to_add + word_info["text"]
            words.append(word_to_add)

    for word in words:
        if bool(re.search('^(?=.*[A-Z0-9])(?=.*\d)[A-Z0-9\d]{6,}$', word)):
            return word

    return ""


@app.route("/test")
def test():
    remote_image_url ="https://meganoni.blob.core.windows.net/plaque/380CUG.jpg"
    img = requests.get(remote_image_url)
    length = img.headers.get("content-length")
    print("CONTENT LENTGH: " + length + " TOO SMALL? " + str(int(length) < 5000))
    if int(length) < 5000:
        return ""

    headers = {'Ocp-Apim-Subscription-Key': COMPUTER_VISION_SUBSCRIPTION_KEY}
    params = {'language': 'unk', 'detectOrientation': 'true'}
    data = {'url': remote_image_url}

    print(remote_image_url)
    response = requests.post( ocr_url, headers=headers, params=params, json=data )

    response.raise_for_status()

    analysis = response.json()

    return json.dumps(analysis)
    # Extract the word bounding boxes and text.
    line_infos = [region["lines"] for region in analysis["regions"]]
    words = list()
    for line in line_infos:
        for word_metadata in line:
            word_to_add = ""
            for word_info in word_metadata["words"]:
                word_to_add = word_to_add + word_info["text"]
            words.append(word_to_add)

    for word in words:
        if bool(re.search('^(?=.*[A-Z0-9])(?=.*\d)[A-Z0-9\d]{6,}$', word)):
            return word

    return ""



@app.route("/getWantedList", methods=['GET'])
def get_wanted_list():
    request_url = "https://licenseplatevalidator.azurewebsites.net/api/lpr/wantedplates"
    username = "equipe13"
    password = "RTFragcan38P5h8j"
    resp = requests.get( request_url, auth=(username, password) )
    return Response(
        resp.text,
        status=resp.status_code
    )


if __name__ == "__main__":
    app.run(debug=FLASK_DEBUG, host='0.0.0.0', port=5005)