"""YouTube client for posting GANGLIA content.

This module provides functionality for:
- Uploading videos to YouTube using the YouTube Data API
- Handling authentication and session management
- Managing video metadata and privacy settings
- Error handling and retries
"""

import os
import re
import json
import subprocess
import datetime

from dataclasses import dataclass
from typing import Optional, Dict, Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from logger import Logger
from utils import exponential_backoff

# If modifying scopes, delete the token file.
SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.readonly'
]

# Get paths from environment or use defaults in ~/.config/ganglia
TOKEN_FILE = os.getenv(
    'YOUTUBE_TOKEN_FILE',
    os.path.expanduser('~/.config/ganglia/youtube_token.json')
)
CREDENTIALS_FILE = os.getenv(
    'YOUTUBE_CREDENTIALS_FILE',
    os.path.expanduser('~/.config/ganglia/youtube_credentials.json')
)

# Ensure config directory exists
os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
os.makedirs(os.path.dirname(CREDENTIALS_FILE), exist_ok=True)

@dataclass
class VideoUploadResult:
    """Result of a video upload attempt."""
    success: bool
    video_id: Optional[str] = None
    error: Optional[str] = None

class YouTubeClient:
    """Client for uploading content to YouTube using the YouTube Data API."""

    API_SERVICE_NAME = "youtube"
    API_VERSION = "v3"

    def __init__(self):
        """Initialize YouTube client with OAuth authentication."""
        self.credentials = self._get_credentials()
        self.youtube: Resource = build(
            self.API_SERVICE_NAME,
            self.API_VERSION,
            credentials=self.credentials
        )

    def _get_credentials(self) -> Credentials:
        """Get OAuth credentials.

        Returns:
            Credentials: OAuth credentials
        """
        credentials = None

        # Load existing token if it exists
        if os.path.exists(TOKEN_FILE):
            try:
                credentials = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
                Logger.print_info(f"[DEBUG] YouTube token file found at {TOKEN_FILE}")
                return credentials
            except Exception as e:
                Logger.print_error(f"Failed to load existing credentials: {e}")

        # If no valid credentials available, let the user login
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                try:
                    credentials.refresh(Request())
                    Logger.print_info("Refreshed YouTube credentials")
                except Exception as e:
                    Logger.print_error(f"Failed to refresh credentials: {e}")
                    credentials = None

            if not credentials:
                if not os.path.exists(CREDENTIALS_FILE):
                    raise FileNotFoundError(
                        f"No valid YouTube token found at {TOKEN_FILE} and no credentials file at {CREDENTIALS_FILE}. "
                        "Please either provide a valid token or download the OAuth client configuration from the "
                        "Google Cloud Console and save it to this location."
                    )

                # Run the OAuth flow
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE,
                    SCOPES,
                    redirect_uri='http://localhost:8090'
                )

                Logger.print_info(
                    "No valid YouTube credentials found. Opening browser for authentication..."
                )
                credentials = flow.run_local_server(
                    port=8090,
                    access_type='offline',
                    prompt='consent'
                )
                Logger.print_info("Successfully authenticated with YouTube")

                # Save the credentials for future use
                with open(TOKEN_FILE, 'w', encoding='utf-8') as token:
                    token.write(credentials.to_json())
                Logger.print_info(f"Saved credentials to {TOKEN_FILE}")

        return credentials

    def upload_video(
        self,
        video_path: str,
        title: str,
        description: Optional[str] = None,
        privacy_status: str = "public",  # Default to public
        tags: Optional[list] = None
    ) -> VideoUploadResult:
        """Upload a video to YouTube.

        Args:
            video_path: Path to the video file
            title: Title of the video
            description: Optional video description
            privacy_status: Privacy status ('private', 'unlisted', or 'public')
            tags: Optional list of video tags

        Returns:
            VideoUploadResult: Result of the upload attempt
        """
        if not os.path.exists(video_path):
            return VideoUploadResult(
                success=False,
                error=f"Video file not found: {video_path}"
            )

        def attempt_upload():
            try:
                Logger.print_info(f"Uploading video to YouTube: {video_path}")

                body = {
                    'snippet': {
                        'title': title,
                        'description': description or '',
                        'tags': tags or [],
                        'categoryId': '22'  # People & Blogs
                    },
                    'status': {
                        'privacyStatus': privacy_status,
                        'selfDeclaredMadeForKids': False
                    }
                }

                # Create MediaFileUpload object
                media = MediaFileUpload(
                    video_path,
                    mimetype='video/*',
                    resumable=True
                )

                # Call the API to insert the video
                # pylint: disable=no-member
                request = self.youtube.videos().insert(
                    part=','.join(body.keys()),
                    body=body,
                    media_body=media
                )

                response = None
                while response is None:
                    status, response = request.next_chunk()
                    if status:
                        Logger.print_info(f"Upload progress: {int(status.progress() * 100)}%")

                video_id = response['id']
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                Logger.print_info(f"Successfully uploaded video to YouTube: {video_url}")
                return VideoUploadResult(success=True, video_id=video_id)

            except HttpError as e:
                error_msg = f"HTTP error occurred: {e.resp.status} {e.content}"
                Logger.print_error(error_msg)
                return VideoUploadResult(success=False, error=error_msg)

            except Exception as e:
                error_msg = f"An error occurred: {str(e)}"
                Logger.print_error(error_msg)
                return VideoUploadResult(success=False, error=error_msg)

        # Try uploading with exponential backoff
        result = exponential_backoff(
            attempt_upload,
            max_retries=3,
            initial_delay=1.0
        )

        return result if result else VideoUploadResult(
            success=False,
            error="Failed after retries"
        )

    def get_video_status(self, video_id: str) -> Dict[str, Any]:
        """Get the status of a video.

        Args:
            video_id: The ID of the video

        Returns:
            dict: Video status information
        """
        try:
            # pylint: disable=no-member
            request = self.youtube.videos().list(
                part="status,snippet",
                id=video_id
            )
            response = request.execute()

            if response['items']:
                return response['items'][0]
            return {}

        except Exception as e:
            Logger.print_error(f"Failed to get video status: {str(e)}")
            return {}

    def create_video_post(
        self,
        title: str,
        video_path: str,
        additional_info: Optional[Dict[str, Any]] = None,
        config_path: Optional[str] = None
    ) -> str:
        """Create and upload a video post to YouTube with rich metadata.

        Args:
            title: Title of the video
            video_path: Path to the video file to upload
            additional_info: Optional dictionary of additional information
            config_path: Optional path to configuration file

        Returns:
            str: URL of uploaded video, or empty string if upload failed
        """
        if not os.path.exists(video_path):
            Logger.print_info("Skipping YouTube upload: Video file not found")
            return ""

        try:
            Logger.print_info("Attempting to upload video to YouTube...")

            def sanitize_text(text: str, max_length: int = 5000) -> str:
                """Sanitize text for YouTube description."""
                # Remove ANSI escape codes
                text = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)
                # Keep only printable ASCII characters
                text = ''.join(char for char in text if char.isprintable() or char in '\n\t')
                # Truncate if too long
                if len(text) > max_length:
                    text = text[:max_length-3] + "..."
                return text

            # Get description from git
            def get_git_description() -> str:
                """Get description from either PR or latest commit."""
                try:
                    # Try to get PR description first
                    result = subprocess.run(
                        ["gh", "pr", "view", "--json", "title,body"],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        pr_info = json.loads(result.stdout)
                        return f"{pr_info['title']}\n\n{pr_info['body']}"
                except Exception:
                    pass  # Fall back to commit message

                try:
                    # Get the most recent commit message
                    result = subprocess.run(
                        ["git", "log", "-1", "--pretty=%B"],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        return result.stdout.strip()
                except Exception:
                    pass

                return "No description available"

            description = get_git_description()

            # Add project information
            project_info = [
                "",
                "🌟 About GANGLIA",
                "GANGLIA is an open-source project that automates the creation of engaging social media content.",
                "It uses AI to generate and synchronize video, audio, and captions for a seamless storytelling experience.",
                "",
                "🔗 Project Links",
                "- GitHub: https://github.com/ScienceIsNeato/ganglia",
                ""
            ]

            # Add config information if provided
            config_info = []
            if config_path and os.path.exists(config_path):
                try:
                    with open(config_path, encoding='utf-8') as f:
                        config = json.loads(f.read())
                        config_info = [
                            "",
                            "📝 Configuration Used",
                            "```json",
                            json.dumps(config, indent=2),
                            "```",
                            ""
                        ]
                except Exception as e:
                    Logger.print_error(f"Failed to read config file: {e}")

            # Add metadata at the end
            metadata_lines = [
                "",
                "🔍 Information",
                f"Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ]

            if additional_info:
                metadata_lines.extend([
                    "",
                    "💻 Additional Information",
                    "```json",
                    json.dumps(additional_info, indent=2),
                    "```"
                ])

            # Combine all sections and sanitize
            full_description = description + "\n" + "\n".join(project_info + config_info + metadata_lines)
            sanitized_description = sanitize_text(full_description)

            # Upload to YouTube
            result = self.upload_video(
                video_path,
                title=title,
                description=sanitized_description,
                privacy_status="public",  # Make videos public for community feedback
                tags=["ganglia", "ai", "video-generation", "python"]
            )

            if not result.success:
                raise RuntimeError(f"Failed to upload video: {result.error}")

            return f"https://www.youtube.com/watch?v={result.video_id}"
        except Exception as e:
            Logger.print_error(f"Failed to create video post: {e}")
            return ""
