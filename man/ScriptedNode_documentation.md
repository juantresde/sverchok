## Scripted Node (Generator)

aka Script Node or SN. (iteration 1)

- Introduction
- Features
- Examples
- Limitations
- Future

### Introduction

When you want to express an idea in written form, if the concept is suitable for a one line Python expression then you can use the Formula nodes. They require little setup just [plug and play](). However, they are not intended for multi-line python statements, and sometimes that's exactly what you want.

ScriptNode (SN) allows you to write multi-line python programs, it's possible to use the node as a Sandbox for writing full nodes. The only real limitation will be your Python Skills. It's a prototype so bug reports are welcome.

### Features

allows:
- Loading/Reloading scripts currently in TextEditor
- imports and aliasing, ie anything you can import from console works in SN
- nested functions and lambdas
- named inputs and outputs
- named operators (buttons to action something upon button press)

At present all scripts for SN must (strict list - general): 
- have 1 `sv_main` function as the main workhorse
- `sv_main` must take 1 or more arguments (even if you don't use it)
- all function arguments for `sv_main` must have defaults.
- each script shall define 'in_sockets' and 'out_sockets'
- TextEditor has automatic `in_sockets` list creation (`Ctrl+I -> Generate in_sockets`) when the key cursor is over `sv_main`.
- 'ui_operators' is an optional third output parameter

#### `in_sockets`

```python
in_sockets = [
    [type, 'socket name on ui', input_variable],
    [type, 'socket name on ui 2', input_variable2],
    # ...
]
```

#### `out_sockets`

```python
out_sockets = [
    [type, 'socket name on ui', output_variable],
    [type, 'socket name on ui 2', output_variable2],
    # ...
]
```

#### `in_sockets and out_sockets`

- Each `"socket name on ui"` string shall be unique.
- `type` are currently limited to
   - 's' : floats, ints, edges, faces
   - 'v' : vertices, vectors
   - 'm' : matrices

#### `ui_operators`

```python
ui_operators = [
    ['button_name', func1]
] 
```
- Here `func1` is the function you want to call when pressing the button.
- Each `"button_name"` is the text you want to appear on the button. For simplicity it must be unique and a valid variable name. Use alphanumerics only and separate words with single underscores if you need.

#### `return`

Simple, only two flavours are allowed at the moment.
```python
return in_sockets, out_sockets
# or
return in_sockets, out_sockets, ui_operators
```

### Examples

The best way to get familiarity with SN is to go through the templates folder. They are intended to be lightweight and educational, but some of them will show
advanced use cases. The [thread on github](https://github.com/nortikin/sverchok/issues/85) may also provide some pictorial insights and animations.

Sverchok includes a plugin in TextEditor which conveniently adds `sv NodeScripts` to the Templates menu.

A typical nodescript may look like this:

```python
from math import sin, cos, radians, pi
from mathutils import Vector, Euler


def sv_main(n_petals=8, vp_petal=20, profile_radius=1.3, amp=1.0):

    in_sockets = [
        ['s', 'Num Petals',  n_petals],
        ['s', 'Verts per Petal',  vp_petal],
        ['s', 'Profile Radius', profile_radius],
        ['s', 'Amp',  amp],
    ]

    # variables
    z_float = 0.0
    n_verts = n_petals * vp_petal
    section_angle = 360.0 / n_verts
    position = (2 * (pi / (n_verts / n_petals)))

    # consumables
    Verts = []
    Edges = []

    # makes vertex coordinates
    for i in range(n_verts):
        # difference is a function of the position on the circumference
        difference = amp * cos(i * position)
        arm = profile_radius + difference
        ampline = Vector((arm, 0.0, 0.0))

        rad_angle = radians(section_angle * i)
        myEuler = Euler((0.0, 0.0, rad_angle), 'XYZ')

        # changes the vector in place, successive calls are accumulative
        # we reset at the start of the loop.
        ampline.rotate(myEuler)
        x_float = ampline.x
        y_float = ampline.y
        Verts.append((x_float, y_float, z_float))

    # makes edge keys
    for i in range(n_verts):
        if i == n_verts - 1:
            Edges.append([i, 0])
            break
        Edges.append([i, i + 1])

    out_sockets = [
        ['v', 'Verts', [Verts]],
        ['s', 'Edges', [Edges]],
    ]

    return in_sockets, out_sockets
```


### Future
SN iteration 1 is itself a prototype and is a testing ground for iteration 2.