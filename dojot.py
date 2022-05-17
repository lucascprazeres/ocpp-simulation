# -*- coding: utf-8 -*-
"""
This module provide functions to send and recover data from Dojot plataform.

.. codeauthor:: João Rodrigo Muniz <rodrigosilvamuniz@gmail.com>

Example
-------
The best way to use this module functionalities is by using Dojot class.

>>> dojot = Dojot(user="admin", password="admin", ip="192.168.0.111", http_port=8000, mqtt_port=1883)

If you are using the default templates file, you can create them on Dojot by using:

>>> dojot.create_all_templates(monthly=True)

The default file can be edited on :file:`comm/iot/templates.json`.

Similarly, you can create all devices using:

>>> dojot.create_all_devices()

The default file can be edited on :file:`comm/iot/devices.json`.

To get information of an specific device, you can use:

>>> dojot.get_device("fv_ceamazon_1")

To send data to a device, you can use:

>>> data = {
>>>     "tensao": 120.0,
>>>     "corrente": 10.0,
>>>     "potencia": 1270.0,
>>>     "eficiencia_conversao": 1.0,
>>>     "fator_dimensionamento_inversor": 1.0,
>>>     "fator_capacidade": 1.0,
>>>     "energia_especifica": 1.0,
>>>     "produtividade_sistema": 1.0,
>>>     "produtividade_referencia": 1.0,
>>>     "rendimento_global": 1.0,
>>>     "intensidade_instalacao": 1.0,
>>>     "timestamp": "2020-02-05T20:38:54.741000Z"
>>> }
>>> dojot.send_data_to_device(device_label="fv_ceamazon_1", data=data)

You can recover the data from a device by using:

>>> dojot.get_device_history(device_label="fv_ceamazon_1", last_n=10)
"""

import requests
import json
import paho.mqtt.publish as publish

from datetime import datetime
from os.path import abspath, dirname, join

from date_tools import (get_localized_datetime, get_localized_current_datetime, convert_from_string, get_timezone,
                              convert_timezone, convert_to_utc)
from exception import (TemplateNotExists, TemplateAlreadyExists, DeviceNotExists, DeviceAlreadyExists,
                                  DataTemplateMismatch)


default_timezone = "America/Belem"
"""str: Timezone string to use on datetime objects."""


override_stdout = None


def set_stdout(stdout):
    global override_stdout
    override_stdout = stdout


def get_templates(path=None):
    """
    Function to get the default templates from the file :file:`comm/iot/templates.json`. It gets the file on ``path``
    and convert it to a dict.

    Parameters
    ----------
    path : str
        Path to the templates json file.

    Returns
    -------
    dict
        Dict containing all templates with the format::

             {
                 "template": {
                     "dynamic": {
                         "variable": {"type": "object"}
                     },
                     "static": {
                         "localizacao": {"type": "geo:point", "value": "lat,long"}
                     }
                 }
            }
    """
    if path is None:
        path = dirname(abspath(__file__))
        templates_json = join(path, "templates.json")
    else:
        templates_json = str(path)

    with open(templates_json, "r") as json_file:
        templates = json.load(json_file)

    return templates


def get_devices(path=None):
    """
    Function to get the default devices from the file :file:`comm/iot/devices.json`. It gets the file on ``path``
    and convert it to a dict.

    Parameters
    ----------
    path : str
        Path to the devices json file.

    Returns
    -------
    dict
        Dict containing all devices separated by template with the format::

            "template_label": [
                {
                    "name": "device_1",
                    "db_id": 1,
                    "group": "group_name",
                    "group_id": group_id,
                    "static_values": {
                        "localizacao": "-1.4668331,-48.4469696",
                        "endereco": "Endereco"
                    }
                }
            ]
    """
    if path is None:
        path = dirname(abspath(__file__))
        devices_json = join(path, "devices.json")
    else:
        devices_json = str(path)

    with open(devices_json, "r") as json_file:
        devices = json.load(json_file)

    return devices


def get_jwt(path=None):
    """
    Function to get the current jwt from the file :file:`comm/iot/.jwt.json`. It gets the file on ``path``
    and convert it to a dict.

    Parameters
    ----------
    path : str
        Path to the jwt json file.

    Returns
    -------
    dict
        Dict containing the jwt.
    """
    if path is None:
        path = dirname(abspath(__file__))
        jwt_file_path = join(path, ".jwt.json")
    else:
        jwt_file_path = str(path)

    try:
        with open(jwt_file_path, "r") as json_file:
            jwt_dict = json.load(json_file)

        last_updated = datetime.fromtimestamp(jwt_dict["last_updated"], tz=get_timezone(default_timezone))
        diff = get_localized_current_datetime(timezone=default_timezone) - last_updated
        diff_hours = diff.total_seconds() / 3600
        if diff_hours > 24:
            jwt_dict = None

    except FileNotFoundError:
        jwt_dict = None

    return jwt_dict


def set_jwt(jwt, path=None):
    """
    Function to set the current jwt value to the file :file:`comm/iot/.jwt.json`.

    Parameters
    ----------
    jwt : str
        Access token.
    path : str
        Path to the jwt json file.

    Returns
    -------
    None
        Just save the file.
    """
    if path is None:
        path = dirname(abspath(__file__))
        jwt_file_path = join(path, ".jwt.json")
    else:
        jwt_file_path = str(path)

    jwt_dict = {"jwt": jwt, "last_updated": get_localized_current_datetime(timezone=default_timezone).timestamp()}

    with open(jwt_file_path, "w") as json_file:
        json.dump(jwt_dict, json_file)


def convert_history_to_dict(history):
    """
    Convert the data returned by the history API function to a dict with correct variable type conversion.

    Parameters
    ----------
    history : dict
        Dict that was returned by history API.

    Returns
    -------
    dict
        Dict with converted numeric types.
    """
    history_dict = {}
    for attr, values in history.items():
        history_dict[attr] = {}
        history_dict[attr]["datetime"] = []
        history_dict[attr]["value"] = []
        for value in values:
            try:
                history_dict[attr]["datetime"].append(
                    convert_timezone(
                        datetime_obj=convert_from_string(datetime_str=value["timestamp"], template="%Y-%m-%dT%H:%M:%S.%fZ"),
                        tz_to=default_timezone
                    )
                )
            except ValueError:
                history_dict[attr]["datetime"].append(
                    convert_timezone(
                        datetime_obj=convert_from_string(datetime_str=value["timestamp"], template="%Y-%m-%dT%H:%M:%SZ"),
                        tz_to=default_timezone
                    )
                )
            history_dict[attr]["value"].append(convert_to_correct_type(value=value["value"], timezone=default_timezone))
    return history_dict


def convert_to_correct_type(value, timezone=None, strptime_template="%Y-%m-%d %H:%M:%S"):
    """
    Convert an individual value from a generic str to the correct data format to be used on SIMA Core dicts.

    The choice of the appropriate format depends on the content of the string. If the string is numeric and does not
    have a numeric separator, the int type is selected. If the string is numeric and has a numeric separator, the float
    type is selected. If it is a date string with the format "% Y-% m-% d% H:% M:% S", then the datetime type is
    selected. If it can be converted to a dict, this format will be used. Otherwise, type str is selected.

    Parameters
    ----------
    value : str
        A generic value in str format.
    timezone : str
        Timezone name to be used if the value is detected as a date. If you have
        `pytz package <https://pypi.org/project/pytz/>`_, you can get a list of all availables timezones by using::

            >>> import pytz
            >>> pytz.all_timezones

    strptime_template : str
        Template to use on converting string to datetime

    Returns
    -------
    int/float/datetime/dict/str
        Value converted to correct type.
    """
    try:
        value = int(value)
    except (ValueError, TypeError):
        try:
            value = float(value)
        except (ValueError, TypeError):
            try:
                value = convert_from_string(datetime_str=value, template=strptime_template)
                if timezone is None:
                    value = get_localized_datetime(datetime_object=value)
                else:
                    value = get_localized_datetime(datetime_object=value, timezone=timezone)
            except (ValueError, TypeError):
                try:
                    value = dict(value)
                except (ValueError, TypeError):
                    value = str(value)
    return value


class Dojot(object):
    """
    Class to be used to send and recover information from Dojot.

    Attributes
    ----------
    user : str
        User to access Dojot API.
    password : str
        Password to access Dojot API.
    ip : str
        IP address of the Dojot host.
    http_port : int
        Port to use to access Dojot HTTP.
    mqtt_port : int
        Port to use to connect across MQTT protocol.
    templates : dict
        Dict with all templates.
    jwt : str
        Token access to Dojot API.
    """
    def __init__(self, user, password, ip, http_port, mqtt_port, templates=None, stdout=None):
        """
        Constructor of Dojot class.

        Parameters
        ----------
        user : str
            Username to be used on Dojot login.
        password : str
            Password of the respective ``user``.
        ip : str
            IP address of the machine where Dojot is hosted.
        http_port : int
            Port to use on HTTP requests. Usually is 8000.
        mqtt_port : int
            Port to use on MQTT publishing. Usually is 1883.
        templates : dict
            Dict containing all templates information to be used. Follow the structure of file
            :file:`comm/iot/templates.json`.
        """
        self.user = user
        self.password = password
        self.ip = ip
        self.http_port = http_port
        self.mqtt_port = mqtt_port
        self.templates = templates if templates is not None else get_templates()
        jwt_dict = get_jwt()
        if jwt_dict is not None:
            self.jwt = jwt_dict["jwt"]
        else:
            self.jwt = self.request_token()
            set_jwt(jwt=self.jwt)
        set_stdout(stdout=stdout)

    def request_token(self):
        """
        Request the access token for ``user`` with ``password``.

        Returns
        -------
        str
            The API access token, usually called jwt.
        """
        url_request_token = "http://" + self.ip + ":" + str(self.http_port) + "/auth"

        headers = {"Content-Type": "application/json"}

        data = "{\"username\": \"" + self.user + "\", \"passwd\" : \"" + self.password + "\"}"

        request = requests.post(url=url_request_token, headers=headers, data=data)

        jwt = json.loads(request.__dict__["_content"].decode("utf-8"))["jwt"]  # Convert the incoming string into a dict
        # and then get the jwt

        return jwt

    def create_template(self, label, attrs):
        """
        Create the ``label`` template with attributes ``attrs`` at Dojot and then returns the response.

        Parameters
        ----------
        label : str
            Name (or label) of the template to be created.
        attrs : list
            List of dicts containing all template attributes with the following format::

                [{"label": "tensao_rms", "type": "dynamic", "value_type": "object"},
                 {"label": "tensao_bateria_cc", "type": "dynamic", "value_type": "float"}]

        Returns
        -------
        dict
            The response of the API request.

        Raises
        ------
        TemplateAlreadyExists
            If the template label already exists on the current Dojot platform.


        .. note::
            See also :meth:`.Dojot.create_template_from_dict` and :meth:`.Dojot.create_all_templates` for other ways to
            create templates.
        """
        url_create_template = "http://" + self.ip + ":" + str(self.http_port) + "/template"

        headers = {"Authorization": "Bearer {0}".format(self.jwt), "Content-Type": "application/json"}

        device_template = {
            "label": label,
            "attrs": attrs
        }

        data = json.dumps(device_template, indent=4)

        template_exist = (self.get_template_id_by_label(label=label) is not None)

        if not template_exist:
            request = requests.post(url=url_create_template, headers=headers, data=data)

            response = json.loads(request.__dict__["_content"].decode("utf-8"))

            return response
        else:
            message = "Template with label {0} already exists on Dojot".format(label)
            error = "A template already created on Dojot can not be created again"
            raise TemplateAlreadyExists(message=message, error=error)

    def create_template_from_dict(self, label, template_dict, monthly=False):
        """
        Create a template on Dojot from a specific dict structure.

        The structure follows that define on :file:`comm/iot/templates.json`::

            {
                "dynamic": {
                    "tensao_rms": {"type": "object"},
                    "tensao_bateria_cc": {"type": "float"}
                },
                "static": {
                    "endereco": {"type": "string", "value": "Prédio de Exemplo"},
                    "localizacao": {"type": "geo:point", "value": "-1.4668331,-48.4469696"}
                },
                "monthly": {
                    "drp": {"type":  "object"},
                    "drc": {"type":  "object"}
                }
            }

        Parameters
        ----------
        label : str
            Name (or label) of the template to be created.
        template_dict : dict
            Dict with all attributes of the template separated by ``dynamic``, ``static`` and ``monthly``
        monthly : bool
            If True will create a virtual device template with the monthly values of the defined variables in
            ``template_dict``, do not create it otherwise.

        Returns
        -------
        None
            Do not return, just create the templates on Dojot.

        Raises
        ------
        TemplateAlreadyExists
            If one of the templates to be created already exists on current Dojot platform.
        """
        attrs = []

        for attr, attr_param in template_dict["dynamic"].items():
            attrs.append(
                {"label": attr, "type": "dynamic", "value_type": attr_param["type"]}
            )

        for attr, attr_param in template_dict["static"].items():
            attrs.append(
                {"label": attr, "type": "static", "value_type": attr_param["type"], "static_value": attr_param["value"]}
            )

        template_exist = False
        monthly_template_exist = False

        try:
            self.create_template(label=label, attrs=attrs)
        except TemplateAlreadyExists:
            template_exist = True

        monthly_label = "{0}_mensal".format(label)
        if monthly:
            attrs = []
            for attr, attr_param in template_dict["monthly"].items():
                attrs.append(
                    {"label": attr, "type": "dynamic", "value_type": attr_param["type"]}
                )
            try:
                self.create_template(label=monthly_label, attrs=attrs)
            except TemplateAlreadyExists:
                monthly_template_exist = True

        error = "A template already created on Dojot can not be created again"
        if template_exist and monthly_template_exist:
            message = "Templates with labels {0} and {1} already exists on Dojot".format(label, monthly_label)
            raise TemplateAlreadyExists(message=message, error=error)
        elif template_exist:
            message = "Template with label {0} already exists on Dojot".format(label)
            raise TemplateAlreadyExists(message=message, error=error)
        elif monthly_template_exist:
            message = "Template with label {0} already exists on Dojot".format(monthly_label)
            raise TemplateAlreadyExists(message=message, error=error)

    def create_all_templates(self, monthly=False):
        """
        Create all templates from :file:`comm/iot/templates.json`.

        Parameters
        ----------
        monthly : bool
            If True will create all virtual devices templates with the monthly values of the corresponding variables,
            do not create it otherwise.

        Returns
        -------
        None
            Do not return, just create the templates on Dojot.


        Warnings
        --------
            If one of the templates to be created already exists on Dojot it will be ignored completely.
            No errors or signals will be raised, so be careful when using this function in a Dojot already with
            devices, no information will be overwritten.
        """
        for template, template_dict in self.templates.items():
            try:
                self.create_template_from_dict(label=template, template_dict=template_dict, monthly=monthly)
            except TemplateAlreadyExists:
                pass

    def get_all_templates_id(self):
        """
        Get all templates in the structure of::

            {"template_label": template_id}

        Returns
        -------
        dict
            A dict containing all templates currently on Dojot.
        """
        url_templates = "http://" + self.ip + ":" + str(self.http_port) + "/template?page_size=999999&sortBy=label"

        headers = {"Authorization": "Bearer {0}".format(self.jwt)}

        request = requests.get(url=url_templates, headers=headers)

        request = json.loads(request.__dict__["_content"].decode("utf-8"))

        template_id = {}
        for template in request["templates"]:
            template_id[template["label"]] = template["id"]

        return template_id

    def get_template_id_by_label(self, label):
        """
        Get the template id of a specific label.

        Parameters
        ----------
        label : str
            Label of the template to be searched on Dojot.

        Returns
        -------
        int/None
            The template id if the label exists on Dojot, else None.
        """
        try:
            templates = self.get_all_templates_id()
            template_id = templates[label]
        except KeyError:
            return None
        else:
            return template_id

    def get_template(self, template_label):
        """
        Get all information of a specific template.

        Parameters
        ----------
        template_label : str
            Label of the template.

        Returns
        -------
        dict
            The response of the template request.

        Raises
        ------
        TemplateNotExists
            If the template do not exists on current Dojot platform.
        """
        template_id = self.get_template_id_by_label(label=template_label)

        template_exist = (template_id is not None)

        if template_exist:
            url_template = "http://" + self.ip + ":" + str(self.http_port) + "/template/" + str(template_id)

            headers = {"Authorization": "Bearer {0}".format(self.jwt)}

            request = requests.get(url=url_template, headers=headers)

            response = json.loads(request.__dict__["_content"].decode("utf-8"))

            return response
        else:
            message = "Template with label {0} do not exists on Dojot".format(template_label)
            error = "A template not created can not be accessed"
            raise TemplateNotExists(message=message, error=error)

    def template_exists(self, label):
        """
        Check if the template exists on Dojot.

        Parameters
        ----------
        label : str
            Label of the template to be checked.

        Returns
        -------
        bool
            True if the template exists, Else otherwise.
        """
        template_id = self.get_template_id_by_label(label=label)
        if template_id is None:
            return False
        else:
            return True

    def delete_template(self, label):
        """
        Delete a specific template from Dojot.

        Parameters
        ----------
        label : str
            Label of the template to be deleted.

        Returns
        -------
        dict
            The response of the API request.

        Raises
        ------
        TemplateNotExists
            If the template to be deleted do not exist on Dojot.
        """
        template_id = self.get_template_id_by_label(label=label)

        template_exists = (template_id is not None)

        if template_exists:
            url_delete_template = "http://" + self.ip + ":" + str(self.http_port) + "/template/" + str(template_id)

            headers = {"Authorization": "Bearer {0}".format(self.jwt)}

            request = requests.delete(url=url_delete_template, headers=headers)

            response = json.loads(request.__dict__["_content"].decode("utf-8"))

            return response
        else:
            message = "Template with label {0} do not exists on Dojot".format(label)
            error = "A template not created on Dojot can not be deleted"
            raise TemplateNotExists(message=message, error=error)

    def delete_all_templates(self):
        """
        Delete all templates from Dojot.

        Returns
        -------
        None
            Just remove the templates.
        """
        template_id = self.get_all_templates_id()

        for label in template_id.keys():
            try:
                self.delete_template(label=label)
            except TemplateNotExists:
                pass

    def create_device(self, device_name, template_label, static_values=None):
        """
        Create a device on Dojot platform.

        Each device must have just one template associated to it.

        If you have defined ``static_values``, it will be updated using :meth:`comm.iot.dojot.update_static`.

        Parameters
        ----------
        device_name : str
            The device name (or device label).
        template_label : str
            Label of the template to be used.
        static_values : dict
            Dict containing the values of static attributes in the following format::

                {
                    "attr_1": "value_1",
                    "attr_2": value_2
                }
        Returns
        -------
        dict
            The response of the device creation request

        Raises
        ------
        DeviceAlreadyExists
            If the device already exists on Dojot.
        TemplateNotExists
            If the template to be used do not exists on Dojot.
        """
        template_id = self.get_template_id_by_label(template_label)

        template_exist = (template_id is not None)

        if template_exist:
            url_create_device = "http://" + self.ip + ":" + str(self.http_port) + "/device"

            headers = {"Authorization": "Bearer {0}".format(self.jwt), "Content-Type": "application/json"}

            label = device_name

            device = {
                "label": label,
                "templates": [str(template_id)]
            }

            data = json.dumps(device, indent=4)

            device_id = self.get_device_id_by_label(label=label)

            device_exists = (device_id is not None)

            if not device_exists:
                request = requests.post(url=url_create_device, headers=headers, data=data)

                response = json.loads(request.__dict__["_content"].decode("utf-8"))

                if static_values is not None:  # Update the static attributes if it has been passed as argument
                    self.update_static(device_label=label, static_values=static_values)

                return response
            else:
                message = "Device with label {0} already exists on Dojot".format(label)
                error = "A device can not be created with the same label of an already created device"
                raise DeviceAlreadyExists(message=message, error=error)
        else:
            message = "Template with label {0} do not exists on Dojot".format(template_label)
            error = "A device can not be created without a valid Dojot template"
            raise TemplateNotExists(message=message, error=error)

    def create_complete_device(self, device_name, template_label, static_values=None):
        """
        Create a device and its virtual monthly device.

        The label of the devices will be: *<template_label>_<device_name>* and *<template_label>_mensal_<device_name>*.

        Parameters
        ----------
        device_name : str
            Name of the device.
        template_label : str
            Label of the template to be used on the default device. For the monthly device, it will be used
            *<template_label>_mensal_*.
        static_values : dict
            Dict containing the values of static attributes in the following format::

                {
                    "attr_1": "value_1",
                    "attr_2": value_2
                }

        Returns
        -------
        None
            Just create the devices.
        """
        self.create_device(device_name=device_name, template_label=template_label, static_values=static_values)
        template_label = "{0}_mensal".format(template_label)
        self.create_device(device_name=device_name, template_label=template_label, static_values=static_values)

    def create_all_devices(self, devices=None):
        """
        Create all devices from file :file:`comm/iot/devices.json`.

        Parameters
        ----------
        devices : dict/None
            The dict containing all devices separated by template information in the following format::

                "template_label": [
                    {
                        "name": "device_1",
                        "db_id": 1,
                        "group": "group_name",
                        "group_id": group_id,
                        "static_values": {
                            "localizacao": "-1.4668331,-48.4469696",
                            "endereco": "Endereco"
                        }
                    }
                ]

            Each item on template list will generate an entire new device and its corresponding monthly virtual device.

            If None, the default file :file:`comm/iot/devices.json` will be read.

        Returns
        -------
        None
            Just creates the devices.

        Warnings
        -----
            Pay attention to the ``devices`` parameter. As defined, one device on the SIMA's Dojot use just one template
            and so each item on template list will generate its own complete devices (default + monthly devices).
        """
        if devices is None:
            devices = get_devices()
        for template, devices_list in devices.items():
            for device in devices_list:
                device_name = device["name"]
                try:
                    print(f'creating device {device_name}')
                    self.create_device(device_name=device_name, template_label=template)
                except DeviceAlreadyExists:
                    pass

    def update_static(self, device_label, static_values):
        """
        Update the values of static parameters of the specified device_label.

        Parameters
        ----------
        device_label : str
            Complete label of the device to be updated.
        static_values : dict
            Dict containing the updated values of static parameters.

        Returns
        -------
        Dict
            The response of the update request.
        """
        device_id = self.get_device_id_by_label(label=device_label)

        template_id = self.get_device_template_id(device_label=device_label)

        url_update_static = "http://" + self.ip + ":" + str(self.http_port) + "/device/" + device_id

        headers = {"Authorization": "Bearer {0}".format(self.jwt), "Content-Type": "application/json"}

        device_info = self.get_device(device_label=device_label)  # Need to send all devices information, not just the
        # parameters to be updated. So, get all information and edit just the corresponding dict keys.

        static_attr = []
        for attr in device_info["attrs"][str(template_id)]:
            if attr["type"] == "static":
                static_attr.append(attr)  # Create a list of all static attributes of device_info

        data = {
            "attrs": [],
            "created": device_info["created"],
            "id": device_info["id"],
            "label": device_info["label"],
            "static_attrs": [],
            "status": "disabled",
            "tags": [],
            "templates": device_info["templates"]
        }  # Create a data with the same information from device_info but with an empty list of static attributes

        for attr in static_attr:  # For each static attribute into device_info...
            data["attrs"].append(  # ...insert into the data list of static attributes...
                {
                    "created": attr["created"],  # ...an attribute with the same previous information...
                    "id": attr["id"],
                    "is_static_overridden": attr["is_static_overridden"],
                    "label": attr["label"],
                    "metadata": [],
                    "static_value": static_values[attr["label"]],  # ... except the values that will be updated
                    "template_id": attr["template_id"],
                    "type": "static",
                    "value_type": attr["value_type"]
                }
            )

        data = json.dumps(data, indent=4)

        request = requests.put(url=url_update_static, headers=headers, data=data)

        response = json.loads(request.__dict__["_content"].decode("utf-8"))

        return response

    def get_all_devices_id(self, template_id):
        """
        Get all devices id as a dict with labels as keys.

        Returns
        -------
        dict
            A dict containing all devices id.
        """
        url_devices = "http://" + self.ip + ":" + str(self.http_port) + "/device/template/" + str(template_id) + "?page_size=999999"

        headers = {"Authorization": "Bearer {0}".format(self.jwt)}

        request = requests.get(url=url_devices, headers=headers)

        request = json.loads(request.__dict__["_content"].decode("utf-8"))

        device_id = {}
        for device in request["devices"]:
            device_id[device["label"]] = device["id"]

        return device_id

    def get_device_id_by_label(self, label):
        """
        Get the device id of a specific device.

        Parameters
        ----------
        label : str
            Label of the device to be searched.

        Returns
        -------
        str/None
            Device id of the device if founded, None otherwise.
        """
        try:
            devices = self.get_all_devices_id(63)
            device_id = devices[label]
        except KeyError:
            return None
        else:
            return device_id

    def get_device_label_by_id(self, device_id):
        """
        Get the device label of a specific device.

        Parameters
        ----------
        device_id : str
            ID of the device to be searched.

        Returns
        -------
        str/None
            Label of the device if founded, None otherwise.
        """
        devices = self.get_all_devices_id()
        device_label = None
        for label, dev_id in devices.items():
            if device_id == dev_id:
                device_label = label
                break
        return device_label

    def device_exists(self, label):
        """
        Check if a device exists.

        Parameters
        ----------
        label : str
            Label of the device to be checked.

        Returns
        -------
        bool
            True if the device exists on Dojot, False otherwise.
        """
        device_id = self.get_device_id_by_label(label=label)
        if device_id is None:
            return False
        else:
            return True

    def get_device(self, device_label):
        """
        Get all information of a specific device.

        Parameters
        ----------
        device_label : str
            Label of the device.

        Returns
        -------
        dict
            The response of the device request.

        Raises
        ------
        DeviceNotExists
            If the device do not exists on current Dojot platform.
        """
        device_id = self.get_device_id_by_label(label=device_label)

        device_exist = (device_id is not None)

        if device_exist:
            url_devices = "http://" + self.ip + ":" + str(self.http_port) + "/device/" + device_id

            headers = {"Authorization": "Bearer {0}".format(self.jwt)}

            request = requests.get(url=url_devices, headers=headers)

            response = json.loads(request.__dict__["_content"].decode("utf-8"))

            return response
        else:
            message = "Device with label {0} do not exists on Dojot".format(device_label)
            error = "A device not created can not be accessed"
            raise DeviceNotExists(message=message, error=error)

    def get_device_template_id(self, device_label):
        """
        Get the template id of a specific device.

        Parameters
        ----------
        device_label : str
            Label of the device to be searched.

        Returns
        -------
        int
            Template id of the device.
        """
        device = self.get_device(device_label=device_label)
        template_id = device["templates"][0]
        return template_id

    def get_device_template_label(self, device_label):
        """
        Get the template label of a specific device.

        Parameters
        ----------
        device_label : str
            Label of the device to be searched.

        Returns
        -------
        str
            Template label of the device.
        """
        template_id = self.get_device_template_id(device_label=device_label)
        templates = self.get_all_templates_id()
        template_label = list(filter(lambda t: templates[t] == template_id, list(templates.keys())))[0]
        return template_label

    def delete_device(self, device_label):
        """
        Delete a specific device from Dojot.

        Parameters
        ----------
        device_label : str
            Label of the device to be deleted.

        Returns
        -------
        dict
            The response of the delete request.

        Raises
        ------
        DeviceNotExists
            If the devices already do not exist.
        """
        device_id = self.get_device_id_by_label(label=device_label)

        device_exist = (device_id is not None)

        if device_exist:
            url_delete_device = "http://" + self.ip + ":" + str(self.http_port) + "/device/" + str(device_id)

            headers = {"Authorization": "Bearer {0}".format(self.jwt)}

            request = requests.delete(url=url_delete_device, headers=headers)

            response = json.loads(request.__dict__["_content"].decode("utf-8"))

            return response
        else:
            message = "Device with label {0} do not exists on Dojot".format(device_label)
            error = "A device not created can not be deleted"
            raise DeviceNotExists(message=message, error=error)

    def delete_all_created_devices(self):
        """
        Delete all devices currently on Dojot.

        Returns
        -------
        None
            Just delete devices.

        Warnings
        --------
        If some of the devices was deleted from Dojot GUI during the execution of this method, it will be ignored.
        """
        devices = get_devices()

        for template, device_list in devices.items():
            for device in device_list:
                try:
                    print(f"deleting device {device['name']}")
                    self.delete_device(device_label=device["name"])
                except DeviceNotExists:
                    pass

    def get_history(self, device_id, params):
        """
        Get data from the Dojot History API of a specific device.

        Parameters
        ----------
        device_id : str
            Device id of the device whose info will be recovered.
        params : dict
            Dict containing all the params to be sent onto the request.

        Returns
        -------
        dict
            Response of the history request.

        Warnings
        --------
        It is recommended to use the method :meth:`comm.iot.dojot.get_device_history` to get history because it is
        in a higher level of abstraction and supports more functionalities. In fact,
        :meth:`comm.iot.dojot.get_device_history` uses this method to make a request and post-process the data
        recovered.
        """
        url_device_history = "http://" + self.ip + ":" + str(self.http_port) + "/history/device/" + device_id + "/history"

        headers = {"Authorization": "Bearer {0}".format(self.jwt)}

        request = requests.get(url_device_history, headers=headers, params=params)

        response = request.json()

        return response

    def get_device_history(self, device_label, **kwargs):
        """
        Get the history of a specific device with ``device_label``. Convert the received data to a correctly dict
        representation.

        Parameters
        ----------
        device_label : str
            Label of the device whose data will be requested.
        **kwargs
            Arbitrary keyword arguments.

        Other Parameters
        ----------------
        last_n : int
            Number of last registered data to be recovered by history.
        date_from : str
            Start time of a time-based query as %Y-%m-%dT%H:%M:%S.%f%z.
        date_to : str
            End time of a time-based query as %Y-%m-%dT%H:%M:%S.%f%z.

        Returns
        -------
        dict
            Dict containing the requested data.

        Raises
        ------
        DeviceNotExists
            If the selected device do not exists on Dojot platform.
        """
        device_id = self.get_device_id_by_label(label=device_label)

        device_exist = (device_id is not None)

        if device_exist:
            template_label = self.get_device_template_label(device_label=device_label)

            attrs = list(self.templates[template_label]["dynamic"].keys())

            params = {"attr": attrs}

            last_n = kwargs.get("last_n", None)
            if last_n is not None:
                params["lastN"] = str(last_n)

            date_from = kwargs.get("date_from", None)
            if date_from is not None:
                params["dateFrom"] = str(date_from)

            date_to = kwargs.get("date_to", None)
            if date_to is not None:
                params["dateTo"] = str(date_to)

            response = self.get_history(device_id=device_id, params=params)

            history = convert_history_to_dict(history=response)

            return history
        else:
            message = "Device with label {0} do not exists on Dojot".format(device_label)
            error = "A device not created can not be accessed"
            raise DeviceNotExists(message=message, error=error)

    def send_data_to_device(self, device_label, data, check_attrs=False):
        """
        Send data to a defined device on Dojot using paho-mqtt publishing mechanisms.

        Parameters
        ----------
        device_label : str
            Label of the device to receive the data.
        data : dict
            Dict containing all data to be sent to device.
        check_attrs : bool
            Check if the ``data`` attributes match with the expected pattern from template before send. If True, do not
            send ``data`` if some parameter is missing or has incorrect name. If False, try to send it anyway.

        Returns
        -------
        None
            Do not return, just send the data.

        Raises
        ------
        DataTemplateMismatch
            If ``check_attrs`` is True and the data attributes do not match the expected pattern from defined templates.
        """
        device_id = self.get_device_id_by_label(label=device_label)

        template_label = self.get_device_template_label(device_label=device_label)

        if isinstance(data["timestamp"], datetime):  # If the data timestamp is a datetime object, convert it to a str
            data["timestamp"] = convert_to_utc(data["timestamp"])
            data["timestamp"] = data["timestamp"].strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        data_to_send = json.dumps(data)

        attrs_match = False

        if check_attrs:
            data_attr = sorted(list(data.keys()))
            data_attr.remove("timestamp")  # Ignore timestamp on comparing to the template

            template_attr = sorted(list(self.templates[template_label]["dynamic"].keys()))

            attrs_match = (data_attr == template_attr)  # Check if data and template attributes match

        if attrs_match or not check_attrs:  # Just send data if the attributes match or check_attrs is False
            topic = "{0}:{1}/attrs".format(self.user, device_id)

            publish.single(
                topic=topic,
                payload=data_to_send,
                hostname=self.ip,
                port=self.mqtt_port,
                client_id=f"{self.user}:{device_id}",
                qos=1,
                auth={
                    "username": f"{self.user}:{device_id}",
                    "password": device_id
                }
            )

        else:
            message = "The provided data do not match the expected pattern from defined templates"
            error = "Provided data and template expected pattern mismatch"
            raise DataTemplateMismatch(message=message, error=error)
