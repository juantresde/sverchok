# ##### BEGIN GPL LICENSE BLOCK #####
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
# ##### END GPL LICENSE BLOCK #####

import math

import bpy
import mathutils
from mathutils import Vector, Matrix

from data_structure import Vector_generate, Matrix_generate

callback_dict = {}
SpaceView3D = bpy.types.SpaceView3D

from bgl import (
    glEnable, glDisable, glBegin, glEnd,
    glColor3f, glVertex3f, glColor4f, glPointSize, glLineWidth,
    glLineStipple, glPolygonStipple, glHint, glShadeModel,
    GL_POINTS, GL_LINE_STRIP, GL_LINES, GL_LINE, GL_LINE_LOOP, GL_LINE_STIPPLE,
    GL_POLYGON, GL_POLYGON_STIPPLE, GL_TRIANGLES, GL_QUADS, GL_POINT_SIZE,
    GL_POINT_SMOOTH, GL_POINT_SMOOTH_HINT, GL_NICEST, GL_FASTEST,
    GL_FLAT, GL_SMOOTH)

# ------------------------------------------------------------------------ #
# parts taken from  "Math Vis (Console)" addon, author Campbell Barton     #
# ------------------------------------------------------------------------ #


class MatrixDraw(object):

    def __init__(self):
        self.zero = Vector((0.0, 0.0, 0.0))
        self.x_p = Vector((0.5, 0.0, 0.0))
        self.x_n = Vector((-0.5, 0.0, 0.0))
        self.y_p = Vector((0.0, 0.5, 0.0))
        self.y_n = Vector((0.0, -0.5, 0.0))
        self.z_p = Vector((0.0, 0.0, 0.5))
        self.z_n = Vector((0.0, 0.0, -0.5))
        self.bb = [Vector() for i in range(24)]

    def draw_matrix(self, mat):
        bb = self.bb
        zero_tx = mat * self.zero

        axis = [
            [(1.0, 0.2, 0.2), self.x_p],
            [(0.6, 0.0, 0.0), self.x_n],
            [(0.2, 1.0, 0.2), self.y_p],
            [(0.0, 0.6, 0.0), self.y_n],
            [(0.2, 0.2, 1.0), self.z_p],
            [(0.0, 0.0, 0.6), self.z_n]
        ]

        glLineWidth(2.0)
        for col, axial in axis:
            glColor3f(*col)
            glBegin(GL_LINES)
            glVertex3f(*(zero_tx))
            glVertex3f(*(mat * axial))
            glEnd()

        # bounding box vertices
        i = 0
        glColor3f(1.0, 1.0, 1.0)
        series1 = (-0.5, -0.3, -0.1, 0.1, 0.3, 0.5)
        series2 = (-0.5, 0.5)
        z = 0

        for x in series1:
            for y in series2:
                bb[i][:] = x, y, z
                bb[i] = mat * bb[i]
                i += 1

        for y in series1:
            for x in series2:
                bb[i][:] = x, y, z
                bb[i] = mat * bb[i]
                i += 1

        # bounding box drawing
        glLineWidth(1.0)
        glLineStipple(1, 0xAAAA)
        glEnable(GL_LINE_STIPPLE)

        for i in range(0, 24, 2):
            glBegin(GL_LINE_STRIP)
            glVertex3f(*bb[i])
            glVertex3f(*bb[i+1])
            glEnd()


def tag_redraw_all_view3d():
    context = bpy.context

    # Py cant access notifers
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                for region in area.regions:
                    if region.type == 'WINDOW':
                        region.tag_redraw()


def callback_enable(n_id, cached_view, options):
    global callback_dict
    if n_id in callback_dict:
        return

    config = (n_id, cached_view, options)
    handle_view = SpaceView3D.draw_handler_add(
        draw_callback_view, config, 'WINDOW', 'POST_VIEW')

    callback_dict[n_id] = handle_view
    tag_redraw_all_view3d()


def callback_disable_all():
    global callback_dict
    temp_list = list(callback_dict.keys())
    for name in temp_list:
        if name:
            callback_disable(name)


def callback_disable(n_id):
    global callback_dict
    handle_view = callback_dict.get(n_id, None)
    if not handle_view:
        return

    SpaceView3D.draw_handler_remove(handle_view, 'WINDOW')
    del callback_dict[n_id]
    tag_redraw_all_view3d()


def draw_callback_view(n_id, cached_view, options):
    context = bpy.context

    sl1 = cached_view[n_id + 'v']
    sl2 = cached_view[n_id + 'ep']
    sl3 = cached_view[n_id + 'm']
    show_verts = options['show_verts']
    show_edges = options['show_edges']
    show_faces = options['show_faces']
    colo = options['face_colors']
    tran = options['transparent']
    shade = options['shading']
    vertex_colors = options['vertex_colors']
    edge_colors = options['edge_colors']
    edge_width = options['edge_width']
    forced_tessellation = options['forced_tessellation']

    if tran:
        polyholy = GL_POLYGON_STIPPLE
        edgeholy = GL_LINE_STIPPLE
        edgeline = GL_LINE_STRIP
    else:
        polyholy = GL_POLYGON
        edgeholy = GL_LINE
        edgeline = GL_LINES

    if sl1:
        data_vector = Vector_generate(sl1)
        verlen = len(data_vector)-1
        verlen_every = [len(d)-1 for d in data_vector]
    else:
        data_vector = []
        verlen = 0

    data_polygons = []
    data_edges = []
    if sl2 and sl2[0]:
        len_sl2 = len(sl2[0][0])
        if len_sl2 == 2:
            data_edges = sl2
        elif len_sl2 > 2:
            data_polygons = sl2

    if sl3:
        data_matrix = Matrix_generate(sl3)
    else:
        data_matrix = [Matrix() for i in range(verlen+1)]

    if (data_vector, data_polygons, data_matrix, data_edges) == (0, 0, 0, 0):
        callback_disable(n_id)

    coloa, colob, coloc = colo[:]

    ''' pre process verts and apply matrices if needed '''

    #
    #
    #

    ''' polygons '''

    vectorlight = options['light_direction']
    if data_polygons and data_vector:

        glLineWidth(1.0)
        glEnable(polyholy)
        normal = mathutils.geometry.normal
        tessellate = mathutils.geometry.tessellate_polygon

        for i, matrix in enumerate(data_matrix):
            k = i
            if i > verlen:
                k = verlen

            oblen = len(data_polygons[k])
            for j, pol in enumerate(data_polygons[k]):

                if max(pol) > verlen_every[k]:
                    pol = data_edges[k][-1]
                    j = len(data_edges[k])-1

                if show_faces:

                    if shade:
                        dvk = data_vector[k]
                        if len(pol) <= 4:
                            normal_no = normal(dvk[pol[0]], dvk[pol[1]], dvk[pol[2]])
                        else:
                            normal_no = normal(dvk[pol[0]], dvk[pol[1]], dvk[pol[2]], dvk[pol[3]])
                        normal_no = (normal_no.angle(vectorlight, 0)) / math.pi

                        r = (normal_no * coloa) - 0.1
                        g = (normal_no * colob) - 0.1
                        b = (normal_no * coloc) - 0.1
                        face_color = (r+0.2, g+0.2, b+0.2)
                    else:
                        #r = ((j/oblen) + coloa) / 2.5
                        #g = ((j/oblen) + colob) / 2.5
                        #b = ((j/oblen) + coloc) / 2.5
                        #face_color = (r+0.2, g+0.2, b+0.2)
                        face_color = colo[:]

                    glColor3f(*face_color)
                    num_verts = len(pol)

                    if (not forced_tessellation) or (num_verts in {3, 4}):
                        glBegin(GL_POLYGON)
                        for point in pol:
                            vec_corrected = data_matrix[i]*data_vector[k][point]
                            glVertex3f(*vec_corrected)

                    else:
                        ''' ngons, we tessellate '''
                        glBegin(GL_TRIANGLES)
                        v = [data_vector[k][i] for i in pol]
                        tess_poly = tessellate([v])
                        for a, b, c in tess_poly:
                            glVertex3f(*(data_matrix[i]*v[a]))
                            glVertex3f(*(data_matrix[i]*v[b]))
                            glVertex3f(*(data_matrix[i]*v[c]))

                    glEnd()

                if show_edges:
                    glLineWidth(edge_width)
                    glBegin(GL_LINE_LOOP)
                    glColor3f(*edge_colors)
                    for point in pol:
                        vec_corrected = data_matrix[i]*data_vector[k][point]
                        glVertex3f(*vec_corrected)
                    glEnd()

        glLineWidth(1.0)
        glDisable(polyholy)

    ''' edges '''

    if data_edges and data_vector and show_edges:
        glColor3f(*edge_colors)
        glLineWidth(edge_width)
        glEnable(edgeholy)

        for i, matrix in enumerate(data_matrix):
            k = i
            if i > verlen:   # filter to share objects
                k = verlen
            for line in data_edges[k]:
                if max(line) > verlen_every[k]:
                    line = data_edges[k][-1]
                glBegin(edgeline)
                for point in line:
                    vec_corrected = data_matrix[i]*data_vector[k][point]
                    glVertex3f(*vec_corrected)
                glEnd()

        glDisable(edgeholy)

    ''' vertices '''

    glEnable(GL_POINT_SIZE)
    glEnable(GL_POINT_SMOOTH)
    #glHint(GL_POINT_SMOOTH_HINT, GL_NICEST)
    glHint(GL_POINT_SMOOTH_HINT, GL_FASTEST)

    vsize = options['vertex_size']

    if show_verts and data_vector:
        glPointSize(vsize)
        glColor3f(*vertex_colors)

        glBegin(GL_POINTS)
        for i, matrix in enumerate(data_matrix):
            k = i
            if i > verlen:
                k = verlen
            for vert in data_vector[k]:
                vec_corrected = data_matrix[i]*vert
                glVertex3f(*vec_corrected)
        glEnd()

    glDisable(GL_POINT_SIZE)

    ''' matrix '''

    if data_matrix and not data_vector:
        md = MatrixDraw()
        for mat in data_matrix:
            md.draw_matrix(mat)


def unregister():
    callback_disable_all()