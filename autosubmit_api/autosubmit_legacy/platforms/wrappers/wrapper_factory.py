#!/usr/bin/env python

# Copyright 2018 Earth Sciences Department, BSC-CNS

# This file is part of Autosubmit.

# Autosubmit is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Autosubmit is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Autosubmit.  If not, see <http://www.gnu.org/licenses/>.

from autosubmitAPIwu.platforms.wrappers.wrapper_builder import WrapperDirector, PythonVerticalWrapperBuilder, \
    PythonHorizontalWrapperBuilder, PythonHorizontalVerticalWrapperBuilder, PythonVerticalHorizontalWrapperBuilder, \
    BashHorizontalWrapperBuilder, BashVerticalWrapperBuilder


class WrapperFactory(object):

    def __init__(self, platform):
        self.platform = platform
        self.wrapper_director = WrapperDirector()
        self.exception = "This type of wrapper is not supported for this platform"

    def get_wrapper(self, wrapper_builder, **kwargs):
        kwargs['allocated_nodes'] = self.allocated_nodes()
        kwargs['dependency'] = self.dependency(kwargs['dependency'])
        kwargs['queue'] = self.queue(kwargs['queue'])
        kwargs['header_directive'] = self.header_directives(**kwargs)

        builder = wrapper_builder(**kwargs)
        return self.wrapper_director.construct(builder)

    def vertical_wrapper(self, **kwargs):
        raise NotImplemented(self.exception)

    def horizontal_wrapper(self, **kwargs):
        raise NotImplemented(self.exception)

    def hybrid_wrapper_horizontal_vertical(self, **kwargs):
        raise NotImplemented(self.exception)

    def hybrid_wrapper_vertical_horizontal(self, **kwargs):
        raise NotImplemented(self.exception)

    def header_directives(self, **kwargs):
        pass

    def allocated_nodes(self):
        return ''

    def dependency(self, dependency):
        return '#' if dependency is None else self.dependency_directive(dependency)

    def queue(self, queue):
        return '#' if not queue else self.queue_directive(queue)

    def dependency_directive(self, dependency):
        pass

    def queue_directive(self, queue):
        pass


class SlurmWrapperFactory(WrapperFactory):

    def vertical_wrapper(self, **kwargs):
        return PythonVerticalWrapperBuilder(**kwargs)

    def horizontal_wrapper(self, **kwargs):
        return PythonHorizontalWrapperBuilder(**kwargs)

    def hybrid_wrapper_horizontal_vertical(self, **kwargs):
        return PythonHorizontalVerticalWrapperBuilder(**kwargs)

    def hybrid_wrapper_vertical_horizontal(self, **kwargs):
        return PythonVerticalHorizontalWrapperBuilder(**kwargs)

    def header_directives(self, **kwargs):
        return self.platform.wrapper_header(kwargs['name'], kwargs['queue'], kwargs['project'], kwargs['wallclock'],
                                            kwargs['num_processors'], kwargs['dependency'], kwargs['directives'])

    def allocated_nodes(self):
        return self.platform.allocated_nodes()

    def dependency_directive(self, dependency):
        return '#SBATCH --dependency=afterok:{0}'.format(dependency)

    def queue_directive(self, queue):
        return '#SBATCH --qos={0}'.format(queue)


class LSFWrapperFactory(WrapperFactory):

    def vertical_wrapper(self, **kwargs):
        return PythonVerticalWrapperBuilder(**kwargs)

    def horizontal_wrapper(self, **kwargs):
        return PythonHorizontalWrapperBuilder(**kwargs)

    def header_directives(self, **kwargs):
        return self.platform.wrapper_header(kwargs['name'], kwargs['queue'], kwargs['project'], kwargs['wallclock'],
                                            kwargs['num_processors'], kwargs['dependency'], kwargs['directives'])

    def queue_directive(self, queue):
        return queue

    def dependency_directive(self, dependency):
        return '#BSUB -w \'done({0})\' [-ti]'.format(dependency)


class EcWrapperFactory(WrapperFactory):

    def vertical_wrapper(self, **kwargs):
        return BashVerticalWrapperBuilder(**kwargs)

    def horizontal_wrapper(self, **kwargs):
        return BashHorizontalWrapperBuilder(**kwargs)

    def header_directives(self, **kwargs):
        return self.platform.wrapper_header(kwargs['name'], kwargs['queue'], kwargs['project'], kwargs['wallclock'],
                                            kwargs['num_processors'], kwargs['expid'], kwargs['dependency'],
                                            kwargs['rootdir'], kwargs['directives'])

    def queue_directive(self, queue):
        return queue

    def dependency_directive(self, dependency):
        return '#PBS -v depend=afterok:{0}'.format(dependency)
