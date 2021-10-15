import falcon
import proxylogger
from server_test import Server
import json
import requests
import logging


def post_payload(endpoint_url, headers, payload):

    try:
        test_quick_mocker = 'https://1hrjl6rb0l.api.quickmocker.com'  # api testing url
        response = requests.post(url=test_quick_mocker, headers=headers, data=payload, timeout=30)
        submission_id = response.json()['submission_id']
    except requests.exceptions.Timeout as tmoterr:
        # If a request times out, a Timeout exception is raised.
        return False, tmoterr
    except requests.exceptions.ConnectionError as cnxnerr:
        # In the event of a network problem (e.g. DNS failure, refused connection, etc)
        return False, cnxnerr
    except requests.exceptions.RequestException as err:
        # catastrophic error. bail.
        return False, err
    else:
        return True, submission_id


def validate_mandatory_data(raw_data):
    """Function will return False if mandatory is empty from json or has missing data"""
    print(raw_data)
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


def format_submission_data(raw_data):
    """Formats the data into correct format for HS submission creation"""
    base_url = "https://on-premise-server.yourcompany.com/"
    endpoint = "api/v5/submissions"
    endpoint_url = base_url + endpoint
    auth_token = "a22d533ebaa60ae5d46b2f0ea67532a4eb8e33be"
    headers = {'Authorization': 'Token ' + auth_token}
    machine_only = "false"

    if not validate_mandatory_data(raw_data):
        return False
    else:
        payload = {
            "document": raw_data["file-location"]
        }
        if "metadata" not in raw_data or raw_data["metadata"] == {}:
            # metadata missing/empty
            print('metadata missing')
        else:
            payload["metadata"] = raw_data["metadata"]
            payload["metadata"]["queue_name"] = f"{raw_data['source']}_{raw_data['document-type']}"
            payload = json.dumps(payload)
            print('metadata not missing')
        return endpoint_url, headers, payload

class Logger:
    # initialising unique id logging system
    logger = logging.getLogger(__name__)
    syslog = logging.FileHandler('testing.log')
    formatter = logging.Formatter('%(app_name)s  %(asctime)s  %(message)s')
    syslog.setFormatter(formatter)
    logger.setLevel(logging.INFO)
    logger.addHandler(syslog)

class HealthCheck(Logger):

    def on_get(self, req, resp, logger=Logger.logger):

        """Handles DMS HealthCheck GET Request"""
        # creates unique_id for logging system, using logging.Filter and separate Class
        logger.addFilter(proxylogger.AppFilter())
        logger.info('test')
        resp.status = falcon.HTTP_200
        resp.content_type = falcon.MEDIA_TEXT
        resp.text = (f"\nHEY THE PROXY IS ALIVE AND WELL\n")
        logger.info('testing')

class Document(Logger):

    def on_post(self, req, resp, logger=Logger.logger):
        """Handles DMS Submission Data Post Request"""

        try:
            dms_raw_data = json.load(req.bounded_stream)
            logger.info('testing3')
        except Exception as exception:
            resp.status = falcon.HTTP_400
            resp.content_type = falcon.MEDIA_JSON
            resp.text = json.dumps({"message": "Invalid JSON"})
            print(resp.text)
        else:
            parsed_data = format_submission_data(dms_raw_data)
            if parsed_data == False:
                resp.status = falcon.HTTP_400
                resp.content_type = falcon.MEDIA_JSON
                resp.text = json.dumps({"message": "JSON missing mandatory data"})
                print(resp.text)
            else:
                print("we have all the required fields - here they are...")
                endpoint_url, headers, payload = parsed_data
                post_request, hs_response = post_payload(endpoint_url, headers, payload)
                if post_request == False:
                    print(hs_response, "400")
                    resp.status = falcon.HTTP_400
                    resp.content_type = falcon.MEDIA_JSON
                    resp.text = json.dumps({"error": resp.status})
                else:
                    print(hs_response, "200")
                    submission_id = hs_response
                    resp.status = falcon.HTTP_202
                    resp.content_type = falcon.MEDIA_JSON
                    resp.text = json.dumps({"submission_id": submission_id})


app = falcon.App()
app.add_route('/get', HealthCheck())
app.add_route('/post', Document())
server = Server()
server.run_server(app)
