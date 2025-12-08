"""LicenseComparator class"""

from abc import ABC, abstractmethod
from pathlib import Path
from copy import deepcopy
import json

import src.analyzer.dep_tree_builder as deptree
import src.analyzer.package_metadata_fetcher as fetcher
import src.infrastructure.scancode_runner as runner

from src.infrastructure.logger_formatter import LoggerFormatter
logger = LoggerFormatter.initialize(__name__,
LoggerFormatter.DEBUG)

class LicenseTreeStrategy(ABC):
    # This class is meant for a single purpose.
    """Abstract Strategy class for  gathering license trees"""
    @abstractmethod
    def generate_license_tree(self, requirements_path):
        """Generate a license-dependency tree

        Args:

        Returns:
        """

class ScancodeTreeStrategy(LicenseTreeStrategy):
    # This class is meant for a single purpose.
    """Generate a tree with Scancode"""
    def generate_license_tree(self, requirements_path):
        """The abstract implementation
        """
        venv = deptree.create_venv()
        depjson = deptree.get_tree_json(venv)
        tree = deptree.build_map(depjson)

        # Not pretty, but ensures all files are in place.
        fetcher.build_package_metadata(requirements_path)


        # Now the Scancode part
        # Ensure we run scancode as little as possible
        flat_tree = set(LicenseComparator.flatten(tree))
        tree_dict = dict.fromkeys(flat_tree, None)
        licenses_dict = tree_dict

        for key in tree_dict:
            scancode_result = runner.run_scancode(
                Path.joinpath(Path.cwd(),'src',
                              fetcher.DOWNLOAD_DIRECTORY, key + '.zip'),
                key, LicenseComparator.scancode_args
            )
            if scancode_result is None:
                logger.error('Failed to extract a suitable license for: %s',
                             key)
                licenses_dict[key] = 'FAILED'
            else:
                tallies = scancode_result['tallies']\
                                          ['detected_license_expression']
                # attach the most popular license (which should be the only one
                # but you never know)
                if not tallies:
                    logger.error('Failed to extract a suitable license for: %s',
                             key)
                    continue
                licenses_dict[key] = 'FAILED'
                if len(tallies) == 1:
                    licenses_dict[key] = tallies[0]['value']
                    continue
                logger.warning("More than one license detected, picking the most common one")
                for tally in tallies:
                    logger.debug("%s : %s",key, tally['value'])
                    if (tally['value'] is not None)\
                        and (not 'AND' in tally['value']):
                        # don't take merged tallies
                        licenses_dict[key] = tally['value']

        # we have got all the licenses
        # for easy comparison we will substitute a package name
        # with a tuple: (pkg_name, license): (str, str)
        license_tree = deepcopy(tree)
        for key, values in tree.items():
            if isinstance(values, list):
                for i, value in enumerate(values):
                    license_tree[key][i] = (value, licenses_dict[value])
            else:
                license_tree[key] = (values, licenses_dict[values])
            license_tree[(key, licenses_dict[key])] = license_tree.pop(key)
        print(license_tree)
        return license_tree
    

class RepoTreeStrategy(LicenseTreeStrategy):
    """Generate a tree based on licenses the dependencies claim themselves."""
    def generate_license_tree(self, requirements_path):
        data = fetcher.build_package_metadata(requirements_path)
        return data

class LicenseComparator:
    """
    Analyzes deptrees from diferent placertainces and reports 
    whether their licenses match.
    """
    scancode_args = [
        '-l',
        '--include',
        'LICENSE',
        '--include',
        'LICENSE.*',
        '--include',
        'COPYING',
        '--ignore',
        'docs',
        '--max-depth',
        '4', # Either a LICENSE file, or a LICENSE dir
        '--license-score',
        '100', # only take 100% certain picks for now
        '--tallies',
        '--json-pp',
        '-'
    ]

    _license_tree_strategy : LicenseTreeStrategy = None

    @property
    def license_tree_strategy(self):
        """The strategy property.

        Returns:
            LicenseTreeStrategy: The current strategy used for\
                acquiring the license-dependency tree.
        """
        return self._license_tree_strategy

    @license_tree_strategy.setter
    def license_tree_strategy(self, content):
        self._license_tree_strategy = content

    def __init__(self, path='requirements.txt', tree_a = None, tree_b = None):
        if not path:
            path = 'requirements.txt'
            logger.warning('Invalid path set, setting a sensible default: %s',
                        path)
        self.path = path

        if tree_a is None:
            # default: get scancode tree
            logger.warning("Primary tree not passed, using default Scancode..")
            self.license_tree_strategy = ScancodeTreeStrategy()
            tree_a = self.get_license_tree()
        if tree_b is None:
            # default: get github tree
            logger.warning("Secondary tree not found, using default GitXXX...")
            self.license_tree_strategy = RepoTreeStrategy()
            tree_b = self.get_license_tree()       
    def get_license_tree(self):
        return self._license_tree_strategy.generate_license_tree(self.path)
    
    @staticmethod
    def flatten(x: list) -> list:
        res = []
        for i in x:
            res.extend(LicenseComparator.flatten(i) if isinstance(i, list) else [i])
        return res

if __name__ == "__main__":
    LC = LicenseComparator()
