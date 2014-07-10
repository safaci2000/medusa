#!/usr/bin/env python
"""
 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
"""
from thrift_medusa.thrift.thrift import Thrift

__author__ = 'sfaci'

import sys
import subprocess
import argparse
import numpy as np

from thrift_medusa.utils.wize_utils import *
from thrift_medusa.utils.config import Config
from thrift_medusa.thrift.thrift_compiler import ThriftCompiler
from thrift_medusa.clients.java_client import JavaClient
from thrift_medusa.clients.ruby_client import RubyClient
from thrift_medusa.clients.documentation_client import Documentation

from thrift_medusa.utils.log import Log
from multiprocessing import Process


class PublishClient():
    """
      The purpose of this class is to setup the environment for processing various service objects
    """

    def __init__(self):
        self.client_list = []
        self.remove_structure("logs")
        wize_mkdir("logs")
        self.business_objects = []
        self.service_objects = []
        self.config = Config()
        self.log = Log(log_file=os.path.join(self.config.repo_dir, "logs/status.log"),
                       logger_name="definitions").get_logger()

    def remove_structure(self, dir):
        """
            Simple method that deletes a directory
        """
        cmd = ['rm', '-fr', dir]
        self.local_assert(subprocess.call(cmd), "failed to run command: {cmd}".format(cmd=str(cmd)))
        return 0

    def local_assert(self, exit_code, message):
        """
        Defines a cleaner version of an assert that is probably more helpful.
        """
        if exit_code != 0:
            self.log.error(message)
            sys.exit(exit_code)

    def create_structure(self):
        """
            Remove old directory structure and re-copy all the files and dependencies
            from the appropriate repos.
        """
        self.remove_structure(self.config.work_dir)
        os.mkdir(self.config.work_dir)

        self.business_objects = build_file_list(self.config.get_path(type="business_object"), ".thrift")
        self.service_objects = build_file_list(self.config.get_path(type="service_object"), ".thrift")
        self.enum_objects = build_file_list(self.config.get_path(type="enum_object"), ".thrift")
        self.exception_objects = build_file_list(self.config.get_path(type="exception_object"), ".thrift")


    def update_client_list(self, thrift_objects, compilers):
        """
          Build a list of all clients for each language and compiler type.

          Note: Multiple thrift compilers not currently supported.
        """
        self.client_list = []
        for item in compilers:
            if self.config.is_java and item.is_language_supported("java"):
                self.client_list.append(JavaClient(thrift_objects, item))
            if self.config.is_ruby and item.is_language_supported("ruby"):
                self.client_list.append(RubyClient(thrift_objects, item))
            if self.config.is_doc_enabled and item.is_language_supported("doc"):
                self.client_list.append(Documentation(thrift_objects, item))

    def process_thrift_services(self):
        """
            This method will iterate through all the service and business object thrift files, and
            deploy the maven artifacts and its dependencies
        """
        compiler_list = []
        for item in self.config.get_thrift_option("compilers"):
            t = ThriftCompiler(item)
            compiler_list.append(t)

        #ensure that vcs is enabled, and thrift-file override hasn't been passed in.
        thrift_objects = []
        if self.config.is_local() and self.config.get_service_override() is not None:
            pass
        elif not self.config.is_vcs or self.config.is_local():
            #flatten list
            thrift_objects = self.service_objects + self.business_objects + self.enum_objects + self.exception_objects
        else:
            vcs = self.config.get_vcs_instance()
            file_objects = vcs.get_modified_files()
            if file_objects is None or len(file_objects) == 0:
                self.config.is_vcs = False
                thrift_objects = self.service_objects + self.business_objects + self.enum_objects + self.exception_objects
            else:
                self.log.info("Using list of objects from VCS")
                thrift_objects = map(lambda current_file: os.path.basename(current_file), file_objects)
                self.log.info("VCS object list is: " + str(thrift_objects))

        if self.config.is_local() and self.config.get_service_override() is not None:
            self.service_objects = []
            thrift_objects = [self.config.get_service_override()]

        self.update_client_list(thrift_objects, compiler_list)

        process_list = []

        for client in self.client_list:
            p = Process(target=client.run)
            p.start()
            process_list.append(p)

        #wait for all threads that have been started to terminate.
        map(lambda proc: proc.join(), process_list)

        # #Check exit codes
        for proc in process_list:
            self.local_assert(proc.exitcode, str(proc))


def display_compilers():
    """
    Will display the list of all current supported compilers defined in configuration.
    """
    config = Config()
    compilers = config.get_thrift_option("compilers")
    for item in compilers:
        print("found compiler %s with binary at: %s which supports: %s languages" % (item.get('name'), item.get('bin'),
                                                                                     ', '.join(map(str, item.get(
                                                                                         'supported_languages')))))
    sys.exit(0)


def set_compiler(override_compiler):
    """
    Allows user to explicitly use a particular compiler when building thrift artifacts.
    """
    config = Config()
    compilers = config.get_thrift_option("compilers")
    found = False
    compiler = None
    for item in compilers:
        if item['name'] == override_compiler:
            found = True
            compiler = item

    if not found:
        print("compiler {compiler} was not found in yaml configuration".format(compiler=override_compiler))
        sys.exit(1)

    config.set_thrift_option("compilers", [compiler])


def sanitize(node_name):
    return node_name.replace("wizecommerce.", "")


def add_visualization(graph, thrift_file, th):
    if th.is_service(sanitize(thrift_file)):
        pass
    graph.add_node(sanitize(thrift_file))
    properties = th.read_thrift_properties(thrift_file)
    graph.node[sanitize(thrift_file)] = properties

    deps = th.read_thrift_dependencies(thrift_file)
    for dep in deps:
        sanitized_thrift = sanitize(thrift_file)
        graph.add_edge(sanitized_thrift, sanitize(dep))
        properties = th.read_thrift_properties(dep)
        graph.node[sanitized_thrift] = properties
        if len(th.read_thrift_dependencies(dep)) > 0:
            add_visualization(graph, dep, th)


def display_visualization(thrift_file):
    """
    Notes:
        http://matplotlib.org/mpl_toolkits/mplot3d/index.html
        http://matplotlib.org/
        http://code.enthought.com/projects/mayavi/documentation.php
        https://networkx.github.io/documentation/latest/examples/drawing/labels_and_colors.html


    """
    thrift_objects = []
    if thrift_file is None:
        config = Config()
        business_objects = build_file_list(config.get_path(type="business_object"), ".thrift")
        service_objects = build_file_list(config.get_path(type="service_object"), ".thrift")
        enum_objects = build_file_list(config.get_path(type="enum_object"), ".thrift")
        exception_objects = build_file_list(config.get_path(type="exception_object"), ".thrift")
        thrift_objects = service_objects + business_objects + enum_objects + exception_objects
    else:
        thrift_objects.append(thrift_file)

    import networkx as nx
    import matplotlib.pyplot as plt
    import mpl_toolkits.mplot3d
    from networkx.readwrite import json_graph
    import http_server
    import json
    graph = nx.Graph()
    ##generate graph for  args.thrift_file
    th = Thrift("Dummy")
    #thrift_file = os.path.basename(thrift_file)
    for some_file in thrift_objects:
        some_file = os.path.basename(some_file)
        add_visualization(graph, some_file, th)

    # nx.draw(graph,  node_color = np.linspace(0, 1, len(graph.nodes())))
    ###
    d = json_graph.node_link_data(graph) # node-link format to serialize
    json.dump(d, open('/tmp/force.json','w'))
    print('Wrote node-link JSON data to tmp/force.json')
    http_server.load_url('tmp/force.html')
    print('Or copy all files in force/ to webserver and load force/force.html')




    nx.draw(graph)
    plt.savefig("/tmp/path.png")
    #plt.show()

    print graph.nodes()
    nx.write_graphml(graph, '/tmp/so.graphml')



def main():
    parser = argparse.ArgumentParser(description='Client Generation Script')
    parser.add_argument('--local', action="store_true", dest="local", default=False, help="Enables Local Mode")
    parser.add_argument('--profile', action="store_true", dest="profile", default=False, help="Profiles App")
    parser.add_argument("--docOnly", action="store_true", dest="doc_only", default=False)
    parser.add_argument('--ruby', action="store_true", dest="ruby", default=False,
                        help="Enables RubyMode, default is Ruby + Java (Local Mode Only)")
    parser.add_argument('--java', action="store_true", dest="java", default=False,
                        help="Enables JavaMode, default is Ruby + Java  (Local Mode Only) ")
    parser.add_argument('--visualize', action="store_true", dest="visualize", default=False,
                        help="Enables visualization mode")
    parser.add_argument('--thrift-file', action="store", dest="thrift_file", type=str,
                        help="Override list of services, and use the one specified (Local Mode Only)\nThis overrides vcs intelligence")
    parser.add_argument('--config', action="store", dest="config", type=str,
                        help="Override default config file and specify your own yaml config")
    parser.add_argument('--compilers', action="store_true", dest="compilers", default=False,
                        help="will list all supported compilers. (Not fully supported)")
    parser.add_argument('--set-compiler', action="store", dest="compiler", type=str,
                        help="accepts a valid compiler name defined in the yaml config.")



    args = parser.parse_args()
    if args.config is None:
        config = Config()
    else:
        config = Config(args.config)

    config.set_local(args.local)

    if args.thrift_file is not None:
        config.set_service_override(os.path.basename(args.thrift_file))

    if args.thrift_file is not None:
        config.set_local(True)

    if args.compilers:
        display_compilers()

    if args.compiler is not None:
        set_compiler(args.compiler)

    publish_client = PublishClient()

    ## these options can only be used in conjunction with local mode
    if config.is_local():
        if args.ruby and args.java:
            print "WARNING: you really should use rubyOverride or JavaOverride, " \
                  "if you pass both it can will fall back on default behavior.  (ie. omit both of them)"
        elif args.ruby:
            config.set_languages({"ruby": True})
        elif args.java:
            config.set_languages({"java": True})

    if args.doc_only:
        config.set_languages({})
        config.is_doc_enabled = True

    if args.profile:
        import cProfile

        cProfile.run('profileProject()')
    elif args.visualize:
        display_visualization(args.thrift_file)
    else:
        # Create Repo Structure
        publish_client.create_structure()
        # Loop through all of our services check for updates
        publish_client.process_thrift_services()


def profile_project():
    publish_client = PublishClient()
    publish_client.create_structure()
    publish_client.process_thrift_services()


if __name__ == "__main__":
    main()
