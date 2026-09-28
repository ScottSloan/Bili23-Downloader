import ctypes
import json
import os
from pathlib import Path
import sys

from PySide6.QtCore import QCoreApplication, QEvent, QItemSelectionModel, qVersion
from PySide6.QtGui import QAccessible, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QApplication, QAbstractItemView, QTableWidget, QTableWidgetItem, QTreeView

app = QApplication([])
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'src'))
lib = ctypes.CDLL(str(root / 'tests/native/qt_cocoa_probe.dylib'))
lib.bili23_selected_children_offset.restype = ctypes.c_size_t
print('QT', qVersion(), 'SELECTED_CHILDREN_OFFSET', hex(lib.bili23_selected_children_offset()), flush=True)
if '--patched' in sys.argv:
    from util.misc.macos import install_accessibility_ownership_fix
    assert install_accessibility_ownership_fix()
    assert install_accessibility_ownership_fix()
    print('PATCH_INSTALLED', flush=True)

lib.bili23_test_selected_children.argtypes = [ctypes.c_uint32, ctypes.POINTER(ctypes.c_int)]
lib.bili23_test_activate.argtypes = [ctypes.c_size_t]
queries = 0

def probe(view, expected):
    global queries
    iface = QAccessible.queryAccessibleInterface(view)
    aid = QAccessible.uniqueId(iface)
    bad = ctypes.c_int()
    actual = lib.bili23_test_selected_children(aid, ctypes.byref(bad))
    assert actual == expected, (actual, expected, [(i.row(),i.column()) for i in view.selectedIndexes()], QAccessible.isActive())
    assert bad.value == 0, bad.value
    assert QAccessible.accessibleInterface(aid) is not None, 'table interface was deleted'
    assert QAccessible.uniqueId(QAccessible.queryAccessibleInterface(view)) == aid, 'table id changed'
    queries += 1

table = QTableWidget(3, 2)
table.resize(900, 500)
table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
table.show()
lib.bili23_test_activate(int(table.winId()))
assert QAccessible.isActive()
for cycle in range(100):
    for columns in (2, 3, 2):
        table.setColumnCount(columns)
        for row in range(3):
            for col in range(columns):
                table.setItem(row, col, QTableWidgetItem(f'{cycle}/{row}/{col}'))
            table.clearSelection()
            table.selectRow(row)
            app.processEvents()
            probe(table, columns)
    table.clearSelection()
    probe(table, 0)
print('TABLE_PASS', queries, flush=True)

tree = QTreeView()
tree.resize(900, 500)
tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
model = QStandardItemModel(tree)
tree.setModel(model)
tree.show()
for cycle in range(100):
    model.clear()
    columns = 2 + cycle % 2
    model.setColumnCount(columns)
    for row in range(3):
        items = [QStandardItem(f'{cycle}/{row}/{col}') for col in range(columns)]
        model.appendRow(items)
        items[0].appendRow([QStandardItem(f'child/{col}') for col in range(columns)])
    tree.expandAll()
    for row in range(3):
        index = model.index(row, 0)
        tree.selectionModel().select(index, QItemSelectionModel.SelectionFlag.ClearAndSelect | QItemSelectionModel.SelectionFlag.Rows)
        app.processEvents()
        probe(tree, columns)
    tree.clearSelection()
    probe(tree, 0)
table_id = QAccessible.uniqueId(QAccessible.queryAccessibleInterface(table))
tree_id = QAccessible.uniqueId(QAccessible.queryAccessibleInterface(tree))
table.close()
tree.close()
table.deleteLater()
tree.deleteLater()
QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
app.processEvents()
assert QAccessible.accessibleInterface(table_id) is None
assert QAccessible.accessibleInterface(tree_id) is None
print(json.dumps({'status':'PASS','queries':queries,'qt':qVersion(),'patched':'--patched' in sys.argv}), flush=True)
os._exit(0)
