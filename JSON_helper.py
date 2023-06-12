import json
from json.decoder import JSONDecodeError

class JSON_helper:
    def __init__(self, json_str: str):
        self.json_str = json_str

    def is_valid(self) -> bool:
        """
        Check if the json_str is a valid json string
        :return: True if valid, False otherwise
        """

        try:
            json.loads(self.json_str)
            return True
        except JSONDecodeError:
            return False

    def to_dict(self) -> dict:
        """
        Convert the json_str to a dict
        :return: dict
        """
        source_dict = json.loads(self.json_str)
        # strip all keys by making a copy of the dict
        stripped_dict = {}
        for key in source_dict.keys():
            stripped_dict[key.strip()] = source_dict[key]
        return stripped_dict

    def has_key(self, key: str) -> bool:
        """
        Check if the json_str has a key
        :param key: key to check
        :return: True if key exists, False otherwise
        """

        return key in self.to_dict()