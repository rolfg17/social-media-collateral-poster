import unittest
from state_manager import AppState, StateCategory, UIState, ImageGridState, ConfigurationState, HeaderSettingsState, FileUploaderState, MainContentState, PhotosState, DriveState
from unittest.mock import MagicMock

class TestAppState(unittest.TestCase):
    def setUp(self):
        self.state = AppState()
        
    def test_get_existing_key(self):
        """Test getting an existing key returns correct value"""
        self.assertEqual(self.state.get('images'), {})
        
    def test_get_nonexistent_key(self):
        """Test getting a nonexistent key returns default"""
        self.assertEqual(self.state.get('nonexistent', 'default'), 'default')
        
    def test_set_new_key(self):
        """Test setting a new key"""
        self.state.set('test_key', 'test_value')
        self.assertEqual(self.state.get('test_key'), 'test_value')
        
    def test_has_existing_key(self):
        """Test has returns True for existing key"""
        self.assertTrue(self.state.has('images'))
        
    def test_has_nonexistent_key(self):
        """Test has returns False for nonexistent key"""
        self.assertFalse(self.state.has('nonexistent'))

    def test_update_dict_merge(self):
        """Test updating a dictionary merges values correctly"""
        initial_dict = {'key1': 'value1'}
        self.state.set('test_dict', initial_dict)
        
        # Update with new key
        self.state.update(test_dict={'key2': 'value2'})
        result = self.state.get('test_dict')
        self.assertEqual(result, {'key1': 'value1', 'key2': 'value2'})
        
        # Update existing key
        self.state.update(test_dict={'key1': 'new_value'})
        result = self.state.get('test_dict')
        self.assertEqual(result, {'key1': 'new_value', 'key2': 'value2'})
        
    def test_sync_with_session(self):
        """Test synchronization with session state"""
        # In test mode, sync_with_session should maintain current state
        initial_value = self.state.get('images')
        self.state.sync_with_session()
        self.assertEqual(self.state.get('images'), initial_value)
        
    def test_update_invalid_key(self):
        """Test updating a non-existent key is handled gracefully"""
        self.state.update(nonexistent_key='value')
        self.assertFalse(self.state.has('nonexistent_key'))

class TestStateCategory(unittest.TestCase):
    def setUp(self):
        """Set up test case with a mock state manager"""
        self.state_manager = AppState()
        
    def test_initialization(self):
        """Test that StateCategory properly initializes with state manager"""
        category = StateCategory(self.state_manager)
        self.assertIs(category.state, self.state_manager)
        
    def test_state_reference(self):
        """Test that state reference is maintained"""
        category = StateCategory(self.state_manager)
        self.state_manager.sections = {"test": "value"}
        self.assertEqual(category.state.sections, {"test": "value"})

class TestUIState(unittest.TestCase):
    def setUp(self):
        """Set up test case with state manager"""
        self.state_manager = AppState()
        self.ui_state = UIState(self.state_manager)
        
    def test_get_checkbox_nonexistent(self):
        """Test getting nonexistent checkbox returns False"""
        self.assertFalse(self.ui_state.get_checkbox("test"))
        
    def test_get_checkbox_existing(self):
        """Test getting existing checkbox returns correct value"""
        setattr(self.state_manager, "checkbox_test", True)
        self.assertTrue(self.ui_state.get_checkbox("test"))

class TestImageGridState(unittest.TestCase):
    def setUp(self):
        """Set up test case."""
        self.app_state = AppState()
        self.ui_state = UIState(self.app_state)
        self.state = ImageGridState(self.ui_state, self.app_state)
        
    def test_image_management(self):
        """Test image state management."""
        # Test getting empty images
        self.assertEqual(self.state.get_images(), [])
        
        # Test setting and getting images
        test_images = ["/path/to/image1.jpg", "/path/to/image2.jpg"]
        self.state.set_images(test_images)
        self.assertEqual(self.state.get_images(), test_images)
        
    def test_selected_images(self):
        """Test selected images state management."""
        # Test getting empty selections
        self.assertEqual(self.state.get_selected_images(), {})
        
        # Test setting and getting selections
        test_selections = {"/path/to/image1.jpg": True, "/path/to/image2.jpg": False}
        self.state.set_selected_images(test_selections)
        self.assertEqual(self.state.get_selected_images(), test_selections)
        
        # Test selecting individual image
        self.state.select_image("/path/to/image3.jpg", True)
        selections = self.state.get_selected_images()
        self.assertTrue(selections["/path/to/image3.jpg"])
        
        # Test clearing selections
        self.state.clear_selections()
        self.assertEqual(self.state.get_selected_images(), {})

class TestConfigurationState(unittest.TestCase):
    def setUp(self):
        """Set up test case with fresh state instances"""
        self.app_state = AppState()
        self.ui_state = UIState(self.app_state)
        self.state = ConfigurationState(self.ui_state, self.app_state)
        
    def test_select_all(self):
        """Test select all checkbox state management"""
        # Test initial state
        self.assertFalse(self.state.get_select_all())
        
        # Test setting state
        self.state.set_select_all(True)
        self.assertTrue(self.state.get_select_all())
        
    def test_show_header_footer(self):
        """Test show header/footer checkbox state management"""
        # Test initial state
        self.assertTrue(self.state.get_show_header_footer())
        
        # Test setting state
        self.state.set_show_header_footer(False)
        self.assertFalse(self.state.get_show_header_footer())

class TestHeaderSettingsState(unittest.TestCase):
    def setUp(self):
        """Set up test case with fresh state instances"""
        self.app_state = AppState()
        self.ui_state = UIState(self.app_state)
        self.state = HeaderSettingsState(self.ui_state, self.app_state)
        
    def test_header_override(self):
        """Test header override text management"""
        # Test initial state
        self.assertEqual(self.state.get_header_override(), "")
        
        # Test setting text
        self.state.set_header_override("Test Header")
        self.assertEqual(self.state.get_header_override(), "Test Header")
        
    def test_header_font_path(self):
        """Test header font path management"""
        # Test initial state
        self.assertEqual(self.state.get_header_font_path(), "")
        
        # Test setting path
        self.state.set_header_font_path("/path/to/header/font")
        self.assertEqual(self.state.get_header_font_path(), "/path/to/header/font")
        
    def test_body_font_path(self):
        """Test body font path management"""
        # Test initial state
        self.assertEqual(self.state.get_body_font_path(), "")
        
        # Test setting path
        self.state.set_body_font_path("/path/to/body/font")
        self.assertEqual(self.state.get_body_font_path(), "/path/to/body/font")

class TestFileUploaderState(unittest.TestCase):
    def setUp(self):
        """Set up test case with fresh state instances"""
        self.app_state = AppState()
        self.ui_state = UIState(self.app_state)
        self.state = FileUploaderState(self.ui_state, self.app_state)
        
    def test_uploaded_files(self):
        """Test uploaded files management"""
        # Test initial state
        self.assertEqual(self.state.get_uploaded_files(), [])
        
        # Test setting uploaded files
        test_files = ["file1.txt", "file2.txt"]
        self.state.set_uploaded_files(test_files)
        self.assertEqual(self.state.get_uploaded_files(), test_files)
        
    def test_upload_status(self):
        """Test upload status message management"""
        # Test initial state
        self.assertEqual(self.state.get_upload_status(), "")
        
        # Test setting status
        self.state.set_upload_status("Uploading...")
        self.assertEqual(self.state.get_upload_status(), "Uploading...")
        
    def test_upload_error(self):
        """Test upload error message management"""
        # Test initial state
        self.assertEqual(self.state.get_upload_error(), "")
        
        # Test setting error
        self.state.set_upload_error("Upload failed")
        self.assertEqual(self.state.get_upload_error(), "Upload failed")

class TestPhotosState(unittest.TestCase):
    def setUp(self):
        """Set up test case with fresh state instances"""
        self.app_state = AppState()
        self.ui_state = UIState(self.app_state)
        self.state = PhotosState(self.ui_state, self.app_state)
        
    def test_processed_file(self):
        """Test processed file management"""
        # Test initial state
        self.assertIsNone(self.state.get_processed_file())
        
        # Test after setting in UIState
        mock_file = MagicMock()
        mock_file.name = "test.md"
        self.ui_state.set_processed_file(mock_file)
        self.assertEqual(self.state.get_processed_file(), mock_file)
        
    def test_image_path(self):
        """Test image path management"""
        # Test initial state
        self.assertEqual(self.state.get_image_path(), "")
        
        # Test setting path
        test_path = "/path/to/image.png"
        self.state.set_image_path(test_path)
        self.assertEqual(self.state.get_image_path(), test_path)

class TestMainContentState(unittest.TestCase):
    def setUp(self):
        """Set up test case with fresh state instances"""
        self.app_state = AppState()
        self.ui_state = UIState(self.app_state)
        self.state = MainContentState(self.ui_state, self.app_state)
        
    def test_sections(self):
        """Test content sections management"""
        # Test initial state
        self.assertEqual(self.state.get_sections(), {})
        
        # Test setting sections
        test_sections = {"section1": "content1", "section2": "content2"}
        self.state.set_sections(test_sections)
        self.assertEqual(self.state.get_sections(), test_sections)
        
    def test_cleaned_contents(self):
        """Test cleaned contents management"""
        # Test initial state
        self.assertEqual(self.state.get_cleaned_contents(), {})
        
        # Test setting contents
        test_contents = {"section1": "cleaned1", "section2": "cleaned2"}
        self.state.set_cleaned_contents(test_contents)
        self.assertEqual(self.state.get_cleaned_contents(), test_contents)
        
    def test_header_override(self):
        """Test header override text retrieval"""
        # Test initial state
        self.assertEqual(self.state.get_header_override(), "")
        
        # Test after setting in UIState
        self.ui_state.set_header_override("Test Header")
        self.assertEqual(self.state.get_header_override(), "Test Header")
        
    def test_font_paths(self):
        """Test font paths retrieval"""
        # Test initial state
        self.assertEqual(self.state.get_header_font_path(), "")
        self.assertEqual(self.state.get_body_font_path(), "")
        
        # Test after setting in UIState
        self.ui_state.set_font_path("header", "/path/to/header")
        self.ui_state.set_font_path("body", "/path/to/body")
        self.assertEqual(self.state.get_header_font_path(), "/path/to/header")
        self.assertEqual(self.state.get_body_font_path(), "/path/to/body")

class TestDriveState(unittest.TestCase):
    """Test drive state management."""
    
    def setUp(self):
        """Set up test case."""
        self.app_state = AppState()
        self.ui_state = UIState(self.app_state)
        self.state = DriveState(self.ui_state, self.app_state)
        
    def test_authentication(self):
        """Test drive authentication state."""
        # Test initial state
        self.assertFalse(self.state.is_authenticated())
        
        # Test setting authenticated
        self.state.set_authenticated(True)
        self.assertTrue(self.state.is_authenticated())
        
        # Test setting not authenticated
        self.state.set_authenticated(False)
        self.assertFalse(self.state.is_authenticated())

if __name__ == '__main__':
    unittest.main()
