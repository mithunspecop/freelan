"""Project related classes and functions."""

import os
import sys
import fnmatch

try:
    import json
except ImportError:
    import simplejson

import file_tools

from environment import EnvironmentHelper

class Project(object):
    """A class to handle project attributes."""

    def __init__(self, path=None):
        """Create a new Project reading from the specified path."""

        super(Project, self).__init__()

        if path is None:
            self.abspath = os.getcwd()
        else:
            self.abspath = os.path.normpath(os.path.join(os.getcwd(), path))

        self.path = os.path.relpath(self.abspath)

        # Set the project file
        self.project_file = os.path.join(self.path, 'project.json')

        # Load the project file
        self.attributes = json.loads(open(self.project_file).read())

    def create_environment(self, scons_module, arguments):
        """Create the environment helper."""

        environment_helper = EnvironmentHelper(scons_module, arguments)
        self.configure_environment_helper(environment_helper)

    def __get_libraries(self):
        """Return the list of used libraries."""

        return sorted(set(self.attributes.get('*', []) + self.attributes.get(sys.platform, [])))

    libraries = property(__get_libraries)

class LibraryProject(Project):
    """A class to handle library project attributes."""

    def __init__(self, path=None, include_path=None, source_path=None):
        """Create a new LibraryProject reading from the specified path."""
        super(LibraryProject, self).__init__(path)

        if include_path is None:
            self.include_path = os.path.join(self.path, 'include', self.attributes['name'])
        else:
            self.include_path = include_path

        if source_path is None:
            self.source_path = os.path.join(self.path, 'src')
        else:
            self.source_path = source_path

        # Scan for include files
        self.include_files = []

        for root, directories, files in os.walk(self.include_path):
            self.include_files += [os.path.join(root, file) for file in file_tools.filter(files, ['*.h', '*.hpp'])]

        # Scan for source files
        self.source_files = []

        for root, directories, files in os.walk(self.source_path):
            self.source_files += [os.path.join(root, file) for file in file_tools.filter(files, ['*.c', '*.cpp'])]

    def get_library_dir(self, arch):
        """Get the library directory for the specified architecture."""

        if arch == '64':
            return os.path.join(self.path, 'lib64')
        else:
            return os.path.join(self.path, 'lib')

    def configure_environment_helper(self, environment_helper):
        environment_helper.build_library(
            self.get_library_dir(environment_helper.get_architecture()),
            self.attributes['name'],
            self.attributes['major'],
            self.attributes['minor'],
            self.include_path,
            self.source_files,
            self.libraries
        )
