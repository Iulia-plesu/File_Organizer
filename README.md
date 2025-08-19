# File Organizer

## 🚀 Overview
File Organizer is an intelligent file management system designed to bring order to your cluttered downloads folder. This Python-based application leverages AI technology to automatically analyze, categorize, and organize your files while maintaining meaningful file names.

### What It Does
The application continuously monitors your downloads folder, automatically sorting files into appropriate category folders (like images, documents, archives, etc.). It intelligently cleans up file names by removing random strings, timestamps, and UUIDs while preserving the meaningful parts of the name. For example, a file named "document_report_abc123def_20250819.pdf" becomes simply "document_report.pdf".

### Key Benefits
- **Automated Organization**: No more manual sorting of files
- **Clean Naming**: Files are renamed intelligently while preserving important information
- **Visual Management**: Web-based dashboard for easy file management
- **AI Integration**: Uses Gemini AI for smart file descriptions and categorization
- **History Tracking**: Maintains a detailed log of all file operations

## ✨ Features
- **Automatic File Organization:** Instantly sort files into category folders (images, documents, videos, etc.)
- **Smart File Renaming:** Cleans up file names by removing random strings, UUIDs, and timestamps while preserving meaningful words
- **AI-Powered Descriptions:** Get concise, meaningful summaries of each file operation using Gemini AI
- **Modern Web Dashboard:** View stats, organize files, and see recent activity in a beautiful interface
- **Full History:** Every operation is logged for transparency and review
- **Recursive Organization:** Handles files in nested folders while maintaining proper categorization

## 🖥️ How to Run Locally
1. Make sure you have Python 3.11+ installed
2. Create and activate a virtual environment:
   ```powershell
   # Create a new virtual environment
   python -m venv venv
   
   # Activate the virtual environment
   .\venv\Scripts\Activate
   
   # You should see (venv) in your terminal prompt
   ```
3. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
3. Set your environment variables (or use a `.env` file):
   ```powershell
   $env:DOWNLOADS_PATH = "C:/Users/Plesu/Documents/File_Organizer/downloads/"
   $env:GEMINI_API_KEY = "your-gemini-api-key"
   python app.py
   ```
   Or create a `.env` file:
   ```
   DOWNLOADS_PATH=C:/Users/Plesu/Documents/File_Organizer/downloads/
   GEMINI_API_KEY=your-gemini-api-key
   ```

## � File Organization and Naming
The File Organizer uses a smart naming convention that:
- Organizes files into category-based folders (images, documents, archives, etc.)
- Cleans up file names by:
  - Removing random strings and UUIDs (e.g., "3d0c1bda-5cee-4dca")
  - Eliminating timestamps and date strings
  - Preserving meaningful words and descriptions
  - Converting to lowercase for consistency
- Handles duplicate files by adding a counter (e.g., "document_report_1.pdf")

Example transformations:
```
Before: archives_validate_3d0c1bda_5cee_4dca_9834_20250819.zip
After:  archives_validate.zip

Before: images_peter-herrmann-gDLbqHXRIe8-unsplash_20250819_132529.jpg
After:  images_peter_herrmann_unsplash.jpg
```

## �🛠️ Troubleshooting
- If you see 0 files, make sure your local `downloads` folder has files
- Ensure the `DOWNLOADS_PATH` environment variable matches your actual folder path
- For any issues, check the logs in the terminal for errors
- If files aren't being renamed as expected, make sure they're not already in a category folder

## ⚙️ Environment Variables
- `DOWNLOADS_PATH`: Path to your downloads folder
- `GEMINI_API_KEY`: Your Gemini API key for AI features
