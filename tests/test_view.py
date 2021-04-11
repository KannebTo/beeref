import os.path
import tempfile
from unittest.mock import patch

from PyQt6 import QtGui, QtWidgets

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

    @patch('beeref.view.BeeGraphicsView.recalc_scene_rect')
    @patch('beeref.gui.WelcomeOverlay.hide')
    def test_on_scene_changed_when_items(self, hide_mock, recalc_mock):
        item = BeePixmapItem(QtGui.QImage())
        self.view.scene.addItem(item)
        self.view.on_scene_changed(None)
        recalc_mock.assert_called_once_with()
        hide_mock.assert_called_once_with()

    @patch('beeref.view.BeeGraphicsView.recalc_scene_rect')
    @patch('beeref.gui.WelcomeOverlay.show')
    def test_on_scene_changed_when_no_items(self, show_mock, recalc_mock):
        self.view.on_scene_changed(None)
        recalc_mock.assert_called_once_with()
        show_mock.assert_called_once_with()

    def test_get_supported_image_formats_for_reading(self):
        formats = self.view.get_supported_image_formats(QtGui.QImageReader)
        assert '*.png' in formats
        assert '*.jpg' in formats

    def test_open_from_file(self):
        root = os.path.dirname(__file__)
        filename = os.path.join(root, 'assets', 'test1item.bee')
        self.view.open_from_file(filename)
        assert len(self.view.scene.items()) == 1

    @patch('PyQt6.QtWidgets.QMessageBox.warning')
    def test_open_from_file_when_error(self, warn_mock):
        self.view.open_from_file('uieauiae')
        assert len(self.view.scene.items()) == 0
        warn_mock.assert_called_once()

    @patch('PyQt6.QtWidgets.QFileDialog.getOpenFileName')
    def test_on_action_open(self, dialog_mock):
        root = os.path.dirname(__file__)
        dialog_mock.return_value = (
            os.path.join(root, 'assets', 'test1item.bee'),
            None)
        self.view.on_action_open()
        assert len(self.view.scene.items()) == 1

    @patch('PyQt6.QtWidgets.QFileDialog.getOpenFileName')
    def test_on_action_open_when_no_filename(self, dialog_mock):
        dialog_mock.return_value = (None, None)
        self.view.on_action_open()
        assert len(self.view.scene.items()) == 0

    @patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName')
    def test_on_action_save_as(self, dialog_mock):
        item = BeePixmapItem(QtGui.QImage(self.imgfilename3x3))
        self.view.scene.addItem(item)
        with tempfile.TemporaryDirectory() as tmpdir:
            filename = os.path.join(tmpdir, 'test.bee')
            assert os.path.exists(filename) is False
            dialog_mock.return_value = (filename, None)
            self.view.on_action_save_as()
            assert os.path.exists(filename) is True

    @patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName')
    @patch('beeref.fileio.save')
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
            assert os.path.exists(f'{filename}.bee') is True

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
            assert os.path.exists(self.view.filename) is True

    @patch('beeref.view.BeeGraphicsView.on_action_save_as')
    def test_on_action_save_when_no_filename(self, save_as_mock):
        item = BeePixmapItem(QtGui.QImage(self.imgfilename3x3))
        self.view.scene.addItem(item)
        self.view.filename = None
        self.view.on_action_save()
        save_as_mock.assert_called_once_with()

    @patch('beeref.scene.BeeGraphicsScene.clearSelection')
    @patch('PyQt6.QtWidgets.QFileDialog.getOpenFileNames')
    def test_on_action_insert_images(self, dialog_mock, clear_mock):
        dialog_mock.return_value = ([self.imgfilename3x3], None)
        self.view.on_action_insert_images()
        assert len(self.view.scene.items()) == 1
        assert self.view.scene.items()[0].isSelected() is True
        clear_mock.assert_called_once_with()

    @patch('beeref.scene.BeeGraphicsScene.clearSelection')
    @patch('PyQt6.QtWidgets.QMessageBox.warning')
    @patch('PyQt6.QtWidgets.QFileDialog.getOpenFileNames')
    def test_on_action_insert_images_when_error(
            self, dialog_mock, warn_mock, clear_mock):
        dialog_mock.return_value = (
            [self.imgfilename3x3, 'iaeiae', 'trntrn'], None)
        self.view.on_action_insert_images()
        assert len(self.view.scene.items()) == 1
        assert self.view.scene.items()[0].isSelected() is True
        warn_mock.assert_called_once()
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
