import uuid
import falcon
from server_test import Server
import json
import requests
import logging
from logging.handlers import RotatingFileHandler


def post_request(endpoint_url, headers, data):
    """POSTs Payload to HS to receive submission_id. Function will try attach response to POST to submission_id var,
    if unsuccessful, will provide exception in return value."""
    test_quick_mocker = 'https://1hrjl6rb0l.api.quickmocker.com'  # api testing url
    try:
        response = requests.post(url=endpoint_url, headers=headers, data=data, timeout=30)
        response.raise_for_status()
        submission_id = response.json()['submission_id']

    except requests.exceptions.RequestException as req_err:
        return req_err, response.status_code

    else:
        return submission_id, response.status_code


def post_request_response(hs_response, status_code):
    """Uses the boolean result, the hs_response and status code from the POST to Hyperscience to formatted response"""

    if status_code == 200:
        status = falcon.HTTP_202
        content_type = falcon.MEDIA_JSON
        text = json.dumps({"submission_id": hs_response})

    elif status_code == 400:
        status = falcon.HTTP_400
        content_type = falcon.MEDIA_JSON
        error = str(hs_response)
        text = json.dumps({"message": error})

    else:
        status = falcon.HTTP_500
        content_type = falcon.MEDIA_JSON
        text = json.dumps({"message": "Internal Server Error"})

    return status, content_type, text


def format_submission_data(raw_data, unique_id, app_log):
    """Formats the data into correct format for HS submission creation"""

    base_url = "https://hyperscience-ora-stg.s.adc.ns2p.corp.hmrc.gov.uk/"  # add environment switch
    endpoint = "api/v5/submissions"
    endpoint_url = base_url + endpoint
    auth_token = "013476527f06d3b375825c34a92e2d2d9cbdc9ee"  # environment switch vault.
    headers = {'Authorization': 'Token ' + auth_token}

    data = {
        "document": raw_data["file-location"]
    }

    if "metadata" not in raw_data or raw_data["metadata"] == {}:
        app_log.info(f"{unique_id} Metadata not found")
    else:
        raw_data["metadata"]["queue_name"] = f"{raw_data['source']}_{raw_data['document-type']}"

        data["metadata"] = json.dumps(raw_data["metadata"])
        print(json.dumps(data, indent=4, sort_keys=True))
        app_log.info(f"{unique_id} Metadata found and added to formatted payload")
    return endpoint_url, headers, data


def contains_mandatory_data(raw_data):
    """Function will return False if mandatory data is empty or missing"""

    if 'source' not in raw_data or raw_data['source'] == "":
        return False
    elif 'document-type' not in raw_data or raw_data['document-type'] == "":
        return False
    elif 'file-location' not in raw_data or raw_data['file-location'] == "":
        return False
    else:
        return True


def prepare_response(resp, status, content_type, text):
    """Function takes response status, content_type and text to send response back to original request source"""

    resp.status = status
    resp.content_type = content_type
    resp.text = text


class HealthCheck:

    def on_get(self, req, resp):
        """Handles HealthCheck"""
        resp.status = falcon.HTTP_204


class Document:

    def on_post(self, req, resp):
        """Handles Hyperscience Submission"""

        unique_id = uuid.uuid4()

        try:
            app_log.info(f"{unique_id} JSON Data received")
            raw_data = json.load(req.bounded_stream)

        except Exception as exception:
            app_log.info(f"{unique_id} Invalid JSON Data! = {exception}")
            prepare_response(resp=resp, status=falcon.HTTP_400, content_type=falcon.MEDIA_JSON,
                             text=json.dumps({"message": "Exception raised while parsing JSON"}))

        else:
            app_log.info(f"{unique_id} Checking for mandatory data")
            if not contains_mandatory_data(raw_data):
                app_log.info(f"{unique_id} Mandatory data missing/empty")
                prepare_response(resp=resp, status=falcon.HTTP_400, content_type=falcon.MEDIA_JSON,
                                 text=json.dumps({"message": "JSON missing mandatory data"}))

            else:
                app_log.info(f"{unique_id} Formatting submission payload")
                endpoint_url, headers, data = format_submission_data(raw_data, unique_id, app_log)

                app_log.info(f"{unique_id} Sending Submission to Hyperscience")
                hs_response, status_code = post_request(endpoint_url, headers, data)

                app_log.info(f"{unique_id} Responding back to request")
                status, content_type, text = post_request_response(hs_response, status_code)
                prepare_response(resp=resp, status=status, content_type=content_type, text=text)
                app_log.info(f"{unique_id} Response sent")


my_handler = RotatingFileHandler("proxy_log", mode="w", maxBytes=5 * 1024 * 1024, backupCount=10, encoding=None,
                                 delay=0)
my_handler.setFormatter(logging.Formatter("%(asctime)s  %(levelname)s  %(message)s"))
my_handler.setLevel(logging.INFO)

app_log = logging.getLogger("root")
app_log.setLevel(logging.INFO)
app_log.addHandler(my_handler)

app = falcon.App()
app.add_route('/health', HealthCheck())
app.add_route('/icr/document', Document())
server = Server()
server.run_server(app)
