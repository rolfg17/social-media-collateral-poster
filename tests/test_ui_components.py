import unittest
from unittest.mock import MagicMock, patch
from state_manager import AppState, UIState, ImageGridState, ConfigurationState, HeaderSettingsState, FileUploaderState, MainContentState, PhotosState, DriveState, ExportOptionsState
from ui_components import ConfigurationUI, ImageGridUI, HeaderSettingsUI, MainContentUI, FileUploaderUI, PhotosUI, DriveUI, ExportOptionsUI

# Mock Config class
class Config:
    def __init__(self):
        self.config = {}
        
    def __getitem__(self, key):
        return self.config.get(key, {})

class TestConfigurationUI(unittest.TestCase):
    def setUp(self):
        """Set up test case with mocked dependencies"""
        self.state = AppState()
        self.config = Config()  # Mock the Config instance
        self.ui = ConfigurationUI(self.state, self.config)
        
    def test_initialization(self):
        """Test that ConfigurationUI properly initializes with UIState"""
        self.assertIsInstance(self.ui.ui_state, UIState)
        self.assertIs(self.ui.ui_state.state, self.state)
        
    def test_select_all_checkbox(self):
        """Test that select all checkbox uses UIState"""
        # Mock the checkbox state
        setattr(self.state, "checkbox_select_all", True)
        self.assertTrue(self.ui.ui_state.get_checkbox("select_all"))

class TestImageGridUI(unittest.TestCase):
    def setUp(self):
        """Set up test case."""
        self.state = AppState()
        self.app = MagicMock()
        self.ui = ImageGridUI(self.state, self.app)
        
    def test_initialization(self):
        """Test that ImageGridUI properly initializes with state."""
        self.assertIsInstance(self.ui.ui_state, UIState)
        self.assertIsInstance(self.ui.grid_state, ImageGridState)
        self.assertEqual(self.ui.state, self.state)
        
    @patch('streamlit.checkbox')
    @patch('streamlit.image')
    def test_image_checkbox(self, mock_image, mock_checkbox):
        """Test image selection checkbox."""
        # Set up state with images
        images = ["/path/to/image1.jpg", "/path/to/image2.jpg"]
        self.ui.grid_state.set_images(images)
        
        # Mock checkbox to return True for first image, False for second
        mock_checkbox.side_effect = [True, False]
        
        # Call render
        self.ui.render()
        
        # Verify state was updated
        selected = self.ui.grid_state.get_selected_images()
        self.assertTrue(selected[images[0]])
        self.assertFalse(selected[images[1]])
        
        # Verify image was displayed
        self.assertEqual(mock_image.call_count, 2)
        mock_image.assert_any_call(images[0])
        mock_image.assert_any_call(images[1])

class TestHeaderSettingsUI(unittest.TestCase):
    def setUp(self):
        """Set up test case with mocked dependencies"""
        self.state = AppState()
        self.config = Config()
        self.config.config['fonts'] = {
            'paths': {'font1': 'path1', 'font2': 'path2'},
            'header_fonts': ['font1', 'font2'],
            'body_fonts': ['font1', 'font2']
        }
        self.ui = HeaderSettingsUI(self.state, self.config)
        
    def test_initialization(self):
        """Test that HeaderSettingsUI properly initializes with UIState"""
        self.assertIsInstance(self.ui.ui_state, UIState)
        self.assertIs(self.ui.ui_state.state, self.state)
        
    def test_header_footer_checkbox(self):
        """Test that header/footer checkbox uses UIState"""
        setattr(self.state, "checkbox_show_header_footer", True)
        self.assertTrue(self.ui.ui_state.get_checkbox("show_header_footer"))
        
    def test_header_override(self):
        """Test header override state management"""
        # Test initial state
        self.assertEqual(self.ui.ui_state.get_header_override(), "")
        
        # Test setting override
        self.ui.ui_state.set_header_override("Test Header")
        self.assertEqual(self.ui.ui_state.get_header_override(), "Test Header")
        
    def test_font_paths(self):
        """Test font path state management"""
        # Test initial state
        self.assertEqual(self.ui.ui_state.get_font_path("header"), "")
        self.assertEqual(self.ui.ui_state.get_font_path("body"), "")
        
        # Test setting paths
        self.ui.ui_state.set_font_path("header", "path1")
        self.ui.ui_state.set_font_path("body", "path2")
        self.assertEqual(self.ui.ui_state.get_font_path("header"), "path1")
        self.assertEqual(self.ui.ui_state.get_font_path("body"), "path2")

class TestMainContentUI(unittest.TestCase):
    def setUp(self):
        """Set up test case."""
        self.state = AppState()
        self.app = MagicMock()
        self.ui = MainContentUI(self.state, self.app)
        
    def test_initialization(self):
        """Test that MainContentUI properly initializes with state."""
        self.assertIsInstance(self.ui.ui_state, UIState)
        self.assertIsInstance(self.ui.main_content_state, MainContentState)
        self.assertEqual(self.ui.state, self.state)
        
    def test_render_empty(self):
        """Test rendering with no content."""
        # Set up empty state
        self.ui.main_content_state.set_sections([])
        self.ui.main_content_state.set_cleaned_contents("")
        
        # Call render
        self.ui.render()
        
    def test_render_with_content(self):
        """Test rendering with content."""
        # Set up state with content
        sections = ["Section 1", "Section 2"]
        cleaned_content = "Cleaned content"
        self.ui.main_content_state.set_sections(sections)
        self.ui.main_content_state.set_cleaned_contents(cleaned_content)
        
        # Call render
        self.ui.render()

class TestFileUploaderUI(unittest.TestCase):
    def setUp(self):
        """Set up test case."""
        self.state = AppState()
        self.file_processor = MagicMock()
        self.ui = FileUploaderUI(self.state, self.file_processor)
        
    def test_initialization(self):
        """Test that FileUploaderUI properly initializes with state."""
        self.assertIsInstance(self.ui.ui_state, UIState)
        self.assertIsInstance(self.ui.uploader_state, FileUploaderState)
        self.assertEqual(self.ui.state, self.state)
        
    @patch('streamlit.file_uploader')
    def test_handle_file_upload_success(self, mock_uploader):
        """Test successful file upload handling."""
        # Mock file upload
        mock_file = MagicMock()
        mock_file.name = "test.txt"
        mock_uploader.return_value = [mock_file]
        
        # Mock file processing
        self.file_processor.process_file.return_value = "Processed content"
        
        # Call render
        self.ui.render()
        
        # Verify state was updated
        self.assertEqual(self.ui.uploader_state.get_processed_file(), "Processed content")
        self.assertEqual(self.ui.uploader_state.get_uploaded_files(), ["test.txt"])
        self.assertEqual(self.ui.uploader_state.get_upload_status(), "Files processed successfully!")
        self.assertEqual(self.ui.uploader_state.get_upload_error(), "")
        
    @patch('streamlit.file_uploader')
    def test_handle_file_upload_failure(self, mock_uploader):
        """Test file upload error handling."""
        # Mock file upload
        mock_file = MagicMock()
        mock_file.name = "test.txt"
        mock_uploader.return_value = [mock_file]
        
        # Mock file processing error
        self.file_processor.process_file.side_effect = Exception("Test error")
        
        # Call render
        self.ui.render()
        
        # Verify error state
        self.assertEqual(self.ui.uploader_state.get_upload_status(), "Error processing files")
        self.assertEqual(self.ui.uploader_state.get_upload_error(), "Test error")

class TestPhotosUI(unittest.TestCase):
    def setUp(self):
        """Set up test case with mocked dependencies"""
        self.state = AppState()
        self.app = MagicMock()
        self.ui = PhotosUI(self.state, self.app)
        
    def test_initialization(self):
        """Test that PhotosUI properly initializes"""
        self.assertIsInstance(self.ui.photos_state, PhotosState)
        self.assertEqual(self.ui.state, self.state)
        
    @patch('streamlit.button')
    @patch('os.path.exists')
    def test_save_to_photos_success(self, mock_exists, mock_button):
        """Test successful photo save"""
        # Mock dependencies
        mock_file = MagicMock()
        mock_file.name = "test.md"
        self.ui.ui_state.set_processed_file(mock_file)
        
        test_path = "/tmp/test.png"
        self.ui.photos_state.set_image_path(test_path)
        self.app.save_to_photos.return_value = True
        mock_button.return_value = True  # Simulate button click
        mock_exists.return_value = True  # Simulate file exists
        
        # Call render
        self.ui.render()
        
        # Verify save was called
        self.app.save_to_photos.assert_called_once_with(test_path)
        
    @patch('streamlit.button')
    @patch('os.path.exists')
    def test_save_to_photos_failure(self, mock_exists, mock_button):
        """Test photo save failure"""
        # Mock dependencies
        mock_file = MagicMock()
        mock_file.name = "test.md"
        self.ui.ui_state.set_processed_file(mock_file)
        
        test_path = "/tmp/test.png"
        self.ui.photos_state.set_image_path(test_path)
        self.app.save_to_photos.return_value = False
        mock_button.return_value = True  # Simulate button click
        mock_exists.return_value = True  # Simulate file exists
        
        # Call render
        self.ui.render()
        
        # Verify save was called
        self.app.save_to_photos.assert_called_once_with(test_path)

class TestDriveUI(unittest.TestCase):
    def setUp(self):
        """Set up test case with mocked dependencies"""
        self.state = AppState()
        self.app = MagicMock()
        self.ui = DriveUI(self.state, self.app)
        
    def test_initialization(self):
        """Test that DriveUI properly initializes with UIState"""
        self.assertIsInstance(self.ui.ui_state, UIState)
        self.assertIsInstance(self.ui.drive_state, DriveState)
        self.assertEqual(self.ui.state, self.state)
        
    @patch('streamlit.button')
    def test_export_to_drive_success(self, mock_button):
        """Test successful drive export"""
        # Mock dependencies
        self.ui.drive_state.set_authenticated(True)
        mock_button.return_value = True
        
        # Call render
        self.ui.render()
        
        # Verify export was called
        self.app.export_to_drive.assert_called_once()
        
    @patch('streamlit.button')
    def test_export_to_drive_failure(self, mock_button):
        """Test drive export failure"""
        # Mock dependencies
        self.ui.drive_state.set_authenticated(True)
        mock_button.return_value = True
        self.app.export_to_drive.return_value = False
        
        # Call render
        self.ui.render()
        
        # Verify export was called
        self.app.export_to_drive.assert_called_once()
        
    @patch('streamlit.button')
    def test_drive_authentication_success(self, mock_button):
        """Test successful drive authentication"""
        # Mock dependencies
        self.app.authenticate_drive.return_value = True
        mock_button.return_value = True
        
        # Call render
        self.ui.render()
        
        # Verify authentication was called and state was updated
        self.app.authenticate_drive.assert_called_once()
        self.assertTrue(self.ui.drive_state.is_authenticated())
        
    @patch('streamlit.button')
    def test_drive_authentication_failure(self, mock_button):
        """Test drive authentication failure"""
        # Mock dependencies
        self.app.authenticate_drive.return_value = False
        mock_button.return_value = True
        
        # Call render
        self.ui.render()
        
        # Verify authentication was called and state was not updated
        self.app.authenticate_drive.assert_called_once()
        self.assertFalse(self.ui.drive_state.is_authenticated())

class TestExportOptionsUI(unittest.TestCase):
    def setUp(self):
        """Set up test case."""
        self.state = AppState()
        self.app = MagicMock()
        self.app.photos_ui = MagicMock()
        self.app.drive_ui = MagicMock()
        self.ui = ExportOptionsUI(self.state, self.app)
        
    def test_initialization(self):
        """Test that ExportOptionsUI properly initializes with state."""
        self.assertIsInstance(self.ui.ui_state, UIState)
        self.assertIsInstance(self.ui.export_state, ExportOptionsState)
        self.assertEqual(self.ui.state, self.state)
        self.assertEqual(self.ui.app, self.app)
        
    @patch('streamlit.button')
    def test_save_to_photos(self, mock_button):
        """Test saving to photos."""
        # Set up state with selected images
        selected_images = ["/path/to/image1.jpg", "/path/to/image2.jpg"]
        self.ui.export_state.set_selected_images(selected_images)
        
        # Mock button click
        mock_button.side_effect = [True, False]  # Photos button clicked, Drive button not clicked
        
        # Call render
        self.ui.render()
        
        # Verify photos_ui was called
        self.app.photos_ui.save_to_photos.assert_called_once_with(selected_images)
        self.app.drive_ui.export_to_drive.assert_not_called()
        
    @patch('streamlit.button')
    def test_export_to_drive(self, mock_button):
        """Test exporting to drive."""
        # Set up state with selected images
        selected_images = ["/path/to/image1.jpg", "/path/to/image2.jpg"]
        self.ui.export_state.set_selected_images(selected_images)
        
        # Mock button click
        mock_button.side_effect = [False, True]  # Photos button not clicked, Drive button clicked
        
        # Call render
        self.ui.render()
        
        # Verify drive_ui was called
        self.app.photos_ui.save_to_photos.assert_not_called()
        self.app.drive_ui.export_to_drive.assert_called_once_with(selected_images)

if __name__ == '__main__':
    unittest.main()
