from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPolygonItem
from PyQt5.QtCore import Qt, QPointF, QRectF, QSizeF
from PyQt5.QtGui import QPixmap, QPen, QPolygonF, QPainter, QPainterPath, QBitmap
import math
from scipy import spatial
import numpy as np

class CustomGraphicsView(QGraphicsView):
    def __init__(self):
        super().__init__()

        self.scene = QGraphicsScene()
        self.setScene(self.scene)

        self.map_item = None
        self.character_items = {}
        self.hex_items = []  # Added hex_items attribute
        self.selected_item = None
        self.last_mouse_pos = QPointF()
        self.arrayCenters = []

        self.setSceneRect(0, 0, self.width(), self.height())
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

    def setMapPixmap(self, pixmap):
        if self.map_item is not None:
            self.scene.removeItem(self.map_item)
        self.map_item = self.scene.addPixmap(pixmap)
        self.map_item.setZValue(0)

    def addCharacterPixmap(self, pixmap, name):
        character_item = self.scene.addPixmap(pixmap)
        self.character_items[name] = character_item
        character_item.setZValue(2)
        if len(self.hex_items) > 0:
            for hex in self.hex_items:
                hex.setZValue(1)
        

    def wheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            zoom_factor = 1.2 if event.angleDelta().y() > 0 else 1 / 1.2
            self.scale(zoom_factor, zoom_factor)
            event.accept() # consume event
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.last_mouse_pos = event.pos()
            item = self.itemAt(event.pos())
            if item == self.map_item:
                self.selected_item = item
            elif item in self.character_items:
                self.selected_item = item
            elif item in self.hex_items:  # Check if clicked item is a hexagon
                self.selected_item = item

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.selected_item:
            delta = event.pos() - self.last_mouse_pos
            if self.selected_item == self.map_item or self.selected_item in self.hex_items:
                self.map_item.setPos(self.map_item.pos() + delta)
                characters = [item for key, item in self.character_items.items()]
                for item in characters:
                    item.setPos(item.pos() + delta)
                for hex_item in self.hex_items:
                    hex_item.setPos(hex_item.pos() + delta)
            elif self.selected_item in characters :
                if len(self.hex_items) >0: # grids exist... snap else dont
                    item = self.map_item
                    delta_x, delta_y = item.pos().x(), item.pos().y() # this was originally 0,0 so any off is delta
                    sceneThing = self.mapToScene(event.pos())
                    hexCenters = [[x.x(), x.y()] for x in self.arrayCenters] # grab initial hex x,y

                    hexArrays = np.array(hexCenters) + np.array([delta_x, delta_y]) # self.arrayCenters is original coord. add delta
                    currentArrayIndex = spatial.KDTree(hexArrays).query((sceneThing.x(), sceneThing.y()))[1] # find index of closest hex
                    snap_coord = hexArrays[currentArrayIndex] # find that coord

                    character_size = self.selected_item.boundingRect().size()
                    snap_x = snap_coord[0] - character_size.width() / 2
                    snap_y = snap_coord[1] - character_size.height() / 2
                    #print([sceneThing.x(), sceneThing.y()], [event.pos().x(), event.pos().y()], snap_coord, [snap_x, snap_y])
                    self.selected_item.setPos(snap_x, snap_y)  # snap to this coord
                else:
                    self.selected_item.setPos(self.selected_item.pos() + delta)
               
            self.last_mouse_pos = event.pos()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.selected_item = None


    def drawHexGrid(self, heightNumber, map_rect):
        if heightNumber == 0:
            self.arrayCenters.clear()
            self.clearGrid()
            return
        height = map_rect.height()
        width = map_rect.width()
        map_item_pos = self.map_item.pos()
        top_left_x = map_item_pos.x()
        top_left_y = map_item_pos.y()
        startingPoint = [top_left_x, top_left_y]
        r = height / (2 * (1 + (heightNumber - 1) * 2 * math.cos(math.pi * 60 / 180)))
        self.radius = r
        a = 2 * math.pi / 6
        x, y = startingPoint

        self.arrayCenters.clear()
        self.clearGrid()
        self.hex_items.clear()

        while y + r * math.sin(a) <= height + 2 * startingPoint[1]:
            previousY = y
            previousX = x
            j = 0
            while x + r * (1 + math.cos(a)) <= width + startingPoint[0]:
                center = QPointF(x, y)
                self.arrayCenters.append(center)

                # Draw hexagon at center
                hex_points = []
                for i in range(6):
                    angle_rad = a * i
                    x_i = x + r * math.cos(angle_rad)
                    y_i = y + r * math.sin(angle_rad)
                    hex_points.append(QPointF(x_i, y_i))

                hex_polygon = QGraphicsPolygonItem()
                hex_polygon.setPolygon(QPolygonF(hex_points))
                self.scene.addItem(hex_polygon)
                self.hex_items.append(hex_polygon)  # Store hexagon in hex_items

                x += r * (1 + math.cos(a))
                y += (-1) ** j * r * math.sin(a)
                j += 1

            x = previousX
            y = previousY
            y += 2 * r * math.sin(a)

        if heightNumber > 0:
            hex_size = QSizeF(4*r * (1+ math.cos(a))/3, 2*r * math.sin(a))  # Adjust size as needed
            hex_path = self.createHexagonPath(hex_size.toSize())

            # Iterate over character items
            characters = [item for key, item in self.character_items.items()]
            for character_item in characters:
                # Resize the character's image to fit within the hexagon
                character_pixmap = character_item.pixmap().scaled(hex_size.toSize(), Qt.KeepAspectRatio)

                # Create a painter path for the character image
                character_path = QPainterPath()
                character_path.addRect(QRectF(QPointF(), hex_size))

                # Clip the character image with the hexagon path
                character_path = character_path.intersected(hex_path)

                # Create a new pixmap and paint the character image onto it
                combined_pixmap = QPixmap(hex_size.toSize())
                combined_pixmap.fill(Qt.transparent)
                painter = QPainter(combined_pixmap)
                painter.setClipPath(character_path)
                painter.drawPixmap(combined_pixmap.rect(), character_pixmap)
                painter.end()

                # Set the combined pixmap as the pixmap for the character item
                character_item.setPixmap(combined_pixmap)
        

    def createHexagonPath(self, size):
        path = QPainterPath()
        path.moveTo(size.width() / 4, 0)
        path.lineTo(3 * size.width() / 4, 0)
        path.lineTo(size.width(), size.height() / 2)
        path.lineTo(3 * size.width() / 4, size.height())
        path.lineTo(size.width() / 4, size.height())
        path.lineTo(0, size.height() / 2)
        path.closeSubpath()
        return path
   

    def clearGrid(self):
        # Clear all grid items from the scene
        for item in self.scene.items():
            if isinstance(item, QGraphicsPolygonItem):
                self.scene.removeItem(item)
