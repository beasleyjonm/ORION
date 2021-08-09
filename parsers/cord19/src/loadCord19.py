import os
import logging
import enum

from Common.utils import LoggingUtil, GetData
from Common.loader_interface import SourceDataLoader
from Common.extractor import Extractor
from Common.node_types import AGGREGATOR_KNOWLEDGE_SOURCES, ORIGINAL_KNOWLEDGE_SOURCE


# the data header columns for both nodes files are:
class NODESDATACOLS(enum.IntEnum):
    ID = 0
    CATEGORY = 1
    NAME = 2


# the data header columns for the SciBites edges file are:
class SBEDGESDATACOLS(enum.IntEnum):
    SUBJECT = 0
    OBJECT = 1
    ENRICHMENT = 5
    EFFECTIVE_PUBS = 6


# the data header columns for the SciGraph edges file are:
class SGEDGESDATACOLS(enum.IntEnum):
    SUBJECT = 0
    OBJECT = 1
    ENRICHMENT = 2
    EFFECTIVE_PUBS = 3


# the data header columns for covid phenotypes are:
class PHENOTYPESDATACOLS(enum.IntEnum):
    PHENOTYPE_NAME = 0
    PHENOTYPE_ID = 1
    PHENOTYPE_HP_NAME = 2


# the data header columns for drug trials:
class TRIALSDATACOLS(enum.IntEnum):
    DRUG_ID = 0
    PREDICATE = 1
    TARGET_ID = 2
    COUNT = 3


##############
# Class: cord19 data source loader
#
# Desc: Class that loads/parses the cord19 model data.
##############
class Cord19Loader(SourceDataLoader):

    source_id: str = 'Cord19'
    provenance_id: str = 'infores:cord19'

    def __init__(self, test_mode: bool = False):
        """
        constructor
        :param test_mode - sets the run into test mode
        """
        # call the super
        super(SourceDataLoader, self).__init__()

        self.associated_with_predicate = 'SEMMEDDB:ASSOCIATED_WITH'

        self.scibite_url = 'https://stars.renci.org/var/data_services/cord19/scibite/v6/'
        self.scibite_nodes_file_name = 'CV19_nodes.txt'
        self.scibite_edges_file_name = 'CV19_edges.txt'

        self.scrigraph_url = 'https://stars.renci.org/var/data_services/cord19/scigraph/v12/'
        self.scigraph_nodes_file_name = 'normalized.txt'
        self.scigraph_edges_file_name = 'pairs.txt'

        self.covid_node_id = 'MONDO:0100096'
        self.has_phenotype_predicate = 'RO:0002200'
        self.covid_phenotypes_url = 'https://stars.renci.org/var/data_services/cord19/'
        self.covid_phenotypes_file_name = 'covid_phenotypes.csv'

        self.drug_bank_trials_url = 'https://raw.githubusercontent.com/TranslatorIIPrototypes/CovidDrugBank/master/'
        self.drug_bank_trials_file_name = 'trials.txt'

        self.data_path: str = os.path.join(os.environ['DATA_SERVICES_STORAGE'], self.source_id)
        self.data_files: list = [self.scibite_nodes_file_name,
                                 self.scibite_edges_file_name,
                                 self.scigraph_nodes_file_name,
                                 self.scigraph_edges_file_name,
                                 self.covid_phenotypes_file_name,
                                 self.drug_bank_trials_file_name]
        self.test_mode: bool = test_mode

        # the final output lists of nodes and edges
        self.final_node_list: list = []
        self.final_edge_list: list = []

        # create a logger
        self.logger = LoggingUtil.init_logging("Data_services.cord19.Cord19Loader", level=logging.INFO, line_format='medium', log_file_path=os.environ['DATA_SERVICES_LOGS'])

    def get_latest_source_version(self) -> str:
        """
        gets the version of the data

        :return:
        """
        return 'scibite_v6_scigraph_v12'

    def get_data(self) -> int:
        """
        Gets the cord19 data.

        """
        sources_to_pull = [
            f'{self.covid_phenotypes_url}{self.covid_phenotypes_file_name}',
            f'{self.scibite_url}{self.scibite_nodes_file_name}',
            f'{self.scibite_url}{self.scibite_edges_file_name}',
            f'{self.scrigraph_url}{self.scigraph_nodes_file_name}',
            f'{self.scrigraph_url}{self.scigraph_edges_file_name}',
            f'{self.drug_bank_trials_url}{self.drug_bank_trials_file_name}'
        ]
        data_puller = GetData()
        for source_url in sources_to_pull:
            data_puller.pull_via_http(source_url, self.data_path)

        return True

    def parse_data(self) -> dict:
        """
        Parses the data file for graph nodes/edges

        :return: ret_val: load_metadata
        """

        extractor = Extractor()

        # parse the nodes files
        for nodes_file_name in [self.scibite_nodes_file_name, self.scigraph_nodes_file_name]:
            nodes_file: str = os.path.join(self.data_path, nodes_file_name)
            with open(nodes_file, 'r') as fp:
                extractor.csv_extract(fp,
                                      lambda line: line[NODESDATACOLS.ID.value], # extract subject id
                                      lambda line: None, # extract object id
                                      lambda line: None, # predicate extractor
                                      lambda line: {'name': line[NODESDATACOLS.NAME.value]}, # subject props
                                      lambda line: {}, # object props
                                      lambda line: {}, # edge props
                                      comment_character=None,
                                      delim='\t',
                                      has_header_row=True)

        # parse the scibites edges file
        edges_file: str = os.path.join(self.data_path, self.scibite_edges_file_name)
        with open(edges_file, 'r') as fp:
            extractor.csv_extract(fp,
                                  lambda line: line[SBEDGESDATACOLS.SUBJECT.value].replace('_', ''),  # subject id
                                  lambda line: line[SBEDGESDATACOLS.OBJECT.value].replace('_', ''),  # object id
                                  lambda line: self.associated_with_predicate,  # predicate extractor
                                  lambda line: {},  # subject props
                                  lambda line: {},  # object props
                                  lambda line: {'num_publications': float(line[SBEDGESDATACOLS.EFFECTIVE_PUBS.value]),
                                                'enrichment_p': float(line[SBEDGESDATACOLS.ENRICHMENT.value]),
                                                ORIGINAL_KNOWLEDGE_SOURCE: 'infores:cord19-scibite'},#edgeprops
                                  comment_character=None,
                                  delim='\t',
                                  has_header_row=True)

        # parse the scigraph edges file
        edges_file: str = os.path.join(self.data_path, self.scigraph_edges_file_name)
        with open(edges_file, 'r') as fp:
            extractor.csv_extract(fp,
                                  lambda line: line[SGEDGESDATACOLS.SUBJECT.value],  # subject id
                                  lambda line: line[SGEDGESDATACOLS.OBJECT.value],  # object id
                                  lambda line:  self.associated_with_predicate,  # predicate extractor
                                  lambda line: {},  # subject props
                                  lambda line: {},  # object props
                                  lambda line: {'num_publications': float(line[SGEDGESDATACOLS.EFFECTIVE_PUBS.value]),
                                                'enrichment_p': float(line[SGEDGESDATACOLS.ENRICHMENT.value]),
                                                ORIGINAL_KNOWLEDGE_SOURCE: 'infores:cord19'},#edgeprops
                                  comment_character=None,
                                  delim='\t',
                                  has_header_row=True)

        # parse the covid phenotypes file
        phenotypes_file: str = os.path.join(self.data_path, self.covid_phenotypes_file_name)
        with open(phenotypes_file, 'r') as fp:
            extractor.csv_extract(fp,
                                  lambda line: self.covid_node_id,  # subject id
                                  lambda line: line[PHENOTYPESDATACOLS.PHENOTYPE_ID.value],  # object id
                                  lambda line: self.has_phenotype_predicate,  # predicate extractor
                                  lambda line: {},  # subject props
                                  lambda line: {},  # object props
                                  lambda line: {AGGREGATOR_KNOWLEDGE_SOURCES: ['infores:cord19']},#edgeprops
                                  comment_character=None,
                                  delim=',',
                                  has_header_row=True)

        trials_file: str = os.path.join(self.data_path, self.drug_bank_trials_file_name)
        with open(trials_file, 'r') as fp:
            extractor.csv_extract(fp,
                                  lambda line: line[TRIALSDATACOLS.DRUG_ID.value],  # subject id
                                  lambda line: line[TRIALSDATACOLS.TARGET_ID.value],  # object id
                                  lambda line: f'ROBOKOVID:{line[TRIALSDATACOLS.PREDICATE.value]}',  # predicate extractor
                                  lambda line: {},  # subject props
                                  lambda line: {},  # object props
                                  lambda line: {'count': line[TRIALSDATACOLS.COUNT.value],
                                                ORIGINAL_KNOWLEDGE_SOURCE: 'infores:drugbank'},#edgeprops
                                  comment_character=None,
                                  delim='\t',
                                  has_header_row=True)

        self.final_node_list = extractor.nodes
        self.final_edge_list = extractor.edges

        return extractor.load_metadata
