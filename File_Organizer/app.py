import os
import shutil
import json
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, jsonify, request
import google.generativeai as genai
from werkzeug.utils import secure_filename
import mimetypes
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
DOWNLOADS_PATH = 'C:/Users/Plesu/Desktop/File_Organizer/downloads/'
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
SUMMARY_FILE = os.path.join(DOWNLOADS_PATH, 'organization_summary.json')

# Initialize Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
else:
    logger.warning("Gemini API key not found. AI features will be disabled.")
    model = None

# File type mappings
FILE_CATEGORIES = {
    'images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.tiff'],
    'documents': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.pages'],
    'spreadsheets': ['.xls', '.xlsx', '.csv', '.ods', '.numbers'],
    'presentations': ['.ppt', '.pptx', '.odp', '.key'],
    'videos': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'],
    'audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a'],
    'archives': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz'],
    'executables': ['.exe', '.msi', '.dmg', '.pkg', '.deb', '.rpm', '.appimage'],
    'code': ['.py', '.js', '.html', '.css', '.java', '.cpp', '.c', '.php', '.rb', '.go'],
    'fonts': ['.ttf', '.otf', '.woff', '.woff2', '.eot']
}

class FileOrganizer:
    def __init__(self):
        self.summary = []
        self.load_existing_summary()
    
    def load_existing_summary(self):
        """Load existing summary from file"""
        if os.path.exists(SUMMARY_FILE):
            try:
                with open(SUMMARY_FILE, 'r') as f:
                    self.summary = json.load(f)
            except Exception as e:
                logger.error(f"Error loading summary: {e}")
                self.summary = []
    
    def save_summary(self):
        """Save summary to file"""
        try:
            with open(SUMMARY_FILE, 'w') as f:
                json.dump(self.summary, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving summary: {e}")
    
    def get_file_category(self, file_path):
        """Determine file category based on extension"""
        extension = Path(file_path).suffix.lower()
        for category, extensions in FILE_CATEGORIES.items():
            if extension in extensions:
                return category
        return 'others'
    
    def sanitize_filename(self, filename):
        """Replace spaces with underscores and sanitize filename"""
        # Replace spaces with underscores
        sanitized = filename.replace(' ', '_')
        # Remove or replace other problematic characters
        sanitized = secure_filename(sanitized)
        return sanitized
    
    def generate_ai_description(self, file_path, action_type, old_name=None, new_name=None):
        """Generate AI description for the file operation"""
        if not model:
            return f"File {action_type}: {new_name or old_name}"
        
        try:
            file_info = {
                'filename': new_name or old_name,
                'size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                'extension': Path(file_path).suffix,
                'action': action_type
            }
            
            prompt = f"""
            Analyze this file operation and provide a brief, informative description:
            
            Action: {action_type}
            Filename: {file_info['filename']}
            File extension: {file_info['extension']}
            File size: {file_info['size']} bytes
            Old name: {old_name if old_name else 'N/A'}
            New name: {new_name if new_name else 'N/A'}
            
            Provide a concise description (max 100 words) of what this file likely contains and the action performed.
            """
            
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error generating AI description: {e}")
            return f"File {action_type}: {new_name or old_name}"
    
    def organize_file(self, file_path):
        """Organize a single file"""
        try:
            if not os.path.exists(file_path):
                return False, "File not found"
            
            # Get file info
            filename = os.path.basename(file_path)
            category = self.get_file_category(file_path)
            sanitized_name = self.sanitize_filename(filename)
            
            # Create category folder
            category_path = os.path.join(DOWNLOADS_PATH, category)
            os.makedirs(category_path, exist_ok=True)
            
            # Determine new file path
            new_file_path = os.path.join(category_path, sanitized_name)
            
            # Handle file name conflicts
            counter = 1
            original_new_path = new_file_path
            while os.path.exists(new_file_path):
                name, ext = os.path.splitext(sanitized_name)
                new_file_path = os.path.join(category_path, f"{name}_{counter}{ext}")
                counter += 1
            
            # Move and rename file
            shutil.move(file_path, new_file_path)
            
            # Generate AI description
            ai_description = self.generate_ai_description(
                new_file_path, 
                "organized and renamed",
                filename, 
                os.path.basename(new_file_path)
            )
            
            # Add to summary
            action_summary = {
                'timestamp': datetime.now().isoformat(),
                'action': 'organize',
                'original_name': filename,
                'new_name': os.path.basename(new_file_path),
                'original_path': file_path,
                'new_path': new_file_path,
                'category': category,
                'ai_description': ai_description
            }
            
            self.summary.append(action_summary)
            self.save_summary()
            
            return True, action_summary
            
        except Exception as e:
            logger.error(f"Error organizing file {file_path}: {e}")
            return False, str(e)
    
    def organize_all_files(self):
        """Organize all files in downloads folder"""
        organized_files = []
        errors = []
        
        # Get all files in downloads folder (not in subfolders)
        for item in os.listdir(DOWNLOADS_PATH):
            item_path = os.path.join(DOWNLOADS_PATH, item)
            if os.path.isfile(item_path) and item != 'organization_summary.json':
                success, result = self.organize_file(item_path)
                if success:
                    organized_files.append(result)
                else:
                    errors.append(f"Error with {item}: {result}")
        
        return organized_files, errors
    
    def get_summary(self, limit=None):
        """Get organization summary"""
        summary_data = self.summary.copy()
        summary_data.reverse()  # Most recent first
        if limit:
            summary_data = summary_data[:limit]
        return summary_data

# Initialize organizer
organizer = FileOrganizer()

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/organize', methods=['POST'])
def organize_files():
    """Organize all files in downloads folder"""
    try:
        organized, errors = organizer.organize_all_files()
        return jsonify({
            'success': True,
            'organized_count': len(organized),
            'organized_files': organized,
            'errors': errors
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/organize/<filename>', methods=['POST'])
def organize_single_file(filename):
    """Organize a specific file"""
    try:
        file_path = os.path.join(DOWNLOADS_PATH, filename)
        success, result = organizer.organize_file(file_path)
        
        if success:
            return jsonify({'success': True, 'result': result})
        else:
            return jsonify({'success': False, 'error': result}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/files')
def list_files():
    """List all files in downloads folder"""
    try:
        files = []
        for item in os.listdir(DOWNLOADS_PATH):
            item_path = os.path.join(DOWNLOADS_PATH, item)
            if os.path.isfile(item_path) and item != 'organization_summary.json':
                file_info = {
                    'name': item,
                    'size': os.path.getsize(item_path),
                    'category': organizer.get_file_category(item_path),
                    'modified': os.path.getmtime(item_path)
                }
                files.append(file_info)
        
        return jsonify({'files': files})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/summary')
def get_summary():
    """Get organization summary"""
    try:
        limit = request.args.get('limit', type=int)
        summary = organizer.get_summary(limit)
        return jsonify({'summary': summary})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/stats')
def get_stats():
    """Get organization statistics"""
    try:
        # Count files by category
        category_counts = {}
        total_files = 0
        
        for category in FILE_CATEGORIES.keys():
            category_path = os.path.join(DOWNLOADS_PATH, category)
            if os.path.exists(category_path):
                count = len([f for f in os.listdir(category_path) if os.path.isfile(os.path.join(category_path, f))])
                category_counts[category] = count
                total_files += count
        
        # Count unorganized files
        unorganized = 0
        for item in os.listdir(DOWNLOADS_PATH):
            item_path = os.path.join(DOWNLOADS_PATH, item)
            if os.path.isfile(item_path) and item != 'organization_summary.json':
                unorganized += 1
        
        return jsonify({
            'total_organized': total_files,
            'unorganized': unorganized,
            'category_counts': category_counts,
            'total_operations': len(organizer.summary)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Ensure downloads directory exists
    os.makedirs(DOWNLOADS_PATH, exist_ok=True)
    
    # Create category folders
    for category in FILE_CATEGORIES.keys():
        category_path = os.path.join(DOWNLOADS_PATH, category)
        os.makedirs(category_path, exist_ok=True)
    
    app.run(host='0.0.0.0', port=5000, debug=True)