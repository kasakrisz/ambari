#!/usr/bin/env python

'''
Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''

__all__ = ["Script"]

import sys
import json
import logging

from resource_management.core.environment import Environment
from resource_management.core.exceptions import Fail
from resource_management.core.resources.packaging import Package
from resource_management.libraries.script.config_dictionary import ConfigDictionary
from resource_management.libraries.script.repo_installer import RepoInstaller

class Script():
  """
  Executes a command for custom service. stdout and stderr are written to
  tmpoutfile and to tmperrfile respectively.
  Script instances share configuration as a class parameter and therefore
  even different Script instances can not be used from different threads at
  the same time
  """
  structuredOut = {}

  def put_structured_out(self, sout):
    Script.structuredOut.update(sout)
    try:
      structuredOut = json.dumps(Script.structuredOut)
      with open(self.stroutfile, 'w') as fp:
        json.dump(structuredOut, fp)
    except IOError:
      Script.structuredOut.update({"errMsg" : "Unable to write to " + self.stroutfile})

  def execute(self):
    """
    Sets up logging;
    Parses command parameters and executes method relevant to command type
    """
    # set up logging (two separate loggers for stderr and stdout with different loglevels)
    logger = logging.getLogger('resource_management')
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    chout = logging.StreamHandler(sys.stdout)
    chout.setLevel(logging.DEBUG)
    chout.setFormatter(formatter)
    cherr = logging.StreamHandler(sys.stderr)
    cherr.setLevel(logging.ERROR)
    cherr.setFormatter(formatter)
    logger.addHandler(cherr)
    logger.addHandler(chout)
    # parse arguments
    if len(sys.argv) < 5:
      logger.error("Script expects at least 4 arguments")
      sys.exit(1)
    command_name = str.lower(sys.argv[1])
    # parse command parameters
    command_data_file = sys.argv[2]
    basedir = sys.argv[3]
    self.stroutfile = sys.argv[4]
    try:
      with open(command_data_file, "r") as f:
        pass
        Script.config = ConfigDictionary(json.load(f))
    except IOError:
      logger.exception("Can not read json file with command parameters: ")
      sys.exit(1)
    # Run class method mentioned by a command type
    self_methods = dir(self)
    if not command_name in self_methods:
      logger.error("Script {0} has not method '{1}'".format(sys.argv[0], command_name))
      sys.exit(1)
    method = getattr(self, command_name)
    try:
      with Environment(basedir) as env:
        method(env)
    except Fail:
      logger.exception("Got exception while executing method '{0}':".format(command_name))
      sys.exit(1)

  @staticmethod
  def get_config():
    """
    HACK. Uses static field to store configuration. This is a workaround for
    "circular dependency" issue when importing params.py file and passing to
     it a configuration instance.
    """
    return Script.config


  def install(self, env):
    """
    Default implementation of install command is to install all packages
    from a list, received from the server.
    Feel free to override install() method with your implementation. It
    usually makes sense to call install_packages() manually in this case
    """
    self.install_packages(env)


  def install_packages(self, env):
    """
    List of packages that are required by service is received from the server
    as a command parameter. The method installs all packages
    from this list
    """
    config = self.get_config()
    RepoInstaller.install_repos(config)
    
    try:
      package_list_str = config['hostLevelParams']['package_list']
      if isinstance(package_list_str,basestring) and len(package_list_str) > 0:
        package_list = json.loads(package_list_str)
        for package in package_list:
          name = package['name']
          Package(name)
    except KeyError:
      pass # No reason to worry
    
    RepoInstaller.remove_repos(config)



  def fail_with_error(self, message):
    """
    Prints error message and exits with non-zero exit code
    """
    print("Error: " + message)
    sys.stderr.write("Error: " + message)
    sys.exit(1)