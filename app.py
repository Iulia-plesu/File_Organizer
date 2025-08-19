import os
import shutil
import json
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, jsonify, request
from flask.cli import load_dotenv
import google.generativeai as genai
from werkzeug.utils import secure_filename
import logging

app = Flask(__name__)

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FileOrganizer")

# --- Environment & Configuration ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DOWNLOADS_PATH = os.getenv('DOWNLOADS_PATH', os.path.abspath('./downloads/'))
SUMMARY_FILE = os.path.join(DOWNLOADS_PATH, 'organization_summary.json')

# --- Gemini AI Initialization ---
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
    logger.info("Gemini AI initialized successfully")
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
    """
    FileOrganizer handles file categorization, organization, and summary logging.
    It moves files into category folders, generates AI-powered descriptions, and maintains an operation log.
    """
    def __init__(self):
        self.summary = []
        self.load_existing_summary()

    def load_existing_summary(self):
        """
        Load the organization summary from disk if it exists.
        Initializes an empty summary if not found or on error.
        """
        if os.path.exists(SUMMARY_FILE):
            try:
                with open(SUMMARY_FILE, 'r') as f:
                    self.summary = json.load(f)
                logger.info(f"Loaded {len(self.summary)} entries from summary file")
            except Exception as e:
                logger.error(f"Error loading summary: {e}")
                self.summary = []
        else:
            logger.info("No existing summary file found, starting fresh")

    def save_summary(self):
        """
        Save the current organization summary to disk.
        Ensures the summary directory exists before writing.
        """
        try:
            os.makedirs(os.path.dirname(SUMMARY_FILE), exist_ok=True)
            with open(SUMMARY_FILE, 'w') as f:
                json.dump(self.summary, f, indent=2, default=str)
            logger.info(f"Summary saved with {len(self.summary)} entries")
        except Exception as e:
            logger.error(f"Error saving summary: {e}")

    def get_file_category(self, file_path):
        """
        Determine the file category based on its extension.
        Returns the category name or 'others' if not matched.
        """
        extension = Path(file_path).suffix.lower()
        for category, extensions in FILE_CATEGORIES.items():
            if extension in extensions:
                return category
        return 'others'

    def sanitize_filename(self, filename):
        """
        Sanitize a filename by replacing spaces and removing unsafe characters.
        """
        sanitized = filename.replace(' ', '_')
        sanitized = secure_filename(sanitized)
        return sanitized

    def generate_ai_description(self, file_path, action_type, old_name=None, new_name=None):
        """
        Generate a brief, AI-powered description of a file operation.
        Returns a string description or a fallback if AI is unavailable.
        """
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
        """
        Organize a single file by moving it to its category folder and logging the operation.
        The new filename will include the category and a timestamp for uniqueness and clarity.
        Returns a tuple (success, result) where result is the summary or error message.
        """
        try:
            if not os.path.exists(file_path):
                logger.warning(f"File not found: {file_path}")
                return False, "File not found"
            filename = os.path.basename(file_path)
            category = self.get_file_category(file_path)
            name, ext = os.path.splitext(filename)
            # Clean the original name - keep only meaningful parts
            # Split by common separators
            name_parts = name.replace('_', ' ').replace('-', ' ').split()
            cleaned_parts = []
            for part in name_parts:
                # Skip parts that look like UUIDs, hashes, or random strings
                if (
                    # Skip long hexadecimal-like strings and UUIDs
                    not (len(part) >= 8 and all(c.isalnum() for c in part)) and
                    # Skip date-like numbers
                    not part.replace('_','').isdigit() and
                    # Skip random short hex strings
                    not (len(part) >= 4 and all(c in '0123456789abcdefABCDEF' for c in part))
                ):
                    cleaned_parts.append(part.lower())
            
            # If we removed all parts, keep just the first part of original name
            if not cleaned_parts:
                cleaned_parts = [name.split('_')[0]]
                
            # Join the cleaned parts
            clean_name = '_'.join(cleaned_parts)
            # Smart rename: just category + cleaned name
            smart_name = f"{category}_{clean_name}{ext}"
            sanitized_name = self.sanitize_filename(smart_name)
            logger.info(f"Organizing file: {filename} -> Category: {category}")
            category_path = os.path.join(DOWNLOADS_PATH, category)
            os.makedirs(category_path, exist_ok=True)
            new_file_path = os.path.join(category_path, sanitized_name)
            counter = 1
            # If file exists, add a counter
            while os.path.exists(new_file_path):
                smart_name = f"{category}_{clean_name}_{counter}{ext}"
                sanitized_name = self.sanitize_filename(smart_name)
                new_file_path = os.path.join(category_path, sanitized_name)
                counter += 1
            try:
                shutil.move(file_path, new_file_path)
                if not os.path.exists(new_file_path):
                    logger.error("File move failed - destination file not found")
                    return False, "File move failed"
            except Exception as move_err:
                logger.error(f"Error moving file: {move_err}")
                return False, f"Error moving file: {move_err}"
            ai_description = self.generate_ai_description(
                new_file_path, "organized and renamed", filename, os.path.basename(new_file_path)
            )
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
        """
        Recursively organize all files in the downloads folder and its subfolders.
        Returns lists of organized files and errors.
        """
        organized_files = []
        errors = []
        logger.info(f"Starting organization of files in: {DOWNLOADS_PATH}")
        if not os.path.exists(DOWNLOADS_PATH):
            logger.error(f"Downloads path does not exist: {DOWNLOADS_PATH}")
            return organized_files, [f"Downloads path does not exist: {DOWNLOADS_PATH}"]
        try:
            for root, dirs, files in os.walk(DOWNLOADS_PATH):
                # Skip the category folders we created
                if root == DOWNLOADS_PATH or not any(root.startswith(os.path.join(DOWNLOADS_PATH, category)) for category in FILE_CATEGORIES.keys()):
                    for file in files:
                        if file != 'organization_summary.json':
                            item_path = os.path.join(root, file)
                            success, result = self.organize_file(item_path)
                            if success:
                                organized_files.append(result)
                            else:
                                errors.append(f"Error with {file}: {result}")
        except Exception as e:
            errors.append(f"Error listing directory contents: {e}")
        logger.info(f"Organization complete. Organized: {len(organized_files)}, Errors: {len(errors)}")
        return organized_files, errors

    def get_summary(self, limit=None):
        """
        Get the organization summary, most recent first. Optionally limit the number of entries.
        """
        summary_data = self.summary.copy()
        summary_data.reverse()
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
        logger.info("Organization request received")
        organized, errors = organizer.organize_all_files()
        
        response_data = {
            'success': True,
            'organized_count': len(organized),
            'organized_files': organized,
            'errors': errors
        }
        
        logger.info(f"Organization response: {len(organized)} files organized, {len(errors)} errors")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error in organize_files endpoint: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/organize/<filename>', methods=['POST'])
def organize_single_file(filename):
    """Organize a specific file"""
    try:
        file_path = os.path.join(DOWNLOADS_PATH, filename)
        logger.info(f"Single file organization request for: {filename}")
        success, result = organizer.organize_file(file_path)
        
        if success:
            return jsonify({'success': True, 'result': result})
        else:
            return jsonify({'success': False, 'error': result}), 400
    except Exception as e:
        logger.error(f"Error in organize_single_file endpoint: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/files')
def list_files():
    """List all files in downloads folder"""
    try:
        files = []
        
        if not os.path.exists(DOWNLOADS_PATH):
            return jsonify({'files': [], 'error': f'Downloads folder not found: {DOWNLOADS_PATH}'})
            
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
        
        logger.info(f"Listed {len(files)} files from downloads folder")
        return jsonify({'files': files})
        
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/summary')
def get_summary():
    """Get organization summary"""
    try:
        limit = request.args.get('limit', type=int)
        summary = organizer.get_summary(limit)
        return jsonify({'summary': summary})
    except Exception as e:
        logger.error(f"Error getting summary: {e}")
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
        if os.path.exists(DOWNLOADS_PATH):
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
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': str(e)}), 500

# Debug endpoint to check paths and permissions
@app.route('/debug')
def debug_info():
    """Debug endpoint to check paths and permissions"""
    try:
        debug_data = {
            'downloads_path': DOWNLOADS_PATH,
            'downloads_exists': os.path.exists(DOWNLOADS_PATH),
            'downloads_is_dir': os.path.isdir(DOWNLOADS_PATH) if os.path.exists(DOWNLOADS_PATH) else False,
            'downloads_writable': os.access(DOWNLOADS_PATH, os.W_OK) if os.path.exists(DOWNLOADS_PATH) else False,
            'current_working_dir': os.getcwd(),
            'environment_downloads_path': os.getenv('DOWNLOADS_PATH'),
            'summary_file': SUMMARY_FILE,
            'gemini_configured': model is not None
        }
        
        if os.path.exists(DOWNLOADS_PATH):
            try:
                items = os.listdir(DOWNLOADS_PATH)
                debug_data['downloads_contents'] = items[:10]  # First 10 items
                debug_data['downloads_item_count'] = len(items)
            except Exception as e:
                debug_data['downloads_list_error'] = str(e)
        
        return jsonify(debug_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Ensure downloads directory exists
    logger.info(f"Ensuring downloads directory exists: {DOWNLOADS_PATH}")
    os.makedirs(DOWNLOADS_PATH, exist_ok=True)
    
    # Create category folders
    for category in FILE_CATEGORIES.keys():
        category_path = os.path.join(DOWNLOADS_PATH, category)
        os.makedirs(category_path, exist_ok=True)
        logger.info(f"Created category folder: {category_path}")
    
    logger.info("Starting Flask application...")
    app.run(host='0.0.0.0', port=5000, debug=True)