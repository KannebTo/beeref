import os.path
import tempfile
from unittest.mock import MagicMock, patch

from pytest import mark

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt

from beeref.items import BeePixmapItem
from beeref import fileio
from beeref.view import BeeGraphicsView
from .base import BeeTestCase


class BeeGraphicsViewTestCase(BeeTestCase):

    def setUp(self):
        config_patcher = patch('beeref.view.commandline_args')
        self.config_mock = config_patcher.start()
        self.config_mock.filename = None
        self.addCleanup(config_patcher.stop)
        self.view = BeeGraphicsView(self.app)

    def tearDown(self):
        del self.view

    def test_inits_menu(self):
        view = BeeGraphicsView(self.app)
        assert isinstance(view.context_menu, QtWidgets.QMenu)
        assert len(view.actions()) > 0
        assert view.bee_actions
        assert view.bee_actiongroups

    @patch('beeref.view.BeeGraphicsView.open_from_file')
    def test_init_without_filename(self, open_file_mock):
        self.config_mock.filename = None
        view = BeeGraphicsView(self.app)
        open_file_mock.assert_not_called()
        del view

    @patch('beeref.view.BeeGraphicsView.open_from_file')
    def test_init_with_filename(self, open_file_mock):
        self.config_mock.filename = 'test.bee'
        view = BeeGraphicsView(self.app)
        open_file_mock.assert_called_once_with('test.bee')
        del view

    @patch('beeref.gui.WelcomeOverlay.hide')
    def test_on_scene_changed_when_items(self, hide_mock):
        item = BeePixmapItem(QtGui.QImage())
        self.view.scene.addItem(item)
        self.view.scale(2, 2)
        with patch('beeref.view.BeeGraphicsView.recalc_scene_rect') as r:
            self.view.on_scene_changed(None)
            r.assert_called_once_with()
            hide_mock.assert_called_once_with()
            assert self.view.get_scale() == 2

    @patch('beeref.gui.WelcomeOverlay.show')
    def test_on_scene_changed_when_no_items(self, show_mock):
        self.view.scale(2, 2)
        with patch('beeref.view.BeeGraphicsView.recalc_scene_rect') as r:
            self.view.on_scene_changed(None)
            r.assert_called()
            show_mock.assert_called_once_with()
            assert self.view.get_scale() == 1

    def test_get_supported_image_formats_for_reading(self):
        formats = self.view.get_supported_image_formats(QtGui.QImageReader)
        assert '*.png' in formats
        assert '*.jpg' in formats

    def test_clear_scene(self):
        item = BeePixmapItem(QtGui.QImage())
        self.view.scene.addItem(item)
        self.view.scale(2, 2)
        self.view.translate(123, 456)
        self.view.filename = 'test.bee'
        self.view.undo_stack = MagicMock()

        self.view.clear_scene()
        assert not self.view.scene.items()
        assert self.view.transform().isIdentity()
        assert self.view.filename is None
        self.view.undo_stack.clear.assert_called_once_with()

    def test_reset_previous_transform_when_other_item(self):
        item1 = MagicMock()
        item2 = MagicMock()
        self.view.previous_transform = {
            'transform': 'foo',
            'toggle_item': item1,
        }
        self.view.reset_previous_transform(toggle_item=item2)
        assert self.view.previous_transform is None

    def test_reset_previous_transform_when_same_item(self):
        item = MagicMock()
        self.view.previous_transform = {
            'transform': 'foo',
            'toggle_item': item,
        }
        self.view.reset_previous_transform(toggle_item=item)
        assert self.view.previous_transform == {
            'transform': 'foo',
            'toggle_item': item,
        }

    @patch('beeref.view.BeeGraphicsView.fitInView')
    def test_fit_rect_no_toggle(self, fit_mock):
        rect = QtCore.QRectF(30, 40, 100, 80)
        self.view.previous_transform = {'toggle_item': MagicMock()}
        self.view.fit_rect(rect)
        fit_mock.assert_called_with(rect, Qt.AspectRatioMode.KeepAspectRatio)
        assert self.view.previous_transform is None

    @patch('beeref.view.BeeGraphicsView.fitInView')
    def test_fit_rect_toggle_when_no_previous(self, fit_mock):
        item = MagicMock()
        self.view.previous_transform = None
        self.view.setSceneRect(QtCore.QRectF(-2000, -2000, 4000, 4000))
        rect = QtCore.QRectF(30, 40, 100, 80)
        self.view.scale(2, 2)
        self.view.horizontalScrollBar().setValue(-40)
        self.view.verticalScrollBar().setValue(-50)
        self.view.fit_rect(rect, toggle_item=item)
        fit_mock.assert_called_with(rect, Qt.AspectRatioMode.KeepAspectRatio)
        assert self.view.previous_transform['toggle_item'] == item
        assert self.view.previous_transform['transform'].m11() == 2
        assert isinstance(self.view.previous_transform['center'],
                          QtCore.QPointF)

    @patch('beeref.view.BeeGraphicsView.fitInView')
    @patch('beeref.view.BeeGraphicsView.centerOn')
    def test_fit_rect_toggle_when_previous(self, center_mock, fit_mock):
        item = MagicMock()
        self.view.previous_transform = {
            'toggle_item': item,
            'transform': QtGui.QTransform.fromScale(2, 2),
            'center': QtCore.QPointF(30, 40)
        }
        self.view.setSceneRect(QtCore.QRectF(-2000, -2000, 4000, 4000))
        rect = QtCore.QRectF(30, 40, 100, 80)
        self.view.fit_rect(rect, toggle_item=item)
        fit_mock.assert_not_called()
        center_mock.assert_called_once_with(QtCore.QPointF(30, 40))
        assert self.view.get_scale() == 2

    @patch('beeref.view.BeeGraphicsView.clear_scene')
    def test_open_from_file(self, clear_mock):
        root = os.path.dirname(__file__)
        filename = os.path.join(root, 'assets', 'test1item.bee')
        self.view.open_from_file(filename)
        self.view.worker.wait()
        items = self.queue2list(self.view.scene.items_to_add)
        assert len(items) == 1
        item, selected = items[0]
        assert items[0][0].pixmap()
        assert items[0][1] is False
        clear_mock.assert_called_once_with()

    @patch('PyQt6.QtWidgets.QMessageBox.warning')
    def test_open_from_file_when_error(self, warn_mock):
        # FIXME: #1
        # Can't check signal handling currently
        self.view.open_from_file('uieauiae')
        self.view.worker.wait()
        assert self.view.scene.items_to_add.empty() is True
        assert len(self.view.scene.items()) == 0

    @patch('PyQt6.QtWidgets.QFileDialog.getOpenFileName')
    def test_on_action_open(self, dialog_mock):
        # FIXME: #1
        # Can't check signal handling currently
        root = os.path.dirname(__file__)
        dialog_mock.return_value = (
            os.path.join(root, 'assets', 'test1item.bee'),
            None)
        self.view.on_action_open()
        self.view.worker.wait()
        items = self.queue2list(self.view.scene.items_to_add)
        assert len(items) == 1
        assert items[0][0].pixmap()
        assert items[0][1] is False

    @patch('PyQt6.QtWidgets.QFileDialog.getOpenFileName')
    @patch('beeref.view.BeeGraphicsView.on_action_open')
    def test_on_action_open_when_no_filename(self, dialog_mock, open_mock):
        dialog_mock.return_value = (None, None)
        self.view.on_action_open()
        open_mock.assert_not_called()

    @patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName')
    def test_on_action_save_as(self, dialog_mock):
        item = BeePixmapItem(QtGui.QImage(self.imgfilename3x3))
        self.view.scene.addItem(item)
        with tempfile.TemporaryDirectory() as tmpdir:
            filename = os.path.join(tmpdir, 'test.bee')
            assert os.path.exists(filename) is False
            dialog_mock.return_value = (filename, None)
            self.view.on_action_save_as()
            self.view.worker.wait()
            assert os.path.exists(filename) is True

    @patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName')
    @patch('beeref.view.BeeGraphicsView.do_save')
    def test_on_action_save_as_when_no_filename(self, save_mock, dialog_mock):
        item = BeePixmapItem(QtGui.QImage(self.imgfilename3x3))
        self.view.scene.addItem(item)
        dialog_mock.return_value = (None, None)
        self.view.on_action_save_as()
        save_mock.assert_not_called()

    @patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName')
    def test_on_action_save_as_filename_doesnt_end_with_bee(self, dialog_mock):
        item = BeePixmapItem(QtGui.QImage(self.imgfilename3x3))
        self.view.scene.addItem(item)
        with tempfile.TemporaryDirectory() as tmpdir:
            filename = os.path.join(tmpdir, 'test')
            assert os.path.exists(filename) is False
            dialog_mock.return_value = (filename, None)
            self.view.on_action_save_as()
            self.view.worker.wait()
            assert os.path.exists(f'{filename}.bee') is True

    @mark.skip('needs pytest-qt')
    @patch('PyQt6.QtWidgets.QMessageBox.warning')
    @patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName')
    @patch('beeref.fileio.save')
    def test_on_action_save_as_when_error(
            self, save_mock, dialog_mock, warn_mock):
        item = BeePixmapItem(QtGui.QImage(self.imgfilename3x3))
        self.view.scene.addItem(item)
        with tempfile.TemporaryDirectory() as tmpdir:
            filename = os.path.join(tmpdir, 'test.bee')
            assert os.path.exists(filename) is False
            dialog_mock.return_value = (filename, None)
            save_mock.side_effect = fileio.BeeFileIOError('foo', 'test.bee')
            self.view.on_action_save_as()
            warn_mock.assert_called_once()
            assert os.path.exists(filename) is False

    def test_on_action_save(self):
        item = BeePixmapItem(QtGui.QImage(self.imgfilename3x3))
        self.view.scene.addItem(item)
        with tempfile.TemporaryDirectory() as tmpdir:
            self.view.filename = os.path.join(tmpdir, 'test.bee')
            assert os.path.exists(self.view.filename) is False
            self.view.on_action_save()
            self.view.worker.wait()
            assert os.path.exists(self.view.filename) is True

    @patch('beeref.view.BeeGraphicsView.on_action_save_as')
    def test_on_action_save_when_no_filename(self, save_as_mock):
        item = BeePixmapItem(QtGui.QImage(self.imgfilename3x3))
        self.view.scene.addItem(item)
        self.view.filename = None
        self.view.on_action_save()
        save_as_mock.assert_called_once_with()

    @patch('beeref.gui.HelpDialog.show')
    def test_on_action_help(self, show_mock):
        self.view.on_action_help()
        show_mock.assert_called_once()

    @patch('beeref.scene.BeeGraphicsScene.clearSelection')
    @patch('PyQt6.QtWidgets.QFileDialog.getOpenFileNames')
    def test_on_action_insert_images(self, dialog_mock, clear_mock):
        # FIXME: #1
        # Can't check signal handling currently
        dialog_mock.return_value = ([self.imgfilename3x3], None)
        self.view.on_action_insert_images()
        self.view.worker.wait()
        items = self.queue2list(self.view.scene.items_to_add)
        assert len(items) == 1
        assert items[0][0].pixmap()
        assert items[0][1] is True
        clear_mock.assert_called_once_with()

    @patch('beeref.scene.BeeGraphicsScene.clearSelection')
    @patch('PyQt6.QtWidgets.QFileDialog.getOpenFileNames')
    def test_on_action_insert_images_when_error(self, dialog_mock, clear_mock):
        # FIXME: #1
        # Can't check signal handling currently
        dialog_mock.return_value = (
            [self.imgfilename3x3, 'iaeiae', 'trntrn'], None)
        self.view.on_action_insert_images()
        self.view.worker.wait()
        items = self.queue2list(self.view.scene.items_to_add)
        assert len(items) == 1
        assert items[0][0].pixmap()
        assert items[0][1] is True
        clear_mock.assert_called_once_with()

    @patch('beeref.scene.BeeGraphicsScene.clearSelection')
    @patch('PyQt6.QtGui.QClipboard.image')
    def test_on_action_paste(self, clipboard_mock, clear_mock):
        clipboard_mock.return_value = QtGui.QImage(self.imgfilename3x3)
        self.view.on_action_paste()
        assert len(self.view.scene.items()) == 1
        assert self.view.scene.items()[0].isSelected() is True
        clear_mock.assert_called_once_with()

    @patch('beeref.scene.BeeGraphicsScene.clearSelection')
    @patch('PyQt6.QtGui.QClipboard.image')
    def test_on_action_paste_when_empty(self, clipboard_mock, clear_mock):
        clipboard_mock.return_value = QtGui.QImage()
        self.view.on_action_paste()
        assert len(self.view.scene.items()) == 0
        clear_mock.assert_not_called()
