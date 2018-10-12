# Copyright 2017,2018 Free Software Foundation, Inc.
# This file is part of GNU Radio
#
# GNU Radio Companion is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# GNU Radio Companion is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA

from __future__ import absolute_import, division

import ast
from collections import OrderedDict

from ..core.io import yaml
from . import xml


def from_xml(filename):
    """Load flow graph from xml file"""
    element, version_info = xml.load(filename, 'flow_graph.dtd')

    data = convert_flow_graph_xml(element)
    try:
        file_format = int(version_info['format'])
    except KeyError:
        file_format = _guess_file_format_1(data)

    data['metadata'] = {'file_format': file_format}

    return data


def dump(data, stream):
    out = yaml.dump(data, indent=2)

    replace = [
        ('blocks:', '\nblocks:'),
        ('connections:', '\nconnections:'),
        ('metadata:', '\nmetadata:'),
    ]
    for r in replace:
        out = out.replace(*r)
    prefix = '# auto-generated by grc.converter\n\n'
    stream.write(prefix + out)


def convert_flow_graph_xml(node):
    blocks = [
        convert_block(block_data)
        for block_data in node.findall('block')
    ]

    options = next(b for b in blocks if b['id'] == 'options')
    blocks.remove(options)
    options.pop('id')

    connections = [
        convert_connection(connection)
        for connection in node.findall('connection')
        ]

    flow_graph = OrderedDict()
    flow_graph['options'] = options
    flow_graph['blocks'] = blocks
    flow_graph['connections'] = connections
    return flow_graph


def convert_block(data):
    block_id = data.findtext('key')

    params = OrderedDict(sorted(
        (param.findtext('key'), param.findtext('value'))
        for param in data.findall('param')
    ))
    if block_id == "import":
        params["imports"] = params.pop("import")
    states = OrderedDict()
    x, y = ast.literal_eval(params.pop('_coordinate', '(10, 10)'))
    states['coordinate'] = yaml.ListFlowing([x, y])
    states['rotation'] = int(params.pop('_rotation', '0'))
    enabled = params.pop('_enabled', 'True')
    states['state'] = (
        'enabled' if enabled in ('1', 'True') else
        'bypassed' if enabled == '2' else
        'disabled'
    )

    block = OrderedDict()
    if block_id != 'options':
        block['name'] = params.pop('id')
    block['id'] = block_id
    block['parameters'] = params
    block['states'] = states

    return block


def convert_connection(data):
    src_blk_id = data.findtext('source_block_id')
    src_port_id = data.findtext('source_key')
    snk_blk_id = data.findtext('sink_block_id')
    snk_port_id = data.findtext('sink_key')

    if src_port_id.isdigit():
        src_port_id = src_port_id
    if snk_port_id.isdigit():
        snk_port_id = snk_port_id

    return yaml.ListFlowing([src_blk_id, src_port_id, snk_blk_id, snk_port_id])


def _guess_file_format_1(data):
    """Try to guess the file format for flow-graph files without version tag"""

    def has_numeric_port_ids(src_id, src_port_id, snk_id, snk_port_id):
        return src_port_id.isdigit() and snk_port_id.is_digit()

    try:
        if any(not has_numeric_port_ids(*con) for con in data['connections']):
            return 1
    except:
        pass
    return 0
