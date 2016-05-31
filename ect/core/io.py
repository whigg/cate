"""
Module Description
==================

This module provides ECT's data access API.

Module Requirements
===================

**Query catalogue**

:Description: Allow querying registered ECV catalogues using a simple function that takes a set of query parameters
    and returns data source identifiers that can be used to open respective ECV dataset in the ECT.
:Specified in: <link to other RST page here>
:Test: <link to test class.function here>
:URD-Source: <name the URD # and optionally the name>

----

**Open dataset**

:Description: Allow opening an ECV dataset given an identifier returned by the *catalogue query*.
   The dataset returned complies to the ECT common data model.
   The dataset to be returned can optionally be constrained in time and space.
:Specified in: <link to other RST page here>
:Test: <link to test class.function here>
:URD-Source: <name the URD # and optioanlly the name>



Module Reference
================
"""
import json
import pkgutil
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Sequence, Union, List

import xarray as xr

from ect.core import Dataset
from ect.core.cdm_xarray import XArrayDatasetAdapter


class DataSource():
    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def open_dataset(self, **constraints) -> Dataset:
        return None

    def matches_filter(self, **filter) -> bool:
        if filter:
            for key, value in filter.items():
                if key == 'name' and not value in self._name:
                    return False
        return True


class Catalogue:
    def __init__(self, data_sources: Sequence[DataSource]):
        self._data_sources = data_sources

    def query(self, **filter) -> Sequence[DataSource]:
        return [ds for ds in self._data_sources if ds.matches_filter(**filter)]


class CatalogueRegistry:
    def __init__(self):
        self._catalogues = dict()

    def get_catalogue(self, name: str) -> Catalogue:
        return self._catalogues.get(name, None)

    def get_catalogues(self) -> Sequence[Catalogue]:
        return self._catalogues.values()

    def add_catalogue(self, name: str, catalogue: Catalogue):
        self._catalogues[name] = catalogue

    def remove_catalogue(self, name: str):
        del self._catalogues[name]

    def __len__(self):
        return len(self._catalogues)


def query_data_sources(catalogues: Union[Catalogue, Sequence[Catalogue]] = None,
                       **constraints) -> Sequence[
    DataSource]:
    """Queries the catalogue(s) for data sources matching the given constrains.

    Parameters
    ----------
    catalogues : Catalogue or Sequence[Catalogue]
       If given these catalogues will be querien. Othewise the DEFAULT_CATALOGUE will be used
    constraints : dict, optional
       The contains may limit the dataset in space or time.

    Returns
    -------
    datasource : List[DataSource]
       All data sources matching the given constrains.

    See Also
    --------
    open_dataset
    """
    if catalogues is None:
        catalogue_list = CATALOGUE_REGISTRY.get_catalogues()
    elif isinstance(catalogues, Catalogue):
        catalogue_list = [catalogues]
    else:
        catalogue_list = catalogues
    results = []
    for catalogue in catalogue_list:
        results.extend(catalogue.query(**constraints))
    return results


def open_dataset(data_source: Union[DataSource, str], **constraints) -> Dataset:
    """Load and decode a dataset.

    Parameters
    ----------
    data_source : str or DataSource
       Strings are interpreted as the identifier of an ECV dataset.
    constraints : str, optional
       The contains may limit the dataset in space or time.

    Returns
    -------
    dataset : Dataset
       The newly created dataset.

    See Also
    --------
    query_data_sources
    """
    if data_source is None:
        raise ValueError('No data_source given')

    if isinstance(data_source, str):
        raise NotImplementedError  # TODO
        # data_source = query_data_sources(DEFAULT_CATALOGUE, name=data_source)
    return data_source.open_dataset(**constraints)


#########################

def _as_datetime(dt: Union[str, datetime], default) -> datetime:
    if dt is None:
        return default
    if isinstance(dt, str):
        if dt == '':
            return default
        # TODO handle format with/without time
        return datetime.strptime(dt, "%Y-%m-%d")
    if isinstance(dt, datetime):
        return dt
    raise ValueError


class FileSetDataSource(DataSource):
    """A class representing the a specific file set with the meta information belonging to it.

    Parameters
    ----------
    name : str
        The name of the file set
    base_dir : str
        The base directory
    file_pattern : str
        The file pattern with wildcards for year, month, and day
    fileset_info : FileSetInfo
        The file set info generated by a scannning, can be None

    Returns
    -------
    new  : FileSetDataSource
    """

    def __init__(self, name: str, base_dir: str, file_pattern: str, fileset_info: 'FileSetInfo' = None):
        super(FileSetDataSource, self).__init__(name)
        self._base_dir = base_dir
        self._file_pattern = file_pattern
        self._fileset_info = fileset_info

    @classmethod
    def from_json(cls, json_str) -> Sequence['FileSetDataSource']:
        fsds = []
        for data in json.loads(json_str):
            if 'start_date' in data and 'end_date' in data and 'num_files' in data and 'size_mb' in data:
                file_set_info = FileSetInfo(
                    datetime.now(),  # TODO
                    data['start_date'],
                    data['end_date'],
                    data['num_files'],
                    data['size_mb']
                )
            else:
                file_set_info = None
            fsds.append(FileSetDataSource(
                data['name'],
                data['base_dir'],
                data['file_pattern'],
                fileset_info=file_set_info
            ))
        return fsds

    def open_dataset(self, **constraints) -> Dataset:
        first_time = constraints.get('first_time', None)
        last_time = constraints.get('last_time', None)
        paths = self.resolve_paths(first_time=first_time, last_time=last_time)
        xr_dataset = xr.open_mfdataset(paths)
        cdm_dataset = XArrayDatasetAdapter(xr_dataset)
        return cdm_dataset

    def to_json_dict(self):
        """
        Return a JSON-serializable dictionary representation of this object.

        :return: A JSON-serializable dictionary
        """
        fsds_dict = OrderedDict()
        fsds_dict['name'] = self.name
        fsds_dict['base_dir'] = self._base_dir
        fsds_dict['file_pattern'] = self._file_pattern
        if self._fileset_info:
            fsds_dict['fileset_info'] = self._fileset_info.to_json_dict()
        return fsds_dict

    @property
    def _full_pattern(self) -> str:
        return self._base_dir + "/" + self._file_pattern

    def resolve_paths(self, first_time: Union[str, datetime] = None, last_time: Union[str, datetime] = None) -> \
    Sequence[str]:
        """Return a list of all paths between the given times.

        For all dates, including the first and the last time, the wildcard in the pattern is resolved for the date.

        Parameters
        ----------
        first_time : str or datetime
            The first date of the time range, can be None if the file set has a *start_time*.
            In this case the *start_time* is used.
        last_date : str or datetime
            The last date of the time range, can be None if the file set has a *end_time*.
            In this case the *end_time* is used.
        """
        if first_time is None and (self._fileset_info is None or self._fileset_info._start_time is None):
            raise ValueError("neither first_time nor start_time are given")
        dt1 = _as_datetime(first_time, self._fileset_info._start_time)

        if last_time is None and (self._fileset_info is None or self._fileset_info._end_time is None):
            raise ValueError("neither last_time nor end_time are given")
        dt2 = _as_datetime(last_time, self._fileset_info._end_time)

        if dt1 > dt2:
            raise ValueError("start time '%s' is after end time '%s'" % (dt1, dt2))

        return [self._resolve_date(dt1 + timedelta(days=x)) for x in range((dt2 - dt1).days + 1)]

    def _resolve_date(self, dt: datetime):
        path = self._full_pattern
        if "{YYYY}" in path:
            path = path.replace("{YYYY}", "%04d" % (dt.year))
        if "{MM}" in path:
            path = path.replace("{MM}", "%02d" % (dt.month))
        if "{DD}" in path:
            path = path.replace("{DD}", "%02d" % (dt.day))
        return path


class FileSetInfo:
    def __init__(self,
                 info_update_time: Union[str, datetime],
                 start_time: Union[str, datetime],
                 end_time: Union[str, datetime],
                 num_files: int,
                 size_in_mb: int):
        self._info_update_time = _as_datetime(info_update_time, None)
        self._start_time = _as_datetime(start_time, None)
        self._end_time = _as_datetime(end_time, None)
        self._num_files = num_files
        self._size_in_mb = size_in_mb

    def to_json_dict(self):
        """
        Return a JSON-serializable dictionary representation of this object.

        :return: A JSON-serializable dictionary
        """
        return dict(
            info_update_time=self._info_update_time,
            start_time=self._start_time,
            end_time=self._end_time,
            num_files=self._num_files,
            size_in_mb=self._size_in_mb,
        )


class FileSetCatalogue(Catalogue):
    def __init__(self, root_dir: str, fileset_datasources: Sequence[FileSetDataSource]):
        super(FileSetCatalogue, self).__init__(fileset_datasources)
        self._root_dir = root_dir

    @property
    def root_dir(self) -> str:
        return self._root_dir


def _read_default_file_catalogue():
    data = pkgutil.get_data('ect.data', 'ESA FTP.json')
    fileset_datasources = FileSetDataSource.from_json(data.decode('utf-8'))
    # TODO get root_dir from ENVIRONMENT
    return FileSetCatalogue('root_dir', fileset_datasources)


CATALOGUE_REGISTRY = CatalogueRegistry()
CATALOGUE_REGISTRY.add_catalogue('default', _read_default_file_catalogue())

