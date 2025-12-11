"""LicenseComparator class"""

from abc import ABC, abstractmethod
from pathlib import Path
from copy import deepcopy

import src.analyzer.dep_tree_builder as deptree
import src.analyzer.package_metadata_fetcher as fetcher
from src.analyzer.license_compatibility_analyzer \
    import LicenseCompatibilityAnalyzer as LCA
import src.infrastructure.scancode_runner as runner


from src.infrastructure.logger_formatter import LoggerFormatter
logger = LoggerFormatter.initialize(__name__,
LoggerFormatter.DEBUG)

class LicenseTreeStrategy(ABC):
    # This class is meant for a single purpose.
    """Abstract Strategy class for  gathering license trees"""
    @abstractmethod
    def generate_license_tree(self, requirements_path):
        """Abstract tree generator function"""

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

        logger.debug('Performing SPDX -> OSADL mapping...')
        for k, v in tree_dict.items():
            licenses_dict[k] = map_scancode_to_osadl(v)

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
                    logger.error('Failed to extract a suitable license for:\
                        %s', key)
                    continue
                licenses_dict[key] = 'FAILED'
                if len(tallies) == 1:
                    licenses_dict[key] = map_scancode_to_osadl(
                        tallies[0]['value'])
                    continue
                logger.warning("More than one license detected, picking the\
                    most likely one")
                for tally in tallies:
                    logger.debug("%s : %s",key, tally['value'])
                    if (tally['value'] is not None)\
                        and (not 'AND' in tally['value']):
                        # don't take merged tallies
                        licenses_dict[key] = map_scancode_to_osadl(
                            tally['value'])

        # we have got all the licenses
        # for easy comparison we will create PyPIMetadata objects
        # no links, because we don't need them
        license_tree = deepcopy(tree)
        for key, values in tree.items():
            if isinstance(values, list):
                for i, value in enumerate(values):
                    license_tree[key][i] = fetcher.\
                        PyPiMetadata(value, licenses_dict[value], None)
            else:
                license_tree[key] = fetcher.\
                    PyPiMetadata(values, licenses_dict[values], None)

            license_tree[fetcher.PyPiMetadata(key, licenses_dict[key], None)]\
                = license_tree.pop(key)
        return license_tree

class RepoTreeStrategy(LicenseTreeStrategy):
    """Generate a tree based on licenses the dependencies claim themselves."""

    def generate_license_tree(self, requirements_path):
        venv = deptree.create_venv()
        depjson = deptree.get_tree_json(venv)
        # This generates a PyPIMetadata tree by default.
        data = fetcher.build_package_metadata(requirements_path)
        tree = deptree.build_map(depjson)

        data_dict = {meta.package: meta for meta in data}
        license_tree = {}

        for key, values in tree.items():
            key_meta = data_dict.get(key)
            if key_meta:
                if isinstance(values, list):
                    license_tree[key_meta] = [data_dict.get(v) for v \
                        in values if data_dict.get(v)]
                else:
                    license_tree[key_meta] = data_dict.get(values) \
                        if data_dict.get(values) else []
        return license_tree

# Analyzing trees is the next logical step after analyzing individual licenses
class LicenseComparator(LCA):
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
        '--ignore',
        'LICENSE_*',
        '--max-depth',
        '3', # Either a LICENSE file, or a LICENSE dir
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
        super().__init__()
        if not path:
            path = 'requirements.txt'
            logger.warning('Invalid path set, setting a sensible default: %s',
                        path)
        self.path = path
        self.tree_a = tree_a
        self.tree_b = tree_b

    def ensure_trees_exist(self):
        """Ensures that the two license trees are present.
        If not, generates them using sensible defaults.

        Returns:
            bool: Do the trees exist (possibly after a generation attempt)?
        """
        if self.tree_a is None:
            # default: get scancode tree
            logger.warning("Primary tree not passed, using default Scancode..")
            self.license_tree_strategy = ScancodeTreeStrategy()
            self.tree_a = self.get_license_tree()
            logger.info(self.tree_a)
        if self.tree_b is None:
            # default: get github tree
            logger.warning("Secondary tree not found, using default GitXXX...")
            self.license_tree_strategy = RepoTreeStrategy()
            self.tree_b = self.get_license_tree()

        if (self.tree_a is None) or (self.tree_b is None):
            logger.error('Unable to generate license tree(s), aborting.')
            return False

        return True

    @staticmethod
    def flatten(x: list) -> list:
        """Flattens an arbitratily nested list into a flat one
        Args:
            x (list): a nested list

        Returns:
            list: a flat list.
        """
        res = []
        for i in x:
            res.extend(LicenseComparator.flatten(i) if isinstance(i, list) else [i])
        return res

    def get_license_tree(self):
        """Wrapper around Strategy

        Returns:
            str: the JSON representation of the license tree.
        """
        return self.license_tree_strategy.generate_license_tree(self.path)

    def compare_license_trees(self):
        """
        Compares two license trees for exact equality.
        Returns True if the trees are structurally identical and have\
            identical licenses, False otherwise.
        """
        if not self.ensure_trees_exist():
            return False

        discrepancies = []

        # Get all packages from tree_a and tree_b
        packages_a = set()
        for key, deps in self.tree_a.items():
            packages_a.add(key.package)
            for dep in deps:
                packages_a.add(dep.package)

        packages_b = set()
        for key, deps in self.tree_b.items():
            packages_b.add(key.package)
            for dep in deps:
                packages_b.add(dep.package)

        if packages_a != packages_b:
            logger.warning('Dependency count mismatch - the trees are\
                different.')
            discrepancies.append(('miscount',))

        # Create license dicts
        licenses_a = {}
        for key, deps in self.tree_a.items():
            licenses_a[key.package] = key.license_type
            for dep in deps:
                licenses_a[dep.package] = dep.license_type

        licenses_b = {}
        for key, deps in self.tree_b.items():
            licenses_b[key.package] = key.license_type
            for dep in deps:
                licenses_b[dep.package] = dep.license_type

        for lic_a, lic_b in zip(licenses_a.values(), 
                                licenses_b.values()):
            logger.debug('Comparing %s against %s', lic_a, lic_b)
            if lic_a != lic_b:
                logger.warning('Different claimed dependency licenses:\
                    %s vs %s', lic_a, lic_b)
                discrepancies.append(('license_mismatch', lic_a, lic_b))

        # Check structure: for each key in tree_a, find corresponding in tree_b
        for key_a, deps_a in self.tree_a.items():
            found = False
            for key_b, deps_b in self.tree_b.items():
                if key_a.package == key_b.package:
                    deps_a_packages = {dep.package for dep in deps_a}
                    deps_b_packages = {dep.package for dep in deps_b}
                    if deps_a_packages != deps_b_packages:
                        logger.warning('Dependency mismatch for _package\
                                       %s: %d vs %d', key_a.package,
                                       deps_a_packages, deps_b_packages)
                        discrepancies.append(('dep_mismatch', deps_a_packages,
                                              deps_b_packages))
                        # return False
                    found = True
                    break
            if not found:
                logger.warning('Package found in only one of the trees: %s',
                               key_a)
                discrepancies.append(('tree_imbalance', key_a))
                #return False

        return discrepancies


def map_scancode_to_osadl(scancode_license):
    """SPDX -> OSADL license name mapping
    
    Args:
        scancode_license (str): Scancode license name

    Returns:
        str: OSADL license name
    """
    # Mapowanie dla specjalnych przypadków, gdzie nazwy mogą się różnić
    # Mapuje niestandardowe nazwy z Scancode na standardowe SPDX ID używane w OSADL
    mapping = {
        # GPL Family
        "GPL-1.0": "GPL-1.0-only",
        "GPL-1.0+": "GPL-1.0-or-later",
        "GNU General Public License v1.0 only": "GPL-1.0-only",
        "GNU General Public License v1.0 or later": "GPL-1.0-or-later",
        "GPL-2.0": "GPL-2.0-only",
        "GPL-2.0+": "GPL-2.0-or-later",
        "GNU General Public License v2.0 only": "GPL-2.0-only",
        "GNU General Public License v2.0 or later": "GPL-2.0-or-later",
        "gpl-2.0": "GPL-2.0-only",
        "GPL-3.0": "GPL-3.0-only",
        "GPL-3.0+": "GPL-3.0-or-later",
        "GNU General Public License v3.0 only": "GPL-3.0-only",
        "GNU General Public License v3.0 or later": "GPL-3.0-or-later",
        "GNU General Public License (GPL)": "GPL-2.0-only",

        # LGPL Family
        "LGPL-2.0": "LGPL-2.0-only",
        "LGPL-2.0+": "LGPL-2.0-or-later",
        "GNU Library General Public License v2 only": "LGPL-2.0-only",
        "GNU Library General Public License v2 or later": "LGPL-2.0-or-later",
        "LGPL-2.1": "LGPL-2.1-only",
        "LGPL-2.1+": "LGPL-2.1-or-later",
        "GNU Lesser General Public License v2.1 only": "LGPL-2.1-only",
        "GNU Lesser General Public License v2.1 or later": "LGPL-2.1-or-later",
        "LGPL-3.0": "LGPL-3.0-only",
        "LGPL-3.0+": "LGPL-3.0-or-later",
        "GNU Lesser General Public License v3.0 only": "LGPL-3.0-only",
        "GNU Lesser General Public License v3.0 or later": "LGPL-3.0-or-later",

        # AGPL Family
        "AGPL-3.0": "AGPL-3.0-only",
        "GNU Affero General Public License v3.0": "AGPL-3.0-only",
        "GNU Affero General Public License v3.0 only": "AGPL-3.0-only",
        "GNU Affero General Public License v3.0 or later": "AGPL-3.0-or-later",

        # Apache Family
        "Apache License 1.0": "Apache-1.0",
        "Apache License 1.1": "Apache-1.1",
        "Apache License 2.0": "Apache-2.0",
        "Apache Software License": "Apache-2.0",
        "apache-2.0": "Apache-2.0",

        # BSD Family
        "BSD Zero Clause License": "0BSD",
        "BSD 1-Clause License": "BSD-1-Clause",
        "BSD 2-Clause \"Simplified\" License": "BSD-2-Clause",
        "bsd-simplified": "BSD-2-Clause",
        "BSD 3-Clause \"New\" or \"Revised\" License": "BSD-3-Clause",
        "BSD License": "BSD-3-Clause",
        "bsd-new": "BSD-3-Clause",
        "BSD 4-Clause \"Original\" or \"Old\" License": "BSD-4-Clause",
        "BSD 4-Clause (University of California-Specific)": "BSD-4-Clause-UC",
        "BSD 3-Clause Open MPI variant": "BSD-3-Clause-Open-MPI",

        # MIT Family
        "MIT License": "MIT",
        "MIT No Attribution": "MIT-0",
        "CMU License": "MIT-CMU",
        "MIT-CMU": "MIT-CMU",
        "cmu-uc": "MIT-CMU",

        # Mozilla Family
        "Mozilla Public License 1.1": "MPL-1.1",
        "Mozilla Public License 2.0": "MPL-2.0",
        "Mozilla Public License 2.0 (MPL 2.0)": "MPL-2.0",
        "mpl-2.0": "MPL-2.0",
        "Mozilla Public License 2.0 (no copyleft exception)": "MPL-2.0-no-copyleft-exception",

        # Other Mappings
        "Academic Free License v2.0": "AFL-2.0",
        "Academic Free License v2.1": "AFL-2.1",
        "Academic Free License v3.0": "AFL-3.0",
        "Apple Public Source License 2.0": "APSL-2.0",
        "Artistic License 1.0": "Artistic-1.0",
        "Artistic License 1.0 (Perl)": "Artistic-1.0-Perl",
        "Artistic License 2.0": "Artistic-2.0",
        "Bitstream Vera Font License": "Bitstream-Vera",
        "Boost Software License 1.0": "BSL-1.0",
        "Creative Commons Attribution 2.5 Generic": "CC-BY-2.5",
        "Creative Commons Attribution 3.0 Unported": "CC-BY-3.0",
        "Common Development and Distribution License 1.0": "CDDL-1.0",
        "Common Development and Distribution License 1.1": "CDDL-1.1",
        "Common Public License 1.0": "CPL-1.0",
        "Educational Community License v1.0": "ECL-1.0",
        "Educational Community License v2.0": "ECL-2.0",
        "Eiffel Forum License v2.0": "EFL-2.0",
        "Eclipse Public License 1.0": "EPL-1.0",
        "Eclipse Public License 2.0": "EPL-2.0",
        "European Union Public License 1.1": "EUPL-1.1",
        "European Union Public License 1.2": "EUPL-1.2",
        "FSF All Permissive License": "FSFAP",
        "FSF Unlimited License": "FSFUL",
        "Freetype Project License": "FTL",
        "Historical Permission Notice and Disclaimer": "HPND",
        "IBM PowerPC Initialization and Boot Software": "IBM-pibs",
        "ICU License": "ICU",
        "Independent JPEG Group License": "IJG",
        "ImageMagick License": "ImageMagick",
        "Info-ZIP License": "Info-ZIP",
        "IBM Public License v1.0": "IPL-1.0",
        "ISC License": "ISC",
        "JasPer License": "JasPer-2.0",
        "libpng License": "Libpng",
        "PNG Reference Library version 2": "libpng-2.0",
        "libtiff License": "libtiff",
        "Minpack License": "Minpack",
        "The MirOS Licence": "MirOS",
        "Microsoft Public License": "MS-PL",
        "Microsoft Reciprocal License": "MS-RL",
        "Net Boolean Public License v1": "NBPL-1.0",
        "University of Illinois/NCSA Open Source License": "NCSA",
        "NTP License": "NTP",
        "OGC Software License, Version 1.0": "OGC-1.0",
        "Open LDAP Public License v2.8": "OLDAP-2.8",
        "OpenSSL License": "OpenSSL",
        "Open Software License 3.0": "OSL-3.0",
        "PHP License v3.01": "PHP-3.01",
        "PostgreSQL License": "PostgreSQL",
        "Python Software Foundation License 2.0": "PSF-2.0",
        "Python Software Foundation License": "PSF-2.0",
        "Python License 2.0": "Python-2.0",
        "Qhull License": "Qhull",
        "RSA Message-Digest License": "RSA-MD",
        "Saxpath License": "Saxpath",
        "SGI Free Software License B v2.0": "SGI-B-2.0",
        "Sleepycat License": "Sleepycat",
        "Standard ML of New Jersey License": "SMLNJ",
        "Spencer License 86": "Spencer-86",
        "SSH OpenSSH license": "SSH-OpenSSH",
        "SSH short notice": "SSH-short",
        "SunPro License": "SunPro",
        "Unicode License v3": "Unicode-3.0",
        "Unicode License Agreement - Data Files and Software (2015)": "Unicode-DFS-2015",
        "Unicode License Agreement - Data Files and Software (2016)": "Unicode-DFS-2016",
        "The Unlicense": "Unlicense",
        "Universal Permissive License v1.0": "UPL-1.0",
        "W3C Software Notice and License (2002-12-31)": "W3C",
        "W3C Software Notice and License (1998-07-20)": "W3C-19980720",
        "W3C Software Notice and Document License (2015-05-13)": "W3C-20150513",
        "Do What The F*ck You Want To Public License": "WTFPL",
        "X11 License": "X11",
        "XFree86 License 1.1": "XFree86-1.1",
        "zlib License": "Zlib",
        "zlib/libpng License with Acknowledgement": "zlib-acknowledgement",
        "Zope Public License 2.0": "ZPL-2.0",
    }

    # Dla większości przypadków, nazwy są identyczne
    return mapping.get(scancode_license, scancode_license)


if __name__ == "__main__":
    LC = LicenseComparator() 
    problems = LC.compare_license_trees()
    for problem in problems:
        print(problem)
