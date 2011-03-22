from PyQt4 import QtCore, QtGui
from main import FACE_POSITIONS, _ActionDelegator

class _TextFaceItem(QtGui.QGraphicsSimpleTextItem, _ActionDelegator):
    def __init__(self, face, node, text):
        QtGui.QGraphicsSimpleTextItem.__init__(self, text)
        self.node = node

class _ImgFaceItem(QtGui.QGraphicsPixmapItem, _ActionDelegator):
    def __init__(self, face, node):
        QtGui.QGraphicsPixmapItem.__init__(self)
        self.node = node

class _BackgroundFaceItem(QtGui.QGraphicsRectItem):
    def __init__(self, face, node):
        QtGui.QGraphicsRectItem.__init__(self)
        self.node = node

    def paint(self, painter, option, index):
        return

class _FaceGroupItem(QtGui.QGraphicsItem): # I resisted to name this FaceBookItem :) 
    def __init__(self, faces, node, *args, **kargs):

        # This caused seg. faults. in some computers. No idea why.
        # QtGui.QGraphicsItem.__init__(self, *args, **kargs) 
        QtGui.QGraphicsItem.__init__(self)  

        self.node = node
        self.column2faces = faces
        self.column2size = {}
        self.columns = sorted(set(self.column2faces.keys()))
        
        # Two dictionaries containing min column size. Can be used to
        # reserve some space to specific columns and draw FaceBlocks
        # like tables.
        self.column_widths = {}
        self.row_heights = {}

        self.w = 0
        self.h = 0
        # updates the size of this grid
        self.update_columns_size()

    def set_min_column_widths(self, column_widths):
        # column_widths is a dictionary of min column size. Can be
        # used to reserve horizontal space to specific columns
        self.column_widths = column_widths
        self.columns = sorted(set(self.column2faces.keys() + self.column_widths.keys()))

    def set_min_column_heights(self, column_heights):
        # column_widths is a dictionary of min column size. Can be
        # used to reserve vertical space to specific columns
        self.row_heights = column_heights

    def paint(self, painter, option, index):
        return

    def boundingRect(self):
        return QtCore.QRectF(0,0, self.w, self.h)

    def get_size(self):
        return self.w, self.h

    def update_columns_size(self):
        self.column2size = {}
        for c in self.columns:
            faces = self.column2faces.get(c, [])
            heights = {}
            width = 0
            for r, f in enumerate(faces):
                f.node = self.node
                if f.type == "pixmap": 
                    f.update_pixmap()
                elif f.type == "item":
                    f.update_items()
                    
                height = max(f._height(), self.row_heights.get(r, 0)) + f.margin_top + f.margin_bottom
                heights[r] = height
                width = max(width, f._width() + f.margin_right + f.margin_left)
            width = max(width, self.column_widths.get(c, 0))
            self.column2size[c] = (width, heights)
        self.w = sum([0]+[size[0] for size in self.column2size.itervalues()])
        self.h = max([0]+[sum(heights.values()) for c_w, heights in self.column2size.itervalues()])

    def setup_grid(self):
        c2max_w, c2max_h = {}, {}
        for c, (c_w, heights) in self.column2size.iteritems():
            c2max_w[c] = max(c_w, c2max_w.get(c,0))
            for r, r_h in heights.iteritems():
                c2max_h[r] = max(r_h, c2max_h.get(c,0))
        
        self.set_min_column_widths(c2max_w)
        self.set_min_column_heights(c2max_h)
        self.update_columns_size()

    def render(self):
        x = 0
        for c in self.columns:
            faces = self.column2faces.get(c, [])
            w, col_h = self.column2size[c]
            # Starting y position. Center columns
            y = (self.h - sum(col_h.values())) / 2 
            for r, f in enumerate(faces):
                h = self.row_heights.get(r, 0)
                f.node = self.node
                if f.type == "text":
                    obj = _TextFaceItem(f, self.node, f.get_text())
                    font = f._get_font()
                    obj.setFont(font)
                    obj.setBrush(QtGui.QBrush(QtGui.QColor(f.fgcolor)))
                    obj.setParentItem(self)
                    obj.setAcceptsHoverEvents(True)
                elif f.type == "item":
                    obj = f.item
                    obj.setParentItem(self)
                else:
                    # Loads the pre-generated pixmap
                    obj = _ImgFaceItem(f, self.node, f.pixmap)
                    obj.setAcceptsHoverEvents(True)
                    obj.setParentItem(self)

                # relative alignemnt of faces
                face_rect = obj.boundingRect()
                x_offset, y_offset = 0, 0 
                if w > face_rect.width():
                    x_offset = (w - face_rect.width()) / 2  
                if h > face_rect.height():
                    y_offset = (h - face_rect.height()) / 2  

                obj.setPos(x + f.margin_left + x_offset,\
                               y + f.margin_top + y_offset )

                if f.opacity < 1:
                    obj.setOpacity(f.opacity)
                obj.rotable = f.rotable

                if f.border: 
                    border = QtGui.QGraphicsRectItem(obj.boundingRect())
                    border.setParentItem(obj)

                # Y position is incremented by the height of last face
                # in column
                y += h 
            # X position is incremented by the max width of the last
            # processed column.
            x += w

    def rotate(self, rotation):
        "rotates item over its own center"
        for obj in self.childItems():
            if obj.rotable:
                rect = obj.boundingRect()
                x =  rect.width()/2
                y =  rect.height()/2
                obj.setTransform(QtGui.QTransform().translate(x, y).rotate(rotation).translate(-x, -y))

    def flip_hz(self):
        for obj in self.childItems():
            rect = obj.boundingRect()
            x =  rect.width()/2
            y =  rect.height()/2
            obj.setTransform(QtGui.QTransform().translate(x, y).scale(-1,1).translate(-x, -y))

    def flip_vt(self):
        for obj in self.childItems():
            rect = obj.boundingRect()
            x =  rect.width()/2
            y =  rect.height()/2
            obj.setTransform(QtGui.QTransform().translate(x, y).scale(1,-1).translate(-x, -y))

def update_node_faces(node, n2f):
    # Organize all faces of this node in FaceGroups objects
    # (tables of faces)
    faceblock = {}

    n2f[node] = faceblock
    for position in FACE_POSITIONS:
        if position in node.img_style["_faces"]:
            # The value of this is expected to be list of columns of faces
            # c2f = [ [f1, f2, f3], 
            #         [f4, f4]
            #       ]
            faceblock[position] = _FaceGroupItem(node.img_style["_faces"][position], node)
        else:
            faceblock[position] = _FaceGroupItem({}, node)
    return faceblock

def _leaf(node):
    collapsed = hasattr(node, "img_style") and not node.img_style["draw_descendants"]
    return collapsed or node.is_leaf()

