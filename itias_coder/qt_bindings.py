"""Qt import surface: PySide6 (dev/macOS) or PySide2 (Windows 7+ legacy builds)."""

from __future__ import annotations

try:
    from PySide6 import QtCore, QtGui, QtMultimedia, QtMultimediaWidgets, QtWidgets

    QT_API = 6
except ImportError:  # Windows 7 CI / PySide2-only installs
    from PySide2 import QtCore, QtGui, QtMultimedia, QtMultimediaWidgets, QtWidgets

    QT_API = 5

# Re-export common symbols
Qt = QtCore.Qt
QApplication = QtWidgets.QApplication
QMainWindow = QtWidgets.QMainWindow
QWidget = QtWidgets.QWidget
QVBoxLayout = QtWidgets.QVBoxLayout
QHBoxLayout = QtWidgets.QHBoxLayout
QGridLayout = QtWidgets.QGridLayout
QLabel = QtWidgets.QLabel
QPushButton = QtWidgets.QPushButton
QGroupBox = QtWidgets.QGroupBox
QDialog = QtWidgets.QDialog
QFileDialog = QtWidgets.QFileDialog
QMessageBox = QtWidgets.QMessageBox
QProgressBar = QtWidgets.QProgressBar
QStatusBar = QtWidgets.QStatusBar
QScrollArea = QtWidgets.QScrollArea
QSizePolicy = QtWidgets.QSizePolicy
QLineEdit = QtWidgets.QLineEdit
QSpinBox = QtWidgets.QSpinBox
QTextEdit = QtWidgets.QTextEdit
QDialogButtonBox = QtWidgets.QDialogButtonBox
QFont = QtGui.QFont
QColor = QtGui.QColor
QKeySequence = QtGui.QKeySequence
QCloseEvent = QtGui.QCloseEvent
QUrl = QtCore.QUrl
QSettings = QtCore.QSettings
QThread = QtCore.QThread
Signal = QtCore.Signal
QObject = QtCore.QObject
QVideoWidget = QtMultimediaWidgets.QVideoWidget
QMediaPlayer = QtMultimedia.QMediaPlayer

if QT_API == 6:
    from PySide6.QtMultimedia import QAudioOutput

    QShortcut = QtGui.QShortcut
    QSizePolicyExpanding = QSizePolicy.Policy.Expanding
    QSizePolicyFixed = QSizePolicy.Policy.Fixed
    MediaEndOfMedia = QMediaPlayer.MediaStatus.EndOfMedia
    MediaNoError = QMediaPlayer.Error.NoError
    MB_YES = QMessageBox.StandardButton.Yes
    MB_NO = QMessageBox.StandardButton.No
else:
    from PySide2.QtMultimedia import QMediaContent

    QShortcut = QtWidgets.QShortcut
    QAudioOutput = None  # type: ignore[misc, assignment]
    QSizePolicyExpanding = QSizePolicy.Expanding
    QSizePolicyFixed = QSizePolicy.Fixed
    MediaEndOfMedia = QMediaPlayer.EndOfMedia
    MediaNoError = QMediaPlayer.NoError
    MB_YES = QMessageBox.Yes
    MB_NO = QMessageBox.No


def qt_exec(app_or_dialog) -> int:
    """Qt5 uses exec_(); Qt6 uses exec()."""
    if QT_API == 6:
        return app_or_dialog.exec()
    return app_or_dialog.exec_()


class SegmentPlayer:
    """Thin wrapper over Qt5/Qt6 video playback for slice loops."""

    def __init__(self, video_widget: QVideoWidget):
        self._video_widget = video_widget
        self._on_end_of_media = None

        if QT_API == 6:
            self._audio = QAudioOutput()
            self._player = QMediaPlayer()
            self._player.setAudioOutput(self._audio)
            self._player.setVideoOutput(video_widget)
            self._player.mediaStatusChanged.connect(self._handle_media_status)
            self._player.errorOccurred.connect(self._handle_error_qt6)
            self._audio.setVolume(0.8)
        else:
            self._audio = None
            self._player = QMediaPlayer()
            self._player.setVideoOutput(video_widget)
            self._player.setVolume(80)
            self._player.mediaStatusChanged.connect(self._handle_media_status)
            self._player.error.connect(self._handle_error_qt5)

    def set_end_of_media_callback(self, callback) -> None:
        self._on_end_of_media = callback

    def play_file(self, filepath: str) -> None:
        url = QUrl.fromLocalFile(filepath)
        if QT_API == 6:
            self._player.setSource(url)
        else:
            self._player.setMedia(QMediaContent(url))
        self._player.play()

    def replay(self) -> None:
        if QT_API == 6:
            self._player.setPosition(0)
        else:
            self._player.setPosition(0)
        self._player.play()

    def stop(self) -> None:
        self._player.stop()

    def _handle_media_status(self, status) -> None:
        if status == MediaEndOfMedia and self._on_end_of_media:
            self._on_end_of_media()

    def _handle_error_qt6(self, error, error_string: str) -> None:
        if error != MediaNoError:
            self._last_error = error_string

    def _handle_error_qt5(self, error) -> None:
        if error != MediaNoError:
            self._last_error = self._player.errorString()

    @property
    def last_error(self) -> str:
        return getattr(self, "_last_error", "")
