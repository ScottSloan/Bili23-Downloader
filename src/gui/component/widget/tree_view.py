from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import QApplication, QTreeView
from PySide6.QtCore import Qt

from qfluentwidgets import TreeView

class CheckableTreeItem(QStandardItem):
    def __init__(self, text: str = ""):
        super().__init__(text)

        self.setFlags(self.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        self.setCheckState(Qt.CheckState.Unchecked)
        self.setEditable(False)

    def isChecked(self):
        return self.checkState() == Qt.CheckState.Checked

class StandardTreeItem(QStandardItem):
    def __init__(self, text: str = ""):
        super().__init__(text)

        self.setEditable(False)

class CheckListView(TreeView):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.setObjectName("CheckListView")
        self.setFont(QApplication.font())
        self.setSelectionMode(QTreeView.SelectionMode.SingleSelection)
        self.setUniformRowHeights(True)
        self.setRootIsDecorated(False)

    def setColumnHeaders(self, headers: list, widths: list):
        self.data_model = QStandardItemModel()
        self.data_model.setColumnCount(len(headers))
        self.data_model.setHorizontalHeaderLabels(headers)

        self.setModel(self.data_model)

        for index, width in enumerate(widths):
            self.setColumnWidth(index, width)

    def appendCheckableRow(self, *args, data = None, checked = False):
        root = self.data_model.invisibleRootItem()

        items = []

        for index, text in enumerate(args):
            if index == 0:
                item = CheckableTreeItem(text)
                item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            else:
                item = StandardTreeItem(text)

            if data:
                item.setData(data, Qt.ItemDataRole.UserRole)

            items.append(item)

        root.appendRow(items)

    def getCheckedItemsData(self):
        data = []

        for i in range(self.data_model.rowCount()):
            item: CheckableTreeItem = self.data_model.item(i)

            if item.isChecked():
                data.append(item.data(Qt.ItemDataRole.UserRole))

        return data
