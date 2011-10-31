#!/usr/bin/env python

##############################################################################
##
## This file is part of Sardana
##
## http://www.tango-controls.org/static/sardana/latest/doc/html/index.html
##
## Copyright 2011 CELLS / ALBA Synchrotron, Bellaterra, Spain
## 
## Sardana is free software: you can redistribute it and/or modify
## it under the terms of the GNU Lesser General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
## 
## Sardana is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU Lesser General Public License for more details.
## 
## You should have received a copy of the GNU Lesser General Public License
## along with Sardana.  If not, see <http://www.gnu.org/licenses/>.
##
##############################################################################

"""This module is part of the Python Pool libray. It defines the base classes
for"""

__all__ = ["CONTROLLER_TEMPLATE", "CTRL_TYPE_MAP", "TYPE_MAP", "TYPE_MAP_OBJ",
           "TypeData", "DTYPE_MAP", "DACCESS_MAP", "DataInfo",
           "ControllerLib", "ControllerClass"]

__docformat__ = 'restructuredtext'

import inspect
import os
import operator
import types

from taurus.core.util import CaselessDict, CodecFactory

from sardana import DataType, DataFormat, DataAccess, \
    DTYPE_MAP, DACCESS_MAP, to_dtype_dformat, to_daccess, \
    ElementType, TYPE_ELEMENTS
from sardana.sardanameta import SardanaMetaLib, SardanaMetaClass

from poolcontroller import PoolController, PoolPseudoMotorController
from poolmotor import PoolMotor
from poolpseudomotor import PoolPseudoMotor
from poolmotorgroup import PoolMotorGroup
from poolmeasurementgroup import PoolMeasurementGroup
from poolcountertimer import PoolCounterTimer
from poolinstrument import PoolInstrument
from controller import Controller, MotorController, CounterTimerController, \
    PseudoMotorController

#: String containing template code for a controller class
CONTROLLER_TEMPLATE = """class @controller_name@(@controller_type@):
    \"\"\"@controller_name@ description.\"\"\"
    
"""

ET = ElementType

#: a dictionary dict<:data:`~sardana.ElementType`, class>
#: mapping element type enumeration with the corresponding controller pool class
#: (:class:`~sardana.pool.poolcontroller.PoolController` or sub-class of it).
CTRL_TYPE_MAP = {
    ET.Motor        : PoolController,
    ET.CTExpChannel : PoolController,
    ET.PseudoMotor  : PoolPseudoMotorController,
}

#: dictionary dict<:data:`~sardana.ElementType`, :class:`tuple`> 
#: where tuple is a sequence:
#: 
#: #. type string representation
#: #. family
#: #. internal pool class
#: #. automatic full name
#: #. controller class
TYPE_MAP = {
    ET.Ctrl             : ("Controller",       "Controller",       CTRL_TYPE_MAP,          "controller/{klass}/{name}",  Controller),
    ET.Instrument       : ("Instrument",       "Instrument",       PoolInstrument,         "{full_name}",                None),
    ET.Motor            : ("Motor",            "Motor",            PoolMotor,              "motor/{ctrl_name}/{axis}",   MotorController),
    ET.CTExpChannel     : ("CTExpChannel",     "ExpChannel",       PoolCounterTimer,       "expchan/{ctrl_name}/{axis}", CounterTimerController),
    ET.PseudoMotor      : ("PseudoMotor",      "Motor",            PoolPseudoMotor,        "pm/{ctrl_name}/{axis}",      PseudoMotorController),
    ET.MotorGroup       : ("MotorGroup",       "MotorGroup",       PoolMotorGroup,         "mg/{pool_name}/{name}",      None),
    ET.MeasurementGroup : ("MeasurementGroup", "MeasurementGroup", PoolMeasurementGroup,   "mntgrp/{pool_name}/{name}",  None),
}

class TypeData(object):
    """Information for a specific Element type"""
    
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

#: dictionary
#: dict<:data:`~sardana.ElementType`, :class:`~sardana.pool.poolmetacontroller.TypeData`>
TYPE_MAP_OBJ = {}
for t, d in TYPE_MAP.items():
    o = TypeData(type=t, name=d[0], family=d[1], klass=d[2] ,
                 auto_full_name=d[3], ctrl_klass=d[4])
    TYPE_MAP_OBJ[t] = o


class ControllerLib(SardanaMetaLib):
    """Object representing a python module containning controller classes.
       Public members:
       
           - module - reference to python module
           - f_path - complete (absolute) path and filename
           - f_name - filename (including file extension)
           - path - complete (absolute) path
           - name - module name (without file extension)
           - controller_list - list<ControllerClass>
           - exc_info - exception information if an error occured when loading 
                        the module
    """
    
    def __init__(self, **kwargs):
        kwargs['manager'] = kwargs.pop('pool')
        SardanaMetaLib.__init__(self, **kwargs)
    
    add_controller = SardanaMetaLib.add_meta_class
    get_controller = SardanaMetaLib.get_meta_class
    get_controllers = SardanaMetaLib.get_meta_classes
    has_controller = SardanaMetaLib.has_meta_class


class DataInfo(object):
    
    def __init__(self, name, dtype, dformat=DataFormat.Scalar,
                 access=DataAccess.ReadWrite, description="", default_value=None,
                 fget=None, fset=None):
        self.name = name
        self.dtype = dtype
        self.dformat = dformat
        self.access = access
        self.description = description
        self.default_value = default_value
        self.fget = fget or "get%s" % name
        self.fset = fset or "set%s" % name
    
    @classmethod
    def toDataInfo(klass, name, info):
        info = CaselessDict(info)
        dformat = DataFormat.Scalar
        dtype = info['type']
        dtype, dformat = to_dtype_dformat(dtype)
        default_value = info.get('defaultvalue')
        description = info.get('description', '')
        daccess = info.get('r/w type', DataAccess.ReadWrite)
        daccess = to_daccess(daccess)
        fget = info.get('fget')
        fset = info.get('fset')
        if default_value is not None and dtype != DataType.String:
            if type(default_value) in types.StringTypes:
                default_value = eval(default_value)
        return DataInfo(name, dtype, dformat, daccess, description,
                        default_value, fget, fset)
    
    def toDict(self):
        return { 'name' : self.name, 'type' : DataType.whatis(self.dtype),
                 'format' : DataFormat.whatis(self.dformat),
                 'access' : DataAccess.whatis(self.access),
                 'description' : self.description,
                 'default_value' : self.default_value }
    
    def serialize(self, *args, **kwargs):
        kwargs.update(self.toDict())
        return kwargs
    
#class PropertyInfo(DataInfo):
    
#    def __init__(self, name, dtype, dformat=DataFormat.Scalar,
#                 description="", default_value=None):
#        DataInfo.__init__(self, name, dtype, dformat, access=DataAcces.ReadWrite,
#                          description=description, default_value=default_value)


#class AttributeInfo(DataInfo):

#    def __init__(self, name, dtype, dformat=DataFormat.Scalar,
#                 access=DataAccess.ReadWrite, description=""):
#        DataInfo.__init__(self, name, dtype, dformat, access=DataAcces.ReadWrite,
#                          description=description, default_value=None)


class ControllerClass(object):
    """Object representing a python controller class. 
       Public members:
       
           - name - class name
           - klass - python class object
           - lib - ControllerLib object representing the module where the
             controller is.
    """
    
    NoDoc = '<Undocumented controller>'
    
    def __init__(self, lib, klass, name=None):
        self.klass = klass
        self.name = name or klass.__name__
        self.lib = lib
        self.types = []
        self.errors = []
        self.dict_extra = {}
        self.api_version = 1
        
        # Generic controller information
        self._ctrl_features = tuple(klass.ctrl_features)
        
        self._ctrl_properties = props = CaselessDict()
        for k, v in klass.class_prop.items(): # old member
            props[k] = DataInfo.toDataInfo(k, v)
        for k, v in klass.ctrl_properties.items():
            props[k] = DataInfo.toDataInfo(k, v)
        
        self._ctrl_attributes = ctrl_attrs = CaselessDict()
        for k, v in klass.ctrl_attributes.items():
            ctrl_attrs[k] = DataInfo.toDataInfo(k, v)
        
        self._axis_attributes = axis_attrs = CaselessDict()
        for k, v in klass.ctrl_extra_attributes.items(): # old member
            axis_attrs[k] = DataInfo.toDataInfo(k, v)
        for k, v in klass.axis_attributes.items():
            axis_attrs[k] = DataInfo.toDataInfo(k, v)
        
        self.types = types = self.__build_types()
        
        if ElementType.PseudoMotor in types:
            self.motor_roles = tuple(klass.motor_roles)
            self.pseudo_motor_roles = tuple(klass.pseudo_motor_roles)
            self.dict_extra['motor_roles'] = self.motor_roles
            self.dict_extra['pseudo_motor_roles'] = self.pseudo_motor_roles
        
        init_args = inspect.getargspec(klass.__init__)
        if init_args.varargs is None or init_args.keywords is None:
            self.api_version = 0
        
    def __build_types(self):
        types = []
        klass = self.klass
        for _type, type_data in TYPE_MAP_OBJ.items():
            if not _type in TYPE_ELEMENTS:
                continue
            if issubclass(klass, type_data.ctrl_klass):
                types.append(_type)
        return types
    
    def __cmp__(self, o):
        if o is None: return cmp(self.getName(), None)
        return cmp(self.getName(), o.getName())

    def __str__(self):
        return self.getName()
    
    def serialize(self, *args, **kwargs):
        kwargs.update(self.toDict())
        return kwargs
    
    def str(self, *args, **kwargs):
        raise NotImplementedError
    
    def toDict(self):
        name = self.getName()
        module_name = self.getModuleName()
        ret = dict(name=name,
                   full_name=name + "." + module_name,
                   id=0,
                   module=module_name,
                   filename=self.getFileName(),
                   description=self.getDescription(),
                   gender=self.getGender(),
                   model=self.getModel(),
                   organization=self.getOrganization(),
                   api_version=self.api_version,)

        ctrl_types = map(ElementType.whatis, self.getTypes())
        ret['types'] = ctrl_types
        
        ctrl_props = {}
        for ctrl_prop in self.getControllerProperties().values():
            ctrl_props[ctrl_prop.name] = ctrl_prop.toDict()
        ctrl_attrs = {}
        for ctrl_attr in self.getControllerAttributes().values():
            ctrl_attrs[ctrl_attr.name] = ctrl_attr.toDict()
        axis_attrs = {}
        for axis_attr in self.getAxisAttributes().values():
            axis_attrs[axis_attr.name] = axis_attr.toDict()
        
        ret['ctrl_properties'] = ctrl_props
        ret['ctrl_attributes'] = ctrl_attrs
        ret['axis_attributes'] = axis_attrs
        ret['ctrl_features'] = self.getControllerFeatures()
        ret['type'] = self.__class__.__name__
        ret.update(self.dict_extra)
        return ret
    
    def setTypes(self, types):
        self.types = types

    def getTypes(self):
        return self.types

    def getControllerLib(self):
        return self.lib
    
    def getControllerClass(self):
        return self.klass

    def getName(self):
        return self.name

    def getFullName(self):
        return '%s.%s' % (self.getModuleName(), self.getName())

    def getModuleName(self):
        return self.getControllerLib().getModuleName()

    def getFileName(self):
        return self.getControllerLib().getFileName()
    
    def getSimpleFileName(self):
        return self.getControllerLib().getSimpleFileName()
    
    def getDescription(self):
        return self.getControllerClass().__doc__ or ControllerClass.NoDoc

    def getBriefDescription(self, max_chars=60):
        d = self.getControllerClass().__doc__ or ControllerClass.NoDoc
        d = d.replace('\n',' ')
        if len(d) > max_chars: d = d[:max_chars-5] + '[...]'
        return d
    
    def getCode(self):
        """Returns a tuple (sourcelines, firstline) corresponding to the 
        definition of the controller class. sourcelines is a list of source code 
        lines. firstline is the line number of the first source code line.
        """
        return inspect.getsourcelines(self.getControllerClass())
    
    def getGender(self):
        return self.getControllerClass().gender
    
    def getModel(self):
        return self.getControllerClass().model
    
    def getOrganization(self):
        return self.getControllerClass().organization
    
    def getImage(self):
        return self.getControllerClass().image
    
    def getLogo(self):
        return self.getControllerClass().logo
    
    def getControllerProperties(self):
        return self._ctrl_properties
    
    def getControllerAttributes(self):
        return self._ctrl_attributes
    
    def getAxisAttributes(self):
        return self._axis_attributes
    
    def getControllerFeatures(self):
        return self._ctrl_features
    
    