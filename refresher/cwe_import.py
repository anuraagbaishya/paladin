import requests
import zipfile
import xml.etree.ElementTree as ET
from typing import List, Optional
from models.models import Cwe
import logging
import os

logging.basicConfig(level=logging.INFO)


class CweImport:
    def __init__(self) -> None:
        self.zip_url = "https://cwe.mitre.org/data/xml/cwec_v4.17.xml.zip"
        self.zip_path = "cwec_v4.17.xml.zip"
        self.logger = logging.getLogger(__name__)

    def import_cwes(self) -> Optional[List[Cwe]]:
        try:
            response = requests.get(self.zip_url)
            with open(self.zip_path, "wb") as f:
                f.write(response.content)

            with zipfile.ZipFile(self.zip_path, "r") as zip_ref:
                zip_ref.extractall(".")
            xml_file = zip_ref.namelist()[0]

            tree = ET.parse(xml_file)
            root = tree.getroot()
            ns = {"cwe": "http://cwe.mitre.org/cwe-7"}

            documents = []
            for weakness in root.findall(".//cwe:Weakness", ns):
                cwe_id = int(weakness.attrib["ID"])
                name = weakness.attrib["Name"]
                documents.append(Cwe(cwe_id, name))

            os.remove(self.zip_path)
            os.remove(xml_file)

            return documents
        except Exception as e:
            self.logger.error(f"Error importing CWEs: {e}")
            return None
