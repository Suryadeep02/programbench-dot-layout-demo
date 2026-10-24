# Plain and plain-ext output

This is an offline task guide to the [Graphviz plain format](https://graphviz.org/docs/outputs/plain/). The reference executable is authoritative for precise layout and formatting.

Run `dot -Tplain file.dot`, `dot -Tplain-ext file.dot`, or send DOT to standard input. Output is one graph line, zero or more node lines, zero or more edge lines, then `stop`:

```text
graph scale width height
node name x y width height label style shape color fillcolor
edge tail head n x1 y1 ... xn yn [label xl yl] style color
stop
```

Coordinates and dimensions are in inches, with the lower left of the drawing at the origin. The graph line gives the drawing width and height; `scale` is normally 1 and changes when a `size` attribute requests scaling. Node centers are `x,y`. Each edge has `n` ordered B-spline control points from tail toward head. Optional edge-label text and its center follow those points. The last two edge fields are style and color. The node style defaults to `solid` when absent. `plain-ext` appends a port name to an endpoint with `:port` when the edge attaches at a port.

Names or labels containing whitespace or special characters can be quoted. Quotes and backslashes in such fields are escaped. HTML-like labels can appear as one unquoted balanced `<...>` token even when they contain spaces in tag attributes or table cells. Record order may follow parser/insertion order; the grader compares records by meaning. A plain stream must have exactly one graph line and one final `stop`, with no other record types. The output gives spline bodies, not arrowhead polygons. Directed edges with arrowheads may therefore end short of the node boundary.

The source [DOT language guide](https://graphviz.org/doc/info/lang.html), [command guide](https://graphviz.org/doc/info/command.html), and [attribute index](https://graphviz.org/doc/info/attrs.html) describe the language and controls. The local `scope.md` identifies the subset used in this task.
