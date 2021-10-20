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
    except requests.exceptions.Timeout as timeout_err:
        # If a request times out, a Timeout exception is raised.
        return False, timeout_err
    except requests.exceptions.ConnectionError as cnxn_err:
        # In the event of a network problem (e.g. DNS failure, refused connection, etc)
        return False, cnxn_err
    except requests.exceptions.RequestException as err:
        # catastrophic error. bail.
        return False, err
    else:
        return True, submission_id


def validate_mandatory_data(raw_data):

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

    logger.info("Formatting DMS Data...")
    base_url = "https://on-premise-server.yourcompany.com/"
    endpoint = "api/v5/submissions"
    endpoint_url = base_url + endpoint
    auth_token = "a22d533ebaa60ae5d46b2f0ea67532a4eb8e33be"
    headers = {'Authorization': 'Token ' + auth_token}

    logger.info("Validating mandatory JSON data...")
    if not validate_mandatory_data(raw_data):
        return False
    else:
        logger.info("Data Validation Complete - JSON Contains all mandatory data")
        data = {
            "document": raw_data["file-location"]
        }
        logger.info("Checking for metadata fields...")
        if "metadata" not in raw_data or raw_data["metadata"] == {}:
            logger.info("Metadata missing/empty - continuing without")
        else:
            logger.info("Metadata found...formatting into Hyperscience payload")
            raw_data["metadata"]["queue_name"] = f"{raw_data['source']}_{raw_data['document-type']}"
            data["metadata"] = json.dumps(raw_data["metadata"])
            print(json.dumps(data, indent=4, sort_keys=True))
        return endpoint_url, headers, data


class Logger:

    """Initialises a logger"""

    logger = logging.getLogger(__name__)
    syslog = logging.FileHandler('testing.log')
    formatter = logging.Formatter('%(unique_id)s  %(asctime)s  %(message)s')
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

        # creates unique_id for logging system, using logging.Filter and separate Class
        logger.addFilter(proxylogger.AppFilter())
        try:
            dms_raw_data = json.load(req.bounded_stream)
        except Exception as exception:
            logger.info("Invalid JSON Received, responding back to DMS")
            resp.status = falcon.HTTP_400
            resp.content_type = falcon.MEDIA_JSON
            resp.text = json.dumps({"message": "Invalid JSON"})
        else:
            logger.info("JSON Received")
            parsed_data = format_submission_data(dms_raw_data, logger)
            if not parsed_data:
                logger.info("Data Validation Complete - Missing/Empty mandatory JSON data")
                resp.status = falcon.HTTP_400
                resp.content_type = falcon.MEDIA_JSON
                resp.text = json.dumps({"message": "JSON missing mandatory data"})
            else:
                logger.info("HS Payload formatted")
                endpoint_url, headers, data = parsed_data
                logger.info("Posting Payload to Hyperscience...")
                post_request, hs_response = post_payload(endpoint_url, headers, data)
                if not post_request:
                    logger.info(f"POST failed due to {hs_response}")
                    resp.status = falcon.HTTP_400
                    resp.content_type = falcon.MEDIA_JSON
                    resp.text = json.dumps({"error": resp.status})
                else:
                    submission_id = hs_response
                    logger.info(f"POST successful, responding to DMS with submission_id...")
                    resp.status = falcon.HTTP_202
                    resp.content_type = falcon.MEDIA_JSON
                    resp.text = json.dumps({"submission_id": submission_id})
                    logger.info(f"Case Complete - responded to DMS with submission_id - ({submission_id})")


app = falcon.App()
app.add_route('/get', HealthCheck())
app.add_route('/post', Document())
server = Server()
server.run_server(app)
