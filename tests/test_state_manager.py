import unittest
from state_manager import AppState

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

if __name__ == '__main__':
    unittest.main()
