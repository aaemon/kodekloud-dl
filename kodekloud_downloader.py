#!/usr/bin/env python3
# /// script
# dependencies = [
#     "requests",
#     "beautifulsoup4",
#     "tqdm",
#     "markdownify",
# ]
# ///

import os
import requests
import json
import re
from datetime import datetime
from tqdm import tqdm
from urllib.parse import urljoin, unquote
from bs4 import BeautifulSoup
from markdownify import markdownify as md

# Configuration
COOKIES_FILE = 'cookie.txt'
PROGRESS_FILE = 'progress.json'
BASE_URL = 'https://kodekloud.com'
API_BASE = 'https://learn-api.kodekloud.com/api'
LEARN_BASE = 'https://learn.kodekloud.com'
DOWNLOAD_DIR = 'Downloads'

class KodeKloudDownloader:
    def __init__(self, cookie_file):
        self.cookie_file = cookie_file
        self.session = requests.Session()
        self.token = None
        self.progress = self._load_progress()
        
        if self.cookie_file and os.path.exists(self.cookie_file):
             self.token = self._load_cookies()
        
        # Set headers for API validity
        if self.token:
            self.session.headers.update({'Authorization': f'Bearer {self.token}'})
            print(f"Loaded session token: {self.token[:10]}...")
            
        # Common headers for browser emulation
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': BASE_URL
        })

    def _load_cookies(self):
        """Loads cookies from Netscape file into session and extracts Bearer token."""
        if not os.path.exists(self.cookie_file):
            print(f"Error: Cookie file '{self.cookie_file}' not found.")
            return None
        
        session_token = None
        try:
            with open(self.cookie_file, 'r') as f:
                for line in f:
                    if line.startswith('#') or not line.strip():
                        continue
                    
                    parts = line.strip().split('\t')
                    if len(parts) >= 7:
                        domain, flag, path, secure, expiration, name, value = parts
                        self.session.cookies.set(name, value, domain=domain, path=path)
                        
                        if name == 'session-cookie':
                            session_token = value
                            
        except Exception as e:
            print(f"Error parsing cookie file: {e}")
            
        return session_token

    def _load_progress(self):
        """Load download progress from JSON file."""
        if os.path.exists(PROGRESS_FILE):
            try:
                with open(PROGRESS_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load progress file: {e}")
        return {"last_updated": None, "courses": {}}
    
    def _save_progress(self):
        """Save download progress to JSON file."""
        try:
            self.progress["last_updated"] = datetime.utcnow().isoformat() + "Z"
            with open(PROGRESS_FILE, 'w') as f:
                json.dump(self.progress, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save progress: {e}")
    
    def _is_lesson_completed(self, course_slug, module_id, lesson_id):
        """Check if a lesson has been completed."""
        course_data = self.progress.get("courses", {}).get(course_slug, {})
        completed_lessons = course_data.get("completed_lessons", {}).get(str(module_id), [])
        return str(lesson_id) in completed_lessons
    
    def _mark_lesson_completed(self, course_slug, course_title, module_id, lesson_id):
        """Mark a lesson as completed in progress tracking."""
        if "courses" not in self.progress:
            self.progress["courses"] = {}
        
        if course_slug not in self.progress["courses"]:
            self.progress["courses"][course_slug] = {
                "title": course_title,
                "completed_modules": [],
                "completed_lessons": {}
            }
        
        course_data = self.progress["courses"][course_slug]
        module_id_str = str(module_id)
        
        if module_id_str not in course_data["completed_lessons"]:
            course_data["completed_lessons"][module_id_str] = []
        
        if str(lesson_id) not in course_data["completed_lessons"][module_id_str]:
            course_data["completed_lessons"][module_id_str].append(str(lesson_id))
        
        self._save_progress()

    def sanitize_filename(self, name):
        return re.sub(r'[\\/*?:"<>|]', "", name).strip()

    def get_all_courses(self):
        """Fetches all courses from the public API."""
        print("Fetching course list...")
        courses = []
        page = 1
        limit = 50
        
        while True:
            try:
                url = f"{API_BASE}/courses?page={page}&limit={limit}"
                response = self.session.get(url)
                if response.status_code != 200:
                    print(f"Failed to fetch courses page {page} (Status: {response.status_code})")
                    break
                
                data = response.json()
                page_courses = data.get('courses', [])
                if not page_courses:
                    break
                
                courses.extend(page_courses)
                
                metadata = data.get('metadata', {})
                if not metadata.get('next_page'):
                    break
                page = metadata['next_page']
                
            except Exception as e:
                print(f"Error fetching courses: {e}")
                break
                
        return courses

    def get_course_details(self, slug):
        """Fetches detailed course structure including modules and lessons."""
        print(f"Fetching details for: {slug}...")
        try:
            url = f"{API_BASE}/courses/{slug}"
            response = self.session.get(url)
            if response.status_code != 200:
                print(f"Failed to fetch course details (Status: {response.status_code})")
                return None
            return response.json()
        except Exception as e:
            print(f"Error fetching course details: {e}")
            return None

    def download_lesson(self, lesson, course_slug, course_title, module_id, output_dir, course_id):
        """Downloads a single lesson content using API and converting to Markdown."""
        lesson_title = lesson.get('title', 'Unknown Lesson')
        lesson_id = lesson.get('id')
        lesson_type = lesson.get('type')

        # Flattened structure: Save directly to output_dir (which is the Module folder)
        target_dir = output_dir 
        # No new directory for lesson
        
        # Sanitize lesson title for filename
        safe_lesson_title = self.sanitize_filename(lesson_title)
        md_filename = f"{safe_lesson_title}.md"
        md_path = os.path.join(target_dir, md_filename)
        
        # Check if file already exists on disk (primary check)
        if os.path.exists(md_path):
            print(f"  Skipping (file exists): {lesson_title}")
            # Mark as completed if not already marked
            if not self._is_lesson_completed(course_slug, module_id, lesson_id):
                self._mark_lesson_completed(course_slug, course_title, module_id, lesson_id)
            return
        
        # If file doesn't exist but marked as completed in progress, re-download it
        if self._is_lesson_completed(course_slug, module_id, lesson_id):
            print(f"  Re-downloading (file missing): {lesson_title}")

        print(f"  Downloading: {lesson_title} ({lesson_type})")

        try:
             # Fetch from API
            url = f"{API_BASE}/lessons/{lesson_id}?course_id={course_id}"
            response = self.session.get(url)
            
            if response.status_code != 200:
                print(f"  Failed to fetch lesson data (Status: {response.status_code})")
                return

            data = response.json()
            content_raw = data.get('content', '')
            video_url = data.get('video_url')
            
            if content_raw:
                # Detect if content is HTML
                is_html = bool(BeautifulSoup(content_raw, "html.parser").find())
                
                if is_html:
                    markdown_content = md(content_raw, heading_style="ATX")
                    soup = BeautifulSoup(content_raw, 'html.parser')
                    # Download HTML Images
                    images = soup.find_all('img')
                    image_map = {}
                    
                    for img in images:
                        src = img.get('src')
                        if src:
                            if not src.startswith('http'):
                                src = urljoin(BASE_URL, src)
                            
                            img_name = self.sanitize_filename(os.path.basename(unquote(src.split('?')[0])))
                            if img_name in image_map.values():
                                 base, ext = os.path.splitext(img_name)
                                 img_name = f"{base}_{len(image_map)}{ext}"

                            self._download_file(src, os.path.join(target_dir, img_name))
                            image_map[src] = img_name
                    
                    final_content = markdown_content
                else:
                    # Already Markdown or Text
                    final_content = content_raw

                # Handle Markdown images (in both cases: either from original MD or leftover/converted)
                md_image_pattern = re.compile(r'!\[(.*?)\]\((.*?)\)')
                
                def replace_image(match):
                    alt_text = match.group(1)
                    img_url = match.group(2)
                    
                    # Be careful with escaped characters if coming from markdownify
                    # But if we skipped markdownify for MD input, it should be clean.
                    # If markdownify ran, it might have escaped underscores in URLs.
                    # We might need to unescape or handle it. 
                    # For now, let's assume if it was HTML, the img tags were handled above?
                    # markdownify converts <img> to ![](). 
                    # If we downloaded via <img> tags, we still need to fix the link in the MD.
                    # But markdownify doesn't know the local filename.
                    
                    # Better approach:
                    # If HTML, we rely on markdownify's output and regex-replace it.
                    # AND we must unescape the URL if markdownify escaped it.
                    
                    clean_url = img_url.replace(r'\_', '_').replace(r'\*', '*')
                    
                    if not clean_url.startswith('http'):
                         # It might be a local path if markdownify kept it? 
                         # Or absolute URL.
                         if not clean_url.startswith('/') and '://' not in clean_url:
                             # Relative?
                             clean_url = urljoin(BASE_URL, clean_url)
                    
                    if not clean_url.startswith('http'):
                        return match.group(0)

                    img_name = self.sanitize_filename(os.path.basename(unquote(clean_url.split('?')[0])))
                    self._download_file(clean_url, os.path.join(target_dir, img_name))
                    
                    return f'![{alt_text}]({img_name})'
                
                final_content = md_image_pattern.sub(replace_image, final_content)

                with open(md_path, 'w', encoding='utf-8') as f:
                    f.write(f"# {lesson_title}\n\n")
                    f.write(final_content)
                
                # Mark lesson as completed
                self._mark_lesson_completed(course_slug, course_title, module_id, lesson_id)
                
                # Download PDFs (from soup of original content if HTML)
                if is_html:
                    pdf_links = soup.find_all('a', href=re.compile(r'\.pdf$', re.I))
                    for link in pdf_links:
                        pdf_url = link['href']
                        if not pdf_url.startswith('http'):
                            pdf_url = urljoin(BASE_URL, pdf_url)
                        
                        pdf_name = os.path.basename(unquote(pdf_url))
                        self._download_file(pdf_url, os.path.join(target_dir, pdf_name))
                else:
                    # Markdown PDF links: [text](url.pdf) or just url.pdf
                    # Regex for [text](url.pdf)
                    md_pdf_pattern = re.compile(r'\[.*?\]\((.*?\.pdf)\)', re.I)
                    matches = md_pdf_pattern.findall(content_raw)
                    for pdf_url in matches:
                        if not pdf_url.startswith('http'):
                            pdf_url = urljoin(BASE_URL, pdf_url)
                        
                        pdf_name = os.path.basename(unquote(pdf_url))
                        self._download_file(pdf_url, os.path.join(target_dir, pdf_name))
            
            else:
                 if lesson_type == 'video':
                     # Create a file for the video URL
                     pass

        except Exception as e:
            print(f"  Error processing lesson: {e}")

    def get_course_id_from_details(self, slug):
        # We need to fetch it or store it. 
        # For efficiency, we should pass it from main.
        # But for valid code here, let's just fetch or rely on caller passing it.
        # I'll update the signature to accept course_id
        return None

    def _download_file(self, url, path):
        if os.path.exists(path):
            print(f"    Skipping (exists): {os.path.basename(path)}")
            return 
            
        print(f"  Downloading: {os.path.basename(path)}")
        try:
            with self.session.get(url, stream=True) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                with open(path, 'wb') as f, tqdm(
                    total=total_size, unit='iB', unit_scale=True, unit_divisor=1024, leave=False
                ) as bar:
                    for chunk in r.iter_content(chunk_size=8192):
                        size = f.write(chunk)
                        bar.update(size)
        except Exception as e:
             print(f"  Failed to download file: {e}")


def parse_selection_input(input_str, max_value):
    """Parse user input like '1-10, 15, 16-19' into a list of indices.
    
    Args:
        input_str: User input string with ranges and comma-separated values
        max_value: Maximum valid index (1-based)
    
    Returns:
        List of valid indices (0-based) or None if invalid
    """
    if not input_str or not input_str.strip():
        return None
    
    indices = set()
    parts = input_str.split(',')
    
    try:
        for part in parts:
            part = part.strip()
            if '-' in part:
                # Range like "1-10"
                start, end = part.split('-', 1)
                start, end = int(start.strip()), int(end.strip())
                if start < 1 or end > max_value or start > end:
                    print(f"Invalid range: {part} (valid: 1-{max_value})")
                    return None
                indices.update(range(start - 1, end))  # Convert to 0-based
            else:
                # Single number
                num = int(part)
                if num < 1 or num > max_value:
                    print(f"Invalid number: {num} (valid: 1-{max_value})")
                    return None
                indices.add(num - 1)  # Convert to 0-based
        
        return sorted(list(indices))
    except ValueError:
        print(f"Invalid input format. Use numbers, ranges (1-10), and commas (1,2,3)")
        return None


def main():
    print("KodeKloud Downloader v2.3 (HTML to Markdown)")
    
    # Check for cookie file or prompt for token
    cookie_path = 'cookie.txt'
    token = None
    
    if os.path.exists(cookie_path):
        print(f"Found '{cookie_path}'. Loading...")
        downloader = KodeKloudDownloader(cookie_path)
    else:
        print(f"'{cookie_path}' not found.")
        token_input = input("Enter your Session Cookie (token) OR path to cookie file: ").strip()
        if os.path.isfile(token_input):
            downloader = KodeKloudDownloader(token_input)
        else:
            # Assume it's a raw token string
            # We need to initialize downloader with dummy file or None and set token manually
            # But the class expects a file. Let's modify the class slightly or mock it.
            # Easier: Just pass None and set the token/cookie.
            downloader = KodeKloudDownloader(None)
            downloader.token = token_input
            downloader.session.cookies.set('session-cookie', token_input)
            downloader.session.headers.update({'Authorization': f'Bearer {token_input}'})
            
    if not downloader.token:
        print("No valid token/cookie provided. Exiting.")
        return

    print("Fetching course list...")
    courses = downloader.get_all_courses()
    if not courses:
        print("No courses found.")
        return

    print(f"\nFound {len(courses)} courses.")
    
    # Always show all courses (no search prompt)
    filtered_courses = courses

    print(f"\n0. Download All Courses ({len(filtered_courses)} courses)")
    for i, c in enumerate(filtered_courses):
        print(f"{i+1}. {c['title']}")
        
    try:
        choice_str = input("\nEnter course number(s) (e.g., '1-10, 15, 16-19' or '0' for All): ").strip()
        
        courses_to_process = []
        if choice_str == '0':
            courses_to_process = filtered_courses
        else:
            # Parse range/comma-separated input
            selected_indices = parse_selection_input(choice_str, len(filtered_courses))
            if selected_indices is None:
                print("Invalid selection.")
                return
            courses_to_process = [filtered_courses[i] for i in selected_indices]
        
        if not courses_to_process:
             print("Invalid selection.")
             return

        for selected in courses_to_process:
            print(f"\n{'='*60}")
            print(f"Processing Course: {selected['title']}")
            print(f"{'='*60}")
            
            details = downloader.get_course_details(selected['slug'])
            if not details:
                continue

            modules = details.get('modules', [])
            course_slug = selected['slug']
            course_title = selected['title']
            
            # Always show all modules (no search prompt)
            modules_to_dl = []
            if len(courses_to_process) > 1:
                # Automatic "All Modules" for bulk course download
                print(f"  Auto-selecting all {len(modules)} modules...")
                modules_to_dl = [(i+1, m) for i, m in enumerate(modules)]
            else:
                # Single course selection - Show all modules and prompt
                print("\nModules:")
                for i, m in enumerate(modules):
                    print(f"  {i+1}. {m['title']} ({m.get('lessons_count', 0)} lessons)")
                    
                mod_choice = input("\nEnter module number (or 'A' for All): ").strip().upper()
                
                if mod_choice == 'A':
                    modules_to_dl = [(i+1, m) for i, m in enumerate(modules)]
                elif mod_choice.isdigit():
                    idx = int(mod_choice) - 1
                    if 0 <= idx < len(modules):
                        modules_to_dl = [(idx+1, modules[idx])]

            if not modules_to_dl:
                continue
            
            # Output Directory
            course_dir = os.path.join(DOWNLOAD_DIR, downloader.sanitize_filename(selected['title']))
            
            # 1. Create ALL module directories with serial numbers
            module_dir_map = {} # Map module_id to its created directory path
            for i, m in enumerate(modules):
                module_title = m.get('title', 'Unknown Module')
                module_dir_name = f"{i+1}. {downloader.sanitize_filename(module_title)}"
                module_path = os.path.join(course_dir, module_dir_name)
                os.makedirs(module_path, exist_ok=True)
                module_dir_map[m.get('id')] = module_path

            # 2. Process selected modules
            for idx, module in modules_to_dl:
                module_title = module.get('title', 'Unknown Module')
                module_id = module.get('id')
                # Use the pre-created path
                module_dir = module_dir_map.get(module_id)
                
                print(f"\n  Module: {os.path.basename(module_dir)}")
                
                lessons = module.get('lessons', [])
                for lesson in lessons:
                    course_id = details.get('id') # Available in details
                    downloader.download_lesson(lesson, course_slug, course_title, module_id, module_dir, course_id)
                    
        
        # Display summary
        print(f"\n{'='*60}")
        print("Download Summary")
        print(f"{'='*60}")
        print(f"User Input: {choice_str}")
        print(f"Total Courses Downloaded: {len(courses_to_process)}")
        print("\nCourses:")
        for idx, course in enumerate(courses_to_process, 1):
            # Find original index in filtered_courses
            original_idx = filtered_courses.index(course) + 1
            print(f"  {original_idx}. {course['title']}")
        print(f"\n{'='*60}")
        print("All downloads completed!")

    except ValueError:
        print("Invalid input.")
    except KeyboardInterrupt:
        print("\nAborted.")

if __name__ == "__main__":
    main()
