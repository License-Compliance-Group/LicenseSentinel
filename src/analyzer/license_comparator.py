"""The tree-comparison class.
"""
from pathlib import Path

from entities.scan_engine import ScanEngine
from entities.abstract_license_comparator import AbstractLicenseComparator
from infrastructure.logger_formatter import LoggerFormatter
from src.analyzer import license_name_normalizer as normalizer

logger = LoggerFormatter.initialize(__name__,
                                    LoggerFormatter.DEBUG)


class LicenseComparator(AbstractLicenseComparator):
    """The license comparator class definition.
    Does not raise."""

    def __init__(self, tree_a, scan_engine: ScanEngine,
                 download_dir=Path.joinpath(Path.cwd(), 'tmpvenv', 'repo_downloads')):
        """_summary_

        Args:
            tree_a (Dict[str, str]): A package-license pairing.
            scan_engine (ScanEngine): The scanning engine used to acquire tree_b
            download_dir (Path, optional): The path to scan for repo sources in.
        """
        self.tree_a = self._process_pypi_metadata(tree_a)
        self.tree_b = {}
        self.scan_engine = scan_engine
        self.download_dir = download_dir

    def _process_pypi_metadata(self, tree_a):
        tree = {}
        for metadata in tree_a:
            tree[metadata.package] = normalizer.normalize(
                metadata.license_type
            )
        return tree

    def compare_license_trees(self, override_cache: bool = False):
        """Compares two license trees, returning incompatibilities
        and potentially dubious results.
        Format of doubts/discrepancies array:
        `(package_name, pypi_license, (tree_b_licenses,))`
        There are multiple `tree_b_licenses` allowed, so this is why.

        Args:
            override_cache: set to True if trees should be recovered
                without using cached data.
        Returns:
            (Optional[Tuple[str,str,Tuple[str]]],
            Optional[Tuple[str,str,str]]): 
            List of dubious/incorrect entries that have been detected.
        """
        discrepancies = []
        doubts = []
        if (not self.tree_b) or override_cache:
            self.tree_b = self.run_scan_engine(override_cache)
        for name, pypi_name in self.tree_a.items():
            if not name in self.tree_b:
                discrepancies.append(f'Package {name} missing from '
                                     'either tree')
                continue
            scan_names = self.tree_b[name]
            if len(scan_names) > 1:
                logger.debug('More than one license declared for %s'
                             'in alternative tree, proceeding with caution.', name)
                if pypi_name in scan_names:
                    doubts.append((name, pypi_name, scan_names))
                    continue
                discrepancies.append((name, pypi_name, scan_names))
                continue
            if pypi_name == 'Unknown'\
                    or scan_names[0] == 'Unknown':
                doubts.append((name, pypi_name, scan_names[0]))
                continue
            if pypi_name != scan_names[0]:
                # Handle 'WITH' exceptions
                if pypi_name.lower() \
                        in scan_names[0].lower().split('with')[0]:
                    logger.warning('Dubious entry: %s - %s/%s',
                                   name,
                                   pypi_name,
                                   scan_names[0])
                    doubts.append(name, pypi_name, scan_names[0])
                else:
                    logger.warning('Incompatible entry: %s - %s/%s',
                                   name,
                                   pypi_name,
                                   scan_names[0])
                    discrepancies.append((name, pypi_name, (scan_names[0],)))
        return discrepancies, doubts

    def run_scan_engine(self, override_cache: bool = False):
        """Runs the ScanEngine instance to determine an alternative
        set of licenses.
        I/O heavy - run only when necsessary.
        Args:
            override_cache (bool): prevents the scanning engine
                from using caching
        """
        tree_b = {}
        for pkg_name in self.tree_a:
            tree_b[pkg_name] = \
                self.scan_engine.scan_for_license(
                Path.joinpath(self.download_dir, pkg_name + '.zip'),
                pkg_name,
                override_cache
            )
        # 6.2. do the actual comparison
        if not tree_b:
            logger.error('Scanning engine met a problem and was unable '
                         'to determine licenses, skipping cross-check.')
            return None
        return tree_b
