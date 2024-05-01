import logging
import configparser
import re
import pandas
import json
import datetime
import enum
import pathlib
import py7zr

class EXTENSION(enum.Enum):
    LOG: str = '.log'
    PSR: str = '.psr'
    EGR: str = '.egr'
    EGRZ: str = '.egrz'

class TOOL(enum.Enum):
    PETS: str = 'PETS'
    POWERBAT: str = 'Power Bat'
    POWERCAT: str = 'Pwer Cat'
    PPS2: str = 'PPS2'
    PPSDC: str = 'PPS DC'
    PPSPCIE: str = 'PPS PCIe'
    PPTS2: str = 'PPTS2'
    PYPPS: str = 'PyPPS'

class File:

    extensions = {
        extension.value: extension
        for extension in EXTENSION
    }

    def __init__(self, file: str):
        self.file = pathlib.Path(file)
    
    @property
    def file_name(self):
        file_name = self.file.stem
        return file_name
    
    @property
    def extension(self):
        extension = self.file.suffix
        return self.extensions[extension]
    
    def convert(self, extension: EXTENSION):
        file = self.file.with_suffix(extension.value)
        file = File(file)
        return file

class Payload:

    tools = {
        tool.value: tool
        for tool in TOOL
    }

    def __init__(self, payload: dict):
        self.payload = payload
    
    @property
    def tool(self):
        payload_tool = self.payload['tool']
        tool = self.tools[payload_tool]
        return tool

class Controller:
    def __init__(self, file: File):
        self.file = file
    
    def process_file(self):
        if self.file.extension == EXTENSION.EGRZ:
            with py7zr.SevenZipFile(self.file.file, 'r') as zip_file:
                zip_file.extractall()
            file = self.file.convert(EXTENSION.EGR)
            return file
        else:
            return self.file
    
    def get_parser(self, payload: Payload):
        if payload.tool in (TOOL.PETS, TOOL.POWERBAT, TOOL.POWERCAT, TOOL.PPTS2,):
            parser_egr = Parser(self.file)
            return parser_egr
        
        elif payload.tool in (TOOL.PYPPS,):
            parser_log = Parser(self.file)
            return parser_log
        
        elif payload.tool in (TOOL.PPSDC, TOOL.PPSPCIE,):
            parser_psr = Parser(self.file)
            return parser_psr

class Parser:
    def __init__(self, file: File):
        self.time = str(datetime.datetime.now())
        self.file = file
        self.configuration = self.parse()

    def parse(self):
            # Create parser.
            configurations = configparser.ConfigParser(
                # Duplicated keys are allow.
                strict=False,
                # Empty Values are allow.
                allow_no_value=True,
                # Commments are allow.
                inline_comment_prefixes='#',
            )
            # Persist capital.
            configurations.optionxform = str
            # Set header pattern.
            pattern_symbols = r'\W+'
            pattern_header = r'(\w|\w+.*\w+)'
            configurations.SECTCRE = re.compile(
                f'^{pattern_symbols}(?P<header>{pattern_header}){pattern_symbols}$'
            )
            # Read file.
            lines = [f'[__DataEngineeringDefaultSection@{self.time}]\n']
            with open(self.file) as file:
                for line in file.readlines():
                    if not line.startswith('='):
                        lines.append(line)
            file = ('').join(lines)
            # Parse.
            configurations.read_string(file)
            return configurations
    
    def find(self, indices: dict = None, patterns: dict = None):
        # Generator for creating DataFrame of configurations.
        def _generator_configuration():
            for section in self.configuration:
                for key in self.configuration[section]:
                    value = self.configuration[section][key]
                    yield (section, key, value)
        # Create DataFrame.
        _configuration=pandas.DataFrame(
            [instance for instance in _generator_configuration()],
            columns=['section', 'key', 'value']
        ).set_index(['section', 'key'])
        if indices:
            for index_key, index_value in indices.items():
                _configuration = _configuration[_configuration.index.get_level_values(index_key) == index_value]
        elif patterns:
            _configuration = _configuration.filter(axis='index', **patterns)
        else:
            logging.warning('One of parameters indices and patterns is necessary.')
        return _configuration

if __name__ == '__main__':
    file = File('PD0016_0071_D_PowerCAT_Windows_PC_APC_S0_Test_DDS2TA.3-0090_480GB.egrz')
    controller = Controller(file)
    parser = controller.get_parser({'tool': 'PETS'})
    # Application One: Calculate Difference.
    for target in (
        'erase',
        'Power',
    ):
        before = pandas.Series(parser.configuration['System Info Before Test']).filter(like=target).apply(float)
        after = pandas.Series(parser.configuration['System Info After Test']).filter(like=target).apply(float)
        difference = (after - before).apply(abs)
        logging.info(target, difference)
    # Application Two: configuration Jsonization.
    jsonized_configuration = {
        section: {
            key: value
            for key, value in key_values.items()
        }
        for section, key_values in parser.configuration.items()
    }
    jsonized_configuration = json.dumps(jsonized_configuration)