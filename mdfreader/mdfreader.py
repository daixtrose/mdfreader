# -*- coding: utf-8 -*-
""" Measured Data Format file reader main module

Platform and python version
----------------------------------------
With Unix and Windows for python 2.6+ and 3.2+

:Author: `Aymeric Rateau <https://github.com/ratal/mdfreader>`__

Created on Sun Oct 10 12:57:28 2010

Dependencies
-------------------
- Python >2.6, >3.2 <http://www.python.org>
- Numpy >1.6 <http://numpy.scipy.org>
- Sympy to convert channels with formula
- bitarray for not byte aligned data parsing
- Matplotlib >1.0 <http://matplotlib.sourceforge.net>
- NetCDF
- h5py for the HDF5 export
- xlwt for the excel export (not existing for python3)
- openpyxl for the excel 2007 export
- scipy for the Matlab file conversion
- zlib to uncompress data block if needed

Attributes
--------------
PythonVersion : float
    Python version currently running, needed for compatibility of both python 2.6+ and 3.2+

mdfreader module
--------------------------
"""
from io import open
from struct import unpack
from math import ceil
try:
    from .mdf3reader import mdf3
    from .mdf4reader import mdf4
except:
    from mdf3reader import mdf3
    from mdf4reader import mdf4
from numpy import arange, linspace, interp, all, diff, mean, vstack, hstack, float64, zeros, empty, delete
from numpy import nan, datetime64, array
from datetime import datetime

from argparse import ArgumentParser
from sys import version_info
from os.path import splitext
PythonVersion = version_info
PythonVersion = PythonVersion[0]


def _convertMatlabName(channel):
    """Removes non allowed characters for a Matlab variable name

    Parameters
    -----------------
    channel : string
        channel name

    Returns
    -----------
    string
        channel name compatible for Matlab
    """
    if PythonVersion < 3:
        try:
            channel = channel.decode('utf-8')
        except:
            print('channel name can not be decoded : ' + channel)
    channelName = channel.replace('[', '_ls_')
    channelName = channelName.replace(']', '_rs_')
    channelName = channelName.replace('$', '')
    channelName = channelName.replace('.', 'p')
    channelName = channelName.replace('\\', '_bs_')
    channelName = channelName.replace('/', '_fs_')
    channelName = channelName.replace('(', '_lp_')
    channelName = channelName.replace(')', '_rp_')
    channelName = channelName.replace(',', '_c_')
    channelName = channelName.replace('@', '_am_')
    channelName = channelName.replace(' ', '_')
    channelName = channelName.replace(':', '_co_')
    channelName = channelName.replace('-', '_hy_')
    channelName = channelName.replace('-', '_hy_')
    def cleanName(name):
        allowedStr = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.'
        buf = ''
        for c in name:
            if c in allowedStr:
                buf += c
        return buf
    channelName = cleanName(channelName)
    return channelName


class mdfinfo(dict):

    """ MDFINFO is a class gathering information from block headers in a MDF (Measure Data Format) file
        Structure is nested dicts. Primary key is Block type, then data group, channel group and channel number.
        Examples of dicts
    - mdfinfo['HDBlock'] header block
    - mdfinfo['DGBlock'][dataGroup] Data Group block
    - mdfinfo['CGBlock'][dataGroup][channelGroup] Channel Group block
    - mdfinfo['CNBlock'][dataGroup][channelGroup][channel] Channel block including text blocks for comment and identifier
    - mdfinfo['CCBlock'][dataGroup][channelGroup][channel] Channel conversion information

    Attributes
    --------------
    fileName : str
        file name
    mdfversion : int
        mdf file version number

    Methods
    ------------
    readinfo( fileName = None, filterChannelNames=False )
        Reads MDF file and extracts its complete structure
    listChannels( fileName = None )
        Read MDF file blocks and returns a list of contained channels

    Examples
    --------------
    >>> import mdfreader
    >>> FILENAME='toto.dat'
    >>> yop=mdfreader.mdfinfo(FILENAME)
    or if you are just interested to have only list of channels
    >>> yop=mdfreader.mdfinfo() # creates new instance f mdfinfo class
    >>> yop=mdfreader.listChannels(FILENAME) # returns a simple list of channel names
    """

    def __init__(self, fileName=None, filterChannelNames=False):

        """ You can give optionally to constructor a file name that will be parsed

        Parameters
        ----------------
        fileName : str, optional
            file name
        filterChannelNames : bool, optional
            flag to filter long channel names including module names separated by a '.'
        """

        self.fileName = fileName
        self.mdfversion = 0
        if fileName is not None:
            self.readinfo(fileName, filterChannelNames)

    def readinfo(self, fileName=None, filterChannelNames=False):

        """ Reads MDF file and extracts its complete structure

        Parameters
        ----------------
        fileName : str, optional
            file name. If not input, uses fileName attribute
        filterChannelNames : bool, optional
            flag to filter long channel names including module names separated by a '.'
        """

        if self.fileName is None:
            self.fileName = fileName
        # Open file
        try:
            fid = open(self.fileName, 'rb')
        except IOError:
            raise Exception('Can not find file ' + self.fileName)
        # Check whether file is MDF file -- assumes that every MDF file starts with the letters MDF
        if fid.read(3) not in ('MDF', b'MDF'):
            raise Exception('file ' + self.fileName + ' is not an MDF file!')
        # read Identifier block
        fid.seek(28)
        MDFVersionNumber = unpack('<H', fid.read(2))
        self.mdfversion = MDFVersionNumber[0]
        if self.mdfversion < 400:  # up to version 3.x not compatible with version 4.x
            from .mdfinfo3 import info3
            self.update(info3(None, fid, filterChannelNames))
        else:  # MDF version 4.x
            from .mdfinfo4 import info4
            self.update(info4(None, fid))

    def listChannels(self, fileName=None):

        """ Read MDF file blocks and returns a list of contained channels

        Parameters
        ----------------
        fileName : string
            file name

        Returns
        -----------
        nameList : list of string
            list of channel names
        """

        if self.fileName is None:
            self.fileName = fileName
        # Open file
        try:
            fid = open(self.fileName, 'rb')
        except IOError:
            raise Exception('Can not find file ' + self.fileName)
        # read Identifier block
        fid.seek(28)
        MDFVersionNumber = unpack('<H', fid.read(2))
        self.mdfversion = MDFVersionNumber[0]
        if self.mdfversion < 400:  # up to version 3.x not compatible with version 4.x
            from .mdfinfo3 import info3
            channelNameList = info3()
            nameList = channelNameList.listChannels3(self.fileName)
        else:
            from .mdfinfo4 import info4
            channelNameList = info4()
            nameList = channelNameList.listChannels4(self.fileName)
        return nameList


class mdf(mdf3, mdf4):

    """ mdf class

    Attributes
    --------------
    fileName : str
        file name
    MDFVersionNumber : int
        mdf file version number
    masterChannelList : dict
        Represents data structure: a key per master channel with corresponding value containing a list of channels
        One key or master channel represents then a data group having same sampling interval.
    multiProc : bool
        Flag to request channel conversion multi processed for performance improvement.
        One thread per data group.
    file_metadata : dict
        file metadata with minimum keys : author, organisation, project, subject, comment, time, date

    Methods
    ------------
    read( fileName = None, multiProc = False, channelList=None, convertAfterRead=True, filterChannelNames=False )
        reads mdf file version 3.x and 4.x
    write( fileName=None )
        writes simple mdf 3.3 file
    getChannelData( channelName )
        returns channel numpy array
    convertAllChannel()
        converts all channel data according to CCBlock information
    getChannelUnit( channelName )
        returns channel unit
    plot( channels )
        Plot channels with Matplotlib
    resample( samplingTime = 0.1, masterChannel=None )
        Resamples all data groups
    exportToCSV( filename = None, sampling = 0.1 )
        Exports mdf data into CSV file
    exportToNetCDF( filename = None, sampling = None )
        Exports mdf data into netcdf file
    exportToHDF5( filename = None, sampling = None )
        Exports mdf class data structure into hdf5 file
    exportToMatlab( filename = None )
        Exports mdf class data structure into Matlab file
    exportToExcel( filename = None )
        Exports mdf data into excel 95 to 2003 file
    exportToXlsx( filename=None )
        Exports mdf data into excel 2007 and 2010 file
    convertToPandas( sampling=None )
        converts mdf data structure into pandas dataframe(s)
    keepChannels( channelList )
        keeps only list of channels and removes the other channels
    mergeMdf( mdfClass ):
        Merges data of 2 mdf classes

    Notes
    --------
    mdf class is a nested dict
    Channel name is the primary dict key of mdf class
    At a higher level, each channel includes the following keys :
        - 'data' : containing vector of data (numpy)
        - 'unit' : unit (string)
        - 'master' : master channel of channel (time, crank angle, etc.)
        - 'description' : Description of channel
        - 'conversion': mdfinfo nested dict for CCBlock.
            Exist if channel not converted, used to convert with getChannelData method

    Examples
    --------------
    >>> import mdfreader
    >>> yop=mdfreader.mdf('NameOfFile')
    >>> yop.keys() # list channels names
    >>> yop.masterChannelList() # list channels grouped by raster or master channel
    >>> yop.plot('channelName') or yop.plot({'channel1','channel2'})
    >>> yop.resample(0.1) or yop.resample(channelName='master3')
    >>> yop.exportoCSV(sampling=0.01)
    >>> yop.exportNetCDF()
    >>> yop.exporttoHDF5()
    >>> yop.exporttoMatlab()
    >>> yop.exporttoExcel()
    >>> yop.exporttoXlsx()
    >>> yop.convertToPandas() # converts data groups into pandas dataframes
    >>> yop.keepChannels({'channel1','channel2','channel3'}) # drops all the channels except the one in argument
    >>> yop.getChannelData('channelName') # returns channel numpy array
    """

    def read(self, fileName=None, multiProc=False, channelList=None, convertAfterRead=True, filterChannelNames=False):
        """ reads mdf file version 3.x and 4.x

        Parameters
        ----------------
        fileName : str, optional
            file name

        multiProc : bool
            flag to activate multiprocessing of channel data conversion

        channelList : list of str, optional
            list of channel names to be read
            If you use channelList, reading might be much slower but it will save you memory. Can be used to read big files

        convertAfterRead : bool, optional
            flag to convert channel after read, True by default
            If you use convertAfterRead by setting it to false, all data from channels will be kept raw, no conversion applied.
            If many float are stored in file, you can gain from 3 to 4 times memory footprint
            To calculate value from channel, you can then use method .getChannelData()

        filterChannelNames : bool, optional
            flag to filter long channel names from its module names separated by '.'

        Notes
        --------
        If you keep convertAfterRead to true, you can set attribute mdf.multiProc to activate channel conversion in multiprocessing.
        Gain in reading time can be around 30% if file is big and using a lot of float channels

        Warning:
        ------------
        MultiProc use should be avoided when reading several files in a batch, it is not thread safe.
        You should better multi process instances of mdf rather than using multiproc in mdf class (see implementation of mdfconverter)
        """
        if self.fileName is None:
            self.fileName = fileName

        print(self.fileName)

        # read file blocks
        info = mdfinfo(self.fileName, filterChannelNames)

        self.MDFVersionNumber = info.mdfversion
        if self.MDFVersionNumber < 400:  # up to version 3.x not compatible with version 4.x
            self.read3(self.fileName, info, multiProc, channelList, convertAfterRead, filterChannelNames=False)
        else:  # MDF version 4.x. Channel by channel reading implemented
            self.read4(self.fileName, info, multiProc, channelList, convertAfterRead, filterChannelNames=False)

    def write(self, fileName=None):
        """Writes simple mdf 3.3 file

        Parameters
        ----------------
        fileName : str, optional
            Name of file
            If file name is not input, written file name will be the one read with appended '_new' string before extension

        Notes
        --------
        All channels will be converted, so size might be bigger than original file
        """
        if fileName is None:
            splitName = splitext(self.fileName)
            self.fileName = splitName[-2] + '_New' + splitName[-1]
        else:
            self.fileName = fileName
        # makes sure all channels are converted
        self.convertAllChannel()
        if self.MDFVersionNumber < 400:
            self.write3(fileName=self.fileName)
        else:
            self.write4(fileName=self.fileName)

    def getChannelData(self, channelName):
        """Return channel numpy array

        Parameters
        ----------------
        channelName : str
            channel name

        Returns:
        -----------
        numpy array
            converted, if not already done, data corresponding to channel name

        Notes
        ------
        This method is the safest to get channel data as numpy array from 'data' dict key might contain raw data
        """
        if self.MDFVersionNumber < 400:
            return self._getChannelData3(channelName)
        else:
            return self._getChannelData4(channelName)

    def convertAllChannel(self):
        """Converts all channels from raw data to converted data according to CCBlock information
        Converted data will take more memory.
        """
        if self.MDFVersionNumber < 400:
            return self._convertAllChannel3()
        else:
            return self._convertAllChannel4()

    def plot(self, channels):
        """Plot channels with Matplotlib

        Parameters
        ----------------
        channels : str or list of str
            channel name or list of channel names

        Notes
        ---------
        Channel description and unit will be tentatively displayed with axis labels
        """
        try:
            import matplotlib.pyplot as plt
        except:
            raise ImportError('matplotlib not found')
        if isinstance(channels, str):
            channels = {channels}
        for channelName in channels:
            if channelName in self:
                data = self.getChannelData(channelName)
                if data.dtype.kind not in ['S', 'U']:  # if channel not a string
                    self.fig = plt.figure()
                    # plot using matplotlib the channel versus master channel
                    if len(list(self.masterChannelList.keys())) == 1:  # Resampled signals
                        masterName = list(self.masterChannelList.keys())[0]
                        if not masterName:  # resampled channels, only one time channel most probably called 'master'
                            masterName = 'master'
                        if masterName in list(self.keys()):  # time channel properly defined
                            plt.plot(self.getChannelData(masterName), data)
                            plt.xlabel(masterName + ' [' + self.getChannelUnit(masterName) + ']')
                        else:  # no time channel found
                            plt.plot(data)
                    else:  # not resampled
                        master_name = self.getChannelMaster(channelName)
                        if master_name in list(self.keys()):  # master channel is proper channel name
                            plt.plot(self.getChannelData(master_name), data)
                            plt.xlabel(master_name + ' [' + self.getChannelUnit(master_name) + ']')
                        else:
                            plt.plot(data)

                    plt.title(self.getChannelDesc(channelName))
                    if self.getChannelUnit(channelName) == {}:
                        plt.ylabel(channelName)
                    else:
                        plt.ylabel(channelName + ' [' + self.getChannelUnit(channelName) + ']')
                    plt.grid(True)
                    plt.show()
            else:
                print(('Channel ' + channelName + ' not existing'))

    def allPlot(self):
        # plot all channels in the object, be careful for test purpose only,
        # can display many many many plots overloading your computer
        for Name in list(self.keys()):
            try:
                self.plot(Name)
            except:
                print(Name)

    def resample(self, samplingTime=None, masterChannel=None):
        """ Resamples all data groups into one data group having defined
        sampling interval or sharing same master channel

        Parameters
        ----------------
        samplingTime : float, optional
            resampling interval, None by default. If None, will merge all datagroups
            into a unique datagroup having the highest sampling rate from all datagroups
        **or**
        masterChannel : str, optional
            master channel name to be used for all channels

        Notes
        --------
        1. resampling is relatively safe for mdf3 as it contains only time series.
        However, mdf4 can contain also distance, angle, etc. It might make not sense
        to apply one resampling to several data groups that do not share same kind
        of master channel (like time resampling to distance or angle data groups)
        If several kind of data groups are used, you should better use pandas to resample

        2. resampling will convert all your channels so be careful for big files
        and memory consumption
        """
        if self: # mdf contains data 
            # must make sure all channels are converted
            self.convertAllChannel()
            masterData = None
            if masterChannel is None:  # create master channel if not proposed
                minTime = []
                maxTime = []
                length = []
                masterChannelName = 'master'
                for master in list(self.masterChannelList.keys()):
                    if master is not None and master != '' and \
                            master in self and self.masterChannelList[master]:
                        masterData = self.getChannelData(master)
                        if master in self and len(masterData) > 5:  # consider groups having minimum size
                            minTime.append(masterData[0])
                            maxTime.append(masterData[-1])
                            length.append(len(masterData))
                if minTime: # at least 1 datagroup has a master channel to be resampled
                    if samplingTime is None:
                        masterData = linspace(min(minTime), max(maxTime), num=max(length))
                    else:
                        masterData = arange(min(minTime), max(maxTime), samplingTime)
                    self.add_channel(0, masterChannelName, \
                        masterData, \
                        masterChannelName, \
                        master_type=self.getChannelMasterType(master), \
                        unit=self.getChannelUnit(master), \
                        description=self.getChannelDesc(master), \
                        conversion=None)
            else:
                masterChannelName = masterChannel # master channel defined in argument
                if masterChannel not in list(self.masterChannelList.keys()):
                    print('master channel name not in existing')
                    raise
            # resample all channels to one sampling time vector
            if len(list(self.masterChannelList.keys())) > 1:  # Not yet resampled or only 1 datagroup
                if masterChannel is None and masterData is not None:  # create master channel if not proposed
                    self.add_channel(0, masterChannelName, \
                        masterData, \
                        masterChannelName, \
                        master_type=self.getChannelMasterType(master), \
                        unit=self.getChannelUnit(master), \
                        description=self.getChannelDesc(master), \
                        conversion=None)

                # Interpolate channels
                timevect = []
                if masterChannelName in self:
                    masterData = self.getChannelData(masterChannelName)
                for Name in list(self.keys()):
                    try:
                        if Name not in list(self.masterChannelList.keys()):  # not a master channel
                            timevect = self.getChannelData(self.getChannelMaster(Name))
                            if not self.getChannelData(Name).dtype.kind in ('S', 'U'):  # if channel not array of string
                                self.setChannelData(Name, interp(masterData, timevect, self.getChannelData(Name)))
                            else:  # can not interpolate strings, remove channel containing string
                                self.remove_channel(Name)
                    except:
                        if len(timevect) != len(self.getChannelData(Name)):
                            print((Name + ' and master channel ' + self.getChannelMaster(Name) + ' do not have same length'))
                        elif not all(diff(timevect) > 0):
                            print((Name + ' has non regularly increasing master channel ' + self.getChannelMaster(Name)))
                # remove time channels in masterChannelList
                for ind in list(self.masterChannelList.keys()):
                    if ind != masterChannelName and ind in self:
                        del self[ind]
                self.masterChannelList = {}  # empty dict
                self.masterChannelList[masterChannelName] = list(self.keys())
            elif len(list(self.masterChannelList.keys())) == 1 and samplingTime is not None: # resamples only 1 datagroup
                masterData = self.getChannelData(list(self.masterChannelList.keys())[0])
                masterData = arange(masterData[0], masterData[-1], samplingTime)
                for Name in list(self.keys()):
                    timevect = self.getChannelData(self.getChannelMaster(Name))
                    self.setChannelData(Name, interp(masterData, timevect, self.getChannelData(Name)))
            elif samplingTime is None:
                print('Already resampled')
        else:
            print('no data to be resampled')

    def exportToCSV(self, filename=None, sampling=None):
        """Exports mdf data into CSV file

        Parameters
        ----------------
        filename : str, optional
            file name. If no name defined, it will use original mdf name and path

        sampling : float, optional
            sampling interval. None by default

        Notes
        --------
        Data saved in CSV fille be automatically resampled as it is difficult to save in this format
        data not sharing same master channel
        Warning: this can be slow for big data, CSV is text format after all
        """
        if self: # data in mdf
            import csv
            self.resample(sampling)
            if filename is None:
                filename = splitext(self.fileName)[0]
                filename = filename + '.csv'
            if PythonVersion < 3:
                f = open(filename, "wb")
            else:
                f = open(filename, "wt", encoding='latin-1')
            writer = csv.writer(f, dialect=csv.excel)
            # writes header
            writer.writerow([name for name in list(self.keys()) \
                    if self.getChannelData(name).dtype.kind not in ('S', 'U', 'V') \
                    and self.getChannelData(name).ndim <= 1])  # writes channel names
            if PythonVersion < 3:
                units = []
                for name in list(self.keys()):
                    data = self.getChannelData(name)
                    if data.dtype.kind not in ('S', 'U', 'V') \
                            and data.ndim <= 1:
                        if self.getChannelUnit(name) is bytes:
                            units.append(self.getChannelUnit(name).encode('unicode', 'ignore'))
                        else:
                            try:
                                units.append(self.getChannelUnit(name).encode('latin-1','replace'))
                            except:
                                units.append(self.getChannelUnit(name))
                writer.writerow(units)  # writes units
            else:
                writer.writerow([self.getChannelUnit(name) \
                        for name in list(self.keys()) 
                        if self.getChannelData(name).dtype.kind not in ('S', 'U', 'V') \
                        and self.getChannelData(name).ndim <= 1])  # writes units
            # concatenate all channels
            temp=[]
            for name in list(self.keys()):
                data = self.getChannelData(name)
                if data.dtype.kind not in ('S', 'U', 'V') \
                        and data.ndim <= 1:
                    temp.append(data.transpose())
            if temp:
                buf = vstack(temp)
                buf = buf.transpose()
                # Write all rows
                r, c = buf.shape
                writer.writerows([list(buf[i, :]) for i in range(r)])
            f.close()
        else:
            print('no data to be exported')

    def exportToNetCDF(self, filename=None, sampling=None):
        """Exports mdf data into netcdf file

        Parameters
        ----------------
        filename : str, optional
            file name. If no name defined, it will use original mdf name and path

        sampling : float, optional
            sampling interval.

        Dependency
        -----------------
        scipy
        """
        try:
            from scipy.io import netcdf
        except:
            raise ImportError('scipy.io module not found')

        def cleanName(name):
            allowedStr = ' ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-+_.@'
            buf = ''
            for c in name:
                if c in allowedStr:
                    buf += c
            return buf

        def setAttribute(f, name, value):
            if value is not None and len(value) > 0:  # netcdf does not allow empty strings...
                if value is dict and 'name' in value:
                    value = value['name']
                if PythonVersion >= 3 and value is bytes:
                    value = value.encode('utf-8', 'ignore')
                value = cleanName(value)
                setattr(f, name, value)
            else:
                pass
        if sampling is not None:
            self.resample(sampling)
        if filename is None:
            filename = splitext(self.fileName)[0]
            filename = filename + '.nc'
        f = netcdf.netcdf_file(filename, 'w')
        setAttribute(f, 'Date', self.file_metadata['date'])
        setAttribute(f, 'Time', self.file_metadata['time'])
        setAttribute(f, 'Author', self.file_metadata['author'])
        setAttribute(f, 'Organization', self.file_metadata['organisation'])
        setAttribute(f, 'ProjectName', self.file_metadata['project'])
        setAttribute(f, 'Subject', self.file_metadata['subject'])
        setAttribute(f, 'Comment', self.file_metadata['comment'])
        # Create dimensions having name of all time channels
        for master in list(self.masterChannelList.keys()):
            f.createDimension(master, len(self.getChannelData(self.masterChannelList[master][0])))
        # Create variables definition, dimension and attributes
        var = {}
        for name in list(self.keys()):
            data = self.getChannelData(name)
            if data.dtype == 'float64':
                dataType = 'd'
            elif data.dtype == 'float32':
                dataType = 'f'
            elif data.dtype in ['int8', 'int16', 'uint8', 'uint16']:
                dataType = 'h'
            elif data.dtype in ['int32', 'uint32']:
                dataType = 'i'
            elif data.dtype.kind in ['S', 'U']:
                dataType = 'c'
            else:
                dataType = None
                print(('Can not process numpy type ' + str(data.dtype)\
                     + ' of channel ' + name))
            if dataType is not None:
                # create variable
                CleanedName = cleanName(name)
                if len(list(self.masterChannelList.keys())) == 1:  # mdf resampled
                    var[name] = f.createVariable(CleanedName, dataType, (list(self.masterChannelList.keys())[0], ))
                else:  # not resampled
                    var[name] = f.createVariable(CleanedName, dataType, (self.getChannelMaster(name), ))
                # Create attributes
                setAttribute(var[name], 'title', CleanedName)
                setAttribute(var[name], 'units', self.getChannelUnit(name))
                setAttribute(var[name], 'Description', self.getChannelDesc(name))
                if name in list(self.masterChannelList.keys()):
                    setAttribute(var[name], 'Type', 'Master Channel')
                    setAttribute(var[name], 'datatype', 'master')
                else:
                    setAttribute(var[name], 'Type', 'Data Channel')
        # put data in variables
        for name in list(self.keys()):
            var[name] = self.getChannelData(name)
        f.close()

    def exportToHDF5(self, filename=None, sampling=None):
        """Exports mdf class data structure into hdf5 file

        Parameters
        ----------------
        filename : str, optional
            file name. If no name defined, it will use original mdf name and path

        sampling : float, optional
            sampling interval.

        Dependency
        ------------------
        h5py

        Notes
        --------
        The maximum attributes will be stored
        Data structure will be similar has it is in masterChannelList attribute
        """
        #
        try:
            import h5py
            import os
        except:
            raise ImportError('h5py not found')

        def setAttribute(obj, name, value):
            if value is not None and len(value) > 0:
                try:
                    if value is dict and 'name' in value:
                        value = value['name']
                    obj.attrs[name] = value
                except:
                    pass
            else:
                pass
        if sampling is not None:
            self.resample(sampling)
        if filename is None:
            filename = splitext(self.fileName)[0]
            filename = filename + '.hdf'
        f = h5py.File(filename, 'w')  # create hdf5 file
        filegroup = f.create_group(os.path.basename(filename))  # create group in root associated to file
        setAttribute(filegroup, 'Author', self.file_metadata['author'])
        setAttribute(filegroup, 'Date', self.file_metadata['date'])
        setAttribute(filegroup, 'Time', self.file_metadata['time'])
        setAttribute(filegroup, 'Time', self.file_metadata['time'])
        setAttribute(filegroup, 'Organization', self.file_metadata['organisation'])
        setAttribute(filegroup, 'ProjectName', self.file_metadata['project'])
        setAttribute(filegroup, 'Subject', self.file_metadata['subject'])
        setAttribute(filegroup, 'Comment', self.file_metadata['comment'])
        if len(list(self.masterChannelList.keys())) > 1:
            # if several time groups of channels, not resampled
            groups = {}
            ngroups = 0
            grp = {}
            for channel in list(self.keys()):
                channelData = self.getChannelData(channel)
                masterName = self.getChannelMaster(channel)
                if 'master' in self[channel] and masterName not in list(groups.keys()):
                    # create new data group
                    ngroups += 1
                    if masterName!='' \
                            and masterName is not None:
                        group_name = masterName
                    else:
                        group_name = 'master'+str(ngroups)
                    groups[group_name] = ngroups
                    grp[ngroups] = filegroup.create_group(group_name)
                elif 'master' in self[channel] and masterName in list(groups.keys()):
                    group_name = masterName
                if channelData.dtype.kind not in ('U', 'O'):  # not supported type
                    dset = grp[groups[group_name]].create_dataset(channel, data=channelData)
                    setAttribute(dset, 'unit', self.getChannelUnit(channel))
                    if 'description' in self[channel]:
                        setAttribute(dset, 'description', self.getChannelDesc(channel))
        else:  # resampled or only one time for all channels : no groups
            for channel in list(self.keys()):
                channelData = self.getChannelData(channel)
                if channelData.dtype.kind not in ('U', 'O'):  # not supported type
                    channelName = _convertMatlabName(channel)
                    dset = filegroup.create_dataset(channelName, data=channelData)
                    setAttribute(dset, 'unit', self.getChannelUnit(channel))
                    if 'description' in self[channel]:
                        setAttribute(dset, 'description', self.getChannelDesc(channel))
        f.close()

    def exportToMatlab(self, filename=None):
        """Export mdf data into Matlab file format 5, tentatively compressed

        Parameters
        ----------------
        filename : str, optional
            file name. If no name defined, it will use original mdf name and path

        Dependency
        ------------------
        scipy

        Notes
        --------
        This method will dump all data into Matlab file but you will loose below information:
        - unit and descriptions of channel
        - data structure, what is corresponding master channel to a channel. Channels might have then different lengths
        """
        # export class data struture into .mat file
        try:
            from scipy.io import savemat
        except:
            raise ImportError('scipy module not found')
        if filename is None:
            filename = splitext(self.fileName)[0]
            filename = filename + '.mat'
        # convert self into simple dict without and metadata
        temp = {}
        for channel in list(self.keys()):
            data = self.getChannelData(channel)
            if data.dtype.kind not in ('S', 'U', 'V'):  # does not like special characters chains, skip
                channelName = _convertMatlabName(channel)
                temp[channelName] = data
        try:  # depends of version used , compression can be used
            savemat(filename, temp, long_field_names=True, format='5', do_compression=True, oned_as='column')
        except:
            savemat(filename, temp, long_field_names=True, format='5')

    def exportToExcel(self, filename=None):
        """Exports mdf data into excel 95 to 2003 file

        Parameters
        ----------------
        filename : str, optional
            file name. If no name defined, it will use original mdf name and path

        Dependencies
        --------------------
        xlwt for python 2.6+
        xlwt3 for python 3.2+

        Notes
        --------
        xlwt is not fast for even for small files, consider other binary formats like HDF5 or Matlab
        If there are more than 256 channels, data will be saved over different worksheets
        Also Excel 203 is becoming rare these days
        """
        try:
            if PythonVersion < 3:
                import xlwt
            else:
                import xlwt3 as xlwt
        except:
            raise ImportError('xlwt module missing')
        if filename is None:
            filename = filename = splitext(self.fileName)[0]
            filename = filename + '.xls'
        styleText = xlwt.easyxf('font: name Times New Roman, color-index black, bold off')
        coding = 'utf-8'
        wb = xlwt.Workbook(encoding=coding)
        channelList = list(self.keys())
        if PythonVersion < 3:
            Units = [self.getChannelUnit(channel).decode(coding, 'replace') for channel in list(self.keys())]
        else:
            Units = [self.getChannelUnit(channel) for channel in list(self.keys())]
        # Excel 2003 limits
        maxCols = 255
        maxLines = 65535
        workbooknumber = int(ceil(len(channelList) * 1.0 / (maxCols * 1.0)))
        tooLongChannels = []
        # split colmuns in several worksheets if more than 256 cols
        for workbook in range(workbooknumber):
            ws = wb.add_sheet('Sheet' + str(workbook))  # , cell_overwrite_ok = True )
            if workbook == workbooknumber - 1:  # last sheet
                columnrange = list(range(workbook * maxCols, len(channelList)))
            elif workbook < workbooknumber - 1 and workbooknumber > 1:  # first sheets
                columnrange = list(range(workbook * maxCols, (workbook + 1) * maxCols))
            for col in columnrange:
                # write header
                ws.write(0, col - workbook * maxCols, channelList[col], styleText)
                ws.write(1, col - workbook * maxCols, Units[col], styleText)
                vect = self.getChannelData(channelList[col])  # data vector
                if not len(vect) > maxLines:
                    if vect.dtype.kind not in ['S', 'U']:  # if not a string or unicode
                        [ws.row(row + 2).set_cell_number(col - workbook * maxCols, vect[row]) for row in list(range(len(vect)))]
                    else:  # it's a string, cannot write for the moment
                        if PythonVersion < 3:
                            try:
                                vect = vect.encode(coding)
                            except:
                                pass
                        [ws.row(row + 2).set_cell_text(col - workbook * maxCols, vect[row]) for row in list(range(len(vect)))]
                else:  # channel too long, written until max Excel line limit
                    if vect.dtype.kind not in ['S', 'U']:  # if not a string
                        [ws.row(row + 2).set_cell_number(col - workbook * maxCols, vect[row]) for row in list(range(maxLines))]
                    else:  # it's a string, cannot write for the moment
                        if PythonVersion < 3:
                            vect = vect.encode(coding)
                        [ws.row(row + 2).set_cell_text(col - workbook * maxCols, vect[row]) for row in list(range(maxLines))]
                    tooLongChannels.append(channelList[col])  # to later warn user the channel is not completely written
        wb.save(filename)  # writes workbook on HDD
        if len(tooLongChannels) > 0:  # if not empty, some channels have been not processed
            print('Following channels were too long to be processed completely, maybe you should resample : ')
            print(tooLongChannels)

    def exportToXlsx(self, filename=None):
        """Exports mdf data into excel 2007 and 2010 file

        Parameters
        ----------------
        filename : str, optional
            file name. If no name defined, it will use original mdf name and path

        Dependency
        -----------------
        openpyxl

        Notes
        --------
        It is recommended to export resampled data for performances
        """
        try:
            import openpyxl
        except:
            raise ImportError('Module openpyxl missing')
        if filename is None:
            filename = splitext(self.fileName)[0]
            filename = filename + '.xlsx'
        channels = list(self.keys())
        maxRows = max([len(self.getChannelData(channel)) for channel in list(self.keys())])  # find max column length
        maxCols = len(list(self.keys()))  # number of columns
        print('Creating Excel sheet')
        if len(list(self.masterChannelList.keys())) > 1:  # not resampled data, can be long, writing cell by cell !
            wb = openpyxl.workbook.Workbook(encoding='utf-8')
            ws = wb.active #get_active_sheet()
            # write header
            if PythonVersion < 3:
                for j in range(maxCols):
                    ws.cell(row=1, column=j+1).value = channels[j]
                    ws.cell(row=2, column=j+1).value = self.getChannelUnit(channels[j])
            else:
                for j in range(maxCols):
                    ws.cell(row=1, column=j+1).value = channels[j]
                    ws.cell(row=2, column=j+1).value = self.getChannelUnit(channels[j])
            # arrange data
            for j in range(maxCols):
                data = self.getChannelData(channels[j])
                if data.ndim <= 1: # not an array channel
                    if data.dtype.kind in ('i', 'u') or 'f4' in data.dtype.str:
                        for r in range(len(data)):
                            ws.cell(row=r + 3, column=j+1).value = float64(data[r])
                    elif data.dtype.kind not in ('V', 'U'):
                        for r in range(len(data)):
                            ws.cell(row=r + 3, column=j+1).value = data[r]
        else:  # resampled data
            wb = openpyxl.workbook.Workbook(optimized_write=True, encoding='utf-8')
            ws = wb.create_sheet()
            # write header
            ws.append(channels)
            ws.append([self.getChannelUnit(channel) for channel in list(self.keys())])
            # write data
            maxRows = max([len(self.getChannelData(channel)) for channel in list(self.keys())])  # find max column length
            maxCols = len(list(self.keys()))  # number of columns
            bigmat = zeros(maxRows)  # create empty column
            buf = bigmat
            for col in range(maxCols):
                data = self.getChannelData(channels[col])
                if data.ndim <= 1: # not an array channel
                    if data.dtype.kind not in ('S', 'U', 'V'):
                        chanlen = len(data)
                        if chanlen < maxRows:
                            buf[:] = None
                            buf[0:chanlen] = data
                            bigmat = vstack((bigmat, buf))
                        else:
                            bigmat = vstack((bigmat, data))
                    else:
                        buf[:] = None
                        bigmat = vstack((bigmat, buf))
            bigmat = delete(bigmat, 0, 0)
            [ws.append(list(bigmat[:, row])) for row in range(maxRows)]
        print('Writing file, please wait')
        wb.save(filename)

    def keepChannels(self, channelList):
        """ keeps only list of channels and removes the other channels

        Parameters
        ----------------
        channelList : list of str
            list of channel names
        """
        channelList = [channel for channel in channelList]
        removeChannels = []
        for channel in list(self.keys()):
            if channel not in channelList and 'master' not in channel and channel not in list(self.masterChannelList.keys()):
                # avoid to remove master channels otherwise problems with resample
                removeChannels.append(channel)
        if not len(removeChannels) == 0:
            [self.masterChannelList[self.getChannelMaster(channel)].remove(channel) for channel in removeChannels]
            [self.pop(channel) for channel in removeChannels]

    def mergeMdf(self, mdfClass):
        """Merges data of 2 mdf classes

        Parameters
        ----------------
        mdfClass : mdf
            mdf class instance to be merge with self

        Notes
        --------
        both classes must have been resampled, otherwise, impossible to know master channel to match
        create union of both channel lists and fill with Nan for unknown sections in channels
        """
        self.convertAllChannel()  # make sure all channels are converted
        if not len(list(self.masterChannelList.keys())) == 1:
            raise Exception('Data not resampled')
        unionedList = list(mdfClass.keys()) and list(self.keys())
        initialTimeSize = len(self.getChannelData('master'))
        for channel in unionedList:
            if channel in mdfClass and channel in self:  # channel exists in both class
                data = self.getChannelData(channel)
                mdfData = mdfClass.getChannelData(channel)
                if not channel == 'master':
                    self.setChannelData(channel, hstack((data, mdfData)))
                else:
                    offset = mean(diff(mdfData))  # sampling
                    offset = data[-1] + offset  # time offset
                    self.setChannelData(channel, hstack((data, mdfData + offset)))
            elif channel in mdfClass:  # new channel for self from mdfClass
                mdfData = mdfClass.getChannelData(channel)
                self[channel] = mdfClass[channel]  # initialise all fields, units, descriptions, etc.
                refill = empty(initialTimeSize)
                refill.fil(nan)  # fill with NANs
                self.setChannelData(channel, hstack((refill, mdfData)))  # readjust against time
            else:  # channel missing in mdfClass
                data = self.getChannelData(channel)
                refill = empty(len(mdfClass.getChannelData('master')))
                refill.fill(nan)  # fill with NANs
                self.setChannelData(channel, hstack((data, refill)))

    def convertToPandas(self, sampling=None):
        """converts mdf data structure into pandas dataframe(s)

        Parameters
        ----------------
        sampling : float, optional
            resampling interval

        Notes
        --------
        One pandas dataframe is converted per data group
        Not adapted yet for mdf4 as it considers only time master channels
        """
        # convert data structure into pandas module
        try:
            import pandas as pd
        except:
            raise ImportError('Module pandas missing')
        if sampling is not None:
            self.resample(sampling)
        if self.file_metadata['date'] != '' and self.file_metadata['time']!='':
            date = self.file_metadata['date'].replace(':', '-')
            time = self.file_metadata['time']
            datetimeInfo = datetime64(date + 'T' + time)
        else:
            datetimeInfo = datetime64(datetime.now())
        originalKeys = list(self.keys())
        for group in list(self.masterChannelList.keys()):
            if group not in self.masterChannelList[group]:
                print('no master channel in group ' + group)
            elif self.getChannelMasterType(group)!=1:
                print('Warning: master channel is not time, not appropriate conversion for pandas')
            temp = {}
            # convert time channel into timedelta
            if group in self.masterChannelList[group]:
                time = datetimeInfo + array(self.getChannelData(group) * 1E6, dtype='timedelta64[us]')
                for channel in self.masterChannelList[group]:
                    data = self.getChannelData(channel)
                    if data.ndim == 1 and data.shape == time.shape:
                        temp[channel] = pd.Series(data, index=time)
                self[group + '_group'] = pd.DataFrame(temp)
                self[group + '_group'].pop(group)  # delete time channel, no need anymore
            else: # no master channel in channel group
                for channel in self.masterChannelList[group]:
                    data = self.getChannelData(channel)
                    if data.ndim == 1:
                        temp[channel] = pd.Series(data)
                self[group + '_group'] = pd.DataFrame(temp)
        # clean rest of self from data and time channel information
        [self[channel].pop('data') for channel in originalKeys]
        [self[channel].pop('master') for channel in originalKeys if 'master' in self[channel]]
        self.masterGroups = []  # save time groups name in list
        [self.masterGroups.append(group + '_group') for group in list(self.masterChannelList.keys())]
        self.masterChannelList = {}
        self._pandasframe = True

if __name__ == "__main__":
    try:
        from multiprocessing import freeze_support
        freeze_support()
    except:
        None
    parser = ArgumentParser(prog='mdfreader', description='reads mdf file')
    parser.add_argument('--export', dest='export', default=None, \
            choices=['CSV', 'HDF5', 'Matlab', 'Xlsx', 'Excel', 'NetCDF', 'MDF3'], \
            help='Export after parsing to defined file type')
    parser.add_argument('--list_channels', dest='list_channels', action='store_true', \
            help='list of channels in file')
    parser.add_argument('fileName', help='mdf file name')
    parser.add_argument('--channelList', dest='channelList', nargs='+', type=str, \
            default=None, help='list of channels to only read')
    parser.add_argument('--plot', dest='plot_channel_list', nargs='+', type=str, \
            default=None, help='plots list of channels')
    parser.add_argument('--noConversion', action='store_false', \
            help='Do not convert raw channel data \
            to physical values just after reading. Useful if you have memory concerns')
    parser.add_argument('--filterChannelNames', action='store_true', \
            help='activates channel name filtering; \
            removes modules names separated by a point character')

    args = parser.parse_args()

    temp = mdf(fileName=args.fileName, channelList=args.channelList)
    #, converAfterRead=args.convertAfterRead, filterChannelNames=args.filterChannelNames)
    if args.export is not None:
        if args.export == 'CSV':
            temp.exportToCSV()
        elif args.export == 'HDF5':
            temp.exportToHDF5()
        elif args.export == 'Matlab':
            temp.exportToMatlab()
        elif args.export == 'Xlsx':
            temp.exportToXlsx()
        elif args.export == 'Excel':
            temp.exportToExcel()
        elif args.export == 'NetCDF':
            temp.exportToNetCDF()
        elif args.export == 'MDF3':
            temp.write()
    if args.plot_channel_list is not None:
        temp.plot(args.plot_channel_list)
    if args.list_channels:
        print(temp.masterChannelList)
