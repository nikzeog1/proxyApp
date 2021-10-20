import falcon
import proxylogger
from server_test import Server
import json
import requests
import logging


def post_payload(endpoint_url, headers, data):
    """POSTs Payload to HS to receive submission_id. Function will try attach response to POST to submission_id var,
    if unsuccessful, will provide exception in return value."""

    try:
        test_quick_mocker = 'https://1hrjl6rb0l.api.quickmocker.com'  # api testing url
        response = requests.post(url=test_quick_mocker, headers=headers, data=data, timeout=30)
        submission_id = response.json()['submission_id']
    except requests.exceptions.RequestException as req_err:
        return False, req_err, response.status_code
    except Exception as err:
        return False, err, response.status_code
    else:
        return True, submission_id, response.status_code


def contains_mandatory_data(raw_data):
    """Function will return False if mandatory is empty from json or has missing data"""

    if 'source' not in raw_data or raw_data['source'] == "":
        print("source is not here")
        return False
    elif 'document-type' not in raw_data or raw_data['document-type'] == "":
        print("document-type is not here")
        return False
    elif 'file-location' not in raw_data or raw_data['file-location'] == "":
        print("file-location is not here")
        return False
    else:
        return True


def format_submission_data(raw_data, logger):
    """Formats the data into correct format for HS submission creation"""

    logger.info("Formatting submission for Hyperscience...")
    base_url = "https://on-premise-server.yourcompany.com/"  # add environment switch
    endpoint = "api/v5/submissions"
    endpoint_url = base_url + endpoint
    auth_token = "a22d533ebaa60ae5d46b2f0ea67532a4eb8e33be"  # environment switch vault.
    headers = {'Authorization': 'Token ' + auth_token}
    data = {
        "document": raw_data["file-location"]
    }
    if "metadata" not in raw_data or raw_data["metadata"] == {}:
        logger.info("no metadata")
    else:
        logger.info("Metadata found...formatting into Hyperscience payload")
        raw_data["metadata"]["queue_name"] = f"{raw_data['source']}_{raw_data['document-type']}"
        data["metadata"] = json.dumps(raw_data["metadata"])
        print(json.dumps(data, indent=4, sort_keys=True))
    return endpoint_url, headers, data


def post_request_response(request_result, hs_response, status_code):
    if request_result == False and status_code == 500:
        status = falcon.HTTP_500
        content_type = falcon.MEDIA_JSON

    elif request_result == False and status_code == 400:
        status = falcon.HTTP_400
        content_type = falcon.MEDIA_JSON
    else:
        submission_id = hs_response
        status = falcon.HTTP_202
        content_type = falcon.MEDIA_JSON
        text = json.dumps({"submission_id": submission_id})
    return status, content_type, text


def send_response(resp, status, content_type, text):
    resp.status = status
    resp.content_type = content_type
    resp.text = text


class HealthCheck(proxylogger.Logger):

    def on_get(self, req, resp):
        """Handles HealthCheck"""
        resp.status = falcon.HTTP_204


class Document(proxylogger.Logger):

    def on_post(self, req, resp, logger=proxylogger.Logger.logger):

        """Handles Hyperscience Submission"""

        # creates unique_id for logging system, using logging.Filter and separate Class
        logger.addFilter(proxylogger.AppFilter())
        logger.info("Request received")
        try:
            dms_raw_data = json.load(req.bounded_stream)
        except Exception as exception:
            logger.info("Exception raised while parsing JSON")
            send_response(resp, falcon.HTTP_400, falcon.MEDIA_JSON,
                          json.dumps({"message": "Exception raised while parsing JSON"}))
        else:
            logger.info("Valid JSON received")
            if not contains_mandatory_data(dms_raw_data):
                logger.info("Data Validation Complete - Missing/Empty mandatory JSON data")
                send_response(resp, falcon.HTTP_400, falcon.MEDIA_JSON,
                              json.dumps({"message": "JSON missing mandatory data"}))
            else:
                endpoint_url, headers, data = format_submission_data(dms_raw_data, logger)
                request_result, hs_response, status_code = post_payload(endpoint_url, headers, data)
                status, content_type, text = post_request_response(request_result, hs_response, status_code)
                send_response(resp=resp, status=status, content_type=content_type, text=text)


app = falcon.App()
app.add_route('/health', HealthCheck())
app.add_route('/icr/document', Document())
server = Server()
server.run_server(app)
