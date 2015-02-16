# BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# END GPL LICENSE BLOCK #####

'''
The intention of this node is to provide optimal js execution speed by
precompiling the .js file, and functions. Hopefully it will serve to
show what can be done in this arena.

- you will be able to declare inputs and outputs
- sliders if it makes sense

'''

import importlib

# necessary for import checking
if importlib.find_loader('execjs'):
    import execjs
    print('execjs will be available')
else:
    print('execjs will not be available, prototype node will not function.')
    print('obtain execjs from: https://github.com/doloopwhile/PyExecJS')

import ast
import os
import traceback

import bpy
from bpy.props import (
    StringProperty,
    EnumProperty,
    BoolProperty,
    FloatVectorProperty,
    IntVectorProperty
)

from sverchok.utils.sv_panels_tools import sv_get_local_path
from sverchok.node_tree import SverchCustomTreeNode
from sverchok.data_structure import (dataCorrect, updateNode)

defaults = list(range(32))
FAIL_COLOR = (0.8, 0.1, 0.1)
READY_COLOR = (0, 0.8, 0.95)


def dirty_reload(script_name):

    # for this to work the text editor needs to have the text-panel visible

    # print('called')
    # text_obj = bpy.data.texts[script_name]
    # text_path = text_obj.filepath
    # if text_path:
    #     print('reloaded from path')
    #     with open(text_path) as fpath:
    #         file_str = ''.join(fpath.readlines())
    #         print(file_str)
    #         text_obj.from_string(file_str)
    #         text_obj.is_modified = False

    # for window in bpy.context.window_manager.windows:
    #     for area in window.screen.areas:

    #         if not area.type == 'TEXT_EDITOR':
    #             continue

    #         for s in area.spaces:
    #             print(s.type, dir(s))
    #             if s.type == 'TEXT_EDITOR':
    #                 # set_props(s)
    #                 # .resolve_conflict(resolution='RELOAD')
    #                 print(dir(s.text))
    pass


sock_dict = {
    'v': 'VerticesSocket',
    's': 'StringsSocket',
    'm': 'MatrixSocket'
}


def new_output_socket(node, name, stype):
    socket_type = sock_dict.get(stype)
    if socket_type:
        node.outputs.new(socket_type, name)


def new_input_socket(node, stype, name, dval):
    socket_type = sock_dict.get(stype)
    if socket_type:
        socket = node.inputs.new(socket_type, name)
        socket.default = dval

        if isinstance(dval, (float, int)):
            offset = len(node.inputs)
            if isinstance(dval, float):
                socket.prop_type = "float_list"
                node.float_list[offset] = dval
            else:  # dval is int
                socket.prop_type = "int_list"
                node.int_list[offset] = dval
            socket.prop_index = offset


class SvJSImporterOp(bpy.types.Operator):

    bl_idname = "node.js_importer"
    bl_label = "sv JS Import Operator"

    filepath = StringProperty(
        name="File Path",
        description="Filepath used for importing the js file",
        maxlen=1024, default="", subtype='FILE_PATH')

    def execute(self, context):
        n = self.node
        t = bpy.data.texts.load(self.filepath)
        n.script_name = t.name
        n.import_script()
        return {'FINISHED'}

    def invoke(self, context, event):
        self.node = context.node
        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}


class SvPrototypeCB(bpy.types.Operator):

    bl_idname = "node.sv_prototypejs_callback"
    bl_label = "PrototypeJS callback"

    fn_name = bpy.props.StringProperty(default='')

    def dispatch(self, context, type_op):
        n = context.node

        if type_op == 'LOAD':
            n.import_script()

        elif type_op == 'RELOAD':
            # get connection matrix
            n.reset_node()
            n.import_script()
            # set connection matrix

        elif type_op == 'CLEAR':  # temp testing
            n.deport_script()
            n.reset_node()

        elif type_op == 'REFRESH_FROM_DISK':
            # bpy.ops.text.resolve_conflict(resolution='RELOAD')
            dirty_reload(n.script_name)

    def execute(self, context):
        self.dispatch(context, self.fn_name)
        return {'FINISHED'}


class SvPrototypeJS(bpy.types.Node, SverchCustomTreeNode):

    ''' Script node JS'''
    bl_idname = 'SvPrototypeJS'
    bl_label = 'JS Generator'

    node_dict = {}
    script_name = StringProperty()
    STATE = StringProperty(default='UNLOADED')
    auto_refresh = BoolProperty(default=0)

    mode_options = [
        ("Internal", "Internal", "", 0),
        ("External", "External", "", 1),
    ]

    origin = EnumProperty(
        items=mode_options,
        description="pick where to load the js from",
        default="Internal",
        update=updateNode
    )

    int_list = IntVectorProperty(
        name='int_list', description="Integer list",
        default=defaults, size=32, update=updateNode)

    float_list = FloatVectorProperty(
        name='float_list', description="Float list",
        default=defaults, size=32, update=updateNode)

    def init(self, context):
        self.node_dict[hash(self)] = {}

    def set_node_function(self, node_function):
        self.node_dict[hash(self)]['node_function'] = node_function

    def get_node_function(self):
        return self.node_dict[hash(self)].get('node_function')

    def set_input_defaults(self):
        this_func = self.get_node_function()
        self.node_dict[hash(self)]['defaults'] = [i[2]['default'] for i in this_func('inputs')]

    def get_input_defaults(self):
        return self.node_dict[hash(self)]['defaults']

    def draw_buttons(self, context, layout):
        D = bpy.data
        sv_callback = "node.sv_prototypejs_callback"

        # I can't believe there's no nice way to do this... yet.
        # if self.script_name:
        #     if bpy.data.texts[self.script_name].is_modified:
        #         col = layout.column(align=True)
        #         col.operator(sv_callback, text='', icon='ERROR').fn_name = 'REFRESH_FROM_DISK'
        #         if self.auto_refresh:
        #             dirty_reload(self.script_name)

        if self.STATE == 'UNLOADED':

            # show options Internal / External
            col = layout.column(align=True)
            row = col.row()
            row.prop(self, "origin", expand=True)

            if self.origin == 'Internal':
                row2 = col.row()
                row2.prop_search(self, 'script_name', D, 'texts', text='', icon='TEXT')
                if self.script_name:
                    row2.operator(sv_callback, text='', icon='PLUGIN').fn_name = 'LOAD'
            else:
                # show file loading, this will import to bpy.data.texts
                col.operator("node.js_importer", text='import', icon='FILESEL')

        else:

            row = layout.row()
            for action in ['RELOAD', 'CLEAR']:
                row.operator(sv_callback, text=action).fn_name = action

    def import_script(self):
        try:
            local_file = bpy.data.texts[self.script_name].as_string()
            ctx = execjs.compile(local_file)
            self.set_node_function(ctx.call)
            self.STATE = 'LOADED'

            this_func = self.get_node_function()
            self.set_input_defaults()

            ins = this_func('inputs')
            if ins:
                # print(ins)
                for name, stype, info in ins:
                    dval = info['default']
                    new_input_socket(self, stype, name, dval)

            outs = this_func('outputs')
            if outs:
                # print(outs)
                for name, prefix in outs:
                    new_output_socket(self, name, prefix)

        except:
            self.STATE = 'UNLOADED'
        print(self.STATE)

    def deport_script(self):
        self.set_node_function({})
        self.STATE = 'UNLOADED'
        print('unloaded: '.format(self.script_name))

    def reset_node(self):
        in_out = [self.inputs, self.outputs]
        for socket_set in in_out:
            socket_set.clear()

    def process(self):

        this_func = self.get_node_function()
        node_input_defaults = self.get_input_defaults()

        args = []
        for _in, default_val in zip(self.inputs, node_input_defaults):
            args_input = _in.sv_get()[0][0]
            args.append(args_input)

        js_output = this_func("sv_proto_main", *args)

        for _out, out_val in zip(self.outputs, js_output):
            if _out.is_linked:
                _out.sv_set(out_val)


classes = [SvJSImporterOp, SvPrototypeCB, SvPrototypeJS]


def register():
    for class_name in classes:
        bpy.utils.register_class(class_name)


def unregister():
    for class_name in classes:
        bpy.utils.unregister_class(class_name)
