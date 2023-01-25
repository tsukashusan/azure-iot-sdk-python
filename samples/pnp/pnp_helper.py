# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""
This module knows how to convert device SDK functionality into a plug and play functionality.
These methods formats the telemetry, methods, properties to plug and play relevant telemetry,
command requests and pnp properties.
"""
from azure.iot.device import Message
from azure.core.exceptions import AzureError
from azure.storage.blob import BlobClient
import json
import os
import datetime
import logging


class PnpProperties(object):
    def __init__(self, top_key, **kwargs):
        self._top_key = top_key
        for name in kwargs:
            setattr(self, name, kwargs[name])

    def _to_value_dict(self):
        all_attrs = list((x for x in self.__dict__ if x != "_top_key"))
        inner = {key: {"value": getattr(self, key)} for key in all_attrs}
        return inner

    def _to_simple_dict(self):
        all_simple_attrs = list((x for x in self.__dict__ if x != "_top_key"))
        inner = {key: getattr(self, key) for key in all_simple_attrs}
        return inner


async def create_telemetry(telemetry_msg, component_name=None, device_client: any = None, store_blob: bool = False, json_list: list = None, file_path_prefix: str = None, chunk_size: int = 0):
    """
    Function to create telemetry for a plug and play device. This function will take the raw telemetry message
    in the form of a dictionary from the user and then create a plug and play specific message.
    :param telemetry_msg: A dictionary of items to be sent as telemetry.
    :param component_name: The name of the device like "sensor"
    :return: The message.
    """
    msg = Message(json.dumps(telemetry_msg))
    if store_blob and json_list is not None:
        await store_json(device_client=device_client, json=msg.data, json_list=json_list, file_path_prefix=file_path_prefix, chunk_size=chunk_size)
    
    msg.content_encoding = "utf-8"
    msg.content_type = "application/json"
    if component_name:
        msg.custom_properties["$.sub"] = component_name
    return msg


def create_reported_properties(component_name=None, **prop_kwargs):
    """
    Function to create properties for a plug and play device. This method will take in the user properties passed as
    key word arguments and then creates plug and play specific reported properties.
    :param component_name: The name of the component. Like "deviceinformation" or "sdkinformation"
    :param prop_kwargs: The user passed keyword arguments which are the properties that the user wants to update.
    :return: The dictionary of properties.
    """
    if component_name:
        print("Updating pnp properties for {component_name}".format(component_name=component_name))
    else:
        print("Updating pnp properties for root interface")
    prop_object = PnpProperties(component_name, **prop_kwargs)
    inner_dict = prop_object._to_simple_dict()
    if component_name:
        inner_dict["__t"] = "c"
        prop_dict = {}
        prop_dict[component_name] = inner_dict
    else:
        prop_dict = inner_dict

    print(prop_dict)
    return prop_dict


def create_response_payload_with_status(command_request, method_name, create_user_response=None):
    """
    Helper method to create the payload for responding to a command request.
    This method is used for all method responses unless the user provides another
    method to construct responses to specific command requests.
    :param command_request: The command request for which the response is being sent.
    :param method_name: The method name for which we are responding to.
    :param create_user_response: Function to create user specific response.
    :return: The response payload.
    """
    if method_name:
        response_status = 200
    else:
        response_status = 404

    if not create_user_response:
        result = True if method_name else False
        data = "executed " + method_name if method_name else "unknown method"
        response_payload = {"result": result, "data": data}
    else:
        response_payload = create_user_response(command_request.payload)

    return (response_status, response_payload)


def create_reported_properties_from_desired(patch):
    """
    Function to create properties for a plug and play device. This method will take in the desired properties patch.
    and then create plug and play specific reported properties.
    :param patch: The patch of desired properties.
    :return: The dictionary of properties.
    """
    print("the data in the desired properties patch was: {}".format(patch))

    ignore_keys = ["__t", "$version"]
    component_prefix = list(patch.keys())[0]
    values = patch[component_prefix]
    print("Values received are :-")
    print(values)

    version = patch["$version"]
    inner_dict = {}

    if hasattr(values, 'items'):
        for prop_name, prop_value in values.items():
            if prop_name in ignore_keys:
                continue
            else:
                inner_dict["ac"] = 200
                inner_dict["ad"] = "Successfully executed patch"
                inner_dict["av"] = version
                inner_dict["value"] = prop_value
                values[prop_name] = inner_dict
    else:
        print("values not have attributes items. values=%s" % values)

    properties_dict = dict()
    if component_prefix:
        properties_dict[component_prefix] = values
    else:
        properties_dict = values

    return properties_dict

async def store_blob(device_client: any, file_name: str):
    try:
    # Get the storage info for the blob
        blob_name = os.path.basename(file_name)
        blob_info = await device_client.get_storage_info_for_blob(blob_name)
        sas_url = "https://{}/{}/{}{}".format(
            blob_info["hostName"],
            blob_info["containerName"],
            blob_info["blobName"],
            blob_info["sasToken"]
        )

        print("\nUploading file: {} to Azure Storage as blob: {} in container {}\n".format(file_name, blob_info["blobName"], blob_info["containerName"]))

        # Upload the specified file
        with BlobClient.from_blob_url(sas_url) as blob_client:
            with open(file_name, "rb") as f:
                result = blob_client.upload_blob(f, overwrite=True)
                return (True, result, blob_info)

    except FileNotFoundError as ex:
        # catch file not found and add an HTTP status code to return in notification to IoT Hub
        ex.status_code = 404
        return (False, ex, blob_info)

    except AzureError as ex:
        # catch Azure errors that might result from the upload operation
        logging.error(ex)
        return (False, ex, blob_info)
    except Exception as ex:
        logging.error(ex)
        return (False, ex, blob_info)

async def store_json(device_client: any, json: str, json_list: list, file_path_prefix: str, chunk_size: int):
    if len(json_list) < chunk_size:
        json_list.append(json)
    else:
        try:
            json_list.append(json)
            file_path = file_path_prefix % datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    
            with open(file_path, mode='a') as f:
                count = 0
                for line in json_list:
                    if count < len(json_list) -1:
                        f.write("%s\n" % line)
                    else:
                        f.write("%s" % line)
                    count = count + 1
    
            success, result, storage_info  = await store_blob(device_client=device_client, file_name=file_path)
            if success == True:
                json_list.clear()
                os.remove(file_path)
                print("Upload succeeded. Result is: \n") 
                print(result)

                await device_client.notify_blob_upload_status(
                    storage_info["correlationId"], True, 200, "OK: {}".format(file_path)
                )
                return

            else :
                # If the upload was not successful, the result is the exception object
                json_list.clear()
                os.remove(file_path)
                logging.error("Upload failed. Exception is: \n") 
                logging.error(result)
                await device_client.notify_blob_upload_status(
                    storage_info["correlationId"], False, result.status_code, str(result)
                )
                return
        except Exception as ex:
            json_list.clear()
            os.remove(file_path)
            logging.error("\nException:")
            logging.error(ex)
            raise ex

